"""
T018 Phase 2: integration matrix for `dt apply`.

Covers the cut matrix from spec.md (Q8 resolved → 8 cases):

- 5 managers × empty target (sanity per manager).
- 3 scaffold-states × uv-manager (PyCharm-like, Poetry-like,
  Hatch-like) — verifies conflict resolution flows.

Plus three sanity tests not in the matrix proper:
- `dt apply --dry-run` doesn't write anything.
- `dt apply` on an already-dreamteam project errors with hint to
  use `dt update`.
- The answers file written by `dt apply` is consumable by
  `dt update` (subsequent update with no template change is a
  no-op).

Marked `@pytest.mark.integration`; CliRunner in-process, no
subprocess. Combined wall time ~5-10 s.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dreamteam.cli import EXIT_ERROR, EXIT_OK, app

pytestmark = pytest.mark.integration

runner = CliRunner()

MANAGERS = ('uv', 'poetry', 'pdm', 'hatch', 'pip')

EXPECTED_NARRATIVE = (
    'CLAUDE.md',
    'README.md',
    'CONCEPT.md',
    'BACKLOG.md',
    'BOARD.md',
    'CHANGELOG.md',
    'DECISIONS.md',
)


@pytest.mark.parametrize('package_manager', MANAGERS)
def test_apply_to_empty_target(
    tmp_path: Path, package_manager: str,
) -> None:
    """5 × empty: each manager renders cleanly into a fresh directory."""
    target = tmp_path / f'empty-{package_manager}'
    result = runner.invoke(
        app,
        [
            'apply',
            str(target),
            '--defaults',
            '--data',
            f'package_manager={package_manager}',
            '--data',
            'language=en',
            '--on-conflict',
            'overwrite',  # irrelevant — empty target produces no conflicts
        ],
    )
    assert result.exit_code == EXIT_OK, result.output
    for narrative in EXPECTED_NARRATIVE:
        assert (target / narrative).exists(), f'{narrative} missing for {package_manager}'
    answers = (target / '.copier-answers.yml').read_text(encoding='utf-8')
    assert f'package_manager: {package_manager}' in answers
    assert '_commit' in answers


def test_apply_pycharm_scaffold_keep_pyproject(tmp_path: Path) -> None:
    """
    PyCharm-style scaffold: `pyproject.toml` + `.venv/` present.

    `--on-conflict keep` preserves the user's pyproject.toml; everything
    else (CLAUDE.md, README.md, …) is created. `.venv/` is untouched.
    """
    target = tmp_path / 'efactory'
    target.mkdir()
    user_pyproject = (
        '[project]\nname = "efactory"\nversion = "0.0.1"\ndescription = "from pycharm"\n'
    )
    (target / 'pyproject.toml').write_text(user_pyproject, encoding='utf-8')
    (target / '.venv').mkdir()
    (target / '.venv' / 'marker').write_text('do not touch')

    result = runner.invoke(
        app,
        [
            'apply',
            str(target),
            '--defaults',
            '--data',
            'package_manager=uv',
            '--data',
            'language=en',
            '--on-conflict',
            'keep',
        ],
    )
    assert result.exit_code == EXIT_OK, result.output

    # PyCharm pyproject preserved.
    assert (target / 'pyproject.toml').read_text(encoding='utf-8') == user_pyproject
    # `.venv/` left alone (apply only walks template-managed files).
    assert (target / '.venv' / 'marker').read_text(encoding='utf-8') == 'do not touch'
    # Narrative files created.
    for narrative in EXPECTED_NARRATIVE:
        assert (target / narrative).exists()
    # Summary mentions one kept.
    assert '1 kept' in result.output


def test_apply_poetry_scaffold_save_as_new(tmp_path: Path) -> None:
    """
    Poetry-style scaffold: `pyproject.toml` with `[tool.poetry]`.

    `--on-conflict save-as-new` writes the template version as
    `pyproject.toml.dt-new`; the user's original stays.
    """
    target = tmp_path / 'pyproj'
    target.mkdir()
    user_pyproject = (
        '[tool.poetry]\nname = "pyproj"\nversion = "0.1.0"\n'
        '\n[project]\nname = "pyproj"\n'
    )
    (target / 'pyproject.toml').write_text(user_pyproject, encoding='utf-8')

    result = runner.invoke(
        app,
        [
            'apply',
            str(target),
            '--defaults',
            '--data',
            'package_manager=poetry',
            '--on-conflict',
            'save-as-new',
        ],
    )
    assert result.exit_code == EXIT_OK, result.output

    # Original kept.
    assert (target / 'pyproject.toml').read_text(encoding='utf-8') == user_pyproject
    # Template version saved next to it.
    assert (target / 'pyproject.toml.dt-new').exists()
    new_text = (target / 'pyproject.toml.dt-new').read_text(encoding='utf-8')
    assert 'poetry-core' in new_text
    # Summary mentions one save-as-new.
    assert '1 saved as .dt-new' in result.output


def test_apply_hatch_scaffold_overwrite(tmp_path: Path) -> None:
    """
    Hatch-style scaffold: `pyproject.toml` with `[tool.hatch]`.

    `--on-conflict overwrite` replaces the user's pyproject with the
    template's hatch-flavoured one; the result must have the
    `[tool.hatch.envs.default]` block.
    """
    target = tmp_path / 'hpro'
    target.mkdir()
    user_pyproject = '[tool.hatch]\nversion = {source = "vcs"}\n'
    (target / 'pyproject.toml').write_text(user_pyproject, encoding='utf-8')

    result = runner.invoke(
        app,
        [
            'apply',
            str(target),
            '--defaults',
            '--data',
            'package_manager=hatch',
            '--on-conflict',
            'overwrite',
        ],
    )
    assert result.exit_code == EXIT_OK, result.output

    rendered = (target / 'pyproject.toml').read_text(encoding='utf-8')
    assert '[tool.hatch.envs.default]' in rendered
    assert 'version = {source = "vcs"}' not in rendered  # user version replaced
    assert '1 overwritten' in result.output


def test_apply_dry_run_writes_nothing(tmp_path: Path) -> None:
    """`--dry-run` must leave the target untouched."""
    target = tmp_path / 'dryrun'
    target.mkdir()
    user_pyproject = '[project]\nname = "x"\n'
    (target / 'pyproject.toml').write_text(user_pyproject, encoding='utf-8')

    result = runner.invoke(
        app,
        [
            'apply',
            str(target),
            '--defaults',
            '--dry-run',
            '--on-conflict',
            'overwrite',  # ignored under --dry-run
        ],
    )
    assert result.exit_code == EXIT_OK, result.output
    assert '--dry-run' in result.output
    assert 'would conflict' in result.output

    # No writes whatsoever besides what existed.
    assert (target / 'pyproject.toml').read_text(encoding='utf-8') == user_pyproject
    assert not (target / '.copier-answers.yml').exists()
    assert not (target / 'CLAUDE.md').exists()


def test_apply_already_dreamteam_errors(tmp_path: Path) -> None:
    """`dt apply` refuses a target that has `.copier-answers.yml`."""
    target = tmp_path / 'existing'
    target.mkdir()
    (target / '.copier-answers.yml').write_text(
        '_commit: 1.5.0\nlanguage: en\npackage_manager: uv\n',
        encoding='utf-8',
    )

    result = runner.invoke(
        app,
        ['apply', str(target), '--defaults', '--on-conflict', 'keep'],
    )
    assert result.exit_code == EXIT_ERROR
    combined = result.output + (result.stderr or '')
    assert 'dt update' in combined or '`dt update`' in combined


def test_apply_then_update_works(tmp_path: Path) -> None:
    """
    The answers file written by `apply` must be consumable by
    `update`. Subsequent update with no template change should
    complete cleanly (overwrite fallback if git absent; three-way
    no-op merge otherwise).
    """
    target = tmp_path / 'pipeline'
    apply_result = runner.invoke(
        app,
        [
            'apply',
            str(target),
            '--defaults',
            '--data',
            'package_manager=uv',
            '--on-conflict',
            'overwrite',
        ],
    )
    assert apply_result.exit_code == EXIT_OK, apply_result.output
    answers = (target / '.copier-answers.yml').read_text(encoding='utf-8')
    assert '_commit' in answers
    assert 'package_manager: uv' in answers

    # `dt update` --force bypasses the three-way merge path (no git
    # repo in target), which is fine here — we just check that the
    # answers file is wired correctly and update doesn't choke.
    update_result = runner.invoke(app, ['update', str(target), '--force'])
    assert update_result.exit_code == EXIT_OK, update_result.output


def test_apply_invalid_on_conflict(tmp_path: Path) -> None:
    """Invalid `--on-conflict` value is rejected with EXIT_ERROR."""
    target = tmp_path / 'bad-flag'
    result = runner.invoke(
        app,
        ['apply', str(target), '--defaults', '--on-conflict', 'nuke'],
    )
    assert result.exit_code == EXIT_ERROR
