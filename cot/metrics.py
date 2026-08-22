"""Derived position metrics: net exposure, weekly change and rolling percentiles."""

import numpy as np
import pandas as pd

from cot.reports import ReportSpec

# Trailing windows in weekly observations.
WINDOWS = {"p25w": 25, "p52w": 52, "p156w": 156}

GAP_KEY = "gap"


def gap_pair(spec: ReportSpec) -> tuple[str, str] | None:
    """The commercial and speculator group whose divergence we track as "gap"."""
    commercial = next((g.key for g in spec.groups if g.stance == "commercial"), None)
    speculator = next((g.key for g in spec.groups if g.stance == "speculator"), None)
    if commercial and speculator:
        return commercial, speculator
    return None


def metric_groups(spec: ReportSpec) -> list[dict]:
    """Group metadata as exported to the site, including the derived gap column."""
    groups = [
        {"key": g.key, "label": g.label, "stance": g.stance, "derived": False}
        for g in spec.groups
    ]
    pair = gap_pair(spec)
    if pair:
        commercial, speculator = pair
        commercial_label = next(g.label for g in spec.groups if g.key == commercial)
        speculator_label = next(g.label for g in spec.groups if g.key == speculator)
        groups.append({
            "key": GAP_KEY,
            "label": "Gap",
            "stance": "derived",
            "derived": True,
            "formula": f"{speculator_label} net − {commercial_label} net",
        })
    return groups


def enrich(frame: pd.DataFrame, spec: ReportSpec) -> pd.DataFrame:
    """Add net/change/percentile columns for every trader group.

    Expects the full history for one report type, ordered by date, so the
    rolling windows have something to look back at.
    """
    if frame.empty:
        return frame

    frame = frame.sort_values(["symbol", "report_date"]).reset_index(drop=True)

    for group in spec.groups:
        long = frame[f"{group.key}_long"]
        short = frame[f"{group.key}_short"]
        frame[f"{group.key}_net"] = long - short
        frame[f"{group.key}_chg"] = (
            frame[f"{group.key}_change_long"] - frame[f"{group.key}_change_short"]
        )

    pair = gap_pair(spec)
    if pair:
        commercial, speculator = pair
        frame[f"{GAP_KEY}_net"] = frame[f"{speculator}_net"] - frame[f"{commercial}_net"]
        frame[f"{GAP_KEY}_chg"] = frame[f"{speculator}_chg"] - frame[f"{commercial}_chg"]

    keys = [g.key for g in spec.groups] + ([GAP_KEY] if pair else [])
    for key in keys:
        net = f"{key}_net"
        frame[f"{key}_pct_oi"] = _safe_ratio(frame[net], frame["open_interest"])
        for name, window in WINDOWS.items():
            frame[f"{key}_{name}"] = (
                frame.groupby("symbol", sort=False)[net]
                .transform(lambda s, w=window: _rolling_percentile(s, w))
            )

    return frame


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    num = pd.to_numeric(numerator, errors="coerce").astype("float64")
    den = pd.to_numeric(denominator, errors="coerce").astype("float64")
    ratio = np.where((den > 0) & np.isfinite(num), num / den * 100.0, np.nan)
    return pd.Series(np.round(ratio, 1), index=numerator.index)


def _rolling_percentile(series: pd.Series, window: int) -> pd.Series:
    """Percentile rank of each value within its trailing window, 0-100.

    A value of 70 means the current net position is above 70% of the
    observations in that window, matching the previous report's definition.
    Windows shorter than two valid observations stay undefined.
    """
    values = pd.to_numeric(series, errors="coerce").to_numpy(dtype="float64")
    if values.size == 0:
        return pd.Series(values, index=series.index)

    padded = np.concatenate([np.full(window - 1, np.nan), values])
    windows = np.lib.stride_tricks.sliding_window_view(padded, window)

    current = values[:, None]
    with np.errstate(invalid="ignore"):
        below = np.sum(windows < current, axis=1)
    valid = np.sum(np.isfinite(windows), axis=1)

    usable = np.isfinite(values) & (valid >= 2)
    out = np.full(values.shape, np.nan)
    np.divide(below, valid, out=out, where=usable)
    out = np.where(usable, np.round(out * 100.0), np.nan)

    return pd.Series(out, index=series.index)
