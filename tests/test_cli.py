"""Tests for the dreamteam CLI."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dreamteam import __version__
from dreamteam.cli import (
    EXIT_CONFLICTS,
    EXIT_ERROR,
    EXIT_OK,
    LEGACY_COMMIT_PREFIX,
    _has_git,
    _resolve_base_version_tag,
    app,
)

runner = CliRunner()


def _git_init(target: Path) -> None:
    """Initialize a derived project as a git repo with one commit."""
    git = shutil.which('git')
    assert git is not None, 'git required for tests'
    subprocess.run([git, 'init', '--initial-branch=main', '--quiet'], cwd=target, check=True)
    subprocess.run([git, 'add', '-A'], cwd=target, check=True)
    subprocess.run(
        [git, '-c', 'user.email=t@t', '-c', 'user.name=t', 'commit', '-q', '-m', 'initial'],
        cwd=target,
        check=True,
    )


def test_version_flag_prints_version() -> None:
    """`dreamteam --version` prints the version and exits 0."""
    result = runner.invoke(app, ['--version'])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_init_creates_project(tmp_path: Path) -> None:
    """`dreamteam init <path> --defaults` creates a full project skeleton."""
    target = tmp_path / 'my-project'
    result = runner.invoke(app, ['init', str(target), '--defaults'])
    assert result.exit_code == 0, result.output
    assert target.is_dir()
    expected_files = [
        'README.md',
        'CLAUDE.md',
        'CONCEPT.md',
        'DECISIONS.md',
        'CHANGELOG.md',
        'BACKLOG.md',
        'BOARD.md',
        'pyproject.toml',
        'hooks/pre-push',
        'specs/spec-template.md',
        'src/main.py',
        'tests/test_main.py',
    ]
    for relative in expected_files:
        assert (target / relative).exists(), f'missing {relative}'
    # `.bundle/` is internal machinery — must never be copied into derived.
    assert not (target / '.bundle').exists(), '.bundle leaked into derived'
    readme = (target / 'README.md').read_text(encoding='utf-8')
    assert 'my-project' in readme
    pyproject = (target / 'pyproject.toml').read_text(encoding='utf-8')
    assert 'name = "my-project"' in pyproject
    main_py = (target / 'src' / 'main.py').read_text(encoding='utf-8')
    assert 'Hello from my-project!' in main_py


def test_init_target_appears_in_output(tmp_path: Path) -> None:
    """`dreamteam init` prints the resolved target path."""
    target = tmp_path / 'another-project'
    result = runner.invoke(app, ['init', str(target), '--defaults'])
    assert result.exit_code == 0
    assert str(target) in result.output


def test_update_after_init_clean(tmp_path: Path) -> None:
    """
    `dreamteam update` on a git-tracked derived project with no edits
    performs a clean three-way merge against the bundled v<version>
    snapshot and exits 0.
    """
    target = tmp_path / 'updatable'
    init_result = runner.invoke(app, ['init', str(target), '--defaults'])
    assert init_result.exit_code == 0, init_result.output
    assert (target / '.copier-answers.yml').exists()
    _git_init(target)
    update_result = runner.invoke(app, ['update', str(target)])
    assert update_result.exit_code == EXIT_OK, update_result.output
    assert 'three-way merge' in update_result.output.lower()


def test_update_force_uses_overwrite(tmp_path: Path) -> None:
    """`dreamteam update --force` bypasses three-way merge (MVP overwrite)."""
    target = tmp_path / 'forced'
    init_result = runner.invoke(app, ['init', str(target), '--defaults'])
    assert init_result.exit_code == 0, init_result.output
    # No git init needed: --force skips the merge path entirely.
    update_result = runner.invoke(app, ['update', str(target), '--force'])
    assert update_result.exit_code == EXIT_OK, update_result.output
    assert 'overwrite' in update_result.output.lower()


def test_update_without_git_repo_fails(tmp_path: Path) -> None:
    """
    Without `git init` on derived (and without --force), update fails
    with a clear error pointing the user to init the repo.
    """
    target = tmp_path / 'no-git'
    init_result = runner.invoke(app, ['init', str(target), '--defaults'])
    assert init_result.exit_code == 0, init_result.output
    update_result = runner.invoke(app, ['update', str(target)])
    assert update_result.exit_code == EXIT_ERROR
    assert 'not a git repository' in (update_result.output + update_result.stderr)


def test_update_without_answers_file_fails(tmp_path: Path) -> None:
    """`dreamteam update` errors if no `.copier-answers.yml` is present."""
    target = tmp_path / 'no-answers'
    target.mkdir()
    result = runner.invoke(app, ['update', str(target)])
    assert result.exit_code == EXIT_ERROR
    assert 'No .copier-answers.yml' in (result.output + result.stderr)


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


def test_resolve_base_version_tag_current() -> None:
    """Current format `_commit: 1.3.0` is returned as-is."""
    assert _resolve_base_version_tag({'_commit': '1.3.0'}) == '1.3.0'
    assert _resolve_base_version_tag({'_commit': '2.0.0rc1'}) == '2.0.0rc1'


def test_resolve_base_version_tag_legacy() -> None:
    """Legacy `dreamteam-1.2.0` is stripped of the prefix."""
    legacy = f'{LEGACY_COMMIT_PREFIX}1.2.0'
    assert _resolve_base_version_tag({'_commit': legacy}) == '1.2.0'


def test_resolve_base_version_tag_missing() -> None:
    """Missing `_commit` or malformed values return None."""
    assert _resolve_base_version_tag({}) is None
    assert _resolve_base_version_tag({'_commit': None}) is None
    assert _resolve_base_version_tag({'_commit': ''}) is None
    assert _resolve_base_version_tag({'_commit': '-broken'}) is None
    assert _resolve_base_version_tag({'_commit': LEGACY_COMMIT_PREFIX}) is None


def test_has_git_runtime() -> None:
    """`_has_git()` returns True when git is on PATH (precondition of the test suite)."""
    assert _has_git() is True


def test_exit_code_constants() -> None:
    """Public exit codes match the spec: 0 clean / 1 error / 2 conflicts."""
    assert (EXIT_OK, EXIT_ERROR, EXIT_CONFLICTS) == (0, 1, 2)


def test_data_invalid_format_rejected(tmp_path: Path) -> None:
    """`dreamteam init --data foo` (no `=`) is a usage error."""
    target = tmp_path / 'bad-data'
    result = runner.invoke(app, ['init', str(target), '--defaults', '--data', 'novalue'])
    assert result.exit_code != 0


def test_no_unused_pytest_import() -> None:
    """Smoke: pytest module is the test framework, not unused."""
    assert pytest.__version__


def test_update_preserves_user_edit(tmp_path: Path) -> None:
    """
    Scenario B (light): user adds a bullet to BACKLOG.md, then runs
    `dreamteam update`. Template version is unchanged, so the merge
    is effectively no-op for template-side; the user edit must be
    preserved.
    """
    target = tmp_path / 'edit-keep'
    init_result = runner.invoke(app, ['init', str(target), '--defaults'])
    assert init_result.exit_code == 0, init_result.output

    backlog = target / 'BACKLOG.md'
    user_marker = '- T999: my custom note that must survive update'
    backlog.write_text(
        backlog.read_text(encoding='utf-8') + '\n' + user_marker + '\n',
        encoding='utf-8',
    )

    _git_init(target)

    update_result = runner.invoke(app, ['update', str(target)])
    assert update_result.exit_code == EXIT_OK, update_result.output
    assert user_marker in backlog.read_text(encoding='utf-8')


def test_update_language_preserved(tmp_path: Path) -> None:
    """
    Scenario D: init derived with language=ru → update → answers
    still record language=ru, narrative still in Russian.
    """
    target = tmp_path / 'ru-stable'
    init_result = runner.invoke(
        app, ['init', str(target), '--defaults', '--data', 'language=ru'],
    )
    assert init_result.exit_code == 0, init_result.output
    _git_init(target)

    update_result = runner.invoke(app, ['update', str(target)])
    assert update_result.exit_code == EXIT_OK, update_result.output

    answers = (target / '.copier-answers.yml').read_text(encoding='utf-8')
    assert 'language: ru' in answers
    # Marker from i18n/ru/CLAUDE.md body — must remain after update.
    claude_text = (target / 'CLAUDE.md').read_text(encoding='utf-8')
    assert 'проектные правила для Claude' in claude_text


def test_update_legacy_commit_falls_back_to_overwrite(tmp_path: Path) -> None:
    """
    Scenario for pre-1.3.0 derived projects: their `_commit` carries
    the legacy `dreamteam-<X.Y.Z>` prefix and the bundle has no such
    tag → fallback to overwrite update with a WARNING.
    """
    target = tmp_path / 'legacy'
    init_result = runner.invoke(app, ['init', str(target), '--defaults'])
    assert init_result.exit_code == 0, init_result.output
    answers_file = target / '.copier-answers.yml'
    text = answers_file.read_text(encoding='utf-8')
    # Rewrite `_commit` to a legacy version not in the bundle.
    text = text.replace(f'_commit: {__version__}', f'_commit: {LEGACY_COMMIT_PREFIX}1.0.0')
    answers_file.write_text(text, encoding='utf-8')
    _git_init(target)

    update_result = runner.invoke(app, ['update', str(target)])
    assert update_result.exit_code == EXIT_OK, update_result.output
    output = update_result.output + update_result.stderr
    assert 'overwrite' in output.lower()
    assert '1.0.0' in output
