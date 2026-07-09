#!/usr/bin/env bash
# Test the Flash Capsule inject-at-start flow in a local Docker container.
#
# Reproduces exactly what Runpod does at container start (run a plain base
# image with the capsule command as its start command), but points
# build_capsule_injection_cmd() at the artifacts via file:// on a mounted
# volume -- no network, no GitHub release needed. Builds the supervisor for
# the host arch so the container runs natively.
#
# Requires a running Docker daemon (e.g. `colima start`).
#
# Usage:
#   scripts/test-capsule-local.sh
# Overridable via env: BASE_IMAGE, PORT, PLATFORM, FLASH_ROOT.
set -euo pipefail

WORKER_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# The flash SDK worktree (holds build_capsule_injection_cmd). Override if elsewhere.
FLASH_ROOT="${FLASH_ROOT:-$WORKER_ROOT/../../flash/capsule-skeleton}"
BASE_IMAGE="${BASE_IMAGE:-python:3.11-slim}"
PORT="${PORT:-8080}"
HOST_ARCH="$(uname -m | sed 's/x86_64/amd64/; s/aarch64/arm64/')"
PLATFORM="${PLATFORM:-linux/$HOST_ARCH}"
GOARCH="${PLATFORM##*/}"
NAME="flash-capsule-test"

if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker daemon not reachable. Start it first (e.g. 'colima start')." >&2
    exit 1
fi

# Create the artifacts dir under $HOME: Docker VMs (colima/Docker Desktop) only
# bind-mount specific host paths ($HOME is mounted; macOS $TMPDIR / /var/folders
# is NOT), so a mktemp there would mount empty inside the container.
ART="$(mktemp -d "$HOME/.flash-capsule-test.XXXXXX")"
cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; rm -rf "$ART"; }
trap cleanup EXIT

echo "==> Building supervisor ($PLATFORM) + echo pack into $ART"
( cd "$WORKER_ROOT/supervisor" \
    && CGO_ENABLED=0 GOOS=linux GOARCH="$GOARCH" go build -trimpath -ldflags="-s -w" -o "$ART/supervisor" . )
tar czf "$ART/python-echo-pack.tar.gz" \
    --exclude='test_*.py' --exclude='__pycache__' --exclude='.coverage*' \
    -C "$WORKER_ROOT/packs/python-echo" .

echo "==> Generating capsule command from the flash SDK (tests the real injection.py)"
CMD="$(cd "$FLASH_ROOT" && uv run python -c '
from runpod_flash.core.capsule.injection import build_capsule_injection_cmd
print(build_capsule_injection_cmd(
    "file:///art/supervisor",
    "file:///art/python-echo-pack.tar.gz",
))')"

echo "==> Starting container ($BASE_IMAGE, $PLATFORM), host port $PORT -> container 80"
docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" --platform "$PLATFORM" \
    -p "$PORT:80" -v "$ART:/art:ro" "$BASE_IMAGE" \
    sh -c "$CMD" >/dev/null

EXPECT_LOG="${EXPECT_LOG:-}"

if [ -n "$EXPECT_LOG" ]; then
    # Expect the capsule to fail to become healthy, with a specific log message.
    sleep 6
    logs="$(docker logs "$NAME" 2>&1 || true)"
    if printf '%s' "$logs" | grep -qF "$EXPECT_LOG"; then
        echo "==> EXPECTED FAILURE observed: matched \"$EXPECT_LOG\""
        echo "$logs" | tail -5
        echo "==> PASS (clear error case)"
        exit 0
    fi
    echo "FAILED: expected log \"$EXPECT_LOG\" not found. Logs:" >&2
    printf '%s\n' "$logs" | tail -20 >&2
    exit 1
fi

echo "==> Waiting for /ping to become healthy"
healthy=0
for _ in $(seq 1 60); do
    if curl -fsS "http://localhost:$PORT/ping" >/dev/null 2>&1; then healthy=1; break; fi
    sleep 1
done
if [ "$healthy" -ne 1 ]; then
    echo "FAILED: /ping never healthy. Container logs:" >&2
    docker logs "$NAME" 2>&1 | tail -30 >&2
    exit 1
fi

echo "==> /ping:"
curl -fsS "http://localhost:$PORT/ping"; echo
echo "==> POST /invoke {\"greeting\":\"hi\"} (expect {\"result\":{\"greeting\":\"hi\"}}):"
curl -fsS -X POST "http://localhost:$PORT/invoke" \
    -H 'content-type: application/json' -d '{"greeting":"hi"}'; echo
echo "==> supervisor logs:"
docker logs "$NAME" 2>&1 | tail -15
echo "==> PASS (container will be removed on exit)"
