"""Tests for fetch.py — URL construction, caching, validation."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from opencot.fetch import (
    _cache_path,
    _fetch_zip,
    _is_stale,
    _validate,
    _zip_to_dataframe,
    clear_cache,
    fetch_raw,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_zip(csv_content: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("annual.txt", csv_content)
    return buf.getvalue()


SAMPLE_CSV = "Market_and_Exchange_Names,As_of_Date_In_Form_YYMMDD\nGOLD,241231\n"
SAMPLE_ZIP = _make_zip(SAMPLE_CSV)


# ---------------------------------------------------------------------------
# _validate
# ---------------------------------------------------------------------------

def test_validate_rejects_supplemental_futures_only():
    with pytest.raises(ValueError, match="supplemental"):
        _validate("supplemental", "futures_only", 2023)


def test_validate_rejects_year_too_early():
    with pytest.raises(ValueError, match="out of range"):
        _validate("disaggregated", "futures_only", 2005)


def test_validate_rejects_year_in_future():
    with pytest.raises(ValueError, match="out of range"):
        _validate("legacy", "futures_only", 2099)


def test_validate_passes_for_valid_inputs():
    _validate("disaggregated", "futures_only", 2023)
    _validate("legacy", "futures_and_options", 2020)
    _validate("supplemental", "futures_and_options", 2023)


# ---------------------------------------------------------------------------
# _cache_path
# ---------------------------------------------------------------------------

def test_cache_path_is_under_home_cache():
    p = _cache_path("disaggregated", "futures_only", 2023)
    assert str(p).endswith("disaggregated_futures_only_2023.zip")
    assert ".cache/opencot" in str(p)


# ---------------------------------------------------------------------------
# _zip_to_dataframe
# ---------------------------------------------------------------------------

def test_zip_to_dataframe_returns_dataframe():
    df = _zip_to_dataframe(SAMPLE_ZIP)
    assert isinstance(df, pd.DataFrame)
    assert "Market_and_Exchange_Names" in df.columns


def test_zip_to_dataframe_raises_on_empty_zip():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w"):
        pass
    with pytest.raises(ValueError, match="No .txt file"):
        _zip_to_dataframe(buf.getvalue())


# ---------------------------------------------------------------------------
# _fetch_zip — caching behaviour
# ---------------------------------------------------------------------------

def test_fetch_zip_writes_to_cache(tmp_path):
    with (
        patch("opencot.fetch._CACHE_DIR", tmp_path),
        patch("opencot.fetch.requests.get") as mock_get,
    ):
        mock_get.return_value = MagicMock(content=SAMPLE_ZIP, raise_for_status=lambda: None)
        result = _fetch_zip("disaggregated", "futures_only", 2023)

    assert result == SAMPLE_ZIP
    assert (tmp_path / "disaggregated_futures_only_2023.zip").exists()


def test_fetch_zip_uses_cache_on_second_call(tmp_path):
    with (
        patch("opencot.fetch._CACHE_DIR", tmp_path),
        patch("opencot.fetch.requests.get") as mock_get,
    ):
        mock_get.return_value = MagicMock(content=SAMPLE_ZIP, raise_for_status=lambda: None)
        _fetch_zip("disaggregated", "futures_only", 2023)
        _fetch_zip("disaggregated", "futures_only", 2023)

    assert mock_get.call_count == 1


# ---------------------------------------------------------------------------
# fetch_raw — integration (mocked network)
# ---------------------------------------------------------------------------

def test_fetch_raw_returns_dataframe(tmp_path):
    with (
        patch("opencot.fetch._CACHE_DIR", tmp_path),
        patch("opencot.fetch.requests.get") as mock_get,
    ):
        mock_get.return_value = MagicMock(content=SAMPLE_ZIP, raise_for_status=lambda: None)
        df = fetch_raw("disaggregated", 2023)

    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0


# ---------------------------------------------------------------------------
# clear_cache
# ---------------------------------------------------------------------------

def test_clear_cache_removes_zip_files(tmp_path):
    (tmp_path / "disaggregated_futures_only_2023.zip").write_bytes(b"x")
    (tmp_path / "legacy_futures_only_2022.zip").write_bytes(b"x")

    with patch("opencot.fetch._CACHE_DIR", tmp_path):
        clear_cache()

    assert list(tmp_path.glob("*.zip")) == []
