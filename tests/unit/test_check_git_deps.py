"""Tests for the CI guard that rejects git dependencies in pyproject.toml.

A git-ref dependency has no version for the Bump Runtime Dependencies workflow
to bump, so it silently defeats that workflow -- and it hard-fails every
`uv lock` once the referenced branch is deleted. See PR #103.
"""

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_checker():
    """Load scripts/check_git_deps.py, which is not on the package path."""
    path = REPO_ROOT / "scripts" / "check_git_deps.py"
    spec = importlib.util.spec_from_file_location("check_git_deps", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_git_deps = _load_checker()


class TestFindGitDependencies:
    def test_flags_direct_url_git_dependency(self):
        pyproject = """
[project]
name = "worker-flash"
dependencies = [
    "requests>=2.25.0",
    "runpod-flash @ git+https://github.com/runpod/flash.git@some-branch",
]
"""

        offenders = check_git_deps.find_git_dependencies(pyproject)

        assert offenders == [
            "project.dependencies: runpod-flash @ git+https://github.com/runpod/flash.git@some-branch"
        ]

    def test_accepts_released_version_constraints(self):
        pyproject = """
[project]
name = "worker-flash"
dependencies = [
    "requests>=2.25.0",
    "runpod-flash>=1.19.0",
]
"""

        assert check_git_deps.find_git_dependencies(pyproject) == []

    def test_flags_git_dependency_in_dependency_group(self):
        pyproject = """
[project]
name = "worker-flash"
dependencies = []

[dependency-groups]
dev = [
    "pytest>=8.3.5",
    "some-tool @ git+https://github.com/example/tool.git",
]
"""

        offenders = check_git_deps.find_git_dependencies(pyproject)

        assert offenders == [
            "dependency-groups.dev: some-tool @ git+https://github.com/example/tool.git"
        ]

    def test_flags_optional_dependency_git_ref(self):
        pyproject = """
[project]
name = "worker-flash"
dependencies = []

[project.optional-dependencies]
extra = ["thing @ git+ssh://git@github.com/example/thing.git"]
"""

        offenders = check_git_deps.find_git_dependencies(pyproject)

        assert offenders == [
            "project.optional-dependencies.extra: thing @ git+ssh://git@github.com/example/thing.git"
        ]

    def test_flags_tool_uv_sources_git_entry(self):
        pyproject = """
[project]
name = "worker-flash"
dependencies = ["runpod"]

[tool.uv.sources]
runpod = { git = "https://github.com/runpod/runpod-python", rev = "main" }
"""

        offenders = check_git_deps.find_git_dependencies(pyproject)

        assert offenders == [
            "tool.uv.sources.runpod: git = https://github.com/runpod/runpod-python"
        ]

    def test_reports_every_offender(self):
        pyproject = """
[project]
name = "worker-flash"
dependencies = [
    "a @ git+https://github.com/example/a.git",
    "b @ git+https://github.com/example/b.git",
]
"""

        assert len(check_git_deps.find_git_dependencies(pyproject)) == 2


class TestMain:
    def test_exits_nonzero_and_names_offender_when_git_dep_present(self, tmp_path, capsys):
        target = tmp_path / "pyproject.toml"
        target.write_text(
            '[project]\nname = "x"\ndependencies = ["p @ git+https://github.com/e/p.git"]\n'
        )

        exit_code = check_git_deps.main([str(target)])

        assert exit_code == 1
        assert "git+https://github.com/e/p.git" in capsys.readouterr().out

    def test_exits_zero_for_clean_file(self, tmp_path):
        target = tmp_path / "pyproject.toml"
        target.write_text('[project]\nname = "x"\ndependencies = ["requests>=2.25.0"]\n')

        assert check_git_deps.main([str(target)]) == 0

    def test_exits_nonzero_when_file_missing(self, tmp_path):
        assert check_git_deps.main([str(tmp_path / "nope.toml")]) == 1


class TestThisRepository:
    """The guard must pass against the real pyproject.toml it protects."""

    def test_repo_pyproject_has_no_git_dependencies(self):
        pyproject = (REPO_ROOT / "pyproject.toml").read_text()

        assert check_git_deps.find_git_dependencies(pyproject) == []


if __name__ == "__main__":
    pytest.main([__file__])
