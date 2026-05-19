"""Tests for parse.py — column normalization and ZIP extraction."""

from __future__ import annotations

import io
import zipfile

import pandas as pd
import pytest

from opencot.parse import _to_snake, normalize_columns, parse_zip


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_zip(csv_content: str, filename: str = "annual.txt") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(filename, csv_content)
    return buf.getvalue()


def _legacy_df() -> pd.DataFrame:
    return pd.DataFrame({
        "Market and Exchange Names": ["GOLD - COMMODITY EXCHANGE INC."],
        "As of Date in Form YYMMDD": [241231],
        "As of Date in Form YYYY-MM-DD": ["2024-12-31"],
        "CFTC Contract Market Code": ["088691"],
        "CFTC Market Code in Initials": ["CMX"],
        "CFTC Region Code": ["0"],
        "CFTC Commodity Code": ["088"],
        "Open Interest (All)": [500000],
        "Noncommercial Positions-Long (All)": [200000],
        "Noncommercial Positions-Short (All)": [100000],
        "Noncommercial Positions-Spreading (All)": [50000],
        "Commercial Positions-Long (All)": [150000],
        "Commercial Positions-Short (All)": [250000],
        "Total Reportable Positions-Long (All)": [400000],
        "Total Reportable Positions-Short (All)": [400000],
        "Nonreportable Positions-Long (All)": [100000],
        "Nonreportable Positions-Short (All)": [100000],
    })


def _disagg_df() -> pd.DataFrame:
    return pd.DataFrame({
        "Market_and_Exchange_Names": ["GOLD - COMMODITY EXCHANGE INC."],
        "As_of_Date_In_Form_YYMMDD": [241231],
        "Report_Date_as_YYYY-MM-DD": ["2024-12-31"],
        "CFTC_Contract_Market_Code": ["088691"],
        "CFTC_Market_Code": ["CMX"],
        "CFTC_Region_Code": ["0"],
        "CFTC_Commodity_Code": ["088"],
        "Open_Interest_All": [500000],
        "Prod_Merc_Positions_Long_All": [100000],
        "Prod_Merc_Positions_Short_All": [200000],
        "Swap_Positions_Long_All": [50000],
        "Swap__Positions_Short_All": [60000],
        "Swap__Positions_Spread_All": [10000],
        "M_Money_Positions_Long_All": [150000],
        "M_Money_Positions_Short_All": [80000],
        "M_Money_Positions_Spread_All": [20000],
        "Other_Rept_Positions_Long_All": [30000],
        "Other_Rept_Positions_Short_All": [40000],
        "Other_Rept_Positions_Spread_All": [5000],
        "Tot_Rept_Positions_Long_All": [330000],
        "Tot_Rept_Positions_Short_All": [380000],
        "NonRept_Positions_Long_All": [170000],
        "NonRept_Positions_Short_All": [120000],
    })


def _tff_df() -> pd.DataFrame:
    return pd.DataFrame({
        "Market_and_Exchange_Names": ["10-YEAR U.S. TREASURY NOTES"],
        "As_of_Date_In_Form_YYMMDD": [241231],
        "Report_Date_as_YYYY-MM-DD": ["2024-12-31"],
        "CFTC_Contract_Market_Code": ["020601"],
        "CFTC_Market_Code": ["CBT"],
        "CFTC_Region_Code": ["0"],
        "CFTC_Commodity_Code": ["020"],
        "Open_Interest_All": [4000000],
        "Dealer_Positions_Long_All": [800000],
        "Dealer_Positions_Short_All": [1200000],
        "Dealer_Positions_Spread_All": [100000],
        "Asset_Mgr_Positions_Long_All": [1500000],
        "Asset_Mgr_Positions_Short_All": [700000],
        "Asset_Mgr_Positions_Spread_All": [150000],
        "Lev_Money_Positions_Long_All": [400000],
        "Lev_Money_Positions_Short_All": [600000],
        "Lev_Money_Positions_Spread_All": [80000],
        "Other_Rept_Positions_Long_All": [200000],
        "Other_Rept_Positions_Short_All": [300000],
        "Other_Rept_Positions_Spread_All": [50000],
        "Tot_Rept_Positions_Long_All": [2900000],
        "Tot_Rept_Positions_Short_All": [2800000],
        "NonRept_Positions_Long_All": [1100000],
        "NonRept_Positions_Short_All": [1200000],
    })


