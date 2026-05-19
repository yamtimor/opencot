"""Derived COT metrics: net positioning, COT index, % of OI, week-over-week change."""

from __future__ import annotations

import pandas as pd


def add_metrics(df: pd.DataFrame, cot_index_window: int = 156) -> pd.DataFrame:
    """
    Compute and append all derived metrics to a normalized COT DataFrame.

    Adds net_*, net_*_pct_oi, change_*, and cot_index columns.

    Parameters
    ----------
    df : pd.DataFrame
        Normalized COT DataFrame (output of parse.normalize_columns).
    cot_index_window : int
        Rolling window in weeks for the COT index calculation. Default 156 (~3 years).

    Returns
    -------
    pd.DataFrame
        Original DataFrame with derived metric columns appended.
    """
    raise NotImplementedError
