"""
Logging configuration for worker-flash.

Provides thin wrapper around RunPodLogger for backward compatibility.
New code should use rp_logger_adapter directly.
"""

import sys
from typing import Union, Optional

from rp_logger_adapter import (
    setup_flash_logging,
    get_log_level as get_rp_log_level,
)


def get_log_level() -> int:
    """Get log level from environment variable, defaulting to INFO.

    Deprecated: Use get_rp_log_level() from rp_logger_adapter instead.
    This is kept for backward compatibility.
    """
    # Convert string level to dummy int for backward compatibility
    level_str = get_rp_log_level()
    level_map = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40}
    return level_map.get(level_str, 20)  # Default to INFO (20)


def get_log_format(level: int) -> str:
    """Get appropriate log format based on level.

    Deprecated: RunPodLogger handles formatting internally.
    This is kept as a placeholder for backward compatibility.
    """
    return "%(message)s"  # RunPodLogger handles the actual format


def setup_logging(
    level: Optional[Union[int, str]] = None,
    stream=sys.stdout,
    fmt: Optional[str] = None,
) -> None:
    """
    Setup logging configuration for worker-flash.

    Deprecated: Use setup_flash_logging() from rp_logger_adapter instead.
    This is kept for backward compatibility.

    Args:
        level: Log level (defaults to LOG_LEVEL env var or INFO)
        stream: Output stream for logs (ignored, RunPodLogger uses stdout)
        fmt: Custom format string (ignored, RunPodLogger handles format)
    """
    # Convert int level to string if needed
    if isinstance(level, int):
        level_map = {10: "DEBUG", 20: "INFO", 30: "WARN", 40: "ERROR"}
        level = level_map.get(level, "INFO")

    setup_flash_logging(level)
