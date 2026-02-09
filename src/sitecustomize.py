"""Python sitecustomize module - automatically imported before any other modules.

This file ensures that ALL bundled packages in /app take precedence over
system-installed versions, while still allowing system packages (torch, etc.)
to serve as fallbacks.

Architecture:
- Flash builds install user dependencies into /app (numpy, pandas, etc.)
- When using --use-local-flash, runpod_flash source is also bundled in /app
- This module ensures /app is first in sys.path so all bundled packages are found
- System packages (torch from base image) are still accessible as fallbacks

This is critical: If /app is not prioritized, NONE of the user's dependencies work!
"""

import sys
from pathlib import Path

# Target directory where build artifacts are extracted
APP_DIR = Path("/app")
app_dir_str = str(APP_DIR)

# Always ensure /app is at the front of sys.path (if it exists)
# This is required for ALL flash deployments, not just --use-local-flash
if APP_DIR.exists() and APP_DIR.is_dir():
    # Remove /app from wherever it might be in sys.path
    sys.path = [p for p in sys.path if p != app_dir_str]

    # Insert /app at position 0 (highest priority)
    sys.path.insert(0, app_dir_str)

    # Check if this is a --use-local-flash build
    bundled_flash = APP_DIR / "runpod_flash"
    if bundled_flash.exists() and bundled_flash.is_dir():
        print(
            f"[sitecustomize] Using bundled packages from {app_dir_str} "
            f"(local runpod_flash detected)",
            file=sys.stderr,
            flush=True,
        )
    else:
        print(
            f"[sitecustomize] Using bundled packages from {app_dir_str}",
            file=sys.stderr,
            flush=True,
        )
