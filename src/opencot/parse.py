"""ZIP/CSV extraction and column name normalization across all CFTC report types."""

from __future__ import annotations

import io
import re
import zipfile

import pandas as pd

from .types import Report

# ---------------------------------------------------------------------------
# Shared metadata renames — covers both Legacy (space-delimited) and
# newer (underscore-delimited) formats
# ---------------------------------------------------------------------------

_SHARED_RENAMES: dict[str, str] = {
    # Instrument name
    "Market and Exchange Names": "market_name",
    "Market_and_Exchange_Names": "market_name",
    # Date (YYMMDD integer — kept for reference)
    "As of Date in Form YYMMDD": "as_of_date",
    "As_of_Date_In_Form_YYMMDD": "as_of_date",
    # Date (ISO string — parsed to datetime in normalize_columns)
    "As of Date in Form YYYY-MM-DD": "report_date",
    "As_of_Date_In_Form_YYYY-MM-DD": "report_date",
    "Report_Date_as_YYYY-MM-DD": "report_date",
    # CFTC identifiers
    "CFTC Contract Market Code": "cftc_contract_code",
    "CFTC_Contract_Market_Code": "cftc_contract_code",
    "CFTC Market Code in Initials": "cftc_market_code",
    "CFTC_Market_Code": "cftc_market_code",
    "CFTC Region Code": "cftc_region_code",
    "CFTC_Region_Code": "cftc_region_code",
    "CFTC Commodity Code": "cftc_commodity_code",
    "CFTC_Commodity_Code": "cftc_commodity_code",
    # Open interest
    "Open Interest (All)": "open_interest_all",
    "Open_Interest_All": "open_interest_all",
    "Open Interest (Old)": "open_interest_old",
    "Open_Interest_Old": "open_interest_old",
    "Open Interest (Other)": "open_interest_other",
    "Open_Interest_Other": "open_interest_other",
}

# ---------------------------------------------------------------------------
# Legacy position columns — drop the redundant "Positions" word
# ---------------------------------------------------------------------------

_LEGACY_RENAMES: dict[str, str] = {
    "Noncommercial Positions-Long (All)": "noncommercial_long_all",
    "Noncommercial Positions-Short (All)": "noncommercial_short_all",
    "Noncommercial Positions-Spreading (All)": "noncommercial_spread_all",
    "Commercial Positions-Long (All)": "commercial_long_all",
    "Commercial Positions-Short (All)": "commercial_short_all",
    "Total Reportable Positions-Long (All)": "total_reportable_long_all",
    "Total Reportable Positions-Short (All)": "total_reportable_short_all",
    "Nonreportable Positions-Long (All)": "nonreportable_long_all",
    "Nonreportable Positions-Short (All)": "nonreportable_short_all",
    "Noncommercial Positions-Long (Old)": "noncommercial_long_old",
    "Noncommercial Positions-Short (Old)": "noncommercial_short_old",
    "Noncommercial Positions-Spreading (Old)": "noncommercial_spread_old",
    "Commercial Positions-Long (Old)": "commercial_long_old",
    "Commercial Positions-Short (Old)": "commercial_short_old",
    "Total Reportable Positions-Long (Old)": "total_reportable_long_old",
    "Total Reportable Positions-Short (Old)": "total_reportable_short_old",
    "Nonreportable Positions-Long (Old)": "nonreportable_long_old",
    "Nonreportable Positions-Short (Old)": "nonreportable_short_old",
    "Noncommercial Positions-Long (Other)": "noncommercial_long_other",
    "Noncommercial Positions-Short (Other)": "noncommercial_short_other",
    "Noncommercial Positions-Spreading (Other)": "noncommercial_spread_other",
    "Commercial Positions-Long (Other)": "commercial_long_other",
    "Commercial Positions-Short (Other)": "commercial_short_other",
    "Total Reportable Positions-Long (Other)": "total_reportable_long_other",
    "Total Reportable Positions-Short (Other)": "total_reportable_short_other",
    "Nonreportable Positions-Long (Other)": "nonreportable_long_other",
    "Nonreportable Positions-Short (Other)": "nonreportable_short_other",
}

# ---------------------------------------------------------------------------
# Disaggregated — expand abbreviated prefixes to readable names
# ---------------------------------------------------------------------------

_DISAGG_RENAMES: dict[str, str] = {
    "Prod_Merc_Positions_Long_All": "producer_merchant_long_all",
    "Prod_Merc_Positions_Short_All": "producer_merchant_short_all",
    "Swap_Positions_Long_All": "swap_dealer_long_all",
    "Swap__Positions_Short_All": "swap_dealer_short_all",   # double underscore in source
    "Swap__Positions_Spread_All": "swap_dealer_spread_all", # double underscore in source
    "M_Money_Positions_Long_All": "money_manager_long_all",
    "M_Money_Positions_Short_All": "money_manager_short_all",
    "M_Money_Positions_Spread_All": "money_manager_spread_all",
    "Other_Rept_Positions_Long_All": "other_reportable_long_all",
    "Other_Rept_Positions_Short_All": "other_reportable_short_all",
    "Other_Rept_Positions_Spread_All": "other_reportable_spread_all",
    "Tot_Rept_Positions_Long_All": "total_reportable_long_all",
    "Tot_Rept_Positions_Short_All": "total_reportable_short_all",
    "NonRept_Positions_Long_All": "nonreportable_long_all",
    "NonRept_Positions_Short_All": "nonreportable_short_all",
}

