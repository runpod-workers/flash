"""Tests for lb_handler mode detection and LB auto-discovery logic.

Since lb_handler.py performs heavy module-level imports (maybe_unpack, RemoteExecutor,
dynamic user app loading), we test by extracting and exercising logic directly via
standalone copies and env var patching, rather than importing lb_handler as a whole module.
"""

import importlib.util
import os

import pytest
from fastapi import FastAPI
from unittest.mock import patch


# WARNING: This function must be kept in sync with lb_handler._is_lb_endpoint() (src/lb_handler.py line ~48).
# It exists as a standalone copy because importing lb_handler triggers heavy module-level side effects.
# If you change the production function, update this copy.
def _is_lb_endpoint_standalone() -> bool:
    """Standalone copy of _is_lb_endpoint for unit testing.

    This mirrors the logic in lb_handler._is_lb_endpoint() without requiring
    the full module import (which triggers maybe_unpack, RemoteExecutor, etc.).
    """
    return os.getenv("FLASH_ENDPOINT_TYPE") == "lb"


# WARNING: This function must be kept in sync with the LB branch in lb_handler.py (lines ~55-86).
# It mirrors the auto-discovery + import logic without module-level side effects.
def _load_lb_handler_standalone(handler_dir: str = "/app") -> FastAPI:
    """Standalone copy of the LB handler auto-discovery logic.

    Mirrors the LB branch in lb_handler.py: derives handler path from
    FLASH_RESOURCE_NAME and imports the FastAPI app.

    Args:
        handler_dir: Base directory for handler files (default /app, overridable for tests).

    Returns:
        FastAPI app from the generated handler.

    Raises:
        RuntimeError: If FLASH_RESOURCE_NAME is not set.
        ImportError: If the handler file cannot be found or loaded.
        AttributeError: If the handler module lacks an 'app' attribute.
        TypeError: If the 'app' attribute is not a FastAPI instance.
    """
    resource_name = os.getenv("FLASH_RESOURCE_NAME")
    if not resource_name:
        raise RuntimeError("FLASH_RESOURCE_NAME not set. Cannot discover generated LB handler.")

    handler_file = f"{handler_dir}/handler_{resource_name}.py"
    app_variable = "app"

    spec = importlib.util.spec_from_file_location("user_main", handler_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot find or load {handler_file}")

    user_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(user_module)

    if not hasattr(user_module, app_variable):
        raise AttributeError(f"Module {handler_file} does not have '{app_variable}' attribute")

    app = getattr(user_module, app_variable)

    if not isinstance(app, FastAPI):
        raise TypeError(f"Expected FastAPI instance, got {type(app).__name__} for {app_variable}")

    return app


class TestIsLbEndpoint:
    """Tests for the _is_lb_endpoint mode detection function."""

    def test_flash_endpoint_type_lb_returns_true(self) -> None:
        """FLASH_ENDPOINT_TYPE=lb triggers LB mode."""
        with patch.dict("os.environ", {"FLASH_ENDPOINT_TYPE": "lb"}, clear=False):
            assert _is_lb_endpoint_standalone() is True

    def test_no_env_vars_returns_false(self) -> None:
        """Neither env var set results in QB mode (returns False)."""
        with patch.dict("os.environ", {}, clear=False):
            os.environ.pop("FLASH_ENDPOINT_TYPE", None)
            assert _is_lb_endpoint_standalone() is False

    def test_flash_endpoint_type_non_lb_value_returns_false(self) -> None:
        """FLASH_ENDPOINT_TYPE with non-lb value does not trigger LB mode."""
        with patch.dict("os.environ", {"FLASH_ENDPOINT_TYPE": "qb"}, clear=False):
            assert _is_lb_endpoint_standalone() is False


class TestLbHandlerAutoDiscovery:
    """Tests for the LB handler auto-discovery logic (FLASH_RESOURCE_NAME -> handler file)."""

    def test_raises_when_resource_name_not_set(self) -> None:
        """Missing FLASH_RESOURCE_NAME raises RuntimeError with clear message."""
        with patch.dict("os.environ", {}, clear=False):
            os.environ.pop("FLASH_RESOURCE_NAME", None)
            with pytest.raises(RuntimeError, match="FLASH_RESOURCE_NAME not set"):
                _load_lb_handler_standalone()

    def test_derives_handler_path_from_resource_name(self, tmp_path) -> None:
        """Handler file path is /app/handler_{resource_name}.py."""
        handler_file = tmp_path / "handler_my_gpu_endpoint.py"
        handler_file.write_text("from fastapi import FastAPI\napp = FastAPI()\n")

        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "my_gpu_endpoint"}, clear=False):
            app = _load_lb_handler_standalone(handler_dir=str(tmp_path))

        assert isinstance(app, FastAPI)

    def test_loads_fastapi_app_variable(self, tmp_path) -> None:
        """Loads the 'app' variable from the generated handler module."""
        handler_file = tmp_path / "handler_inference.py"
        handler_file.write_text(
            "from fastapi import FastAPI\n"
            "app = FastAPI(title='Test LB Handler')\n"
            "@app.get('/health')\n"
            "def health(): return {'ok': True}\n"
        )

        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "inference"}, clear=False):
            app = _load_lb_handler_standalone(handler_dir=str(tmp_path))

        assert isinstance(app, FastAPI)
        assert app.title == "Test LB Handler"

    def test_raises_when_handler_file_missing(self, tmp_path) -> None:
        """Missing handler file raises FileNotFoundError."""
        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "nonexistent"}, clear=False):
            with pytest.raises(FileNotFoundError):
                _load_lb_handler_standalone(handler_dir=str(tmp_path))

    def test_raises_attribute_error_when_app_missing(self, tmp_path) -> None:
        """Handler module without 'app' attribute raises AttributeError."""
        handler_file = tmp_path / "handler_broken.py"
        handler_file.write_text("x = 42\n")

        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "broken"}, clear=False):
            with pytest.raises(AttributeError, match="does not have 'app' attribute"):
                _load_lb_handler_standalone(handler_dir=str(tmp_path))

    def test_raises_type_error_when_app_not_fastapi(self, tmp_path) -> None:
        """Handler module with non-FastAPI 'app' raises TypeError."""
        handler_file = tmp_path / "handler_wrong_type.py"
        handler_file.write_text("app = 'not a FastAPI instance'\n")

        with patch.dict("os.environ", {"FLASH_RESOURCE_NAME": "wrong_type"}, clear=False):
            with pytest.raises(TypeError, match="Expected FastAPI instance"):
                _load_lb_handler_standalone(handler_dir=str(tmp_path))
