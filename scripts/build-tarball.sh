#!/usr/bin/env bash
# Build a self-contained flash-worker tarball for process injection.
# Output: dist/flash-worker-v{VERSION}-py{PYTHON_VERSION}-linux-x86_64.tar.gz
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Read version from source
VERSION=$(python3 -c "
import re
text = open('$REPO_ROOT/src/version.py').read()
print(re.search(r'__version__\\s*=\\s*\"([^\"]+)\"', text).group(1))
")
echo "Building flash-worker tarball v${VERSION}"

# Configuration
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"

# Validate Python version against project requirement (>=3.10, <3.15)
PY_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
if [ "$PY_MINOR" -lt 10 ] || [ "$PY_MINOR" -ge 15 ]; then
    echo "ERROR: Python ${PYTHON_VERSION} is outside project requirement (>=3.10, <3.15)"
    exit 1
fi

UV_VERSION="0.7.19"
UV_URL="https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-x86_64-unknown-linux-gnu.tar.gz"

# Build in container-local tmpdir to avoid macOS case-insensitive filesystem issues
BUILD_DIR="/tmp/flash-worker-build"
TARBALL_ROOT="$BUILD_DIR/flash-worker"
OUTPUT_DIR="$REPO_ROOT/dist"
TARBALL_NAME="flash-worker-v${VERSION}-py${PYTHON_VERSION}-linux-x86_64.tar.gz"

# Clean previous build
rm -rf "$BUILD_DIR"
mkdir -p "$TARBALL_ROOT" "$OUTPUT_DIR" "$OUTPUT_DIR/.cache"

# 1. Install Python via uv (handles version resolution and caching)
echo "Installing Python ${PYTHON_VERSION} via uv..."
uv python install "$PYTHON_VERSION"
PYTHON_BIN=$(uv python find --python-preference only-managed "$PYTHON_VERSION")
PYTHON_INSTALL_DIR=$(cd "$(dirname "$PYTHON_BIN")/.." && pwd -P)
cp -r "$PYTHON_INSTALL_DIR" "$TARBALL_ROOT/python"

# Verify installation
if [ ! -f "$TARBALL_ROOT/python/bin/python3" ]; then
    echo "ERROR: Python installation failed - python3 binary not found"
    exit 1
fi
PYTHON_FULL_VERSION=$("$TARBALL_ROOT/python/bin/python3" -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}.{v.micro}')")
echo "  Python ${PYTHON_FULL_VERSION} installed"

# 2. Download uv static binary
echo "Downloading uv ${UV_VERSION}..."
if [ -f "$OUTPUT_DIR/.cache/uv-${UV_VERSION}.tar.gz" ]; then
    echo "  Using cached uv download"
    tar xzf "$OUTPUT_DIR/.cache/uv-${UV_VERSION}.tar.gz" -C "$TARBALL_ROOT" --no-same-owner --strip-components=1 "uv-x86_64-unknown-linux-gnu/uv" 2>/dev/null || true
else
    curl -fsSL "$UV_URL" -o "$OUTPUT_DIR/.cache/uv-${UV_VERSION}.tar.gz"
    tar xzf "$OUTPUT_DIR/.cache/uv-${UV_VERSION}.tar.gz" -C "$TARBALL_ROOT" --no-same-owner --strip-components=1 "uv-x86_64-unknown-linux-gnu/uv" 2>/dev/null || true
fi
chmod +x "$TARBALL_ROOT/uv"

# 3. Create venv using portable Python
echo "Creating virtual environment..."
"$TARBALL_ROOT/python/bin/python3" -m venv "$TARBALL_ROOT/venv"

# Fix venv symlinks to be relative (python -m venv creates absolute symlinks)
cd "$TARBALL_ROOT/venv/bin"
for link in python python3 python3.*; do
    [ -L "$link" ] || continue
    target=$(readlink "$link")
    case "$target" in
        /*)  # Absolute path — make relative to ../../python/bin/
            basename=$(basename "$target")
            ln -sf "../../python/bin/$basename" "$link"
            ;;
    esac
done
cd "$REPO_ROOT"

# 4. Export and install production dependencies
echo "Installing production dependencies..."
cd "$REPO_ROOT"
# Use the host uv to export requirements (it reads pyproject.toml/uv.lock)
uv export --format requirements-txt --no-dev --no-hashes > "$BUILD_DIR/requirements.txt"

# Install into the tarball's venv using the tarball's uv
"$TARBALL_ROOT/uv" pip install \
    --python "$TARBALL_ROOT/venv/bin/python" \
    -r "$BUILD_DIR/requirements.txt"

# 5. Copy source files
echo "Copying source files..."
cp -r "$REPO_ROOT/src/"*.py "$TARBALL_ROOT/src/" 2>/dev/null || true
mkdir -p "$TARBALL_ROOT/src"
for f in "$REPO_ROOT/src/"*.py; do
    [ -f "$f" ] && cp "$f" "$TARBALL_ROOT/src/"
done
# Copy test scripts (used by --test flag)
for f in "$REPO_ROOT/src/"*.sh; do
    [ -f "$f" ] && cp "$f" "$TARBALL_ROOT/src/" && chmod +x "$TARBALL_ROOT/src/$(basename "$f")"
done
# Copy test JSON files
if [ -d "$REPO_ROOT/src/tests" ]; then
    cp -r "$REPO_ROOT/src/tests" "$TARBALL_ROOT/src/tests"
fi

# 6. Copy bootstrap script
cp "$REPO_ROOT/scripts/bootstrap.sh" "$TARBALL_ROOT/bootstrap.sh"
chmod +x "$TARBALL_ROOT/bootstrap.sh"

# 7. Write version file for cache invalidation
echo "$VERSION" > "$TARBALL_ROOT/.version"

# 8. Write MANIFEST.json
# Use sha256sum on Linux, shasum on macOS
if command -v sha256sum >/dev/null 2>&1; then
    SHA_CMD="sha256sum"
else
    SHA_CMD="shasum -a 256"
fi
CONTENTS_SHA=$(find "$TARBALL_ROOT" -type f -exec $SHA_CMD {} \; | sort | $SHA_CMD | cut -d' ' -f1)
cat > "$TARBALL_ROOT/MANIFEST.json" <<MANIFEST
{
    "version": "${VERSION}",
    "python_version": "${PYTHON_FULL_VERSION}",
    "uv_version": "${UV_VERSION}",
    "platform": "x86_64-unknown-linux-gnu",
    "sha256": "${CONTENTS_SHA}"
}
MANIFEST

# 9. Package tarball
echo "Packaging tarball..."
cd "$BUILD_DIR"
tar czf "$OUTPUT_DIR/$TARBALL_NAME" flash-worker/

# 10. Report
TARBALL_SIZE=$(du -h "$OUTPUT_DIR/$TARBALL_NAME" | cut -f1)
echo ""
echo "Tarball built: $OUTPUT_DIR/$TARBALL_NAME"
echo "Size: $TARBALL_SIZE"
echo "Version: $VERSION"
echo "SHA256: $($SHA_CMD "$OUTPUT_DIR/$TARBALL_NAME" | cut -d' ' -f1)"

# Cleanup build dir (keep cache)
rm -rf "$BUILD_DIR"
