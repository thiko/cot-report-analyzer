"""Checks on the parts that would fail silently in an unattended weekly run."""

import json
import sqlite3
import textwrap
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import requests

from cot.config import API_KEY_ENV, Config
from cot.download import normalize_column
from cot.export import report_index_entry, write_index, write_report_years
from cot.markets import (COMMODITY_MARKETS, FINANCIAL_MARKETS,
                         PRICE_SYMBOL_OVERRIDES, price_targets)
from cot.metrics import _rolling_percentile, enrich
from cot.prices import (MAX_CONSECUTIVE_FAILURES, _as_of, parse_series,
                        update_all, weekly_closes)
from cot.prices import ensure_table as ensure_prices_table
from cot.reports import REPORTS
from cot.store import ensure_table, ingest_file, read_report


@pytest.mark.parametrize("raw, expected", [
    ("Market_and_Exchange_Names", "Market_and_Exchange_Names"),
    ("Open Interest (All)", "Open_Interest_All"),
    (" Total Reportable Positions-Long (All)", "Total_Reportable_Positions_Long_All"),
    ("Swap__Positions_Short_All", "Swap_Positions_Short_All"),
    ("Change_Comm_Short_All_NoCIT ", "Change_Comm_Short_All_NoCIT"),
    ("As of Date in Form YYYY-MM-DD", "As_of_Date_in_Form_YYYY_MM_DD"),
])
def test_normalize_column(raw, expected):
    assert normalize_column(raw) == expected


def test_every_report_date_column_is_normalised():
    for spec in REPORTS.values():
        assert normalize_column(spec.date_col) == spec.date_col


def test_market_symbols_are_unique_within_a_universe():
    for universe in (COMMODITY_MARKETS, FINANCIAL_MARKETS):
        symbols = [m.symbol for m in universe.values()]
        assert len(symbols) == len(set(symbols))


def test_rolling_percentile_matches_a_naive_implementation():
    values = pd.Series([5, 3, 9, 1, 7, 7, 2, 8, 10, 4], dtype="float64")
    result = _rolling_percentile(values, 4)

    for i in range(len(values)):
        window = values[max(0, i - 3):i + 1]
        expected = round(float((window < values[i]).sum()) / len(window) * 100)
        if len(window) < 2:
            assert pd.isna(result[i])
        else:
            assert result[i] == expected


def test_rolling_percentile_ignores_gaps():
    values = pd.Series([1.0, np.nan, 3.0, 2.0])
    result = _rolling_percentile(values, 4)
    assert pd.isna(result[1])
    # The window includes the current observation, as the original report did,
    # so a value can rank above at most n-1 of n and never reaches 100.
    assert result[2] == 50       # 3 beats 1 of the two valid observations
    assert result[3] == 33       # 2 beats 1 of three


CSV = textwrap.dedent("""\
    "Market_and_Exchange_Names","Report_Date_as_YYYY-MM-DD","CFTC_Contract_Market_Code","CFTC_Market_Code","CFTC_Region_Code","CFTC_Commodity_Code","Open_Interest_All","Prod_Merc_Positions_Long_All","Prod_Merc_Positions_Short_All","M_Money_Positions_Long_All","M_Money_Positions_Short_All","Change_in_Open_Interest_All","Change_in_Prod_Merc_Long_All","Change_in_Prod_Merc_Short_All","Change_in_M_Money_Long_All","Change_in_M_Money_Short_All"
    "CORN - CHICAGO BOARD OF TRADE","2026-01-06","002602","CBT","0","002",1000,400,900,300,100,10,5,-5,20,-10
    "CORN - CHICAGO BOARD OF TRADE","2026-01-13","002602","CBT","0","002",1100,420,800,350,90,100,20,-100,50,-10
    "NOT A MARKET WE TRACK","2026-01-13","999999","CBT","0","999",50,1,2,3,4,0,0,0,0,0
    """)


