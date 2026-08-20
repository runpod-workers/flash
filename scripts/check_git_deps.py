#!/usr/bin/env python3
"""Fail if pyproject.toml declares any dependency from a git ref.

Why this exists: a git-ref dependency carries no version, so the Bump Runtime
Dependencies workflow has nothing to bump and silently stops tracking that
package. Worse, the ref is not immutable -- when the referenced branch is
deleted, every `uv lock` and `uv sync` on main hard-fails with
"couldn't find remote ref". That happened for real: a temporary pin to a flash
feature branch broke main for two weeks (PR #103).

Usage:
    python scripts/check_git_deps.py [pyproject.toml]

Exits 0 when clean, 1 when a git dependency is found or the file is unreadable.

Temporary pins during a coordinated cross-repo release are the legitimate use
case this blocks. When you need one, land it behind an explicit, time-boxed
exception rather than deleting this check -- and revert it the moment the
depended-on version is published.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # tomllib is stdlib only on 3.11+; tomli is the drop-in backport
    import tomli as tomllib

GIT_MARKERS = ("git+", "git://")
DEFAULT_PYPROJECT = "pyproject.toml"


def _is_git_requirement(requirement: str) -> bool:
    """True if a PEP 508 requirement string points at a git repository."""
    return any(marker in requirement for marker in GIT_MARKERS)


def _scan_requirements(requirements: Any, label: str) -> list[str]:
    """Collect offending requirement strings from one dependency list."""
    if not isinstance(requirements, list):
        return []
    return [
        f"{label}: {req}"
        for req in requirements
        if isinstance(req, str) and _is_git_requirement(req)
    ]


def find_git_dependencies(pyproject_text: str) -> list[str]:
    """Return a labelled description of every git-sourced dependency.

    Covers the four places a git ref can enter a uv project: project
    dependencies, optional-dependency extras, PEP 735 dependency groups, and
    `[tool.uv.sources]`.

    Returns an empty list when the file declares no git dependencies.
    """
    data = tomllib.loads(pyproject_text)
    offenders: list[str] = []

    project = data.get("project", {})
    offenders += _scan_requirements(project.get("dependencies"), "project.dependencies")

    for extra, requirements in (project.get("optional-dependencies") or {}).items():
        offenders += _scan_requirements(requirements, f"project.optional-dependencies.{extra}")

    for group, requirements in (data.get("dependency-groups") or {}).items():
        offenders += _scan_requirements(requirements, f"dependency-groups.{group}")

    sources = (data.get("tool", {}).get("uv", {}) or {}).get("sources") or {}
    for name, source in sources.items():
        if isinstance(source, dict) and "git" in source:
            offenders.append(f"tool.uv.sources.{name}: git = {source['git']}")

    return offenders


def main(argv: list[str] | None = None) -> int:
    """Check a pyproject.toml and report offenders. Returns a process exit code."""
    args = argv if argv is not None else sys.argv[1:]
    target = Path(args[0]) if args else Path(DEFAULT_PYPROJECT)

    try:
        text = target.read_text()
    except OSError as e:
        print(f"error: cannot read {target}: {e}")
        return 1

    try:
        offenders = find_git_dependencies(text)
    except tomllib.TOMLDecodeError as e:
        print(f"error: cannot parse {target}: {e}")
        return 1

    if not offenders:
        print(f"{target}: no git dependencies")
        return 0

    print(f"{target}: git dependencies are not allowed on main:")
    for offender in offenders:
        print(f"  {offender}")
    print(
        "\nA git ref has no version for the bump workflow to track, and breaks "
        "every uv lock once the branch is deleted.\n"
        "Depend on a published release instead."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