# ---------------------------------------------------------------------------
# _to_snake
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    ("Open Interest (All)", "open_interest_all"),
    ("Market and Exchange Names", "market_and_exchange_names"),
    ("Noncommercial Positions-Long (All)", "noncommercial_positions_long_all"),
    ("Open_Interest_All", "open_interest_all"),
    ("Swap__Positions_Short_All", "swap_positions_short_all"),
    ("As_of_Date_In_Form_YYYY-MM-DD", "as_of_date_in_form_yyyy_mm_dd"),
])
def test_to_snake(raw, expected):
    assert _to_snake(raw) == expected


# ---------------------------------------------------------------------------
# normalize_columns — shared metadata
# ---------------------------------------------------------------------------

def test_normalize_metadata_legacy():
    df = normalize_columns(_legacy_df(), "legacy")
    assert "market_name" in df.columns
    assert "report_date" in df.columns
    assert "open_interest_all" in df.columns
    assert "cftc_contract_code" in df.columns


def test_normalize_metadata_disaggregated():
    df = normalize_columns(_disagg_df(), "disaggregated")
    assert "market_name" in df.columns
    assert "report_date" in df.columns
    assert "open_interest_all" in df.columns


def test_report_date_is_datetime():
    for report, make_df in [
        ("legacy", _legacy_df),
        ("disaggregated", _disagg_df),
        ("tff", _tff_df),
    ]:
        df = normalize_columns(make_df(), report)
        assert pd.api.types.is_datetime64_any_dtype(df["report_date"]), report


# ---------------------------------------------------------------------------
# normalize_columns — position columns
# ---------------------------------------------------------------------------

def test_legacy_position_columns():
    df = normalize_columns(_legacy_df(), "legacy")
    assert "noncommercial_long_all" in df.columns
    assert "noncommercial_short_all" in df.columns
    assert "commercial_long_all" in df.columns
    assert "commercial_short_all" in df.columns
    assert "nonreportable_long_all" in df.columns
    assert "nonreportable_short_all" in df.columns


def test_disagg_position_columns():
    df = normalize_columns(_disagg_df(), "disaggregated")
    assert "producer_merchant_long_all" in df.columns
    assert "producer_merchant_short_all" in df.columns
    assert "swap_dealer_long_all" in df.columns
    assert "swap_dealer_short_all" in df.columns
    assert "swap_dealer_spread_all" in df.columns
    assert "money_manager_long_all" in df.columns
    assert "money_manager_short_all" in df.columns
    assert "other_reportable_long_all" in df.columns
    assert "nonreportable_long_all" in df.columns


def test_tff_position_columns():
    df = normalize_columns(_tff_df(), "tff")
    assert "dealer_long_all" in df.columns
    assert "dealer_short_all" in df.columns
    assert "asset_manager_long_all" in df.columns
    assert "asset_manager_short_all" in df.columns
    assert "leveraged_money_long_all" in df.columns
    assert "leveraged_money_short_all" in df.columns


def test_no_raw_cftc_names_survive_for_explicit_columns():
    """Explicitly mapped columns must not keep their raw CFTC name."""
    df = normalize_columns(_disagg_df(), "disaggregated")
    assert "M_Money_Positions_Long_All" not in df.columns
    assert "Swap__Positions_Short_All" not in df.columns
    assert "Market_and_Exchange_Names" not in df.columns


# ---------------------------------------------------------------------------
# parse_zip
# ---------------------------------------------------------------------------

LEGACY_CSV = (
    "Market and Exchange Names,As of Date in Form YYMMDD,"
    "As of Date in Form YYYY-MM-DD,CFTC Contract Market Code,"
    "CFTC Market Code in Initials,CFTC Region Code,CFTC Commodity Code,"
    "Open Interest (All),Noncommercial Positions-Long (All),"
    "Noncommercial Positions-Short (All),Noncommercial Positions-Spreading (All),"
    "Commercial Positions-Long (All),Commercial Positions-Short (All),"
    "Total Reportable Positions-Long (All),Total Reportable Positions-Short (All),"
    "Nonreportable Positions-Long (All),Nonreportable Positions-Short (All)\n"
    "GOLD - COMMODITY EXCHANGE INC.,241231,2024-12-31,088691,CMX,0,088,"
    "500000,200000,100000,50000,150000,250000,400000,400000,100000,100000\n"
)


def test_parse_zip_returns_normalized_dataframe():
    data = _make_zip(LEGACY_CSV)
    df = parse_zip(data, "legacy")
    assert isinstance(df, pd.DataFrame)
    assert "market_name" in df.columns
    assert "money_manager_long_all" not in df.columns  # not in legacy
    assert pd.api.types.is_datetime64_any_dtype(df["report_date"])


def test_parse_zip_raises_on_empty_zip():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w"):
        pass
    with pytest.raises(ValueError, match="No .txt file"):
        parse_zip(buf.getvalue(), "legacy")
