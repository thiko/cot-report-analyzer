"""SQLite storage for COT positions.

Every report type gets its own table with an identical, generic shape: one row
per (report date, contract) with a long/short/spread/change block per trader
group. Report-specific CFTC column names are mapped away at ingest time so
everything downstream can stay report-agnostic.
"""

import logging
import sqlite3
from pathlib import Path

import pandas as pd

from cot.download import normalize_column
from cot.markets import markets_for
from cot.reports import ReportSpec

logger = logging.getLogger(__name__)

BASE_COLUMNS = [
    ("report_date", "TEXT NOT NULL"),
    ("contract_code", "TEXT NOT NULL"),
    ("symbol", "TEXT NOT NULL"),
    ("name", "TEXT NOT NULL"),
    ("category", "TEXT NOT NULL"),
    ("market_name", "TEXT"),
    ("open_interest", "INTEGER"),
    ("open_interest_change", "INTEGER"),
]

GROUP_FIELDS = ["long", "short", "spread", "change_long", "change_short"]


def group_columns(spec: ReportSpec) -> list[str]:
    return [f"{group.key}_{field}" for group in spec.groups for field in GROUP_FIELDS]


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_table(conn: sqlite3.Connection, spec: ReportSpec) -> None:
    columns = [f"{name} {decl}" for name, decl in BASE_COLUMNS]
    columns += [f"{name} INTEGER" for name in group_columns(spec)]
    columns.append("PRIMARY KEY (report_date, contract_code)")
    conn.execute(f"CREATE TABLE IF NOT EXISTS {spec.table} (\n  " + ",\n  ".join(columns) + "\n)")
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{spec.table}_symbol_date "
        f"ON {spec.table} (symbol, report_date)"
    )
    conn.commit()


def ingest_file(conn: sqlite3.Connection, spec: ReportSpec, path: Path) -> int:
    """Load one annual CFTC file into the report's table. Returns rows written."""
    # Read everything as text: contract market codes such as "001602" are
    # numeric for some report types and alphanumeric ("0233A3") for others, and
    # type inference would silently strip the leading zeros.
    raw = pd.read_csv(path, low_memory=False, dtype=str)
    raw.columns = [normalize_column(c) for c in raw.columns]

    missing = [c for c in [spec.date_col, "CFTC_Contract_Market_Code"] if c not in raw.columns]
    if missing:
        logger.error("%s is missing columns %s — skipping", path.name, missing)
        return 0

    markets = markets_for(spec.universe)
    contract_codes = raw["CFTC_Contract_Market_Code"].astype(str).str.strip()
    subset = raw[contract_codes.isin(markets)].copy()
    if subset.empty:
        logger.warning("No whitelisted markets found in %s", path.name)
        return 0
    subset["contract_code"] = contract_codes[subset.index]

    frame = pd.DataFrame({
        "report_date": subset[spec.date_col].astype(str).str.strip(),
        "contract_code": subset["contract_code"],
        "symbol": subset["contract_code"].map(lambda c: markets[c].symbol),
        "name": subset["contract_code"].map(lambda c: markets[c].name),
        "category": subset["contract_code"].map(lambda c: markets[c].category),
        "market_name": subset.get("Market_and_Exchange_Names", pd.Series(dtype=str)),
        "open_interest": _numeric(subset, "Open_Interest_All"),
        "open_interest_change": _numeric(subset, spec.oi_change_col),
    })

    for group in spec.groups:
        source = {
            "long": group.long_col,
            "short": group.short_col,
            "spread": group.spread_col,
            "change_long": group.change_long_col,
            "change_short": group.change_short_col,
        }
        for field, column in source.items():
            frame[f"{group.key}_{field}"] = _numeric(subset, column)

    frame = frame.drop_duplicates(subset=["report_date", "contract_code"], keep="last")
    return _upsert(conn, spec, frame)


def _numeric(frame: pd.DataFrame, column: str | None) -> pd.Series:
    if not column or column not in frame.columns:
        return pd.Series([None] * len(frame), index=frame.index, dtype="object")
    values = pd.to_numeric(frame[column], errors="coerce")
    return values.astype("Int64")


def _upsert(conn: sqlite3.Connection, spec: ReportSpec, frame: pd.DataFrame) -> int:
    columns = [name for name, _ in BASE_COLUMNS] + group_columns(spec)
    placeholders = ", ".join("?" for _ in columns)
    updates = ", ".join(f"{c}=excluded.{c}" for c in columns if c not in ("report_date", "contract_code"))
    sql = (
        f"INSERT INTO {spec.table} ({', '.join(columns)}) VALUES ({placeholders}) "
        f"ON CONFLICT(report_date, contract_code) DO UPDATE SET {updates}"
    )
    rows = [tuple(_sqlite_value(value) for value in record)
            for record in frame[columns].itertuples(index=False, name=None)]
    conn.executemany(sql, rows)
    conn.commit()
    return len(rows)


def _sqlite_value(value):
    """sqlite3 stores numpy scalars as BLOBs, so hand it plain Python types."""
    if value is None or value is pd.NA:
        return None
    if isinstance(value, str):
        return value
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    item = getattr(value, "item", None)
    return item() if callable(item) else value


def available_dates(conn: sqlite3.Connection, spec: ReportSpec) -> list[str]:
    cursor = conn.execute(f"SELECT DISTINCT report_date FROM {spec.table} ORDER BY report_date")
    return [row[0] for row in cursor.fetchall()]


def read_report(conn: sqlite3.Connection, spec: ReportSpec, since: str | None = None) -> pd.DataFrame:
    sql = f"SELECT * FROM {spec.table}"
    params: tuple = ()
    if since:
        sql += " WHERE report_date >= ?"
        params = (since,)
    sql += " ORDER BY report_date, symbol"
    return pd.read_sql_query(sql, conn, params=params)
