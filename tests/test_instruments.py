"""Tests for instruments.py — lookup, fuzzy matching, and instrument listing."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from opencot.instruments import (
    _build_instrument_list,
    _instrument_cache,
    _reference_year,
    list_instruments,
    resolve_instrument,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DISAGG_RAW = pd.DataFrame({
    "Market_and_Exchange_Names": [
        "GOLD - COMMODITY EXCHANGE INC.",
        "SILVER - COMMODITY EXCHANGE INC.",
        "CRUDE OIL, LIGHT SWEET - NEW YORK MERCANTILE EXCHANGE",
        "GOLD MINI - COMMODITY EXCHANGE INC.",
    ],
    "As_of_Date_In_Form_YYMMDD": [241231] * 4,
    "Report_Date_as_YYYY-MM-DD": ["2024-12-31"] * 4,
    "CFTC_Contract_Market_Code": ["088691", "084691", "067651", "088692"],
    "CFTC_Market_Code": ["CMX", "CMX", "NYM", "CMX"],
    "CFTC_Region_Code": ["0"] * 4,
    "CFTC_Commodity_Code": ["088", "084", "067", "088"],
    "Open_Interest_All": [500000, 100000, 2000000, 50000],
    "Prod_Merc_Positions_Long_All": [100000, 20000, 400000, 10000],
    "Prod_Merc_Positions_Short_All": [200000, 40000, 800000, 20000],
    "Swap_Positions_Long_All": [50000, 10000, 200000, 5000],
    "Swap__Positions_Short_All": [60000, 12000, 240000, 6000],
    "Swap__Positions_Spread_All": [10000, 2000, 40000, 1000],
    "M_Money_Positions_Long_All": [150000, 30000, 600000, 15000],
    "M_Money_Positions_Short_All": [80000, 16000, 320000, 8000],
    "M_Money_Positions_Spread_All": [20000, 4000, 80000, 2000],
    "Other_Rept_Positions_Long_All": [30000, 6000, 120000, 3000],
    "Other_Rept_Positions_Short_All": [40000, 8000, 160000, 4000],
    "Other_Rept_Positions_Spread_All": [5000, 1000, 20000, 500],
    "Tot_Rept_Positions_Long_All": [330000, 66000, 1320000, 33000],
    "Tot_Rept_Positions_Short_All": [380000, 76000, 1520000, 38000],
    "NonRept_Positions_Long_All": [170000, 34000, 680000, 17000],
    "NonRept_Positions_Short_All": [120000, 24000, 480000, 12000],
})


def _patch_fetch(raw_df: pd.DataFrame):
    """Context manager: patches fetch_raw to return raw_df without network."""
    return patch("opencot.instruments.fetch_raw", return_value=raw_df)


# ---------------------------------------------------------------------------
# _reference_year
# ---------------------------------------------------------------------------

def test_reference_year_is_previous_year():
    from datetime import date
    assert _reference_year("disaggregated") == date.today().year - 1


def test_reference_year_clamped_to_earliest():
    # tff earliest is 2011; if today.year - 1 < 2011 this would clamp (won't happen
    # in practice, but the logic should be correct)
    year = _reference_year("tff")
    assert year >= 2011


# ---------------------------------------------------------------------------
# list_instruments
# ---------------------------------------------------------------------------

def test_list_instruments_returns_dataframe():
    _instrument_cache.clear()
    with _patch_fetch(DISAGG_RAW):
        df = list_instruments("disaggregated")
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["market_name", "cftc_contract_code", "exchange"]


def test_list_instruments_sorted_alphabetically():
    _instrument_cache.clear()
    with _patch_fetch(DISAGG_RAW):
        df = list_instruments("disaggregated")
    assert df["market_name"].is_monotonic_increasing


def test_list_instruments_extracts_exchange():
    _instrument_cache.clear()
    with _patch_fetch(DISAGG_RAW):
        df = list_instruments("disaggregated")
    gold_row = df[df["market_name"] == "GOLD - COMMODITY EXCHANGE INC."]
    assert gold_row["exchange"].iloc[0] == "COMMODITY EXCHANGE INC."


def test_list_instruments_uses_memory_cache():
    _instrument_cache.clear()
    with _patch_fetch(DISAGG_RAW) as mock_fetch:
        list_instruments("disaggregated")
        list_instruments("disaggregated")
    assert mock_fetch.call_count == 1


def test_list_instruments_deduplicates_market_names():
    df_with_dupes = pd.concat([DISAGG_RAW, DISAGG_RAW], ignore_index=True)
    _instrument_cache.clear()
    with _patch_fetch(df_with_dupes):
        df = list_instruments("disaggregated")
    assert df["market_name"].nunique() == len(df)


# ---------------------------------------------------------------------------
# resolve_instrument
# ---------------------------------------------------------------------------

def test_resolve_exact_match_case_insensitive():
    _instrument_cache.clear()
    with _patch_fetch(DISAGG_RAW):
        result = resolve_instrument("gold - commodity exchange inc.", "disaggregated")
    assert result == "GOLD - COMMODITY EXCHANGE INC."


def test_resolve_substring_single_match():
    _instrument_cache.clear()
    with _patch_fetch(DISAGG_RAW):
        result = resolve_instrument("Silver", "disaggregated")
    assert result == "SILVER - COMMODITY EXCHANGE INC."


def test_resolve_substring_crude():
    _instrument_cache.clear()
    with _patch_fetch(DISAGG_RAW):
        result = resolve_instrument("CRUDE OIL", "disaggregated")
    assert result == "CRUDE OIL, LIGHT SWEET - NEW YORK MERCANTILE EXCHANGE"


def test_resolve_ambiguous_raises_with_matches():
    # "GOLD" matches both "GOLD - ..." and "GOLD MINI - ..."
    _instrument_cache.clear()
    with _patch_fetch(DISAGG_RAW):
        with pytest.raises(ValueError, match="matches 2 instruments"):
            resolve_instrument("Gold", "disaggregated")


def test_resolve_no_match_raises():
    _instrument_cache.clear()
    with _patch_fetch(DISAGG_RAW):
        with pytest.raises(ValueError, match="No instrument matching"):
            resolve_instrument("Platinum", "disaggregated")


def test_resolve_no_match_suggests_instruments_call():
    _instrument_cache.clear()
    with _patch_fetch(DISAGG_RAW):
        with pytest.raises(ValueError, match="cot.instruments"):
            resolve_instrument("Nonexistent", "disaggregated")
