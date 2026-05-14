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


def test_init_stub_echoes_path(tmp_path: Path) -> None:
    """`dreamteam init <path>` echoes a stub message including the path."""
    target = tmp_path / 'my-project'
    result = runner.invoke(app, ['init', str(target)])
    assert result.exit_code == 0
    assert 'Stub' in result.output
    assert str(target) in result.output


def test_update_stub_echoes_message() -> None:
    """`dreamteam update` echoes a stub message about copier update."""
    result = runner.invoke(app, ['update'])
    assert result.exit_code == 0
    assert 'Stub' in result.output
    assert 'copier update' in result.output


def test_help_lists_subcommands() -> None:
    """`dreamteam --help` shows the available subcommands."""
    result = runner.invoke(app, ['--help'])
    assert result.exit_code == 0
    assert 'init' in result.output
    assert 'update' in result.output


def test_no_args_shows_help() -> None:
    """`dreamteam` without args shows help and exits non-zero."""
    result = runner.invoke(app, [])
    # no_args_is_help=True → Typer exits with code 2 by default
    assert result.exit_code != 0
    assert 'init' in result.output or 'Commands' in result.output
