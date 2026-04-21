"""Tests for version utilities."""

import platform
import sys
from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

import pytest

from version import (
    PythonVersionMismatchError,
    __version__,
    _get_version,
    assert_python_version_matches_image,
    format_version_banner,
    get_flash_version,
    get_runpod_version,
    get_worker_version,
)


class TestGetVersion:
    """Tests for the _get_version helper."""

    @patch("version.version", return_value="1.2.3")
    def test_returns_version_for_installed_package(self, mock_version):
        assert _get_version("some-package") == "1.2.3"
        mock_version.assert_called_once_with("some-package")

    @patch("version.version", side_effect=PackageNotFoundError("not found"))
    def test_returns_unknown_for_missing_package(self, mock_version):
        assert _get_version("missing-package") == "unknown"


class TestVersionGetters:
    """Tests for individual version getter functions."""

    def test_get_worker_version_returns_module_version(self):
        assert get_worker_version() == __version__

    def test_get_flash_version_from_bundled_package(self):
        """Reads __version__ from bundled runpod_flash when available."""
        fake_module = type("mod", (), {"__version__": "1.5.0"})()
        with patch.dict("sys.modules", {"runpod_flash": fake_module}):
            assert get_flash_version() == "1.5.0"

    @patch("version._get_version", return_value="1.4.0")
    def test_get_flash_version_falls_back_to_metadata(self, mock_get):
        """Falls back to importlib.metadata when bundled package unavailable."""
        with patch.dict("sys.modules", {"runpod_flash": None}):
            assert get_flash_version() == "1.4.0"
            mock_get.assert_called_once_with("runpod-flash")

    @patch("version._get_version", return_value="0.9.0")
    def test_get_runpod_version(self, mock_get):
        assert get_runpod_version() == "0.9.0"
        mock_get.assert_called_once_with("runpod")


class TestFormatVersionBanner:
    """Tests for the version banner formatter."""

    @patch("version.get_runpod_version", return_value="0.9.0")
    @patch("version.get_flash_version", return_value="1.5.0")
    @patch("version.get_worker_version", return_value="2.0.0")
    def test_format_version_banner(self, mock_worker, mock_flash, mock_runpod):
        result = format_version_banner()
        py = platform.python_version()
        assert (
            result
            == f"Starting Flash Worker 2.0.0 | Python {py} | runpod-flash 1.5.0 | runpod 0.9.0"
        )

    @patch("version.get_runpod_version", return_value="unknown")
    @patch("version.get_flash_version", return_value="unknown")
    @patch("version.get_worker_version", return_value="unknown")
    def test_banner_handles_unknown_versions(self, mock_worker, mock_flash, mock_runpod):
        result = format_version_banner()
        py = platform.python_version()
        assert (
            result
            == f"Starting Flash Worker unknown | Python {py} | runpod-flash unknown | runpod unknown"
        )


class TestAssertPythonVersionMatchesImage:
    """Tests for the AE-2827 Python version assertion."""

    @pytest.fixture(autouse=True)
    def _clear_env(self, monkeypatch):
        monkeypatch.delenv("FLASH_PYTHON_VERSION", raising=False)

    def test_noop_when_env_var_unset(self):
        """Local dev and test harnesses don't set FLASH_PYTHON_VERSION; skip check."""
        assert_python_version_matches_image()

    def test_passes_when_declared_matches_interpreter(self, monkeypatch):
        actual = f"{sys.version_info.major}.{sys.version_info.minor}"
        monkeypatch.setenv("FLASH_PYTHON_VERSION", actual)
        assert_python_version_matches_image()

    def test_raises_on_mismatch(self, monkeypatch):
        monkeypatch.setenv("FLASH_PYTHON_VERSION", "3.99")
        with pytest.raises(PythonVersionMismatchError, match="interpreter mismatch"):
            assert_python_version_matches_image()

    def test_mismatch_error_message_includes_both_versions(self, monkeypatch):
        declared = "3.99"
        monkeypatch.setenv("FLASH_PYTHON_VERSION", declared)
        with pytest.raises(PythonVersionMismatchError) as excinfo:
            assert_python_version_matches_image()

        actual = f"{sys.version_info.major}.{sys.version_info.minor}"
        message = str(excinfo.value)
        assert declared in message
        assert actual in message
