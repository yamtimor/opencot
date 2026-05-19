"""Human-readable instrument name → CFTC market code lookup with fuzzy matching."""

from __future__ import annotations

import pandas as pd

from .types import Report


def resolve_instrument(name: str, report: Report) -> str:
    """
    Resolve a human-readable instrument name to the CFTC market name string.

    Supports exact matches and fuzzy matching (e.g. 'Gold', 'Crude', 'EUR').

    Parameters
    ----------
    name : str
        Human-readable instrument name.
    report : Report
        Report type to search within.

    Returns
    -------
    str
        The exact CFTC market name string used in the data files.

    Raises
    ------
    ValueError
        If no match is found.
    """
    raise NotImplementedError


def list_instruments(report: Report) -> pd.DataFrame:
    """
    Return a DataFrame of all available instruments for a given report type.

    Parameters
    ----------
    report : Report
        One of 'legacy', 'supplemental', 'disaggregated', 'tff'.

    Returns
    -------
    pd.DataFrame
        Columns: market_name, cftc_code, exchange.
    """
    raise NotImplementedError
