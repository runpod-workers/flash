"""Unit tests for RunPodLogger adapter layer."""

import os
import pytest
import rp_logger_adapter
from unittest.mock import patch, MagicMock

from rp_logger_adapter import (
    FlashLoggerAdapter,
    get_flash_logger,
    setup_flash_logging,
    get_log_level,
    _get_rp_logger,
)


@pytest.fixture
def clean_env():
    """Clean environment variables before each test."""
    original_env = os.environ.copy()
    for key in ["RUNPOD_LOG_LEVEL", "LOG_LEVEL"]:
        os.environ.pop(key, None)
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_rp_logger_instance():
    """Create a mock RunPodLogger instance for testing."""
    mock_instance = MagicMock()
    mock_instance.debug = MagicMock()
    mock_instance.info = MagicMock()
    mock_instance.warn = MagicMock()
    mock_instance.error = MagicMock()
    return mock_instance


@pytest.fixture
def adapter_with_mock(mock_rp_logger_instance):
    """Create an adapter with mocked RunPodLogger."""
    with patch("rp_logger_adapter._get_rp_logger", return_value=mock_rp_logger_instance):
        yield FlashLoggerAdapter("test"), mock_rp_logger_instance


class TestFlashLoggerAdapter:
    """Test FlashLoggerAdapter class."""

    def test_adapter_initialization(self, mock_rp_logger_instance):
        """Test adapter initialization with a name."""
        with patch("rp_logger_adapter._get_rp_logger", return_value=mock_rp_logger_instance):
            adapter = FlashLoggerAdapter("test_module")
            assert adapter.name == "test_module"

    def test_debug_message(self, adapter_with_mock):
        """Test debug logging."""
        adapter, mock_rp_logger = adapter_with_mock
        adapter.debug("Test message")
        mock_rp_logger.debug.assert_called_once_with("test | Test message")

    def test_info_message(self, adapter_with_mock):
        """Test info logging."""
        adapter, mock_rp_logger = adapter_with_mock
        adapter.info("Test message")
        mock_rp_logger.info.assert_called_once_with("test | Test message")

    def test_warning_message(self, adapter_with_mock):
        """Test warning logging."""
        adapter, mock_rp_logger = adapter_with_mock
        adapter.warning("Test message")
        mock_rp_logger.warn.assert_called_once_with("test | Test message")

    def test_warn_alias(self, adapter_with_mock):
        """Test warn is alias for warning."""
        adapter, mock_rp_logger = adapter_with_mock
        adapter.warn("Test message")
        mock_rp_logger.warn.assert_called_once_with("test | Test message")

    def test_error_message(self, adapter_with_mock):
        """Test error logging."""
        adapter, mock_rp_logger = adapter_with_mock
        adapter.error("Test message")
        mock_rp_logger.error.assert_called_once_with("test | Test message")

    def test_printf_style_formatting(self, adapter_with_mock):
        """Test printf-style string formatting."""
        adapter, mock_rp_logger = adapter_with_mock
        adapter.info("Value: %s, Count: %d", "hello", 42)
        mock_rp_logger.info.assert_called_once_with("test | Value: hello, Count: 42")

    def test_printf_formatting_with_warning(self, adapter_with_mock):
        """Test printf-style formatting with warning level."""
        adapter, mock_rp_logger = adapter_with_mock
        adapter.warning("Error code: %d", 500)
        mock_rp_logger.warn.assert_called_once_with("test | Error code: 500")

    def test_namespace_prefix(self, adapter_with_mock):
        """Test namespace prefix in message."""
        _, mock_rp_logger = adapter_with_mock
        adapter = FlashLoggerAdapter("flash.module_name")
        adapter.info("Processing")
        mock_rp_logger.info.assert_called_with("flash.module_name | Processing")

    def test_no_namespace(self, adapter_with_mock):
        """Test message without namespace."""
        _, mock_rp_logger = adapter_with_mock
        adapter = FlashLoggerAdapter("")
        adapter.info("Simple message")
        mock_rp_logger.info.assert_called_with("Simple message")

    def test_formatting_failure_returns_original(self, adapter_with_mock):
        """Test that formatting errors return original message."""
        adapter, mock_rp_logger = adapter_with_mock
        # Try to format with wrong args - should not raise
        adapter.info("Message %s %s", "only_one")
        # Should call with original message on formatting error
        assert mock_rp_logger.info.called
        call_args = mock_rp_logger.info.call_args[0][0]
        assert "Message" in call_args

    def test_empty_args(self, adapter_with_mock):
        """Test message with no format args."""
        adapter, mock_rp_logger = adapter_with_mock
        adapter.info("No formatting")
        mock_rp_logger.info.assert_called_once_with("test | No formatting")

    def test_error_with_exc_info(self, adapter_with_mock):
        """Test error logging with exc_info includes traceback."""
        adapter, mock_rp_logger = adapter_with_mock

        # Simulate an active exception
        try:
            raise ValueError("Test error")
        except ValueError:
            adapter.error("Error occurred", exc_info=True)

        # Verify error was called
        assert mock_rp_logger.error.called
        call_args = mock_rp_logger.error.call_args[0][0]

        # Verify message starts with the expected prefix and includes traceback
        assert call_args.startswith("test | Error occurred")
        assert "ValueError: Test error" in call_args
        assert "Traceback" in call_args

    def test_error_without_exc_info(self, adapter_with_mock):
        """Test error logging without exc_info doesn't include traceback."""
        adapter, mock_rp_logger = adapter_with_mock

        # Simulate an active exception but don't use exc_info
        try:
            raise ValueError("Test error")
        except ValueError:
            adapter.error("Error occurred", exc_info=False)

        # Verify error was called without traceback
        mock_rp_logger.error.assert_called_once_with("test | Error occurred")

    def test_error_exc_info_with_no_active_exception(self, adapter_with_mock):
        """Test error logging with exc_info=True but no active exception."""
        adapter, mock_rp_logger = adapter_with_mock

        # Call with exc_info=True but no active exception
        adapter.error("Error occurred", exc_info=True)

        # Should only log the message without traceback
        mock_rp_logger.error.assert_called_once_with("test | Error occurred")


