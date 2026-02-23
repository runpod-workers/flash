"""Tests for lb_handler mode detection and LB auto-discovery logic.

Tests import the production functions (_is_lb_endpoint, _discover_lb_app)
directly from lb_handler by mocking module-level side effects (maybe_unpack,
RemoteExecutor, etc.) before the import.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI


# Mock heavy dependencies before importing lb_handler to prevent side effects
_MOCK_MODULES = {
    "logger": MagicMock(),
    "unpack_volume": MagicMock(),
    "remote_executor": MagicMock(),
    "runpod_flash": MagicMock(),
    "runpod_flash.protos": MagicMock(),
    "runpod_flash.protos.remote_execution": MagicMock(),
}


@pytest.fixture(autouse=True)
def _import_lb_handler():
    """Import lb_handler with side effects mocked out.

    Patches sys.modules to prevent heavy imports (unpack_volume, RemoteExecutor,
    runpod_flash) from executing, then imports lb_handler fresh for each test.
    """
    # Remove any cached lb_handler import so we get a fresh one
    sys.modules.pop("lb_handler", None)

    with patch.dict("sys.modules", _MOCK_MODULES):
        # Prevent module-level _is_lb_endpoint() from triggering LB discovery
        with patch.dict("os.environ", {}, clear=False):
            os.environ.pop("FLASH_ENDPOINT_TYPE", None)
            import lb_handler  # noqa: F811

            yield lb_handler

    sys.modules.pop("lb_handler", None)


class TestIsLbEndpoint:
    """Tests for the _is_lb_endpoint mode detection function."""

    def test_flash_endpoint_type_lb_returns_true(self, _import_lb_handler) -> None:
        """FLASH_ENDPOINT_TYPE=lb triggers LB mode."""
        with patch.dict("os.environ", {"FLASH_ENDPOINT_TYPE": "lb"}, clear=False):
            assert _import_lb_handler._is_lb_endpoint() is True

    def test_no_env_vars_returns_false(self, _import_lb_handler) -> None:
        """Neither env var set results in QB mode (returns False)."""
        with patch.dict("os.environ", {}, clear=False):
            os.environ.pop("FLASH_ENDPOINT_TYPE", None)
            assert _import_lb_handler._is_lb_endpoint() is False

    def test_flash_endpoint_type_non_lb_value_returns_false(self, _import_lb_handler) -> None:
        """FLASH_ENDPOINT_TYPE with non-lb value does not trigger LB mode."""
        with patch.dict("os.environ", {"FLASH_ENDPOINT_TYPE": "qb"}, clear=False):
            assert _import_lb_handler._is_lb_endpoint() is False


class TestDiscoverLbApp:
    """Tests for the _discover_lb_app auto-discovery function (production code)."""

    def test_raises_when_resource_name_not_set(self, _import_lb_handler) -> None:
        """Missing FLASH_RESOURCE_NAME raises RuntimeError with clear message."""
        with patch.dict("os.environ", {}, clear=False):
            os.environ.pop("FLASH_RESOURCE_NAME", None)
            with pytest.raises(RuntimeError, match="FLASH_RESOURCE_NAME not set"):
                _import_lb_handler._discover_lb_app()

    def test_derives_handler_path_from_resource_name(self, _import_lb_handler, tmp_path) -> None:
        """Handler file path is {handler_dir}/handler_{resource_name}.py."""
        handler_file = tmp_path / "handler_my_gpu_endpoint.py"
        handler_file.write_text("from fastapi import FastAPI\napp = FastAPI()\n")

        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "my_gpu_endpoint"}, clear=False):
            app = _import_lb_handler._discover_lb_app(handler_dir=str(tmp_path))

        assert isinstance(app, FastAPI)

    def test_loads_fastapi_app_variable(self, _import_lb_handler, tmp_path) -> None:
        """Loads the 'app' variable from the generated handler module."""
        handler_file = tmp_path / "handler_inference.py"
        handler_file.write_text(
            "from fastapi import FastAPI\n"
            "app = FastAPI(title='Test LB Handler')\n"
            "@app.get('/health')\n"
            "def health(): return {'ok': True}\n"
        )

        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "inference"}, clear=False):
            app = _import_lb_handler._discover_lb_app(handler_dir=str(tmp_path))

        assert isinstance(app, FastAPI)
        assert app.title == "Test LB Handler"

    def test_raises_when_handler_file_missing(self, _import_lb_handler, tmp_path) -> None:
        """Missing handler file raises FileNotFoundError."""
        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "nonexistent"}, clear=False):
            with pytest.raises(FileNotFoundError):
                _import_lb_handler._discover_lb_app(handler_dir=str(tmp_path))

    def test_raises_attribute_error_when_app_missing(self, _import_lb_handler, tmp_path) -> None:
        """Handler module without 'app' attribute raises AttributeError."""
        handler_file = tmp_path / "handler_broken.py"
        handler_file.write_text("x = 42\n")

        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "broken"}, clear=False):
            with pytest.raises(AttributeError, match="does not have 'app' attribute"):
                _import_lb_handler._discover_lb_app(handler_dir=str(tmp_path))

    def test_raises_type_error_when_app_not_fastapi(self, _import_lb_handler, tmp_path) -> None:
        """Handler module with non-FastAPI 'app' raises TypeError."""
        handler_file = tmp_path / "handler_wrong_type.py"
        handler_file.write_text("app = 'not a FastAPI instance'\n")

        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "wrong_type"}, clear=False):
            with pytest.raises(TypeError, match="Expected FastAPI instance"):
                _import_lb_handler._discover_lb_app(handler_dir=str(tmp_path))
