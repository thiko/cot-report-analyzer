"""Forward test behind the tier table in the README.

Reads the committed year files and asks one question: eight weeks after a given
week, had the speculator net position moved back toward the middle of its own
range? The move is divided by that market's trailing 52-week standard deviation
so a Corn week and a Gold week count the same.

The point of running it as a script rather than quoting the numbers is the base
rate. Positions mean-revert over eight weeks whether or not anything is flagged,
and a bucket that unwinds 64% of the time is only worth the distance between 64
and that baseline. Every tier is printed against it.

    python -m cot.forward_test
"""
from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from cot.markets import price_sources

DATA = Path(__file__).resolve().parent.parent / "data"

HORIZON = 8
MIN_OI = 50_000
OI_LOOKBACK = 4
EXTREME_HIGH = 90
EXTREME_LOW = 10
MIN_WINDOW = 20

# The three report types the tier table was measured over, each as
# (speculator group, hedger group). The futopt variants of the disaggregated
# report and the supplemental report cover the same contracts again, so
# including them would count the same market-week more than once.
REPORTS = {
    "disaggregated_futopt": ("managed_money", "producer"),
    "legacy_fut": ("noncommercial", "commercial"),
    "traders_in_financial_futures_fut": ("leveraged_money", "dealer"),
}


def _series(report: str, spec: str, comm: str) -> dict[str, dict[str, list]]:
    """One aligned set of lists per market symbol, across every committed year."""
    out: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for path in sorted(DATA.joinpath(report).glob("[0-9]" * 4 + ".json")):
        year = json.loads(path.read_text())
        symbols = [m["symbol"] for m in year["markets"]]
        wanted = (("net", spec, "net"), ("chg", spec, "chg"),
                  ("p52", spec, "p52w"), ("comm_p52", comm, "p52w"))
        for date_idx in range(len(year["dates"])):
            for market_idx, symbol in enumerate(symbols):
                row = out[symbol]
                row["date"].append(year["dates"][date_idx])
                row["oi"].append(year["open_interest"][date_idx][market_idx])
                for name, group, field in wanted:
                    values = year["groups"][group][field][date_idx]
                    row[name].append(values[market_idx] if values else None)
    return out


def _prices() -> dict[str, dict[str, float]]:
    """symbol -> {report date: close}, empty when no price file has been built.

    Read straight from the exported file rather than the build database: it is
    already aligned to report dates, and it is the same thing the site sees.
    """
    path = DATA / "prices.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text())
    dates = payload["dates"]
    return {
        symbol: {day: close for day, close in zip(dates, closes) if close is not None}
        for symbol, closes in payload.get("closes", {}).items()
    }


def _price_move(series: dict[str, float], history: list[str], i: int,
                horizon: int, invert: bool) -> float | None:
    """Eight-week return, in units of that market's own weekly volatility.

    Normalising lets a yield series and an ETF sit in the same column, and
    `invert` turns a yield or a reversed currency quote back into the direction
    the contract moves — without it every rates market reads backwards.
    """
    here, ahead = series.get(history[i]), series.get(history[i + horizon])
    if here is None or ahead is None or here <= 0 or ahead <= 0:
        return None

    window = [series.get(day) for day in history[max(0, i - 51):i + 1]]
    steps = [math.log(b / a) for a, b in zip(window, window[1:])
             if a and b and a > 0 and b > 0]
    if len(steps) < MIN_WINDOW:
        return None
    spread = statistics.pstdev(steps)
    if not spread:
        return None

    move = math.log(ahead / here) / (spread * math.sqrt(horizon))
    return -move if invert else move


def _deviation(net: list, i: int) -> float | None:
    window = [v for v in net[max(0, i - 51):i + 1] if v is not None]
    if len(window) < MIN_WINDOW:
        return None
    spread = statistics.pstdev(window)
    return spread or None


def observations() -> list[dict]:
    """Every market-week that has both a trailing window and a forward value."""
    prices = _prices()
    sources = price_sources()
    rows = []
    for report, (spec, comm) in REPORTS.items():
        for symbol, series in _series(report, spec, comm).items():
            source = sources.get(symbol)
            price_series = prices.get(symbol, {})
            for i in range(len(series["net"]) - HORIZON):
                net = series["net"][i]
                ahead = series["net"][i + HORIZON]
                p52, oi = series["p52"][i], series["oi"][i]
                if None in (net, ahead, p52, oi):
                    continue
                deviation = _deviation(series["net"], i)
                if deviation is None:
                    continue
                back = i - OI_LOOKBACK
                oi_before = series["oi"][back] if back >= 0 else None
                rows.append({
                    "report": report, "symbol": symbol, "p52": p52,
                    "chg": series["chg"][i], "comm_p52": series["comm_p52"][i],
                    "liquid": oi >= MIN_OI,
                    "oi_rising": oi_before is not None and oi > oi_before,
                    "move": (ahead - net) / deviation,
                    "price_move": _price_move(price_series, series["date"], i,
                                              HORIZON, source.invert) if source else None,
                    "price_kind": source.kind if source else None,
                })
    return rows


def _unwind(row: dict, side: int) -> float:
    """Positive when the position moved against the side it was leaning on."""
    return -side * row["move"]


