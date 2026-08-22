"""Daily settlement prices, so a positioning signal can be scored against what
the market actually did rather than only against how the position unwound.

Deliberately best-effort. Every fetch is wrapped, a failure is logged and the
symbol is skipped, and the caller gets a count rather than an exception: the
weekly build's job is to keep the committed COT history current, and a price
feed that is rate-limiting or down must not be able to take that with it. The
site degrades the same way it does for the missing term structure — the panels
that need a price say so and the rest of the report is unaffected.
"""

import logging
import random
import sqlite3
import time
from datetime import date, datetime, timedelta, timezone

import requests

from cot.markets import price_targets

logger = logging.getLogger(__name__)

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
TIMEOUT = 20

# Plain browser headers. The endpoint is public and unauthenticated; this is
# only here because a bare urllib default agent gets refused.
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"),
    "Accept": "application/json,text/plain,*/*",
}

# A ticker that resolves but carries almost nothing is worse than one that does
# not resolve: it looks like coverage. Below this many observations the symbol
# is treated as having no price series.
MIN_OBSERVATIONS = 40

# The feed throttles bursts, and a weekly run asks it for 57 symbols back to
# back. 429 is a rate limit rather than a refusal, so it is worth waiting out —
# honouring Retry-After when the response carries one, backing off if not.
RETRY_STATUS = {429, 502, 503, 504}
MAX_ATTEMPTS = 4
BACKOFF_BASE = 5.0
MAX_BACKOFF = 90.0


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            symbol TEXT NOT NULL,
            trade_date TEXT NOT NULL,
            close REAL NOT NULL,
            PRIMARY KEY (symbol, trade_date)
        )
    """)
    conn.commit()


def parse_series(payload: dict) -> list[tuple[date, float]]:
    """Pull (date, close) pairs out of a chart response.

    Timestamps come back as UTC epochs stamped at the exchange's session open,
    which for the overnight CME session falls on the previous calendar day in
    UTC. Shifting by the exchange offset the response carries puts each bar on
    the session date the exchange itself would name.
    """
    results = (payload.get("chart") or {}).get("result")
    if not results:
        return []

    block = results[0]
    stamps = block.get("timestamp") or []
    try:
        closes = block["indicators"]["quote"][0].get("close") or []
    except (KeyError, IndexError, TypeError):
        return []

    offset = block.get("meta", {}).get("gmtoffset") or 0
    points = []
    for stamp, close in zip(stamps, closes):
        if close is None:
            continue
        day = datetime.fromtimestamp(stamp + offset, tz=timezone.utc).date()
        points.append((day, float(close)))
    points.sort()
    return points


def _retry_after(response, attempt: int) -> float:
    header = response.headers.get("Retry-After")
    if header:
        try:
            return min(float(header), MAX_BACKOFF)
        except ValueError:
            pass
    return min(BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 1), MAX_BACKOFF)


def fetch_series(ticker: str, start: date, end: date,
                 session: requests.Session | None = None) -> list[tuple[date, float]]:
    params = {
        "period1": int(datetime.combine(start, datetime.min.time(),
                                        tzinfo=timezone.utc).timestamp()),
        "period2": int(datetime.combine(end + timedelta(days=1), datetime.min.time(),
                                        tzinfo=timezone.utc).timestamp()),
        "interval": "1d",
    }
    get = (session or requests).get

    for attempt in range(MAX_ATTEMPTS):
        response = get(CHART_URL.format(ticker=ticker), params=params,
                       headers=HEADERS, timeout=TIMEOUT)
        if response.status_code == 200:
            try:
                return parse_series(response.json())
            except ValueError:
                logger.warning("Price feed returned non-JSON for %s", ticker)
                return []

        if response.status_code in RETRY_STATUS and attempt < MAX_ATTEMPTS - 1:
            wait = _retry_after(response, attempt)
            logger.info("Price feed HTTP %s for %s, retrying in %.0fs",
                        response.status_code, ticker, wait)
            time.sleep(wait)
            continue

        logger.warning("Price feed HTTP %s for %s", response.status_code, ticker)
        return []

    return []


def last_stored(conn: sqlite3.Connection, symbol: str) -> date | None:
    row = conn.execute("SELECT MAX(trade_date) FROM prices WHERE symbol = ?",
                       (symbol,)).fetchone()
    return date.fromisoformat(row[0]) if row and row[0] else None


def update_all(conn: sqlite3.Connection, start: date, end: date | None = None,
               polite_delay: bool = True) -> int:
    """Bring every mapped market's price series up to date.

    Returns the number of markets that gained rows. Never raises: a symbol that
    fails is logged and skipped, and so is a feed that is down entirely.
    """
    ensure_table(conn)
    end = end or date.today()
    updated = 0
    session = requests.Session()

    for symbol, ticker in price_targets().items():
        stored = last_stored(conn, symbol)
        # Re-request the last stored week so a revised settlement is picked up.
        since = max(start, stored - timedelta(days=7)) if stored else start
        if since > end:
            continue

        try:
            points = fetch_series(ticker, since, end, session)
        except requests.RequestException as exc:
            logger.warning("Price fetch failed for %s (%s): %s", symbol, ticker, exc)
            points = []
        except Exception:  # noqa: BLE001 - the weekly build must survive anything here
            logger.exception("Unexpected error fetching %s (%s)", symbol, ticker)
            points = []

        if not points:
            logger.info("No price data for %s (%s)", symbol, ticker)
            continue

        conn.executemany(
            "INSERT OR REPLACE INTO prices (symbol, trade_date, close) VALUES (?, ?, ?)",
            [(symbol, day.isoformat(), close) for day, close in points],
        )
        conn.commit()
        updated += 1
        logger.info("Stored %d price points for %s (%s)", len(points), symbol, ticker)

        if polite_delay:
            time.sleep(random.uniform(0.6, 1.4))

    return updated


def weekly_closes(conn: sqlite3.Connection, dates: list[str]) -> dict[str, list[float | None]]:
    """Close per market as of each report date.

    The CFTC stamps a report for Tuesday; if that Tuesday was a holiday the
    close carried forward is the most recent one before it, which is what a
    reader comparing the two series would assume.
    """
    ensure_table(conn)
    if not dates:
        return {}

    rows = conn.execute(
        "SELECT symbol, trade_date, close FROM prices ORDER BY symbol, trade_date"
    ).fetchall()

    series: dict[str, list[tuple[str, float]]] = {}
    for symbol, trade_date, close in rows:
        series.setdefault(symbol, []).append((trade_date, close))

    aligned = {}
    for symbol, points in series.items():
        if len(points) < MIN_OBSERVATIONS:
            logger.info("Ignoring %s: only %d price observations", symbol, len(points))
            continue
        aligned[symbol] = _as_of(points, dates)
    return aligned


# How long a close may stand in for a missing one. A holiday or a data gap is a
# day or two; anything beyond this is a series that stopped, and carrying its
# last price forward would draw a flat line where there is no data at all.
MAX_CARRY_DAYS = 10


def _as_of(points: list[tuple[str, float]], dates: list[str]) -> list[float | None]:
    out: list[float | None] = []
    cursor = 0
    carried: tuple[date, float] | None = None
    for target in dates:
        while cursor < len(points) and points[cursor][0] <= target:
            carried = (date.fromisoformat(points[cursor][0]), points[cursor][1])
            cursor += 1
        if carried and (date.fromisoformat(target) - carried[0]).days <= MAX_CARRY_DAYS:
            out.append(carried[1])
        else:
            out.append(None)
    return out
