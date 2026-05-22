"""Human-readable instrument name → CFTC market string lookup with fuzzy matching."""

from __future__ import annotations

from datetime import date

import pandas as pd

from .fetch import _EARLIEST_YEAR, fetch_raw
from .parse import normalize_columns
from .types import Report, Variant

# Process-level cache: avoids re-downloading the instrument list on every call.
# Keyed by report type; variant is fixed per report (see _variant_for).
_instrument_cache: dict[Report, pd.DataFrame] = {}

# Supplemental is only available as futures_and_options.
_VARIANT_FOR: dict[Report, Variant] = {
    "legacy": "futures_only",
    "supplemental": "futures_and_options",
    "disaggregated": "futures_only",
    "tff": "futures_only",
}


def resolve_instrument(name: str, report: Report) -> str:
    """
    Resolve a human-readable name to the exact CFTC market name string.

    Matching is case-insensitive. An exact match is preferred; if none,
    falls back to substring matching. Raises if zero or multiple matches
    remain ambiguous.

    Parameters
    ----------
    name : str
        Human-readable search term, e.g. ``'Gold'``, ``'Crude'``, ``'EUR'``.
    report : Report
        Report type to search within.

    Returns
    -------
    str
        The exact CFTC market name string used in the data files.

    Raises
    ------
    ValueError
        If no match is found, or if multiple substring matches are ambiguous.
    """
    df = list_instruments(report)
    market_names: list[str] = df["market_name"].tolist()

    # 1. Exact case-insensitive match
    exact = [m for m in market_names if m.lower() == name.lower()]
    if len(exact) == 1:
        return exact[0]

    # 2. Substring match
    needle = name.lower()
    matches = [m for m in market_names if needle in m.lower()]

    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        raise ValueError(
            f"'{name}' matches {len(matches)} instruments in '{report}'. "
            f"Be more specific. Matches:\n" + "\n".join(f"  {m}" for m in matches)
        )

    raise ValueError(
        f"No instrument matching '{name}' found in '{report}'. "
        f"Use cot.instruments(report='{report}') to see available instruments."
    )


def list_instruments(report: Report) -> pd.DataFrame:
    """
    Return a DataFrame of all instruments available for a given report type.

    The list is sourced from the previous calendar year's data file and
    cached in memory for the lifetime of the process.

    Parameters
    ----------
    report : Report
        One of ``'legacy'``, ``'supplemental'``, ``'disaggregated'``, ``'tff'``.

    Returns
    -------
    pd.DataFrame
        Columns: ``market_name``, ``cftc_contract_code``, ``exchange``.
        Sorted alphabetically by ``market_name``.
    """
    if report not in _instrument_cache:
        _instrument_cache[report] = _build_instrument_list(report)
    return _instrument_cache[report]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_instrument_list(report: Report) -> pd.DataFrame:
    variant = _VARIANT_FOR[report]
    year = _reference_year(report)

    df_raw = fetch_raw(report, year, variant)
    df = normalize_columns(df_raw, report)

    instruments = (
        df[["market_name", "cftc_contract_code"]]
        .drop_duplicates(subset="market_name")
        .copy()
    )

    # Split "INSTRUMENT NAME - EXCHANGE NAME" into separate columns.
    # Some names don't contain " - ", so fill_value keeps them intact.
    split = instruments["market_name"].str.rsplit(" - ", n=1, expand=True)
    instruments["exchange"] = split[1].fillna("") if 1 in split.columns else ""

    return instruments[["market_name", "cftc_contract_code", "exchange"]].sort_values(
        "market_name", ignore_index=True
    )


def _reference_year(report: Report) -> int:
    """Previous calendar year, clamped to the report's earliest available year."""
    return max(date.today().year - 1, _EARLIEST_YEAR[report])
