"""Term structure (futures curve) data from the CME settlements API."""

import logging
import random
import sqlite3
import time
from datetime import date, datetime, timedelta

import requests

from cot.markets import term_structure_targets

logger = logging.getLogger(__name__)

SETTLEMENTS_URL = "https://www.cmegroup.com/CmeWS/mvc/Settlements/Futures/Settlements/{key}/FUT"
TIMEOUT = 30

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.cmegroup.com/markets/agriculture.html",
    "Origin": "https://www.cmegroup.com",
    "Connection": "keep-alive",
}

MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JLY": 7, "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS term_structure (
            symbol TEXT NOT NULL,
            report_date TEXT NOT NULL,
            settlement_date TEXT NOT NULL,
            settlement_price REAL,
            PRIMARY KEY (symbol, report_date, settlement_date)
        )
    """)
    conn.commit()


def last_business_day(today: date | None = None) -> date:
    today = today or date.today()
    offset = max(1, (today.weekday() + 6) % 7 - 3)
    return today - timedelta(days=offset)


def parse_contract_month(value: str) -> date | None:
    try:
        month, year = value.split()
        return date(2000 + int(year), MONTHS[month.upper()], 1)
    except (ValueError, KeyError):
        logger.debug("Unparseable contract month %r", value)
        return None


def parse_price(value) -> float | None:
    """CME quotes fractional prices as 1234'5 — treat the tick part as decimals."""
    if value in (None, "", "-"):
        return None
    try:
        return float(str(value).replace("'", ".").replace(",", ""))
    except ValueError:
        return None


def fetch_curve(cme_key: str, trade_date: date) -> list[tuple[date, float]]:
    params = {
        "strategy": "DEFAULT",
        "tradeDate": trade_date.strftime("%m/%d/%Y"),
        "pageSize": "500",
        "isProtected": "",
        "_t": str(int(time.time() * 1000)),
    }
    response = requests.get(SETTLEMENTS_URL.format(key=cme_key), params=params,
                            headers=HEADERS, timeout=TIMEOUT)
    if response.status_code != 200:
        logger.warning("CME settlements HTTP %s for product %s", response.status_code, cme_key)
        return []

    try:
        payload = response.json()
    except ValueError:
        logger.warning("CME settlements returned non-JSON for product %s", cme_key)
        return []

    points = []
    for entry in payload.get("settlements", []):
        if entry.get("month") in (None, "Total"):
            continue
        month = parse_contract_month(entry["month"])
        price = parse_price(entry.get("settle"))
        if month and price is not None and price > 0:
            points.append((month, price))
    points.sort()
    return points


def scrape_all(conn: sqlite3.Connection, trade_date: date | None = None,
               polite_delay: bool = True) -> int:
    """Fetch every configured curve for one trade date. Returns markets updated."""
    ensure_table(conn)
    trade_date = trade_date or last_business_day()
    updated = 0

    for symbol, cme_key in term_structure_targets().items():
        existing = conn.execute(
            "SELECT COUNT(*) FROM term_structure WHERE symbol = ? AND report_date = ?",
            (symbol, trade_date.isoformat()),
        ).fetchone()[0]
        if existing:
            logger.debug("Curve for %s on %s already stored", symbol, trade_date)
            continue

        try:
            points = fetch_curve(cme_key, trade_date)
        except requests.RequestException as exc:
            logger.warning("Curve fetch failed for %s: %s", symbol, exc)
            points = []

        if points:
            conn.executemany(
                "INSERT OR REPLACE INTO term_structure "
                "(symbol, report_date, settlement_date, settlement_price) VALUES (?, ?, ?, ?)",
                [(symbol, trade_date.isoformat(), month.isoformat(), price)
                 for month, price in points],
            )
            conn.commit()
            updated += 1
            logger.info("Stored %d curve points for %s", len(points), symbol)
        else:
            logger.info("No curve data for %s on %s", symbol, trade_date)

        if polite_delay:
            time.sleep(random.uniform(0.5, 2.0))

    return updated


def latest_curves(conn: sqlite3.Connection) -> dict[str, dict]:
    """Latest stored curve per symbol, with a contango/backwardation read."""
    ensure_table(conn)
    rows = conn.execute("""
        SELECT t.symbol, t.report_date, t.settlement_date, t.settlement_price
        FROM term_structure t
        JOIN (SELECT symbol, MAX(report_date) AS report_date
              FROM term_structure GROUP BY symbol) latest
          ON latest.symbol = t.symbol AND latest.report_date = t.report_date
        ORDER BY t.symbol, t.settlement_date
    """).fetchall()

    curves: dict[str, dict] = {}
    for symbol, report_date, settlement_date, price in rows:
        curve = curves.setdefault(symbol, {"report_date": report_date, "points": []})
        curve["points"].append([settlement_date, price])

    for curve in curves.values():
        curve["points"] = curve["points"][:24]
        curve.update(_structure(curve["points"]))
    return curves


def _structure(points: list[list]) -> dict[str, str | None]:
    prices = [p[1] for p in points]
    if len(prices) < 3:
        return {"short_term": None, "long_term": None, "overall": None, "slope_pct": None}

    diffs = [b - a for a, b in zip(prices, prices[1:])]
    near = diffs[:3]
    far = diffs[3:] or diffs[-1:]
    slope_pct = (prices[-1] - prices[0]) / prices[0] * 100 if prices[0] else None

    return {
        "short_term": _label(near),
        "long_term": _label(far),
        "overall": _label(diffs),
        "slope_pct": round(slope_pct, 2) if slope_pct is not None else None,
    }


def _label(diffs: list[float]) -> str | None:
    if not diffs:
        return None
    mean = sum(diffs) / len(diffs)
    if abs(mean) < 1e-9:
        return "Flat"
    return "Contango" if mean > 0 else "Backwardation"
