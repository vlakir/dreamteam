"""
T017 Phase 2: integration matrix for `package_manager` × `language`.

Verifies that every combination of the new `package_manager`
prompt (uv / poetry / pdm / hatch / pip) and the existing
`language` prompt (en / ru / fr / de / zh) renders into a derived
project with:

- correct manager-aware command prefix in CLAUDE.md (`uv run ` for
  uv, `.venv/bin/` for pip, etc.);
- correct build-backend in pyproject.toml;
- the chosen language preserved in `.copier-answers.yml`;
- translation frontmatter (`source_hash`, etc.) stripped from
  derived narrative files (per the post-render task).

Matrix: 5 × 5 = 25 cases. Run as part of the integration suite
because it exercises copier's full template render pipeline
including Jinja conditionals and the post-render `_tasks_post_render.py`
script. Per-case wall time is ~0.4-0.7 s.
"""

from __future__ import annotations

from itertools import product
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dreamteam.cli import EXIT_OK, app

pytestmark = pytest.mark.integration

runner = CliRunner()

MANAGERS = ('uv', 'poetry', 'pdm', 'hatch', 'pip')
LANGUAGES = ('en', 'ru', 'fr', 'de', 'zh')

# Expected manager-aware command prefix in rendered CLAUDE.md
# pre-push chain. Mirrors the `pm_run` mapping in the template.
PM_RUN_PREFIX = {
    'uv': 'uv run ',
    'poetry': 'poetry run ',
    'pdm': 'pdm run ',
    'hatch': 'hatch run ',
    'pip': '.venv/bin/',
}

# Expected build-backend string in rendered pyproject.toml.
# Only poetry has a `[build-system]` block: poetry-core is required
# at runtime by `poetry install`. The other four managers manage a
# venv + dev-deps without building the project itself (which is an
# app, not a library), so no `[build-system]` is rendered — matches
# the pre-T017 template behaviour for uv-mode.
EXPECTED_BUILD_BACKEND = {
    'uv': None,
    'poetry': 'poetry.core.masonry.api',
    'pdm': None,
    'hatch': None,
    'pip': None,
}


@pytest.mark.parametrize(
    ('package_manager', 'language'),
    list(product(MANAGERS, LANGUAGES)),
)
def test_render_matches_manager_and_language(
    tmp_path: Path,
    package_manager: str,
    language: str,
) -> None:
    target = tmp_path / f'proj-{package_manager}-{language}'
    result = runner.invoke(
        app,
        [
            'init',
            str(target),
            '--defaults',
            '--data',
            f'package_manager={package_manager}',
            '--data',
            f'language={language}',
        ],
    )
    assert result.exit_code == EXIT_OK, result.output

    # Manager-aware command prefix appears in CLAUDE.md pre-push chain.
    claude = (target / 'CLAUDE.md').read_text(encoding='utf-8')
    prefix = PM_RUN_PREFIX[package_manager]
    assert f'{prefix}ruff check .' in claude, (
        f'{package_manager}/{language}: expected pre-push command '
        f'{prefix!r}ruff check . missing'
    )
    assert f'{prefix}pytest' in claude

    # Build-backend matches the chosen manager (only poetry renders a
    # `[build-system]` block in this template; the others are app-mode
    # without a build-system).
    pyproject = (target / 'pyproject.toml').read_text(encoding='utf-8')
    backend = EXPECTED_BUILD_BACKEND[package_manager]
    if backend is None:
        assert '[build-system]' not in pyproject, (
            f'{package_manager}: did not expect a [build-system] block'
        )
    else:
        assert backend in pyproject, (
            f'{package_manager}: expected build-backend {backend!r} in pyproject.toml'
        )

    # Poetry-specific section appears only when poetry is chosen.
    if package_manager == 'poetry':
        assert '[tool.poetry]' in pyproject
        assert '[tool.poetry.group.dev.dependencies]' in pyproject
    else:
        assert '[tool.poetry]' not in pyproject

    # Hatch-specific env section appears only when hatch is chosen.
    if package_manager == 'hatch':
        assert '[tool.hatch.envs.default]' in pyproject
        assert '[tool.hatch.envs.default.scripts]' in pyproject
    else:
        assert '[tool.hatch.envs.default]' not in pyproject

    # Language preserved in answers; translation frontmatter stripped
    # from the rendered CLAUDE.md (would start with `---` otherwise).
    answers = (target / '.copier-answers.yml').read_text(encoding='utf-8')
    assert f'language: {language}' in answers
    assert f'package_manager: {package_manager}' in answers
    assert not claude.startswith('---'), (
        f'{package_manager}/{language}: translation frontmatter leaked '
        'into derived CLAUDE.md'
    )


def test_default_package_manager_is_uv(tmp_path: Path) -> None:
    """No `--data package_manager=...` → default `uv` (Q2 resolved)."""
    target = tmp_path / 'proj-default-pm'
    result = runner.invoke(app, ['init', str(target), '--defaults'])
    assert result.exit_code == EXIT_OK, result.output
    answers = (target / '.copier-answers.yml').read_text(encoding='utf-8')
    assert 'package_manager: uv' in answers
    claude = (target / 'CLAUDE.md').read_text(encoding='utf-8')
    assert 'uv run ruff check .' in claude


def test_pip_uses_venv_bin_paths(tmp_path: Path) -> None:
    """pip-mode renders `.venv/bin/<tool>` (CodeRabbit-flagged in #51 spec)."""
    target = tmp_path / 'proj-pip-explicit'
    result = runner.invoke(
        app,
        ['init', str(target), '--defaults', '--data', 'package_manager=pip'],
    )
    assert result.exit_code == EXIT_OK, result.output
    claude = (target / 'CLAUDE.md').read_text(encoding='utf-8')
    # No bare `ruff check` / `pytest` — they would flake without
    # an activated venv in a git pre-push hook context.
    for bare in ('\nruff check', '\npytest', '\nmypy '):
        assert bare not in claude, (
            f'bare {bare.strip()!r} command in pip-mode CLAUDE.md — '
            'should be .venv/bin/-prefixed'
        )
    assert '.venv/bin/ruff check .' in claude
    assert '.venv/bin/pytest' in claude
