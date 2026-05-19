"""opencot — CFTC Commitment of Traders data, clean and Pythonic."""

from __future__ import annotations

import pandas as pd

from .fetch import clear_cache, fetch_raw
from .instruments import list_instruments
from .types import Report, Variant

__all__ = ["get", "instruments", "clear_cache", "fetch_raw"]
__version__ = "0.1.0"


def get(
    instrument: str,
    report: Report = "disaggregated",
    variant: Variant = "futures_only",
    years: int = 3,
) -> pd.DataFrame:
    """
    Fetch COT data for an instrument, with derived metrics pre-computed.

    Parameters
    ----------
    instrument : str
        Human-readable instrument name, e.g. 'Gold', 'Crude', 'EUR'.
    report : Report
        One of 'legacy', 'supplemental', 'disaggregated', 'tff'.
    variant : Variant
        'futures_only' or 'futures_and_options'.
    years : int
        Number of years of history to fetch (counting back from today).

    Returns
    -------
    pd.DataFrame
        Normalized COT data with derived metrics (net_*, cot_index, change_*).
    """
    raise NotImplementedError


def instruments(report: Report = "disaggregated") -> pd.DataFrame:
    """
    List all instruments available for a given report type.

    Parameters
    ----------
    report : Report
        One of 'legacy', 'supplemental', 'disaggregated', 'tff'.

    Returns
    -------
    pd.DataFrame
        Columns: market_name, cftc_code, exchange.
    """
    return list_instruments(report)