@pytest.fixture()
def built(tmp_path: Path):
    spec = REPORTS["disaggregated_fut"]
    source = tmp_path / "f_year.txt"
    source.write_text(CSV)

    conn = sqlite3.connect(":memory:")
    ensure_table(conn, spec)
    assert ingest_file(conn, spec, source) == 2      # the unlisted market is dropped

    frame = enrich(read_report(conn, spec), spec)
    return spec, frame, tmp_path


def test_ingest_keeps_leading_zero_contract_codes(built):
    _, frame, _ = built
    assert set(frame["contract_code"]) == {"002602"}
    assert set(frame["symbol"]) == {"ZC"}


def test_net_change_and_gap(built):
    _, frame, _ = built
    latest = frame[frame["report_date"] == "2026-01-13"].iloc[0]
    assert latest["producer_net"] == 420 - 800
    assert latest["managed_money_net"] == 350 - 90
    assert latest["producer_chg"] == 20 - -100
    # Gap is speculator minus commercial, using the first group of each stance.
    assert latest["gap_net"] == latest["managed_money_net"] - latest["producer_net"]


def test_export_round_trip(built, tmp_path):
    spec, frame, _ = built
    years = write_report_years(frame, spec, tmp_path / "data")
    assert years == [2026]

    payload = json.loads((tmp_path / "data" / spec.key / "2026.json").read_text())
    assert payload["dates"] == ["2026-01-06", "2026-01-13"]
    assert [m["symbol"] for m in payload["markets"]] == ["ZC"]
    assert payload["groups"]["producer"]["net"] == [[-500], [-380]]
    assert payload["open_interest"] == [[1000], [1100]]

    write_index([report_index_entry(spec, frame, years)], tmp_path / "data")
    index = json.loads((tmp_path / "data" / "index.json").read_text())
    assert index["latest_date"] == "2026-01-13"
    assert index["reports"][0]["key"] == spec.key


def test_every_report_carries_a_german_description():
    """The site can switch languages; a missing translation would render blank."""
    for spec in REPORTS.values():
        assert spec.description_de.strip()
        assert spec.description_de != spec.description


def test_price_targets_are_unique_and_non_empty():
    targets = price_targets()
    assert targets, "no market maps to a price ticker"
    assert all(ticker for ticker in targets.values())
    assert len(set(targets.values())) == len(targets)
    # Markets explicitly marked as having no comparable series stay out.
    for symbol, ticker in PRICE_SYMBOL_OVERRIDES.items():
        if ticker is None:
            assert symbol not in targets


def test_parse_series_uses_the_exchange_offset_and_skips_gaps():
    # 2026-01-05 23:00 UTC, which is 2026-01-06 at a +7200s exchange.
    payload = {"chart": {"result": [{
        "timestamp": [1767654000, 1767740400, 1767826800],
        "meta": {"gmtoffset": 7200},
        "indicators": {"quote": [{"close": [10.0, None, 12.5]}]},
    }]}}
    points = parse_series(payload)
    assert [p[1] for p in points] == [10.0, 12.5]
    assert points[0][0] == date(2026, 1, 6)


@pytest.mark.parametrize("payload", [
    {}, {"chart": {}}, {"chart": {"result": []}},
    {"chart": {"result": [{"timestamp": [], "indicators": {}}]}},
])
def test_parse_series_survives_a_reshaped_response(payload):
    assert parse_series(payload) == []


def test_as_of_carries_a_close_forward_but_not_indefinitely():
    points = [("2026-01-05", 10.0), ("2026-01-06", 11.0), ("2026-01-20", 12.0)]
    dates = ["2026-01-05", "2026-01-07", "2026-01-13", "2026-01-19", "2026-01-20", "2026-02-10"]
    # A holiday takes the previous close; a series that stopped goes empty
    # rather than drawing a flat line where there is no data.
    assert _as_of(points, dates) == [10.0, 11.0, 11.0, None, 12.0, None]


def test_weekly_closes_ignores_a_series_that_is_too_short(tmp_path):
    conn = sqlite3.connect(tmp_path / "p.db")
    ensure_prices_table(conn)
    conn.executemany("INSERT INTO prices (symbol, trade_date, close) VALUES (?, ?, ?)",
                     [("THIN", f"2026-01-{d:02d}", 1.0) for d in range(1, 6)])
    conn.commit()
    assert "THIN" not in weekly_closes(conn, ["2026-01-05"])


