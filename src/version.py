"""Version utilities for flash-worker boot logging."""

import re
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def _read_pyproject_version(pyproject_path: Path) -> str | None:
    """Read version from a pyproject.toml file via simple regex."""
    try:
        text = pyproject_path.read_text()
        match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
        return match.group(1) if match else None
    except FileNotFoundError:
        return None


def _get_version(package_name: str) -> str:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "unknown"


def get_worker_version() -> str:
    """Read worker version from pyproject.toml (co-located in Docker image)."""
    ver = _read_pyproject_version(Path(__file__).parent / "pyproject.toml")
    return ver or _get_version("worker-flash")


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
        f"runpod-flash {get_flash_version()} | "
        f"runpod {get_runpod_version()}"
    )
