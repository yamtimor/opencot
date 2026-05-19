"""ZIP/CSV parsing and column name normalization."""

from __future__ import annotations

import pandas as pd

from .types import Report


def parse_zip(data: bytes, report: Report) -> pd.DataFrame:
    """
    Parse a CFTC ZIP archive and return a normalized DataFrame.

    Parameters
    ----------
    data : bytes
        Raw ZIP file bytes downloaded from cftc.gov.
    report : Report
        Report type, used to select the correct column mapping.

    Returns
    -------
    pd.DataFrame
        DataFrame with snake_case column names normalized across report types.
    """
    raise NotImplementedError


def normalize_columns(df: pd.DataFrame, report: Report) -> pd.DataFrame:
    """
    Rename raw CFTC column names to consistent snake_case names.

    Parameters
    ----------
    df : pd.DataFrame
        Raw DataFrame with original CFTC column names.
    report : Report
        Report type to select the correct column mapping.

    Returns
    -------
    pd.DataFrame
        DataFrame with normalized column names.
    """
    raise NotImplementedError