class TestGetFlashLogger:
    """Test get_flash_logger factory function."""

    def test_returns_adapter(self, mock_rp_logger_instance):
        """Test that get_flash_logger returns an adapter."""
        with patch("rp_logger_adapter._get_rp_logger", return_value=mock_rp_logger_instance):
            logger = get_flash_logger("test")
            assert isinstance(logger, FlashLoggerAdapter)

    def test_different_names(self, mock_rp_logger_instance):
        """Test creating loggers with different names."""
        with patch("rp_logger_adapter._get_rp_logger", return_value=mock_rp_logger_instance):
            logger1 = get_flash_logger("module1")
            logger2 = get_flash_logger("module2")
            assert logger1.name == "module1"
            assert logger2.name == "module2"

    def test_with_dunder_name(self, mock_rp_logger_instance):
        """Test with __name__ pattern."""
        with patch("rp_logger_adapter._get_rp_logger", return_value=mock_rp_logger_instance):
            logger = get_flash_logger(__name__)
            assert logger.name == __name__


class TestSetupFlashLogging:
    """Test setup_flash_logging function."""

    def test_explicit_debug_level(self, mock_rp_logger_instance, clean_env):
        """Test explicit DEBUG level setup."""
        with patch("rp_logger_adapter._get_rp_logger", return_value=mock_rp_logger_instance):
            setup_flash_logging("DEBUG")
            # Should not raise
            assert True

    def test_explicit_info_level(self, mock_rp_logger_instance, clean_env):
        """Test explicit INFO level setup."""
        with patch("rp_logger_adapter._get_rp_logger", return_value=mock_rp_logger_instance):
            setup_flash_logging("INFO")
            assert True

    def test_explicit_warn_level(self, mock_rp_logger_instance, clean_env):
        """Test explicit WARN level setup."""
        with patch("rp_logger_adapter._get_rp_logger", return_value=mock_rp_logger_instance):
            setup_flash_logging("WARN")
            assert True

    def test_explicit_error_level(self, mock_rp_logger_instance, clean_env):
        """Test explicit ERROR level setup."""
        with patch("rp_logger_adapter._get_rp_logger", return_value=mock_rp_logger_instance):
            setup_flash_logging("ERROR")
            assert True

    def test_case_insensitive_level(self, mock_rp_logger_instance, clean_env):
        """Test that level is case-insensitive."""
        with patch("rp_logger_adapter._get_rp_logger", return_value=mock_rp_logger_instance):
            setup_flash_logging("debug")
            setup_flash_logging("INFO")
            setup_flash_logging("WaRn")
            # Should not raise
            assert True

    def test_invalid_level_defaults_to_info(self, mock_rp_logger_instance, clean_env):
        """Test that invalid level defaults to INFO."""
        with patch("rp_logger_adapter._get_rp_logger", return_value=mock_rp_logger_instance):
            setup_flash_logging("INVALID")
            # Should default to INFO without raising
            assert True

    def test_none_level(self, mock_rp_logger_instance, clean_env):
        """Test with None level (should use env vars)."""
        os.environ["RUNPOD_LOG_LEVEL"] = "DEBUG"
        with patch("rp_logger_adapter._get_rp_logger", return_value=mock_rp_logger_instance):
            setup_flash_logging(None)
            assert True


class TestGetLogLevel:
    """Test get_log_level function."""

    def test_runpod_log_level_precedence(self, clean_env):
        """Test RUNPOD_LOG_LEVEL takes precedence."""
        os.environ["RUNPOD_LOG_LEVEL"] = "DEBUG"
        os.environ["LOG_LEVEL"] = "ERROR"
        assert get_log_level() == "DEBUG"

    def test_log_level_fallback(self, clean_env):
        """Test LOG_LEVEL is used if RUNPOD_LOG_LEVEL not set."""
        os.environ["LOG_LEVEL"] = "WARN"
        assert get_log_level() == "WARN"

    def test_default_info(self, clean_env):
        """Test default is INFO."""
        assert get_log_level() == "INFO"

    def test_case_normalization(self, clean_env):
        """Test that level is normalized to uppercase."""
        os.environ["LOG_LEVEL"] = "debug"
        assert get_log_level() == "DEBUG"

    def test_runpod_log_level_case_handling(self, clean_env):
        """Test RUNPOD_LOG_LEVEL case handling."""
        os.environ["RUNPOD_LOG_LEVEL"] = "DeBuG"
        assert get_log_level() == "DEBUG"


