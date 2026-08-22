"""Orchestration: download → store → derive metrics → export JSON."""

import logging
from datetime import date

from cot.config import Config
from cot.download import fetch_year
from cot.export import (report_index_entry, write_index, write_report_years,
                        write_term_structure)
from cot.metrics import enrich
from cot.reports import REPORTS, ReportSpec
from cot.store import connect, ensure_table, ingest_file, read_report
from cot.termstructure import latest_curves, scrape_all

logger = logging.getLogger(__name__)


def run(config: Config, report_keys: list[str] | None = None,
        with_term_structure: bool = False, download: bool = True,
        today: date | None = None) -> None:
    """Build every configured report.

    Term structure is off by default: CME Group blocks automated access to its
    settlement endpoint and returns HTTP 403 with a scraping notice, so the
    scrape only runs when explicitly asked for.
    """
    today = today or date.today()
    specs = [REPORTS[key] for key in (report_keys or REPORTS)]

    conn = connect(config.database)
    try:
        for spec in specs:
            ensure_table(conn, spec)
            if download:
                _load_years(conn, spec, config, today)

        if with_term_structure:
            scrape_all(conn)

        entries = []
        for spec in specs:
            frame = read_report(conn, spec)
            frame = enrich(frame, spec)
            years = write_report_years(frame, spec, config.data_dir)
            entries.append(report_index_entry(spec, frame, years))

        write_term_structure(latest_curves(conn), config.data_dir)
        write_index(entries, config.data_dir)
    finally:
        conn.close()


def _load_years(conn, spec: ReportSpec, config: Config, today: date) -> None:
    first = max(spec.first_year, today.year - config.history_years + 1)
    for year in range(first, today.year + 1):
        path = fetch_year(spec, year, config.cache_dir)
        if path is None:
            continue
        rows = ingest_file(conn, spec, path)
        logger.info("%s %s: %d rows", spec.key, year, rows)
