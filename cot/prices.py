"""Weekly price series, so a positioning signal can be scored against what the
market actually did rather than only against how the position unwound.

Two providers, because neither covers the board alone. FRED serves rates,
exchange rates, equity indices, the energy benchmarks, crypto and the VIX as
daily series, with no key and no request limit. Alpha Vantage fills in
agriculture, softs and metals through weekly ETF closes — its own commodity
endpoints answer with one observation a month whatever `interval` is passed,
which is no use against a report that moves weekly.

Deliberately best-effort. Every fetch is wrapped, a failure is logged and the
series is skipped, and the caller gets a count rather than an exception: the
weekly build's job is to keep the committed COT history current, and a price
feed that is rate-limiting or down must not be able to take that with it. With
no API key configured the Alpha Vantage half is skipped and the FRED half still
runs, so the report degrades to partial coverage instead of none.
"""

import csv
import io
import logging
import random
import sqlite3
import time
from datetime import date, timedelta

import requests

from cot.markets import PriceSource, price_sources

logger = logging.getLogger(__name__)

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
ALPHAVANTAGE_URL = "https://www.alphavantage.co/query"
TIMEOUT = 30

# A ticker that resolves but carries almost nothing is worse than one that does
# not resolve: it looks like coverage. Below this many observations the symbol
# is treated as having no price series.
MIN_OBSERVATIONS = 40

RETRY_STATUS = {429, 502, 503, 504}
MAX_ATTEMPTS = 4
BACKOFF_BASE = 5.0
MAX_BACKOFF = 90.0

# Backing off is right for a provider that is briefly busy and wrong for one
# refusing this host outright. After this many series fail in a row at the
# transport level the run gives up on that provider rather than proving the
# point for every remaining symbol. A series the provider simply has no data
# for does not count.
MAX_CONSECUTIVE_FAILURES = 3

# Alpha Vantage asks for no more than one request a second on the free tier and
# answers a burst with a throttle notice rather than an error, so pacing is the
# difference between a series and a polite refusal.
ALPHAVANTAGE_DELAY = 1.5

# The free tier allows 25 requests a day. The mapping needs 14, so this is a
# backstop against a future mapping quietly growing past the allowance rather
# than a limit anything should reach.
ALPHAVANTAGE_DAILY_BUDGET = 25


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


def parse_fred_csv(text: str) -> list[tuple[date, float]]:
    """(date, close) pairs from a fredgraph.csv body.

    FRED writes a lone "." for a day the series has no observation — a holiday,
    or a gap in the underlying collection — which is not zero and not an error.
    """
    points = []
    for row in csv.DictReader(io.StringIO(text)):
        values = list(row.values())
        if len(values) < 2:
            continue
        stamp, raw = values[0], values[1]
        # A malformed body can put a list here: csv.DictReader collects fields
        # beyond the header under a single key.
        if not isinstance(stamp, str) or not isinstance(raw, str):
            continue
        if raw.strip() in {".", ""}:
            continue
        try:
            points.append((date.fromisoformat(stamp.strip()), float(raw)))
        except ValueError:
            continue
    points.sort()
    return points


def parse_alphavantage(payload: dict) -> list[tuple[date, float]] | None:
    """(date, close) pairs from a TIME_SERIES_WEEKLY response.

    Returns None for a throttle or error notice, which is a reason to stop
    asking rather than a symbol without data. Alpha Vantage answers both with
    HTTP 200 and a one-key body, so the status code cannot carry this.
    """
    series = payload.get("Weekly Time Series")
    if series is None:
        note = payload.get("Note") or payload.get("Information") or payload.get("Error Message")
        if note:
            logger.warning("Alpha Vantage: %s", str(note)[:160])
        return None

    points = []
    for stamp, row in series.items():
        close = row.get("4. close")
        if close is None:
            continue
        try:
            points.append((date.fromisoformat(stamp), float(close)))
        except ValueError:
            continue
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


def _get(url: str, params: dict, session, label: str):
    """GET with a retry ladder. Returns the response, or None if unreachable."""
    get = (session or requests).get
    for attempt in range(MAX_ATTEMPTS):
        response = get(url, params=params, timeout=TIMEOUT)
        if response.status_code == 200:
            return response
        if response.status_code in RETRY_STATUS and attempt < MAX_ATTEMPTS - 1:
            wait = _retry_after(response, attempt)
            logger.info("HTTP %s for %s, retrying in %.0fs",
                        response.status_code, label, wait)
            time.sleep(wait)
            continue
        logger.warning("HTTP %s for %s", response.status_code, label)
        return None
    return None


