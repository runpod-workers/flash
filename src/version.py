"""Version utilities for flash-worker boot logging."""

from importlib.metadata import PackageNotFoundError, version

# Worker version — keep in sync with pyproject.toml
__version__ = "1.1.0"


def _get_version(package_name: str) -> str:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "unknown"


def get_worker_version() -> str:
    return __version__


def get_flash_version() -> str:
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
