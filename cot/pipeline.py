"""Orchestration: download → store → derive metrics → export JSON."""

import json
import logging
from datetime import date

from cot.config import Config
from cot.download import fetch_year
from cot.export import (report_index_entry, write_index, write_prices,
                        write_report_years, write_term_structure)
from cot.metrics import enrich
from cot.prices import update_all as update_prices, weekly_closes
from cot.reports import REPORTS, ReportSpec
from cot.store import connect, ensure_table, ingest_file, read_report
from cot.termstructure import latest_curves, scrape_all

logger = logging.getLogger(__name__)


def run(config: Config, report_keys: list[str] | None = None,
        with_term_structure: bool = False, with_prices: bool = False,
        force_prices: bool = False,
        download: bool = True, today: date | None = None) -> None:
    """Build every configured report.

    Both external feeds are off by default and for the same reason: CME Group
    answers automated settlement requests with HTTP 403 and a scraping notice,
    and the price feed answers shared address ranges with a standing 429. Each
    runs only when asked for, and neither can fail the build — see
    _update_prices.
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
        if with_prices:
            _update_prices(conn, config, today, force=force_prices)

        entries = []
        report_dates: set[str] = set()
        for spec in specs:
            frame = read_report(conn, spec)
            frame = enrich(frame, spec)
            years = write_report_years(frame, spec, config.data_dir)
            entry = report_index_entry(spec, frame, years)
            report_dates.update(entry["dates"])
            entries.append(entry)

        dates = sorted(report_dates)
        write_prices(weekly_closes(conn, dates), dates, config.data_dir)
        write_term_structure(latest_curves(conn), config.data_dir)
        write_index(entries, config.data_dir)
    finally:
        conn.close()


def run_prices_only(config: Config, today: date | None = None,
                    force: bool = False) -> None:
    """Refresh prices and rewrite prices.json, leaving the COT data untouched.

    Split out because the feed refuses shared CI address ranges outright, which
    makes the weekly runner the one place the price stage cannot work. This
    lets it run from a host that the feed does answer, against report dates the
    committed index already knows, and the result is committed like any other
    generated file.
    """
    today = today or date.today()
    index_path = config.data_dir / "index.json"
    if not index_path.exists():
        logger.error("%s is missing — build the reports before fetching prices",
                     index_path)
        return

    dates = sorted({d for entry in json.loads(index_path.read_text())["reports"]
                    for d in entry.get("dates", [])})
    conn = connect(config.database)
    try:
        _update_prices(conn, config, today, force=force)
        write_prices(weekly_closes(conn, dates), dates, config.data_dir)
    finally:
        conn.close()


def _update_prices(conn, config: Config, today: date, force: bool = False) -> None:
    """Refresh the price series, swallowing anything that goes wrong.

    The committed COT history is what this build exists to keep current. Prices
    are an enrichment on top of it, so a feed that is down, throttled or has
    changed shape gets logged and left behind rather than allowed to abort the
    run and skip the week.
    """
    start = date(today.year - config.history_years + 1, 1, 1)
    try:
        updated = update_prices(conn, start, today, api_key=config.api_key,
                                force=force)
        logger.info("Price series updated for %d markets", updated)
    except Exception:  # noqa: BLE001 - deliberately total
        logger.exception("Price update failed; continuing without fresh prices")


def _load_years(conn, spec: ReportSpec, config: Config, today: date) -> None:
    first = max(spec.first_year, today.year - config.history_years + 1)
    for year in range(first, today.year + 1):
        path = fetch_year(spec, year, config.cache_dir)
        if path is None:
            continue
        rows = ingest_file(conn, spec, path)
        logger.info("%s %s: %d rows", spec.key, year, rows)
