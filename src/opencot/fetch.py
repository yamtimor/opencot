"""CFTC ZIP file downloading and local disk caching."""

from __future__ import annotations

import io
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from .types import Report, Variant

_BASE_URL = "https://www.cftc.gov/files/dea/history/"
_CACHE_DIR = Path.home() / ".cache" / "opencot"

# Maps (report, variant) -> CFTC ZIP filename template (use .format(year=year))
_ZIP_TEMPLATES: dict[tuple[Report, Variant], str] = {
    ("legacy", "futures_only"): "deahistfo{year}.zip",
    ("legacy", "futures_and_options"): "deacot{year}.zip",
    ("supplemental", "futures_and_options"): "dea_cit_txt_{year}.zip",
    ("disaggregated", "futures_only"): "fut_disagg_txt_{year}.zip",
    ("disaggregated", "futures_and_options"): "com_disagg_txt_{year}.zip",
    ("tff", "futures_only"): "fut_fin_txt_{year}.zip",
    ("tff", "futures_and_options"): "com_fin_txt_{year}.zip",
}

# Earliest year available per report type
_EARLIEST_YEAR: dict[Report, int] = {
    "legacy": 1995,
    "supplemental": 2006,
    "disaggregated": 2010,
    "tff": 2011,
}

# How old a cached current-year file can be before we re-download (in days)
_CURRENT_YEAR_TTL_DAYS = 7


def fetch_raw(report: Report, year: int, variant: Variant = "futures_only") -> pd.DataFrame:
    """
    Download and return raw COT data for a single year.

    Results are cached on disk under ``~/.cache/opencot/``. Past years are
    cached permanently; the current year is re-fetched after 7 days.

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
        Raw data with original CFTC column names (no normalization).

    Raises
    ------
    ValueError
        If the (report, variant) combination is not available, or the year
        is outside the supported range.
    requests.HTTPError
        If the CFTC server returns a non-200 response.
    """
    _validate(report, variant, year)
    zip_bytes = _fetch_zip(report, variant, year)
    return _zip_to_dataframe(zip_bytes)


def clear_cache() -> None:
    """Remove all locally cached CFTC data files."""
    if _CACHE_DIR.exists():
        for f in _CACHE_DIR.glob("*.zip"):
            f.unlink()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate(report: Report, variant: Variant, year: int) -> None:
    if (report, variant) not in _ZIP_TEMPLATES:
        raise ValueError(
            f"'{report}' is not available in '{variant}' variant. "
            f"'supplemental' only supports 'futures_and_options'."
        )
    earliest = _EARLIEST_YEAR[report]
    current = date.today().year
    if not (earliest <= year <= current):
        raise ValueError(
            f"Year {year} is out of range for '{report}' (available: {earliest}–{current})."
        )


def _cache_path(report: Report, variant: Variant, year: int) -> Path:
    return _CACHE_DIR / f"{report}_{variant}_{year}.zip"


def _is_stale(path: Path, year: int) -> bool:
    if year < date.today().year:
        return False  # past years never change
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    age_days = (datetime.now(tz=timezone.utc) - mtime).days
    return age_days >= _CURRENT_YEAR_TTL_DAYS


def _fetch_zip(report: Report, variant: Variant, year: int) -> bytes:
    path = _cache_path(report, variant, year)
    if path.exists() and not _is_stale(path, year):
        return path.read_bytes()

    url = _BASE_URL + _ZIP_TEMPLATES[(report, variant)].format(year=year)
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)
    return response.content


def _zip_to_dataframe(zip_bytes: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        txt_files = [n for n in zf.namelist() if n.endswith(".txt")]
        if not txt_files:
            raise ValueError("No .txt file found inside CFTC ZIP archive.")
        with zf.open(txt_files[0]) as f:
            return pd.read_csv(f, encoding="latin-1", low_memory=False)
