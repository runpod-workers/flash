"""Offline tests for the pack `run` entrypoint (Python discovery + validation).

Each stub handles both calls `run` makes: the version probe (`python -c
...`) prints a *version baked into the stub itself* (not read from a
shared env var), and any other invocation (the `pack.py` launch) records
its argv into a marker file and exits 0, so pack.py never actually runs.
Baking the version into each stub lets a single test give the PATH
`python3` stub and the `FLASH_PYTHON` stub different, independently
verifiable versions.
"""

import subprocess
from pathlib import Path

RUN = Path(__file__).parent / "run"

STUB_TEMPLATE = """#!/bin/sh
case "$1" in
  -c) echo "{version}" ;;
  *)  printf '%s ' "$@" > "{marker}"; exit 0 ;;
esac
"""


def _write_stub(path: Path, version: str, marker: Path) -> None:
    path.write_text(STUB_TEMPLATE.format(version=version, marker=marker))
    path.chmod(0o755)


def _run(
    tmp_path, *, pyver, path_has_python=True, flash_python=None, supported="3.10 3.11 3.12 3.13"
):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    marker = tmp_path / "marker"
    env = {
        "PATH": str(bindir) if path_has_python else "/nonexistent",
        "FLASH_SUPPORTED_PYTHONS": supported,
    }
    if path_has_python:
        _write_stub(bindir / "python3", pyver, marker)
    if flash_python is not None:
        fp = tmp_path / "flash_python_stub"
        _write_stub(fp, flash_python, marker)
        env["FLASH_PYTHON"] = str(fp)
    proc = subprocess.run(
        [str(RUN), "--socket", "/tmp/x.sock"],
        env=env,
        capture_output=True,
        text=True,
    )
    return proc, marker


def test_supported_python_execs_pack(tmp_path):
    proc, marker = _run(tmp_path, pyver="3.11")
    assert proc.returncode == 0, proc.stderr
    assert marker.exists()
    assert "pack.py" in marker.read_text()
    assert "--socket /tmp/x.sock" in marker.read_text()


def test_unsupported_python_exits_4_with_message(tmp_path):
    proc, _ = _run(tmp_path, pyver="3.9")
    assert proc.returncode == 4
    assert "not supported" in proc.stderr
    assert "3.9" in proc.stderr


def test_no_python_exits_3_with_message(tmp_path):
    proc, _ = _run(tmp_path, pyver="3.11", path_has_python=False)
    assert proc.returncode == 3
    assert "no Python" in proc.stderr


def test_flash_python_override_is_used(tmp_path):
    # PATH python3 reports an UNSUPPORTED version; FLASH_PYTHON reports a
    # SUPPORTED, distinct version. If `run` ignored FLASH_PYTHON and used
    # PATH python3 instead, it would see "3.9" and exit 4 (unsupported),
    # so this test can only pass if the override is actually honored.
    proc, marker = _run(tmp_path, pyver="3.9", flash_python="3.12")
    assert proc.returncode == 0, proc.stderr
    assert marker.exists() and "pack.py" in marker.read_text()


def test_python_fallback_when_no_python3(tmp_path):
    # No `python3` on PATH, but a `python` binary (supported version) is
    # present; `run` should fall back to discovering `python`.
    bindir = tmp_path / "bin"
    bindir.mkdir()
    marker = tmp_path / "marker"
    _write_stub(bindir / "python", "3.11", marker)
    env = {
        "PATH": str(bindir),
        "FLASH_SUPPORTED_PYTHONS": "3.10 3.11 3.12 3.13",
    }
    proc = subprocess.run(
        [str(RUN), "--socket", "/tmp/x.sock"], env=env, capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr
    assert marker.exists() and "pack.py" in marker.read_text()
