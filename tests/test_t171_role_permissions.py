"""T171 native question permission, without a runtime, provider or server."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from dreamteam.cli import app

ROLE_NAMES = {
    'tech-lead',
    'architect',
    'designer',
    'frontend',
    'mobile',
    'backend',
    'tester',
    'reviewer',
    'devops',
}
REPOSITORY = Path(__file__).resolve().parents[1]


def _assert_role_permissions(root: Path) -> None:
    """Only the primary lead explicitly enables the native question tool."""
    agents = {path.stem: path for path in (root / '.opencode/agents').glob('*.md')}
    assert set(agents) == ROLE_NAMES
    for name, path in agents.items():
        text = path.read_text(encoding='utf-8')
        assert text.startswith('---\n')
        assert text.count('\n---\n') == 1
        _opening, header, body = text.split('---\n', 2)
        role = yaml.safe_load(header)
        assert isinstance(role, dict)
        assert isinstance(role['description'], str)
        assert role['description'].strip()
        assert body.strip()
        assert 'model' not in role
        assert 'provider' not in role
        if name == 'tech-lead':
            assert role['mode'] == 'primary'
            assert role['permission'] == {'question': 'allow'}
        else:
            assert role['mode'] == 'subagent'
            assert role.get('permission', {}).get('question') != 'allow'


@pytest.mark.parametrize('language', ['en', 'ru', 'fr', 'de', 'zh'])
def test_repository_and_fresh_roles_enable_only_lead_questions(
    tmp_path: Path, language: str
) -> None:
    """Fresh Copier init in each language agrees with the library's own role."""
    target = tmp_path / language
    result = CliRunner().invoke(
        app,
        ['init', str(target), '--defaults', '--data', f'language={language}'],
    )
    assert result.exit_code == 0, result.output
    _assert_role_permissions(target)
    _assert_role_permissions(REPOSITORY)
