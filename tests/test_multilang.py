"""Multilang T013 tests: render correctness for all 5 languages + e2e."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dreamteam.cli import app

runner = CliRunner()

LANGUAGES = ('en', 'ru', 'fr', 'de', 'zh')

EXPECTED_NARRATIVE = (
    'CLAUDE.md',
    'README.md',
    'CONCEPT.md',
    'BACKLOG.md',
    'BOARD.md',
    'CHANGELOG.md',
    'DECISIONS.md',
    'specs/spec-template.md',
)

# A short distinctive marker per language: it must appear in the rendered
# CLAUDE.md only when that language is selected. ru source carries the
# legacy English heading "# Project rules for Claude" with a Russian body
# — the marker below targets the body, not the heading.
LANGUAGE_MARKERS = {
    'en': 'project-specific rules for Claude',
    'ru': 'проектные правила для Claude',
    'fr': 'règles projet pour Claude',
    'de': 'projektspezifischen Regeln',
    'zh': '项目规则',
}


@pytest.mark.parametrize('language', LANGUAGES)
def test_init_renders_each_language(tmp_path: Path, language: str) -> None:
    """`dreamteam init --data language=<lang>` produces narrative in that language."""
    target = tmp_path / f'proj-{language}'
    result = runner.invoke(
        app,
        ['init', str(target), '--defaults', '--data', f'language={language}'],
    )
    assert result.exit_code == 0, result.output

    for relative in EXPECTED_NARRATIVE:
        assert (target / relative).exists(), f'{language}: missing {relative}'

    # i18n/ removed, post-render task removed.
    assert not (target / 'i18n').exists(), f'{language}: i18n/ still present'
    assert not (target / '_tasks_post_render.py').exists(), (
        f'{language}: _tasks_post_render.py not cleaned up'
    )

    # Frontmatter must NOT bleed into derived files.
    claude_text = (target / 'CLAUDE.md').read_text(encoding='utf-8')
    assert not claude_text.startswith('---'), (
        f'{language}: translation frontmatter leaked into derived CLAUDE.md'
    )

    # Language-specific content marker.
    marker = LANGUAGE_MARKERS[language]
    assert marker.lower() in claude_text.lower(), (
        f'{language}: marker {marker!r} not found in rendered CLAUDE.md'
    )

    # Answers file captures the chosen language.
    answers = (target / '.copier-answers.yml').read_text(encoding='utf-8')
    assert f'language: {language}' in answers


def test_default_language_is_en(tmp_path: Path) -> None:
    """No `--data language=...` → default `en` (UX expectation)."""
    target = tmp_path / 'proj-default'
    result = runner.invoke(app, ['init', str(target), '--defaults'])
    assert result.exit_code == 0, result.output
    answers = (target / '.copier-answers.yml').read_text(encoding='utf-8')
    assert 'language: en' in answers
    claude_text = (target / 'CLAUDE.md').read_text(encoding='utf-8')
    assert LANGUAGE_MARKERS['en'].lower() in claude_text.lower()


def test_data_parsing_rejects_bad_input(tmp_path: Path) -> None:
    """`--data key` without `=value` is rejected as a usage error."""
    target = tmp_path / 'proj-bad'
    result = runner.invoke(
        app, ['init', str(target), '--defaults', '--data', 'broken'],
    )
    assert result.exit_code != 0


@pytest.mark.integration
@pytest.mark.parametrize('language', LANGUAGES)
def test_derived_project_passes_pre_push_checks(
    tmp_path: Path, language: str,
) -> None:
    """For each language, the generated project passes ruff/format/mypy/pytest.

    Slow: each variant runs `uv sync` plus the 4 pre-push checks in the
    derived project. Run via `uv run pytest -m integration`.
    """
    uv = shutil.which('uv')
    if uv is None:
        pytest.skip('uv binary not on PATH')

    target = tmp_path / f'proj-{language}'
    result = runner.invoke(
        app,
        ['init', str(target), '--defaults', '--data', f'language={language}'],
    )
    assert result.exit_code == 0, result.output

    # Isolate from any outer venv so uv picks up the project's own .venv.
    env = {k: v for k, v in os.environ.items() if k != 'VIRTUAL_ENV'}

    sync = subprocess.run(
        [uv, 'sync'], cwd=target, capture_output=True, text=True,
        env=env, check=False,
    )
    assert sync.returncode == 0, sync.stdout + sync.stderr

    for cmd in (
        (uv, 'run', 'ruff', 'check', '.'),
        (uv, 'run', 'ruff', 'format', '--check', '.'),
        (uv, 'run', 'mypy', 'src'),
        (uv, 'run', 'pytest'),
    ):
        proc = subprocess.run(
            list(cmd), cwd=target, capture_output=True, text=True,
            env=env, check=False,
        )
        assert proc.returncode == 0, (
            f'{language}: {" ".join(cmd)} failed\n'
            f'stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}'
        )
