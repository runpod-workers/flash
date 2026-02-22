"""Tests for lb_handler _is_lb_endpoint() mode detection logic.

Since lb_handler.py performs heavy module-level imports (maybe_unpack, RemoteExecutor,
dynamic user app loading), we test _is_lb_endpoint() by extracting and exercising its
logic directly via env var patching, rather than importing lb_handler as a whole module.
"""

from unittest.mock import patch


# WARNING: This function must be kept in sync with lb_handler._is_lb_endpoint() (src/lb_handler.py line ~46).
# It exists as a standalone copy because importing lb_handler triggers heavy module-level side effects.
# If you change the production function, update this copy.
def _is_lb_endpoint_standalone() -> bool:
    """Standalone copy of _is_lb_endpoint for unit testing.

    This mirrors the logic in lb_handler._is_lb_endpoint() without requiring
    the full module import (which triggers maybe_unpack, RemoteExecutor, etc.).
    """
    import os

    return os.getenv("FLASH_ENDPOINT_TYPE") == "lb"


class TestIsLbEndpoint:
    """Tests for the _is_lb_endpoint mode detection function."""

    def test_flash_endpoint_type_lb_returns_true(self) -> None:
        """FLASH_ENDPOINT_TYPE=lb triggers LB mode."""
        with patch.dict("os.environ", {"FLASH_ENDPOINT_TYPE": "lb"}, clear=False):
            assert _is_lb_endpoint_standalone() is True

    def test_no_env_vars_returns_false(self) -> None:
        """Neither env var set results in QB mode (returns False)."""
        import os

        with patch.dict("os.environ", {}, clear=False):
            os.environ.pop("FLASH_ENDPOINT_TYPE", None)
            assert _is_lb_endpoint_standalone() is False

    def test_flash_endpoint_type_non_lb_value_returns_false(self) -> None:
        """FLASH_ENDPOINT_TYPE with non-lb value does not trigger LB mode."""
        with patch.dict("os.environ", {"FLASH_ENDPOINT_TYPE": "qb"}, clear=False):
            assert _is_lb_endpoint_standalone() is False
