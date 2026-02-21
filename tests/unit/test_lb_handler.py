"""Tests for lb_handler _is_lb_endpoint() mode detection logic.

Since lb_handler.py performs heavy module-level imports (maybe_unpack, RemoteExecutor,
dynamic user app loading), we test _is_lb_endpoint() by extracting and exercising its
logic directly via env var patching, rather than importing lb_handler as a whole module.
"""

import logging
from unittest.mock import patch

import pytest


# WARNING: This function must be kept in sync with lb_handler._is_lb_endpoint() (src/lb_handler.py line ~46).
# It exists as a standalone copy because importing lb_handler triggers heavy module-level side effects.
# If you change the production function, update this copy.
def _is_lb_endpoint_standalone(logger: logging.Logger) -> bool:
    """Standalone copy of _is_lb_endpoint for unit testing.

    This mirrors the logic in lb_handler._is_lb_endpoint() without requiring
    the full module import (which triggers maybe_unpack, RemoteExecutor, etc.).
    """
    import os

    if os.getenv("FLASH_ENDPOINT_TYPE") == "lb":
        return True
    if os.getenv("FLASH_IS_MOTHERSHIP") == "true":
        logger.warning("FLASH_IS_MOTHERSHIP is deprecated. Use FLASH_ENDPOINT_TYPE=lb instead.")
        return True
    return False


class TestIsLbEndpoint:
    """Tests for the _is_lb_endpoint mode detection function."""

    def test_flash_endpoint_type_lb_returns_true(self) -> None:
        """FLASH_ENDPOINT_TYPE=lb triggers LB mode."""
        logger = logging.getLogger("test")
        with patch.dict("os.environ", {"FLASH_ENDPOINT_TYPE": "lb"}, clear=False):
            assert _is_lb_endpoint_standalone(logger) is True

    def test_legacy_flash_is_mothership_returns_true(self) -> None:
        """Legacy FLASH_IS_MOTHERSHIP=true still triggers LB mode (backward compat)."""
        logger = logging.getLogger("test")
        env = {"FLASH_IS_MOTHERSHIP": "true"}
        with patch.dict("os.environ", env, clear=False):
            # Remove FLASH_ENDPOINT_TYPE if present
            with patch.dict("os.environ", {}, clear=False):
                import os

                os.environ.pop("FLASH_ENDPOINT_TYPE", None)
                assert _is_lb_endpoint_standalone(logger) is True

    def test_legacy_env_var_logs_deprecation_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Legacy FLASH_IS_MOTHERSHIP=true logs a deprecation warning."""
        logger = logging.getLogger("test")
        with caplog.at_level(logging.WARNING, logger="test"):
            env = {"FLASH_IS_MOTHERSHIP": "true"}
            with patch.dict("os.environ", env, clear=False):
                import os

                os.environ.pop("FLASH_ENDPOINT_TYPE", None)
                _is_lb_endpoint_standalone(logger)

        assert any(
            "FLASH_IS_MOTHERSHIP is deprecated" in record.message for record in caplog.records
        )

    def test_no_env_vars_returns_false(self) -> None:
        """Neither env var set results in QB mode (returns False)."""
        logger = logging.getLogger("test")
        import os

        with patch.dict("os.environ", {}, clear=False):
            os.environ.pop("FLASH_ENDPOINT_TYPE", None)
            os.environ.pop("FLASH_IS_MOTHERSHIP", None)
            assert _is_lb_endpoint_standalone(logger) is False

    def test_flash_endpoint_type_takes_precedence(self) -> None:
        """FLASH_ENDPOINT_TYPE=lb takes precedence when both env vars are set."""
        logger = logging.getLogger("test")
        env = {"FLASH_ENDPOINT_TYPE": "lb", "FLASH_IS_MOTHERSHIP": "true"}
        with patch.dict("os.environ", env, clear=False):
            # Should return True via FLASH_ENDPOINT_TYPE without hitting legacy path
            assert _is_lb_endpoint_standalone(logger) is True

    def test_flash_endpoint_type_takes_precedence_no_deprecation_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When FLASH_ENDPOINT_TYPE=lb is set, no deprecation warning is logged."""
        logger = logging.getLogger("test")
        with caplog.at_level(logging.WARNING, logger="test"):
            env = {"FLASH_ENDPOINT_TYPE": "lb", "FLASH_IS_MOTHERSHIP": "true"}
            with patch.dict("os.environ", env, clear=False):
                _is_lb_endpoint_standalone(logger)

        deprecation_warnings = [
            r for r in caplog.records if "FLASH_IS_MOTHERSHIP is deprecated" in r.message
        ]
        assert len(deprecation_warnings) == 0

    def test_flash_endpoint_type_non_lb_value_returns_false(self) -> None:
        """FLASH_ENDPOINT_TYPE with non-lb value does not trigger LB mode."""
        logger = logging.getLogger("test")
        import os

        with patch.dict("os.environ", {"FLASH_ENDPOINT_TYPE": "qb"}, clear=False):
            os.environ.pop("FLASH_IS_MOTHERSHIP", None)
            assert _is_lb_endpoint_standalone(logger) is False

    def test_flash_is_mothership_false_returns_false(self) -> None:
        """FLASH_IS_MOTHERSHIP=false does not trigger LB mode."""
        logger = logging.getLogger("test")
        import os

        with patch.dict("os.environ", {"FLASH_IS_MOTHERSHIP": "false"}, clear=False):
            os.environ.pop("FLASH_ENDPOINT_TYPE", None)
            assert _is_lb_endpoint_standalone(logger) is False
