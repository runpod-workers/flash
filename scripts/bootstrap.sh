#!/bin/sh
# Flash Worker bootstrap -- entry point for process-injected runtime.
# Launched by dockerArgs after tarball extraction.
set -e

FW_DIR="$(cd "$(dirname "$0")" && pwd)"

# Self-test mode (used by tarball-test targets)
if [ "$1" = "--test" ]; then
    echo "Flash Worker bootstrap self-test"
    echo "FW_DIR: $FW_DIR"
    echo "Python: $("$FW_DIR/python/bin/python3" --version)"
    echo "uv: $("$FW_DIR/uv" --version)"
    "$FW_DIR/venv/bin/python" -c "import pydantic; print(f'pydantic {pydantic.__version__}')"
    "$FW_DIR/venv/bin/python" -c "import fastapi; print(f'fastapi {fastapi.__version__}')"
    echo "Version: $(cat "$FW_DIR/.version")"
    echo "Self-test passed"
    exit 0
fi

# Isolated flash-worker environment
export PATH="$FW_DIR/venv/bin:$FW_DIR/python/bin:$FW_DIR:$PATH"
export VIRTUAL_ENV="$FW_DIR/venv"
PYTHON_MINOR=$("$FW_DIR/python/bin/python3" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
export PYTHONPATH="$FW_DIR/src:$VIRTUAL_ENV/lib/python${PYTHON_MINOR}/site-packages${PYTHONPATH:+:$PYTHONPATH}"

# Signal tarball mode for dependency installer
export FLASH_WORKER_INSTALL_DIR="$FW_DIR"

# Mode detection (same contract as Docker images)
ENDPOINT_TYPE="${FLASH_ENDPOINT_TYPE:-qb}"

if [ "$ENDPOINT_TYPE" = "lb" ]; then
    exec uvicorn lb_handler:app \
        --host 0.0.0.0 \
        --port 80 \
        --timeout-keep-alive 600 \
        --app-dir "$FW_DIR/src"
else
    exec python3 "$FW_DIR/src/handler.py"
fi
