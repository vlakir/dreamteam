"""
End-to-end integration tests for the dreamteam template.

These tests are slow (run `uv sync` and a full pre-push check suite
inside a temporary project) and require network access. They are
marked `integration` and excluded from the default pytest run; trigger
explicitly via `uv run pytest -m integration`.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dreamteam.cli import app

pytestmark = pytest.mark.integration

runner = CliRunner()


def _have_uv() -> bool:
    return shutil.which('uv') is not None


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a subprocess and return CompletedProcess; raise on non-zero."""
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.mark.skipif(not _have_uv(), reason='uv binary not in PATH')
def test_generated_project_passes_pre_push_checks(tmp_path: Path) -> None:
    """End-to-end: dreamteam init → uv sync → all 4 pre-push checks pass."""
    target = tmp_path / 'e2e-project'
    init_result = runner.invoke(app, ['init', str(target), '--defaults'])
    assert init_result.exit_code == 0, init_result.output
    assert target.is_dir()

    # Install deps in the generated project
    _run(['uv', 'sync'], cwd=target)

    # 4 pre-push checks
    _run(['uv', 'run', 'ruff', 'check', '.'], cwd=target)
    _run(['uv', 'run', 'ruff', 'format', '--check', '.'], cwd=target)
    _run(['uv', 'run', 'mypy', 'src'], cwd=target)
    _run(['uv', 'run', 'pytest'], cwd=target)


@pytest.mark.skipif(not _have_uv(), reason='uv binary not in PATH')
def test_generated_project_main_runs(tmp_path: Path) -> None:
    """End-to-end: generated `uv run python src/main.py` actually runs."""
    target = tmp_path / 'run-project'
    init_result = runner.invoke(app, ['init', str(target), '--defaults'])
    assert init_result.exit_code == 0, init_result.output

    _run(['uv', 'sync'], cwd=target)
    result = _run(['uv', 'run', 'python', 'src/main.py'], cwd=target)
    # main.py logs via stderr by design (CLI-style split). Combine streams.
    combined = result.stdout + result.stderr
    assert 'Hello from my-project!' in combined
