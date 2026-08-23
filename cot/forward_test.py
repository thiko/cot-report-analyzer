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
import statistics
from collections import defaultdict
from pathlib import Path

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
                row["oi"].append(year["open_interest"][date_idx][market_idx])
                for name, group, field in wanted:
                    values = year["groups"][group][field][date_idx]
                    row[name].append(values[market_idx] if values else None)
    return out


def _deviation(net: list, i: int) -> float | None:
    window = [v for v in net[max(0, i - 51):i + 1] if v is not None]
    if len(window) < MIN_WINDOW:
        return None
    spread = statistics.pstdev(window)
    return spread or None


def observations() -> list[dict]:
    """Every market-week that has both a trailing window and a forward value."""
    rows = []
    for report, (spec, comm) in REPORTS.items():
        for symbol, series in _series(report, spec, comm).items():
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