def _report(label: str, unwinds: list[float]) -> None:
    if not unwinds:
        print(f"{label:<52} {0:>6}")
        return
    share = sum(1 for u in unwinds if u > 0) / len(unwinds)
    print(f"{label:<52} {len(unwinds):>6} {statistics.median(unwinds):>+8.2f} {share:>9.1%}")


def _band(n: int) -> float:
    """Half-width of a 95% interval on a hit rate near a half.

    Consecutive observations share seven of their eight forward weeks, so the
    row count is not a count of independent trials. Dividing by the horizon is
    rough but it is the right order, and quoting a rate without it makes a
    coin flip look like a finding.
    """
    effective = max(n / HORIZON, 1)
    return 1.96 * (0.25 / effective) ** 0.5


def _price_rows(rows: list[dict], side_of) -> list[float]:
    """Positive when the price moved the way an unwind of that side implies:
    a crowded long unwinding is selling, so the setup wants the price down."""
    out = []
    for row in rows:
        if row["price_move"] is None:
            continue
        out.append(-side_of(row) * row["price_move"])
    return out


def _report_price(label: str, rows: list[dict], side_of) -> None:
    moves = _price_rows(rows, side_of)
    if not moves:
        print(f"{label:<52} {0:>6}")
        return
    share = sum(1 for m in moves if m > 0) / len(moves)
    print(f"{label:<52} {len(moves):>6} {statistics.median(moves):>+8.2f} "
          f"{share:>9.1%} ±{_band(len(moves)):.1%}")


def main() -> None:
    rows = observations()
    print(f"{'bucket':<52} {'n':>6} {'median':>8} {'unwound':>9}")

    # The baseline first, because every tier below is only worth the distance
    # from it. Side is simply which half of its own range the position sits in,
    # so "unwound" means the same thing it does for the extremes.
    base = [(r, 1 if r["p52"] > 50 else -1) for r in rows
            if r["liquid"] and r["p52"] != 50]
    _report("base rate  liquid, any position off its own median",
            [_unwind(r, side) for r, side in base])

    extremes = []
    for row in rows:
        side = 1 if row["p52"] >= EXTREME_HIGH else (-1 if row["p52"] <= EXTREME_LOW else 0)
        if not side:
            continue
        comm = row["comm_p52"]
        extremes.append({
            **row, "side": side, "unwind": _unwind(row, side),
            "turning": row["chg"] is not None and side * row["chg"] < 0,
            "mirror": comm is not None and
                      (comm <= EXTREME_LOW if side > 0 else comm >= EXTREME_HIGH),
        })

    liquid = [r for r in extremes if r["liquid"]]
    tier_c = [r for r in liquid if r["turning"]]
    tier_b = [r for r in tier_c if r["mirror"]]
    tier_a = [r for r in tier_b if r["oi_rising"]]
    for label, bucket in (
        ("liquid, extreme percentile only", liquid),
        ("C  liquid + weekly flow turning", tier_c),
        ("B  C + hedgers at the mirror extreme", tier_b),
        ("A  B + open interest rising", tier_a),
        ("(excluded) illiquid + turning + mirror",
         [r for r in extremes if not r["liquid"] and r["turning"] and r["mirror"]]),
    ):
        _report(label, [r["unwind"] for r in bucket])

    # The step the interface deliberately does not take. Everything above
    # measures whether the *position* unwound; this measures whether the price
    # went the way that unwinding implies. They are not the same question, and
    # the base rate matters even more here — prices drift, so some hit rate is
    # available for free.
    print()
    print(f"{'price, eight weeks on':<52} {'n':>6} {'median':>8} "
          f"{'went that way':>14}")
    _report_price("base rate  liquid, any position off its own median",
                  [r for r, _ in base], lambda r: 1 if r["p52"] > 50 else -1)
    for label, bucket in (("liquid, extreme percentile only", liquid),
                          ("C  liquid + weekly flow turning", tier_c),
                          ("B  C + hedgers at the mirror extreme", tier_b),
                          ("A  B + open interest rising", tier_a)):
        _report_price(label, bucket, lambda r: r["side"])

    # A proxy is an ETF standing in for a contract, with its own fees and roll.
    # If the result only holds on the proxies it is about the ETFs, not the
    # positioning, so the two are never pooled into one headline number.
    print()
    for kind in ("benchmark", "proxy"):
        _report_price(f"  tier C, {kind} series only",
                      [r for r in tier_c if r["price_kind"] == kind],
                      lambda r: r["side"])

    # Extremity is not monotone, which is why the interface treats a percentile
    # as a condition rather than a dial: the top band unwinds less than the one
    # below it, because a position pinned at its own edge means a trend is on.
    print()
    print(f"{'distance from own 52-week median':<52} {'n':>6} {'median':>8} {'unwound':>9}")
    for low, high in ((0, 10), (10, 20), (20, 30), (30, 40), (40, 45),
                        (45, 50), (50, 51)):
        band = [_unwind(r, side) for r, side in base if low <= abs(r["p52"] - 50) < high]
        _report(f"  |percentile - 50| in [{low}, {high})", band)


if __name__ == "__main__":
    main()
