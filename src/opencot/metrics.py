"""Derived COT metrics: net positioning, COT index, % of OI, week-over-week change."""

from __future__ import annotations

import pandas as pd

# These are aggregate columns, not individual trader classes — skip them.
_EXCLUDED_CLASSES = {"total_reportable"}


def add_metrics(df: pd.DataFrame, cot_index_window: int = 156) -> pd.DataFrame:
    """
    Compute and append all derived metrics to a normalized COT DataFrame.

    Detects trader classes automatically from the ``*_long_*`` / ``*_short_*``
    column pairs present in the DataFrame, so it works across all report types.

    Adds the following columns for each trader class found:

    - ``net_{class}`` — long minus short
    - ``net_{class}_pct_oi`` — net as % of ``open_interest_all``
    - ``change_{class}`` — week-over-week change in net positioning
    - ``cot_index_{class}`` — rolling position index, 0–100

    Parameters
    ----------
    df : pd.DataFrame
        Normalized COT DataFrame for a **single instrument**, sorted or
        unsorted. Must be the output of ``parse.normalize_columns``.
    cot_index_window : int
        Rolling window in weeks for the COT index. Default 156 (~3 years).
        Uses an expanding window for rows with fewer than ``cot_index_window``
        observations.

    Returns
    -------
    pd.DataFrame
        Original rows with derived metric columns appended, sorted ascending
        by ``report_date``.
    """
    df = df.sort_values("report_date").reset_index(drop=True)

    for class_name, long_col, short_col in _find_position_pairs(df):
        net = df[long_col] - df[short_col]

        df[f"net_{class_name}"] = net

        if "open_interest_all" in df.columns:
            df[f"net_{class_name}_pct_oi"] = net / df["open_interest_all"] * 100

        df[f"change_{class_name}"] = net.diff(1)
        df[f"cot_index_{class_name}"] = _cot_index(net, cot_index_window)

    return df


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_position_pairs(df: pd.DataFrame) -> list[tuple[str, str, str]]:
    """Return (class_name, long_col, short_col) for every matched pair in df."""
    pairs: list[tuple[str, str, str]] = []
    seen: set[str] = set()

    for col in df.columns:
        if "_long_" not in col:
            continue
        short_col = col.replace("_long_", "_short_", 1)
        if short_col not in df.columns:
            continue
        class_name = col[: col.index("_long_")]
        if class_name in seen or class_name in _EXCLUDED_CLASSES:
            continue
        seen.add(class_name)
        pairs.append((class_name, col, short_col))

    return pairs


def _cot_index(series: pd.Series, window: int) -> pd.Series:
    """Scale net positioning to 0–100 vs its rolling min/max."""
    rolling_min = series.rolling(window, min_periods=1).min()
    rolling_max = series.rolling(window, min_periods=1).max()
    denom = rolling_max - rolling_min
    # When max == min (flat positioning), index is undefined — return NaN.
    denom = denom.where(denom != 0, other=float("nan"))
    return (series - rolling_min) / denom * 100
