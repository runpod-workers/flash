"""
Adapter layer for RunPodLogger providing compatibility with standard logging interface.

This module wraps RunPodLogger from runpod.serverless to provide a drop-in replacement
for Python's standard logging module. It handles:
- Singleton access to RunPodLogger
- Namespace prefixes (e.g., "flash.module_name | message")
- Printf-style formatting (e.g., logger.info("Val: %s", val))
- Environment variable configuration
"""

import os
import sys
import traceback
from typing import Optional, Any

from runpod.serverless.modules.rp_logger import RunPodLogger


# Singleton RunPodLogger instance
_rp_logger_instance: Optional[RunPodLogger] = None


def _get_rp_logger() -> RunPodLogger:
    """Get or create the global RunPodLogger instance (singleton).

    Returns:
        Global RunPodLogger instance
    """
    global _rp_logger_instance
    if _rp_logger_instance is None:
        _rp_logger_instance = RunPodLogger()
    return _rp_logger_instance


class FlashLoggerAdapter:
    """
    Adapter that wraps RunPodLogger with a standard logging-like interface.

    Maintains namespace prefixes and printf-style formatting for compatibility
    with existing code while using RunPodLogger internally.
    """

    def __init__(self, name: str):
        """
        Initialize the adapter with a logger namespace.

        Args:
            name: Logger name (e.g., __name__)
        """
        self.name = name
        self._rp_logger = _get_rp_logger()

    def _format_message(self, msg: str, args: tuple[Any, ...]) -> str:
        """
        Format message using printf-style arguments.

        Args:
            msg: Message template
            args: Printf-style arguments

        Returns:
            Formatted message
        """
        if args:
            try:
                return msg % args
            except (TypeError, ValueError):
                # If formatting fails, return message as-is
                return msg
        return msg

    def _build_log_line(self, level: str, msg: str, args: tuple[Any, ...]) -> str:
        """
        Build the complete log line with namespace prefix.

        Args:
            level: Log level string (DEBUG, INFO, WARN, ERROR)
            msg: Message template
            args: Printf-style arguments

        Returns:
            Complete log line
        """
        formatted_msg = self._format_message(msg, args)

        # Add namespace prefix if name is set
        if self.name:
            return f"{self.name} | {formatted_msg}"
        return formatted_msg

    def _append_traceback(self, line: str, exc_info: bool) -> str:
        """
        Append exception traceback to log line if exc_info is True and exception is active.

        Args:
            line: Current log line
            exc_info: Whether to include exception traceback

        Returns:
            Log line with traceback appended if applicable
        """
        if exc_info and sys.exc_info()[0] is not None:
            line += "\n" + traceback.format_exc().rstrip()
        return line

    def debug(self, msg: str, *args, **kwargs) -> None:
        """Log a debug message."""
        line = self._build_log_line("DEBUG", msg, args)
        exc_info = kwargs.get("exc_info", False)
        line = self._append_traceback(line, exc_info)
        self._rp_logger.debug(line)

    def info(self, msg: str, *args, **kwargs) -> None:
        """Log an info message."""
        line = self._build_log_line("INFO", msg, args)
        exc_info = kwargs.get("exc_info", False)
        line = self._append_traceback(line, exc_info)
        self._rp_logger.info(line)

    def warning(self, msg: str, *args, **kwargs) -> None:
        """Log a warning message."""
        line = self._build_log_line("WARN", msg, args)
        exc_info = kwargs.get("exc_info", False)
        line = self._append_traceback(line, exc_info)
        self._rp_logger.warn(line)

    def warn(self, msg: str, *args, **kwargs) -> None:
        """Log a warning message (alias for warning)."""
        self.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        """Log an error message."""
        line = self._build_log_line("ERROR", msg, args)
        exc_info = kwargs.get("exc_info", False)
        line = self._append_traceback(line, exc_info)
        self._rp_logger.error(line)


def get_flash_logger(name: str) -> FlashLoggerAdapter:
    """
    Get a FlashLoggerAdapter instance for the given name.

    This is the main factory function that replaces logging.getLogger().

    Args:
        name: Logger name (typically __name__)

    Returns:
        FlashLoggerAdapter instance
    """
    return FlashLoggerAdapter(name)


def setup_flash_logging(level: Optional[str] = None) -> None:
    """
    Setup RunPodLogger with the specified log level.

    Reads log level from environment variables in order of precedence:
    1. RUNPOD_LOG_LEVEL (preferred)
    2. LOG_LEVEL (deprecated but supported)
    3. "INFO" (default)

    Args:
        level: Optional log level override (DEBUG, INFO, WARN, ERROR)
    """
    if level is None:
        level = os.environ.get("RUNPOD_LOG_LEVEL") or os.environ.get("LOG_LEVEL", "INFO")

    level = level.upper()

    # Validate and set log level
    valid_levels = {"DEBUG", "INFO", "WARN", "ERROR"}
    if level not in valid_levels:
        level = "INFO"

    rp_logger = _get_rp_logger()

    # Configure RunPodLogger with the specified level
    rp_logger.set_level(level)

    # Log confirmation of level change
    if level == "DEBUG":
        rp_logger.debug("Debug logging enabled")
    elif level == "WARN":
        rp_logger.warn(f"Log level set to {level}")
    elif level == "ERROR":
        rp_logger.error(f"Log level set to {level}")
    # INFO is default, no action needed


def get_log_level() -> str:
    """
    Get the current log level from environment variables.

    Returns:
        Log level string (DEBUG, INFO, WARN, ERROR)
    """
    level = os.environ.get("RUNPOD_LOG_LEVEL") or os.environ.get("LOG_LEVEL", "INFO")
    return level.upper()
