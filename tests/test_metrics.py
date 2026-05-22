"""Tests for metrics.py — net positioning, COT index, % of OI, change."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from opencot.metrics import _cot_index, _find_position_pairs, add_metrics


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _disagg_df(n: int = 10) -> pd.DataFrame:
    """Minimal disaggregated-style DataFrame with money_manager and producer_merchant."""
    dates = pd.date_range("2024-01-05", periods=n, freq="W-FRI")
    return pd.DataFrame({
        "report_date": dates,
        "market_name": ["GOLD - COMMODITY EXCHANGE INC."] * n,
        "open_interest_all": [500_000 + i * 1_000 for i in range(n)],
        "money_manager_long_all": [150_000 + i * 500 for i in range(n)],
        "money_manager_short_all": [80_000 + i * 200 for i in range(n)],
        "producer_merchant_long_all": [100_000 - i * 300 for i in range(n)],
        "producer_merchant_short_all": [200_000 + i * 100 for i in range(n)],
        "total_reportable_long_all": [400_000] * n,  # should be excluded
        "total_reportable_short_all": [400_000] * n,
    })


def _legacy_df(n: int = 10) -> pd.DataFrame:
    dates = pd.date_range("2024-01-05", periods=n, freq="W-FRI")
    return pd.DataFrame({
        "report_date": dates,
        "market_name": ["GOLD - COMMODITY EXCHANGE INC."] * n,
        "open_interest_all": [500_000] * n,
        "noncommercial_long_all": [200_000 + i * 1_000 for i in range(n)],
        "noncommercial_short_all": [100_000 + i * 500 for i in range(n)],
        "commercial_long_all": [150_000] * n,
        "commercial_short_all": [250_000] * n,
        "nonreportable_long_all": [100_000] * n,
        "nonreportable_short_all": [100_000] * n,
        "total_reportable_long_all": [400_000] * n,
        "total_reportable_short_all": [400_000] * n,
    })


# ---------------------------------------------------------------------------
# _find_position_pairs
# ---------------------------------------------------------------------------

def test_find_position_pairs_detects_classes():
    df = _disagg_df()
    pairs = _find_position_pairs(df)
    class_names = [p[0] for p in pairs]
    assert "money_manager" in class_names
    assert "producer_merchant" in class_names


def test_find_position_pairs_excludes_total_reportable():
    df = _disagg_df()
    pairs = _find_position_pairs(df)
    class_names = [p[0] for p in pairs]
    assert "total_reportable" not in class_names


def test_find_position_pairs_returns_correct_column_names():
    df = _disagg_df()
    pairs = _find_position_pairs(df)
    mm = next(p for p in pairs if p[0] == "money_manager")
    assert mm[1] == "money_manager_long_all"
    assert mm[2] == "money_manager_short_all"


# ---------------------------------------------------------------------------
# _cot_index
# ---------------------------------------------------------------------------

def test_cot_index_bounded_0_to_100():
    s = pd.Series([100, 200, 150, 50, 300, 250, 175])
    result = _cot_index(s, window=4)
    valid = result.dropna()
    assert (valid >= 0).all() and (valid <= 100).all()


def test_cot_index_extremes():
    # Monotonically increasing: current is always the rolling max → always 100
    s_up = pd.Series([100.0, 200.0, 300.0, 400.0, 500.0])
    result_up = _cot_index(s_up, window=5)
    assert result_up.iloc[-1] == pytest.approx(100.0)
    assert pd.isna(result_up.iloc[0])  # single point → NaN

    # Monotonically decreasing: current is always the rolling min → always 0
    s_down = pd.Series([500.0, 400.0, 300.0, 200.0, 100.0])
    result_down = _cot_index(s_down, window=5)
    assert result_down.iloc[-1] == pytest.approx(0.0)


def test_cot_index_flat_series_returns_nan():
    s = pd.Series([100.0] * 5)
    result = _cot_index(s, window=5)
    assert result.isna().all()


def test_cot_index_uses_expanding_window_for_early_rows():
    s = pd.Series([10.0, 20.0, 30.0])
    # window=10 but only 3 rows; first row is NaN (single point, min==max),
    # subsequent rows have a range and produce valid values.
    result = _cot_index(s, window=10)
    assert result.iloc[1:].notna().all()


# ---------------------------------------------------------------------------
# add_metrics — net positioning
# ---------------------------------------------------------------------------

def test_net_positioning_is_long_minus_short():
    df = add_metrics(_disagg_df())
    expected = df["money_manager_long_all"] - df["money_manager_short_all"]
    pd.testing.assert_series_equal(df["net_money_manager"], expected, check_names=False)


def test_net_columns_added_for_all_classes():
    df = add_metrics(_disagg_df())
    assert "net_money_manager" in df.columns
    assert "net_producer_merchant" in df.columns


def test_net_total_reportable_not_added():
    df = add_metrics(_disagg_df())
    assert "net_total_reportable" not in df.columns


# ---------------------------------------------------------------------------
# add_metrics — % of OI
# ---------------------------------------------------------------------------

def test_net_pct_oi_formula():
    df = add_metrics(_disagg_df())
    expected = df["net_money_manager"] / df["open_interest_all"] * 100
    pd.testing.assert_series_equal(
        df["net_money_manager_pct_oi"], expected, check_names=False
    )


def test_net_pct_oi_not_added_without_open_interest():
    df = _disagg_df().drop(columns=["open_interest_all"])
    result = add_metrics(df)
    assert "net_money_manager_pct_oi" not in result.columns


# ---------------------------------------------------------------------------
# add_metrics — change (week-over-week)
# ---------------------------------------------------------------------------

def test_change_is_week_over_week_diff():
    df = add_metrics(_disagg_df())
    expected = df["net_money_manager"].diff(1)
    pd.testing.assert_series_equal(df["change_money_manager"], expected, check_names=False)


def test_first_change_row_is_nan():
    df = add_metrics(_disagg_df())
    assert pd.isna(df["change_money_manager"].iloc[0])


# ---------------------------------------------------------------------------
# add_metrics — COT index
# ---------------------------------------------------------------------------

def test_cot_index_columns_added():
    df = add_metrics(_disagg_df())
    assert "cot_index_money_manager" in df.columns
    assert "cot_index_producer_merchant" in df.columns


def test_cot_index_in_range():
    df = add_metrics(_disagg_df(n=20))
    valid = df["cot_index_money_manager"].dropna()
    assert (valid >= 0).all() and (valid <= 100).all()


# ---------------------------------------------------------------------------
# add_metrics — sorting and legacy report
# ---------------------------------------------------------------------------

def test_output_sorted_by_report_date():
    df = _disagg_df().sample(frac=1, random_state=42)  # shuffle
    result = add_metrics(df)
    assert result["report_date"].is_monotonic_increasing


def test_works_with_legacy_report():
    df = add_metrics(_legacy_df())
    assert "net_noncommercial" in df.columns
    assert "net_commercial" in df.columns
    assert "cot_index_noncommercial" in df.columns