# ---------------------------------------------------------------------------
# TFF — expand abbreviated prefixes
# ---------------------------------------------------------------------------

_TFF_RENAMES: dict[str, str] = {
    "Dealer_Positions_Long_All": "dealer_long_all",
    "Dealer_Positions_Short_All": "dealer_short_all",
    "Dealer_Positions_Spread_All": "dealer_spread_all",
    "Asset_Mgr_Positions_Long_All": "asset_manager_long_all",
    "Asset_Mgr_Positions_Short_All": "asset_manager_short_all",
    "Asset_Mgr_Positions_Spread_All": "asset_manager_spread_all",
    "Lev_Money_Positions_Long_All": "leveraged_money_long_all",
    "Lev_Money_Positions_Short_All": "leveraged_money_short_all",
    "Lev_Money_Positions_Spread_All": "leveraged_money_spread_all",
    "Other_Rept_Positions_Long_All": "other_reportable_long_all",
    "Other_Rept_Positions_Short_All": "other_reportable_short_all",
    "Other_Rept_Positions_Spread_All": "other_reportable_spread_all",
    "Tot_Rept_Positions_Long_All": "total_reportable_long_all",
    "Tot_Rept_Positions_Short_All": "total_reportable_short_all",
    "NonRept_Positions_Long_All": "nonreportable_long_all",
    "NonRept_Positions_Short_All": "nonreportable_short_all",
}

# ---------------------------------------------------------------------------
# Supplemental (CIT)
# ---------------------------------------------------------------------------

_SUPPLEMENTAL_RENAMES: dict[str, str] = {
    "NComm_Positions_Long_All_NoCIT": "noncommercial_long_all_excl_cit",
    "NComm_Positions_Short_All_NoCIT": "noncommercial_short_all_excl_cit",
    "NComm_Postions_Spread_All_NoCIT": "noncommercial_spread_all_excl_cit",  # source typo
    "Comm_Positions_Long_All_NoCIT": "commercial_long_all_excl_cit",
    "Comm_Positions_Short_All_NoCIT": "commercial_short_all_excl_cit",
    "Tot_Rept_Positions_Long_All": "total_reportable_long_all",
    "Tot_Rept_Positions_Short_All": "total_reportable_short_all",
    "NonRept_Positions_Long_All": "nonreportable_long_all",
    "NonRept_Positions_Short_All": "nonreportable_short_all",
    "CIT_Positions_Long_All": "cit_long_all",
    "CIT_Positions_Short_All": "cit_short_all",
}

_REPORT_RENAMES: dict[Report, dict[str, str]] = {
    "legacy": _LEGACY_RENAMES,
    "supplemental": _SUPPLEMENTAL_RENAMES,
    "disaggregated": _DISAGG_RENAMES,
    "tff": _TFF_RENAMES,
}


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def parse_zip(data: bytes, report: Report) -> pd.DataFrame:
    """
    Extract a CSV from a CFTC ZIP archive and return a normalized DataFrame.

    Parameters
    ----------
    data : bytes
        Raw ZIP file bytes downloaded from cftc.gov.
    report : Report
        Report type, used to select the correct column mapping.

    Returns
    -------
    pd.DataFrame
        DataFrame with snake_case column names and ``report_date`` as datetime.
    """
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        txt_files = [n for n in zf.namelist() if n.endswith(".txt")]
        if not txt_files:
            raise ValueError("No .txt file found inside CFTC ZIP archive.")
        with zf.open(txt_files[0]) as f:
            df = pd.read_csv(f, encoding="latin-1", low_memory=False)
    return normalize_columns(df, report)


def normalize_columns(df: pd.DataFrame, report: Report) -> pd.DataFrame:
    """
    Rename raw CFTC column names to consistent snake_case names.

    Applies explicit mappings for metadata and key position columns; all
    remaining columns are auto-converted to snake_case.

    Parameters
    ----------
    df : pd.DataFrame
        Raw DataFrame with original CFTC column names.
    report : Report
        Report type to select the correct position-column mapping.

    Returns
    -------
    pd.DataFrame
        DataFrame with normalized column names and ``report_date`` as datetime.
    """
    renames = {**_SHARED_RENAMES, **_REPORT_RENAMES[report]}

    # Auto-convert any column not covered by the explicit map
    auto = {col: _to_snake(col) for col in df.columns if col not in renames}
    df = df.rename(columns={**auto, **renames})

    if "report_date" in df.columns:
        df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")

    return df


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _to_snake(name: str) -> str:
    """Convert an arbitrary CFTC column name to snake_case."""
    s = re.sub(r"[^a-zA-Z0-9]+", "_", name.lower())
    return s.strip("_")
