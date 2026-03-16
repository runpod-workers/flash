"""
Logging configuration for worker-flash.

Provides centralized logging setup matching runpod-flash style with level-based formatting.
"""

import logging
import os
import sys
from contextvars import ContextVar, Token
from typing import Union, Optional


_REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Inject request_id from context into each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _REQUEST_ID.get()
        return True


_REQUEST_ID_FILTER = RequestIdFilter()


def set_request_id(request_id: Optional[str]) -> Token[str]:
    """Set request id in log context and return reset token."""
    if request_id:
        normalized = request_id.strip() or "-"
    else:
        normalized = "-"
    return _REQUEST_ID.set(normalized)


def reset_request_id(token: Token[str]) -> None:
    """Reset request id context with token from set_request_id."""
    _REQUEST_ID.reset(token)


def get_request_id() -> str:
    return _REQUEST_ID.get()


def ensure_request_id_filter(handler: logging.Handler) -> None:
    if not any(isinstance(existing, RequestIdFilter) for existing in handler.filters):
        handler.addFilter(_REQUEST_ID_FILTER)


def get_log_level() -> int:
    """Get log level from environment variable, defaulting to INFO."""
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    return getattr(logging, log_level, logging.INFO)


def get_log_format(level: int) -> str:
    """Get appropriate log format based on level, matching runpod-flash style."""
    if level == logging.DEBUG:
        return (
            "%(asctime)s | %(levelname)-5s | %(request_id)s | "
            "%(name)s | %(filename)s:%(lineno)d | %(message)s"
        )
    else:
        return "%(asctime)s | %(levelname)-5s | %(request_id)s | %(message)s"


def setup_logging(
    level: Optional[Union[int, str]] = None,
    stream=sys.stdout,
    fmt: Optional[str] = None,
) -> None:
    """
    Setup logging configuration for worker-flash.
    Only shows DEBUG logs from flash namespace when LOG_LEVEL=DEBUG.

    Args:
        level: Log level (defaults to LOG_LEVEL env var or INFO)
        stream: Output stream for logs
        fmt: Custom format string (auto-selected based on level if None)
    """
    if level is None:
        resolved_level = get_log_level()
    elif isinstance(level, str):
        resolved_level = getattr(logging, level.upper(), logging.INFO)
    else:
        resolved_level = level

    if fmt is None:
        fmt = get_log_format(resolved_level)

    root_logger = logging.getLogger()
    root_logger.setLevel(resolved_level)

    if not root_logger.hasHandlers():
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter(fmt))
        ensure_request_id_filter(handler)
        root_logger.addHandler(handler)

    for handler in root_logger.handlers:
        ensure_request_id_filter(handler)

        current_formatter = handler.formatter
        if current_formatter is None:
            handler.setFormatter(logging.Formatter(fmt))
            continue

        current_format = getattr(current_formatter, "_fmt", "")
        if "%(request_id)s" not in current_format:
            handler.setFormatter(logging.Formatter(fmt))

    if resolved_level == logging.DEBUG:
        logging.getLogger("filelock").setLevel(logging.INFO)
