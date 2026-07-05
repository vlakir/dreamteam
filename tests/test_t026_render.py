"""
T026 Phase 8 — init acceptance for the Architect subagent render (§8.8).

Fast tests (plain `dreamteam init`, no `uv sync`): on every language the
rendered `.claude/agents/architect.md` has exactly one (functional)
frontmatter, the right constants, `model == architect_model`, a body in
the methodology language with no translation-frontmatter remnants, and
the `partials/` render machinery does not leak into the derived project.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml
from typer.testing import CliRunner

from dreamteam.cli import app

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()

LANGUAGES = ('en', 'ru', 'fr', 'de', 'zh')
# First word of the translated body per language — proves the body is on
# the methodology language, not a fallback.
BODY_OPENER = {
    'en': 'You',
    'ru': 'Ты',
    'fr': 'Tu',
    'de': 'Du',
    'zh': '你',
}


def _init(target: Path, *extra: str) -> None:
    result = runner.invoke(app, ['init', str(target), '--defaults', *extra])
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize('language', LANGUAGES)
def test_architect_render_per_language(tmp_path: Path, language: str) -> None:
    """One valid frontmatter, right constants, body on the methodology language."""
    target = tmp_path / f'proj-{language}'
    _init(target, '--data', f'language={language}')

    architect = target / '.claude' / 'agents' / 'architect.md'
    assert architect.is_file(), 'architect subagent not rendered'
    text = architect.read_text(encoding='utf-8')

    # Exactly one frontmatter block: starts with `---` and has a single
    # closing `\n---\n` delimiter.
    assert text.startswith('---\n')
    assert text.count('\n---\n') == 1, 'expected exactly one frontmatter block'

    _lead, frontmatter, body = text.split('---\n', 2)
    parsed = yaml.safe_load(frontmatter)
    assert parsed['name'] == 'architect'
    assert parsed['tools'] == 'Read, Glob, Grep'
    assert parsed['model'] == 'inherit'  # the architect_model default
    assert isinstance(parsed['description'], str) and parsed['description'].strip()

    # Body on the methodology language, with no translation-frontmatter
    # keys or leftover description comment leaking through.
    assert body.lstrip().startswith(BODY_OPENER[language])
    assert 'source_hash' not in body
    assert 'translated_from' not in body
    assert '<!-- description:' not in body


def test_architect_model_override(tmp_path: Path) -> None:
    """`--data architect_model=opus` reaches the rendered subagent header."""
    target = tmp_path / 'proj-opus'
    _init(target, '--data', 'language=en', '--data', 'architect_model=opus')
    text = (target / '.claude' / 'agents' / 'architect.md').read_text(encoding='utf-8')
    _lead, frontmatter, _body = text.split('---\n', 2)
    assert yaml.safe_load(frontmatter)['model'] == 'opus'


def test_render_machinery_does_not_leak(tmp_path: Path) -> None:
    """`partials/` / `extensions/` are excluded; no body partial materializes."""
    target = tmp_path / 'proj-leak'
    _init(target, '--data', 'language=en')
    assert not (target / 'partials').exists()
    assert not (target / 'extensions').exists()
    assert list(target.rglob('architect.body.*.md')) == []
