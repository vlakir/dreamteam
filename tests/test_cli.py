"""Tests for the dreamteam CLI."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from dreamteam import __version__
from dreamteam.cli import app

runner = CliRunner()


def test_version_flag_prints_version() -> None:
    """`dreamteam --version` prints the version and exits 0."""
    result = runner.invoke(app, ['--version'])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_init_creates_project(tmp_path: Path) -> None:
    """`dreamteam init <path> --defaults` creates a project with rendered files."""
    target = tmp_path / 'my-project'
    result = runner.invoke(app, ['init', str(target), '--defaults'])
    assert result.exit_code == 0, result.output
    assert target.is_dir()
    assert (target / 'README.md').exists()
    readme = (target / 'README.md').read_text(encoding='utf-8')
    # Jinja-substitution happened: project_name appears in rendered content.
    assert 'my-project' in readme
    # .copier-answers.yml requires VCS-versioned template; addressed in Phase 4.


def test_init_target_appears_in_output(tmp_path: Path) -> None:
    """`dreamteam init` prints the resolved target path."""
    target = tmp_path / 'another-project'
    result = runner.invoke(app, ['init', str(target), '--defaults'])
    assert result.exit_code == 0
    assert str(target) in result.output


def test_update_stub_echoes_message() -> None:
    """`dreamteam update` still echoes a stub message (real impl in Phase 4)."""
    result = runner.invoke(app, ['update'])
    assert result.exit_code == 0
    assert 'Stub' in result.output


def test_help_lists_subcommands() -> None:
    """`dreamteam --help` shows the available subcommands."""
    result = runner.invoke(app, ['--help'])
    assert result.exit_code == 0
    assert 'init' in result.output
    assert 'update' in result.output


def test_no_args_shows_help() -> None:
    """`dreamteam` without args shows help and exits non-zero."""
    result = runner.invoke(app, [])
    assert result.exit_code != 0
    assert 'init' in result.output or 'Commands' in result.output
