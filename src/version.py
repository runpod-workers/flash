"""Version utilities for flash-worker boot logging."""

import os
import platform
import sys
from importlib.metadata import PackageNotFoundError, version

__version__ = "1.5.0"  # x-release-please-version


class PythonVersionMismatchError(RuntimeError):
    """Raised when the running interpreter does not match the image's declared version."""


def assert_python_version_matches_image() -> None:
    """Fail fast if ``sys.version_info`` disagrees with ``FLASH_PYTHON_VERSION``.

    The Dockerfiles stamp ``FLASH_PYTHON_VERSION`` with the image's target
    Python (e.g. ``3.11``). If an image is mis-tagged, an apt upgrade
    changes ``python`` symlinks, or the GPU side-by-side torch install fails
    silently, this surfaces the skew immediately at worker boot instead of
    letting user code fail later with a confusing ABI error.

    Skips the check when ``FLASH_PYTHON_VERSION`` is unset (local dev,
    test harnesses).
    """
    declared = os.environ.get("FLASH_PYTHON_VERSION")
    if not declared:
        return

    actual = f"{sys.version_info.major}.{sys.version_info.minor}"
    if actual != declared:
        raise PythonVersionMismatchError(
            f"Worker interpreter mismatch: image declares FLASH_PYTHON_VERSION="
            f"{declared!r} but sys.version_info reports {actual!r}. "
            f"Rebuild the image with the correct PYTHON_VERSION build arg."
        )


class PythonVersionMismatchError(RuntimeError):
    """Raised when the running interpreter does not match the image's declared version."""


def assert_python_version_matches_image() -> None:
    """Fail fast if ``sys.version_info`` disagrees with ``FLASH_PYTHON_VERSION``.

    The Dockerfiles stamp ``FLASH_PYTHON_VERSION`` with the image's target
    Python (e.g. ``3.11``). If an image is mis-tagged, an apt upgrade
    changes ``python`` symlinks, or the GPU side-by-side torch install fails
    silently, this surfaces the skew immediately at worker boot instead of
    letting user code fail later with a confusing ABI error.

    Skips the check when ``FLASH_PYTHON_VERSION`` is unset (local dev,
    test harnesses).
    """
    declared = os.environ.get("FLASH_PYTHON_VERSION")
    if not declared:
        return

    actual = f"{sys.version_info.major}.{sys.version_info.minor}"
    if actual != declared:
        raise PythonVersionMismatchError(
            f"Worker interpreter mismatch: image declares FLASH_PYTHON_VERSION="
            f"{declared!r} but sys.version_info reports {actual!r}. "
            f"Rebuild the image with the correct PYTHON_VERSION build arg."
        )


def _get_version(package_name: str) -> str:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "unknown"


def get_worker_version() -> str:
    return __version__


def get_flash_version() -> str:
    """Read bundled flash version, falling back to pip metadata."""
    try:
        from runpod_flash import __version__ as flash_ver

        return str(flash_ver)
    except (ImportError, AttributeError):
        return _get_version("runpod-flash")


def get_runpod_version() -> str:
    return _get_version("runpod")


def format_version_banner() -> str:
    return (
        f"Starting Flash Worker {get_worker_version()} | "
        f"Python {platform.python_version()} | "
        f"runpod-flash {get_flash_version()} | "
        f"runpod {get_runpod_version()}"
    )
