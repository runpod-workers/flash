"""Offline tests for the pack `run` entrypoint (Python discovery + validation).

A stub `python3` handles both calls `run` makes: the version probe
(`python -c ...`) prints a configurable version; any other invocation
(the `pack.py` launch) records its argv and exits 0, so pack.py never
actually runs.
"""

import subprocess
from pathlib import Path

RUN = Path(__file__).parent / "run"

STUB = """#!/bin/sh
case "$1" in
  -c) echo "$STUB_PYVER" ;;
  *)  printf '%s ' "$@" > "$STUB_MARKER"; exit 0 ;;
esac
"""


def _make_stub(dir_: Path, name: str, version: str, marker: Path) -> None:
    p = dir_ / name
    p.write_text(STUB)
    p.chmod(0o755)


def _run(
    tmp_path, *, pyver, path_has_python=True, flash_python=None, supported="3.10 3.11 3.12 3.13"
):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    marker = tmp_path / "marker"
    env = {
        "PATH": str(bindir) if path_has_python else "/nonexistent",
        "FLASH_SUPPORTED_PYTHONS": supported,
        "STUB_PYVER": pyver,
        "STUB_MARKER": str(marker),
    }
    if path_has_python:
        _make_stub(bindir, "python3", pyver, marker)
    if flash_python is not None:
        fp = tmp_path / "mypy"
        fp.write_text(STUB)
        fp.chmod(0o755)
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
    bindir = tmp_path / "bin"
    bindir.mkdir()
    marker = tmp_path / "marker"
    # PATH python3 reports unsupported 3.9
    (bindir / "python3").write_text(STUB)
    (bindir / "python3").chmod(0o755)
    # FLASH_PYTHON points at a stub reporting supported 3.12
    fp = tmp_path / "mypy"
    fp.write_text(STUB)
    fp.chmod(0o755)
    env = {
        "PATH": str(bindir),
        "FLASH_SUPPORTED_PYTHONS": "3.10 3.11 3.12 3.13",
        "STUB_MARKER": str(marker),
        "STUB_PYVER": "3.12",  # both stubs read this; override is what we assert gets used
        "FLASH_PYTHON": str(fp),
    }
    proc = subprocess.run(
        [str(RUN), "--socket", "/tmp/x.sock"], env=env, capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr
    assert marker.exists() and "pack.py" in marker.read_text()
