"""Checks on the parts that would fail silently in an unattended weekly run."""

import json
import sqlite3
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from cot.download import normalize_column
from cot.export import report_index_entry, write_index, write_report_years
from cot.markets import COMMODITY_MARKETS, FINANCIAL_MARKETS
from cot.metrics import _rolling_percentile, enrich
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
