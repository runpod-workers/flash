"""
Centralized log streaming system for capturing stdout to FunctionResponse.stdout.

This module provides thread-safe output buffering and streaming capabilities to ensure
all system logs (dependency installation, workspace setup, etc.) are visible in the
remote execution response. It captures stdout directly rather than using logging handlers,
since RunPodLogger uses print() internally.
"""

import sys
import threading
from collections import deque
from typing import Optional, Deque, Callable


class LogCapturingWriter:
    """
    Write-through stdout wrapper that captures output while maintaining console visibility.

    This class intercepts stdout writes, buffers complete lines, and forwards all output
    to the original stdout.
    """

    def __init__(self, original_stdout, log_streamer: "LogStreamer"):
        """
        Initialize the capturing writer.

        Args:
            original_stdout: The original sys.stdout
            log_streamer: The LogStreamer instance to buffer lines to
        """
        self.original_stdout = original_stdout
        self.log_streamer = log_streamer
        self._line_buffer = ""
        self._lock = threading.Lock()

    def write(self, text: str) -> int:
        """
        Write text to stdout, capturing complete lines.

        Args:
            text: Text to write

        Returns:
            Number of characters written
        """
        with self._lock:
            # Write to original stdout immediately (write-through)
            self.original_stdout.write(text)

            # Buffer incomplete lines
            self._line_buffer += text

            # Process complete lines
            while "\n" in self._line_buffer:
                line, self._line_buffer = self._line_buffer.split("\n", 1)
                if line:  # Don't add empty lines
                    self.log_streamer.add_log_entry(line)

        return len(text)

    def flush(self) -> None:
        """Flush both the capturing writer and original stdout."""
        with self._lock:
            self.original_stdout.flush()

    def isatty(self) -> bool:
        """Check if original stdout is a TTY."""
        try:
            return bool(self.original_stdout.isatty())
        except (AttributeError, TypeError):
            return False


class LogStreamer:
    """
    Thread-safe log streaming system that captures stdout and buffers complete lines.
    """

    def __init__(self, max_buffer_size: int = 1000):
        """
        Initialize the log streamer.

        Args:
            max_buffer_size: Maximum number of log entries to keep in buffer
        """
        self._buffer: Deque[str] = deque(maxlen=max_buffer_size)
        self._lock = threading.Lock()
        self._writer: Optional[LogCapturingWriter] = None
        self._original_stdout: Optional[object] = None
        self._callback: Optional[Callable[[str], None]] = None

    def start_streaming(
        self,
        level: int = 20,  # INFO level (unused, kept for compatibility)
        callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Start capturing stdout.

        Args:
            level: Log level (unused, kept for compatibility with previous API)
            callback: Optional callback function called for each log line
        """
        with self._lock:
            if self._writer is not None:
                return  # Already streaming

            self._callback = callback

            # Save original stdout and replace with capturing writer
            self._original_stdout = sys.stdout
            self._writer = LogCapturingWriter(self._original_stdout, self)
            sys.stdout = self._writer

    def stop_streaming(self) -> None:
        """Stop capturing stdout and restore original."""
        with self._lock:
            if self._writer is None:
                return  # Not streaming

            # Restore original stdout
            if self._original_stdout is not None:
                sys.stdout = self._original_stdout

            self._writer = None
            self._original_stdout = None
            self._callback = None

    def add_log_entry(self, log_entry: str) -> None:
        """
        Add a log entry to the buffer.

        Args:
            log_entry: Complete log line to add
        """
        with self._lock:
            self._buffer.append(log_entry)

            # Call callback if provided
            if self._callback:
                try:
                    self._callback(log_entry)
                except Exception:
                    # Don't let callback errors break logging
                    pass

    def get_logs(self, clear_buffer: bool = False) -> str:
        """
        Get all buffered log entries as a single string.

        Args:
            clear_buffer: If True, clear the buffer after getting logs

        Returns:
            All log entries joined with newlines
        """
        with self._lock:
            if not self._buffer:
                return ""

            logs = "\n".join(self._buffer)

            if clear_buffer:
                self._buffer.clear()

            return logs

    def get_new_logs(self) -> str:
        """
        Get all buffered logs and clear the buffer.
        Convenience method equivalent to get_logs(clear_buffer=True).

        Returns:
            All log entries joined with newlines
        """
        return self.get_logs(clear_buffer=True)

    def has_logs(self) -> bool:
        """Check if there are any logs in the buffer."""
        with self._lock:
            return len(self._buffer) > 0


# Global log streamer instance for convenience
_global_streamer: Optional[LogStreamer] = None
_streamer_lock = threading.Lock()


def get_global_log_streamer() -> LogStreamer:
    """
    Get or create the global log streamer instance.

    Returns:
        Global LogStreamer instance
    """
    global _global_streamer

    with _streamer_lock:
        if _global_streamer is None:
            _global_streamer = LogStreamer()
        return _global_streamer


def start_log_streaming(
    level: int = 20, callback: Optional[Callable[[str], None]] = None
) -> LogStreamer:
    """
    Convenience function to start log streaming with the global streamer.

    Args:
        level: Minimum log level (unused, kept for compatibility)
        callback: Optional callback for each log line

    Returns:
        The global LogStreamer instance
    """
    streamer = get_global_log_streamer()
    streamer.start_streaming(level=level, callback=callback)
    return streamer


def stop_log_streaming() -> None:
    """Convenience function to stop log streaming with the global streamer."""
    if _global_streamer is not None:
        _global_streamer.stop_streaming()


def get_streamed_logs(clear_buffer: bool = False) -> str:
    """
    Convenience function to get logs from the global streamer.

    Args:
        clear_buffer: If True, clear the buffer after getting logs

    Returns:
        All buffered log entries as a string
    """
    if _global_streamer is None:
        return ""
    return _global_streamer.get_logs(clear_buffer=clear_buffer)
