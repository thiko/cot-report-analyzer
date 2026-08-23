"""Write the JSON the static site consumes.

Data is partitioned by report type and calendar year: only the current year's
file changes on a weekly run, which keeps the committed history small.

Within a file the layout is columnar — a list of dates, a list of markets, and
one date-by-market matrix per metric. Repeating a key like "managed_money_net"
for every market of every week would triple the file size, and the matrices
feed the site's charts directly.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from cot.markets import category_rank, price_sources
from cot.metrics import GAP_KEY, WINDOWS, gap_pair, metric_groups
from cot.reports import ReportSpec

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 3
GROUP_FIELDS = ["net", "chg", "long", "short", "spread", "pct_oi", *WINDOWS]


def write_report_years(frame: pd.DataFrame, spec: ReportSpec, data_dir: Path) -> list[int]:
    """Write one JSON file per calendar year. Returns the years written."""
    if frame.empty:
        logger.warning("No rows to export for %s", spec.key)
        return []

    target_dir = data_dir / spec.key
    target_dir.mkdir(parents=True, exist_ok=True)

    frame = frame.copy()
    frame["year"] = frame["report_date"].str.slice(0, 4).astype(int)
    group_keys = [g.key for g in spec.groups] + ([GAP_KEY] if gap_pair(spec) else [])

    years = []
    for year, year_frame in frame.groupby("year", sort=True):
        payload = _year_payload(spec, int(year), year_frame, group_keys)
        _write_json(target_dir / f"{year}.json", payload)
        years.append(int(year))

    return years


def _year_payload(spec: ReportSpec, year: int, frame: pd.DataFrame,
                  group_keys: list[str]) -> dict:
    dates = sorted(frame["report_date"].unique().tolist())
    markets = _market_order(frame)
    symbols = [m["symbol"] for m in markets]

    def matrix(column: str, as_float: bool = False) -> list[list]:
        return _matrix(frame, column, dates, symbols, as_float)

    return {
        "schema": SCHEMA_VERSION,
        "report": spec.key,
        "year": year,
        "dates": dates,
        "markets": markets,
        "fields": GROUP_FIELDS,
        "open_interest": matrix("open_interest"),
        "open_interest_change": matrix("open_interest_change"),
        "groups": {
            key: {
                field: matrix(f"{key}_{field}", as_float=(field == "pct_oi"))
                for field in GROUP_FIELDS
            }
            for key in group_keys
        },
    }


def _market_order(frame: pd.DataFrame) -> list[dict]:
    unique = frame.drop_duplicates(subset=["symbol"])[["symbol", "name", "category"]]
    records = unique.to_dict("records")
    records.sort(key=lambda m: (category_rank(m["category"]), m["name"]))
    return records


def _matrix(frame: pd.DataFrame, column: str, dates: list[str],
            symbols: list[str], as_float: bool) -> list[list]:
    if column not in frame.columns:
        return [[None] * len(symbols) for _ in dates]

    pivot = (frame.pivot_table(index="report_date", columns="symbol", values=column,
                               aggfunc="last", dropna=False)
             .reindex(index=dates, columns=symbols))
    convert = _float if as_float else _int
    return [[convert(value) for value in row] for row in pivot.to_numpy()]


def write_prices(closes: dict[str, list], dates: list[str], data_dir: Path) -> None:
    """Close per market as of every report date, in the same columnar shape as
    the report files: one date list, one row of closes per market.

    Each series carries where it came from and whether it is the benchmark the
    contract settles against or an ETF standing in for it. A proxy has its own
    fees, roll schedule and — for the international funds — currency exposure,
    so a return computed off it is not the contract's return. Shipping that
    unlabelled is what would mislead; shipping the label lets the interface say
    so.
    """
    sources = price_sources()
    _write_json(data_dir / "prices.json", {
        "schema": SCHEMA_VERSION,
        "dates": dates,
        "closes": closes,
        "sources": {
            symbol: {
                "provider": sources[symbol].provider,
                "series": sources[symbol].series,
                "kind": sources[symbol].kind,
            }
            for symbol in closes if symbol in sources
        },
    })


def write_term_structure(curves: dict, data_dir: Path) -> None:
    _write_json(data_dir / "term_structure.json",
                {"schema": SCHEMA_VERSION, "curves": curves})


def write_index(entries: list[dict], data_dir: Path) -> None:
    latest = max((e["latest_date"] for e in entries if e.get("latest_date")), default=None)
    _write_json(data_dir / "index.json", {
        "schema": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "latest_date": latest,
        "reports": entries,
    })


def report_index_entry(spec: ReportSpec, frame: pd.DataFrame, years: list[int]) -> dict:
    dates = sorted(frame["report_date"].unique().tolist()) if not frame.empty else []
    categories = []
    if not frame.empty:
        categories = sorted(frame["category"].unique().tolist(), key=category_rank)
    return {
        "key": spec.key,
        "label": spec.label,
        "short_label": spec.short_label,
        "description": spec.description,
        "description_de": spec.description_de,
        "universe": spec.universe,
        "groups": metric_groups(spec),
        "windows": list(WINDOWS),
        "fields": GROUP_FIELDS,
        "categories": categories,
        "years": years,
        "dates": dates,
        "latest_date": dates[-1] if dates else None,
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, separators=(",", ":"), allow_nan=False)
    path.write_text(text + "\n", encoding="utf-8")
    logger.info("Wrote %s (%.0f KB)", path, path.stat().st_size / 1024)


def _int(value) -> int | None:
    if value is None or value is pd.NA:
        return None
    try:
        if pd.isna(value):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _float(value) -> float | None:
    if value is None or value is pd.NA:
        return None
    try:
        if pd.isna(value):
            return None
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None