def test_update_all_never_raises_when_the_feed_is_broken(tmp_path, monkeypatch):
    """The weekly build's job is the COT history. A price feed that is down,
    throttled or returning nonsense must not be able to take that with it."""
    conn = sqlite3.connect(tmp_path / "p.db")

    for failure in (requests.RequestException("connection reset"),
                    ValueError("not json"),
                    RuntimeError("something else entirely")):
        def explode(*args, _exc=failure, **kwargs):
            raise _exc
        monkeypatch.setattr("cot.prices.fetch_series", explode)
        assert update_all(conn, date(2026, 1, 1), date(2026, 1, 8),
                          polite_delay=False) == 0

    monkeypatch.setattr("cot.prices.fetch_series", lambda *a, **k: [])
    assert update_all(conn, date(2026, 1, 1), date(2026, 1, 8), polite_delay=False) == 0


def test_update_all_gives_up_once_the_feed_stops_answering(tmp_path, monkeypatch):
    """A host the feed refuses outright would otherwise burn the full retry
    ladder on every one of the mapped markets."""
    conn = sqlite3.connect(tmp_path / "p.db")
    attempts = []

    def refuse(ticker, *args, **kwargs):
        attempts.append(ticker)
        return None

    monkeypatch.setattr("cot.prices.fetch_series", refuse)
    assert update_all(conn, date(2026, 1, 1), date(2026, 1, 8), polite_delay=False) == 0
    assert len(attempts) == MAX_CONSECUTIVE_FAILURES


def test_a_symbol_without_data_does_not_trip_the_breaker(tmp_path, monkeypatch):
    """An empty answer is a delisted contract, not a wall — the run carries on."""
    conn = sqlite3.connect(tmp_path / "p.db")
    seen = []

    def empty(ticker, *args, **kwargs):
        seen.append(ticker)
        return []

    monkeypatch.setattr("cot.prices.fetch_series", empty)
    update_all(conn, date(2026, 1, 1), date(2026, 1, 8), polite_delay=False)
    assert len(seen) == len(price_targets())


def _write_ini(directory: Path, extra: str = "") -> Path:
    path = directory / "config.ini"
    path.write_text(f"[app]\ncache_directory = {directory}/tmp\n{extra}")
    return path


def test_the_api_key_comes_from_the_environment(tmp_path, monkeypatch):
    monkeypatch.setenv(API_KEY_ENV, "from-env")
    assert Config.load(_write_ini(tmp_path)).api_key == "from-env"


def test_a_missing_api_key_is_none_rather_than_empty(tmp_path, monkeypatch):
    """So a caller can test truthiness and skip the feed instead of sending ''."""
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    assert Config.load(_write_ini(tmp_path)).api_key is None


def test_a_dotenv_file_supplies_the_key_for_local_runs(tmp_path, monkeypatch):
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    (tmp_path / ".env").write_text(f'# comment\n\n{API_KEY_ENV}="from-dotenv"\n')
    assert Config.load(_write_ini(tmp_path)).api_key == "from-dotenv"


def test_a_real_environment_variable_beats_dotenv(tmp_path, monkeypatch):
    """CI sets the secret; a .env checked out by accident must not shadow it."""
    monkeypatch.setenv(API_KEY_ENV, "from-env")
    (tmp_path / ".env").write_text(f"{API_KEY_ENV}=from-dotenv\n")
    assert Config.load(_write_ini(tmp_path)).api_key == "from-env"


def test_a_key_in_config_ini_is_refused(tmp_path, monkeypatch):
    """config.ini is committed, so a key there would ship on the next data push."""
    monkeypatch.setenv(API_KEY_ENV, "from-env")
    path = _write_ini(tmp_path, "alphavantage_api_key = leaked\n")
    with pytest.raises(ValueError, match="committed"):
        Config.load(path)
