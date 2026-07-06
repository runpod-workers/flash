#!/usr/bin/env bash
# Build the two Flash Capsule artifacts for the walking skeleton:
#   dist/supervisor              - static linux/amd64 supervisor binary
#   dist/python-echo-pack.tar.gz - the echo language pack
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$REPO_ROOT/dist"
mkdir -p "$DIST"

echo "Building supervisor (static linux/amd64)..."
( cd "$REPO_ROOT/supervisor" && CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath -ldflags="-s -w" -o "$DIST/supervisor" . )

echo "Packaging echo pack..."
tar czf "$DIST/python-echo-pack.tar.gz" -C "$REPO_ROOT/packs/python-echo" .

echo ""
echo "Artifacts:"
ls -la "$DIST/supervisor" "$DIST/python-echo-pack.tar.gz"
file "$DIST/supervisor"