def fetch_series(source: PriceSource, api_key: str | None = None,
                 session: requests.Session | None = None
                 ) -> list[tuple[date, float]] | None:
    """Every stored point for one source.

    Returns a list of points, an empty list when the provider answered but has
    nothing for this series, or None when the provider could not be reached —
    the caller needs that distinction to tell a dead series from a wall.

    Both providers return their whole history in one request, so there is no
    incremental mode to exploit; the caller trims to the window it wants.
    """
    if source.provider == "fred":
        response = _get(FRED_URL, {"id": source.series}, session, source.series)
        return None if response is None else parse_fred_csv(response.text)

    if source.provider == "alphavantage":
        if not api_key:
            return None
        response = _get(ALPHAVANTAGE_URL, {
            "function": "TIME_SERIES_WEEKLY",
            "symbol": source.series,
            "apikey": api_key,
        }, session, source.series)
        if response is None:
            return None
        try:
            return parse_alphavantage(response.json())
        except ValueError:
            logger.warning("Alpha Vantage returned non-JSON for %s", source.series)
            return None

    logger.warning("Unknown price provider %r for %s", source.provider, source.series)
    return None


def last_stored(conn: sqlite3.Connection, symbol: str) -> date | None:
    row = conn.execute("SELECT MAX(trade_date) FROM prices WHERE symbol = ?",
                       (symbol,)).fetchone()
    return date.fromisoformat(row[0]) if row and row[0] else None


def update_all(conn: sqlite3.Connection, start: date, end: date | None = None,
               api_key: str | None = None, polite_delay: bool = True) -> int:
    """Bring every mapped market's price series up to date.

    Returns the number of markets that gained rows. Never raises: a series that
    fails is logged and skipped, and so is a provider that is down entirely.

    Several markets share a series — the ten-year note and the ultra ten-year
    both settle against DGS10 — so each series is fetched once and written to
    every market that maps to it. That is what keeps the Alpha Vantage half
    inside the free tier's daily allowance.
    """
    ensure_table(conn)
    end = end or date.today()
    sources = price_sources()

    if not api_key:
        skipped = sum(1 for s in sources.values() if s.provider == "alphavantage")
        if skipped:
            logger.warning(
                "No API key configured; skipping %d markets that need Alpha Vantage. "
                "The FRED half still runs.", skipped)

    # symbol -> source, grouped by the request that serves it
    by_series: dict[tuple[str, str], list[str]] = {}
    for symbol, source in sources.items():
        by_series.setdefault((source.provider, source.series), []).append(symbol)

    updated = 0
    failures = {"fred": 0, "alphavantage": 0}
    dead: set[str] = set()
    spent = 0
    session = requests.Session()

    for (provider, series), symbols in by_series.items():
        if provider in dead:
            continue
        if provider == "alphavantage":
            if not api_key:
                continue
            if spent >= ALPHAVANTAGE_DAILY_BUDGET:
                logger.warning("Alpha Vantage daily budget of %d requests reached; "
                               "%s and anything after it are left for the next run",
                               ALPHAVANTAGE_DAILY_BUDGET, series)
                dead.add(provider)
                continue
            spent += 1

        source = sources[symbols[0]]
        try:
            points = fetch_series(source, api_key, session)
        except requests.RequestException as exc:
            logger.warning("Price fetch failed for %s (%s): %s", series, provider, exc)
            points = None
        except Exception:  # noqa: BLE001 - the weekly build must survive anything here
            logger.exception("Unexpected error fetching %s (%s)", series, provider)
            points = None

        if provider == "alphavantage" and polite_delay:
            time.sleep(ALPHAVANTAGE_DELAY)

        if points is None:
            failures[provider] += 1
            if failures[provider] >= MAX_CONSECUTIVE_FAILURES:
                logger.warning("%s unreachable for %d series in a row; abandoning it "
                               "for this run", provider, failures[provider])
                dead.add(provider)
            continue

        failures[provider] = 0
        window = [(day, close) for day, close in points if start <= day <= end]
        if not window:
            logger.info("No price data in range for %s (%s)", series, provider)
            continue

        for symbol in symbols:
            conn.executemany(
                "INSERT OR REPLACE INTO prices (symbol, trade_date, close) "
                "VALUES (?, ?, ?)",
                [(symbol, day.isoformat(), close) for day, close in window],
            )
            updated += 1
        conn.commit()
        logger.info("Stored %d points from %s (%s) for %s",
                    len(window), series, provider, ", ".join(symbols))

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


# How long a close may stand in for a missing one. FRED's daily series skip
# holidays by a day or two; the Alpha Vantage series are weekly by construction,
# so a fortnight covers a missed week without inventing a flat line where a
# series has actually stopped.
MAX_CARRY_DAYS = 14


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
