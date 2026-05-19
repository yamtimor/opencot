"""CFTC ZIP file downloading and local caching."""

from __future__ import annotations

import pandas as pd

from .types import Report, Variant


def fetch_raw(report: Report, year: int, variant: Variant = "futures_only") -> pd.DataFrame:
    """
    Download and return raw COT data for a single year.

    Parameters
    ----------
    report : Report
        One of 'legacy', 'supplemental', 'disaggregated', 'tff'.
    year : int
        The calendar year to fetch.
    variant : Variant
        'futures_only' or 'futures_and_options'.

    Returns
    -------
    pd.DataFrame
        Raw, unparsed data for the requested year.
    """
    raise NotImplementedError


def clear_cache() -> None:
    """Remove all locally cached CFTC data files."""
    raise NotImplementedError