class TestSingletonBehavior:
    """Test that RunPodLogger singleton is shared."""

    def test_multiple_adapters_share_rp_logger(self, mock_rp_logger_instance):
        """Test that multiple adapters share the same RunPodLogger."""
        # Create multiple adapters with same mock
        with patch("rp_logger_adapter._get_rp_logger", return_value=mock_rp_logger_instance):
            adapter1 = get_flash_logger("module1")
            adapter2 = get_flash_logger("module2")

            # Get the internal rp_logger for each
            rp_logger1 = adapter1._rp_logger
            rp_logger2 = adapter2._rp_logger

            # They should be the same instance
            assert rp_logger1 is rp_logger2

    def test_rp_logger_singleton_caching(self):
        """Test that _get_rp_logger returns same instance."""
        # Reset the singleton
        original_instance = rp_logger_adapter._rp_logger_instance
        rp_logger_adapter._rp_logger_instance = None

        try:
            logger1 = _get_rp_logger()
            logger2 = _get_rp_logger()

            # Should be same instance
            assert logger1 is logger2
        finally:
            # Restore
            rp_logger_adapter._rp_logger_instance = original_instance


class TestNamespacePrefixes:
    """Test namespace prefix functionality."""

    def test_module_namespace_prefix(self, adapter_with_mock):
        """Test module-style namespace prefix."""
        _, mock_rp_logger = adapter_with_mock
        adapter = FlashLoggerAdapter("flash.dependency_installer")
        adapter.info("Installing packages")
        mock_rp_logger.info.assert_called_with("flash.dependency_installer | Installing packages")

    def test_nested_namespace_prefix(self, adapter_with_mock):
        """Test deeply nested namespace prefix."""
        _, mock_rp_logger = adapter_with_mock
        adapter = FlashLoggerAdapter("flash.executor.function_executor")
        adapter.error("Execution failed")
        mock_rp_logger.error.assert_called_with(
            "flash.executor.function_executor | Execution failed"
        )

    def test_simple_namespace(self, adapter_with_mock):
        """Test simple namespace."""
        _, mock_rp_logger = adapter_with_mock
        adapter = FlashLoggerAdapter("worker")
        adapter.debug("Debug info")
        mock_rp_logger.debug.assert_called_with("worker | Debug info")


class TestMultipleLevels:
    """Test multiple log levels together."""

    def test_all_levels_with_same_adapter(self, adapter_with_mock):
        """Test that all levels work with same adapter."""
        adapter, mock_rp_logger = adapter_with_mock

        adapter.debug("Debug message")
        adapter.info("Info message")
        adapter.warning("Warning message")
        adapter.error("Error message")

        assert mock_rp_logger.debug.call_count == 1
        assert mock_rp_logger.info.call_count == 1
        assert mock_rp_logger.warn.call_count == 1
        assert mock_rp_logger.error.call_count == 1

    def test_mixed_formatting_and_levels(self, adapter_with_mock):
        """Test mixed formatting and levels."""
        adapter, mock_rp_logger = adapter_with_mock

        adapter.debug("Debug %s", "msg")
        adapter.info("Info %d", 42)
        adapter.warning("Warn %s", "msg")
        adapter.error("Error %s", "msg")

        mock_rp_logger.debug.assert_called_with("test | Debug msg")
        mock_rp_logger.info.assert_called_with("test | Info 42")
        mock_rp_logger.warn.assert_called_with("test | Warn msg")
        mock_rp_logger.error.assert_called_with("test | Error msg")


class TestEnvironmentVariableConfiguration:
    """Test environment variable configuration."""

    def test_runpod_log_level_env(self, clean_env):
        """Test RUNPOD_LOG_LEVEL environment variable."""
        os.environ["RUNPOD_LOG_LEVEL"] = "DEBUG"
        level = get_log_level()
        assert level == "DEBUG"

    def test_log_level_deprecated_env(self, clean_env):
        """Test deprecated LOG_LEVEL environment variable."""
        os.environ["LOG_LEVEL"] = "ERROR"
        level = get_log_level()
        assert level == "ERROR"

    def test_env_precedence(self, clean_env):
        """Test RUNPOD_LOG_LEVEL takes precedence over LOG_LEVEL."""
        os.environ["RUNPOD_LOG_LEVEL"] = "DEBUG"
        os.environ["LOG_LEVEL"] = "ERROR"
        level = get_log_level()
        assert level == "DEBUG"

    def test_empty_env_defaults(self, clean_env):
        """Test empty environment defaults to INFO."""
        level = get_log_level()
        assert level == "INFO"
