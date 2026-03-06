# Logger Configuration
NAMESPACE = "flash"
"""Application logger namespace for all components."""

# System Package Acceleration with Nala
LARGE_SYSTEM_PACKAGES = [
    "build-essential",
    "cmake",
    "cuda-toolkit",
    "curl",
    "g++",
    "gcc",
    "git",
    "libssl-dev",
    "nvidia-cuda-dev",
    "python3-dev",
    "wget",
]
"""List of system packages that benefit from nala's accelerated installation."""

# Cache Sync Configuration
CACHE_DIR = "/root/.cache"
"""Directory containing package and model caches."""

VOLUME_CACHE_PATH = "/runpod-volume/.cache"
"""Network volume path for cache tarball storage."""

# Volume Unpacking Configuration
DEFAULT_APP_DIR = "/app"
"""Default application directory for unpacking build artifacts."""

DEFAULT_ARTIFACT_PATH = "/root/.runpod/artifact.tar.gz"
"""Default path for build artifact tarball.

Can be overridden via FLASH_BUILD_ARTIFACT_PATH environment variable.
"""

# Environment Variables for Volume Unpacking
# FLASH_BUILD_ARTIFACT_PATH: Custom path to build artifact tarball
# FLASH_DISABLE_UNPACK: Set to "1", "true", or "yes" to disable unpacking

# Cross-Endpoint Function Routing
FLASH_MANIFEST_PATH = "/app/flash_manifest.json"
"""Path to Flash manifest with function routing configuration."""

DEFAULT_ENDPOINT_TIMEOUT = 300
"""Default timeout in seconds for cross-endpoint HTTP requests."""

DEFAULT_TARBALL_UNPACK_ATTEMPTS = 3
"""Number of times the Flash-deployed endpoint will attempt to unpack the worker-flash tarball from mounted volume."""
DEFAULT_TARBALL_UNPACK_INTERVAL = 30
"""Time in seconds the Flash-deployed endpoint will wait between tarball unpack attempts."""

# Dependency Recovery Configuration
MAX_IMPORT_RECOVERY_ATTEMPTS = 3
"""Max on-the-fly package installs before giving up during handler loading.

When a deployed handler fails to import due to a missing package, the worker
attempts to install it and retry. This caps the retry loop to prevent unbounded
installs (e.g. a package with many missing transitive deps).
"""

# Process Injection (Tarball Mode)
FLASH_WORKER_INSTALL_DIR_ENV = "FLASH_WORKER_INSTALL_DIR"
"""Env var set by bootstrap.sh to signal tarball mode. Value is the extraction directory."""
