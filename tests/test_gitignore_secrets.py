"""
Fast unit tests for the `template/.gitignore` "Secrets / config" section.

The template ships a `.gitignore` to derived projects (`src/dreamteam/
template/.gitignore`). T022 closed a gap: the pattern set used to cover
`.secrets.toml`, `.secrets.env`, `secrets.env`, `.env`, but missed the
plain `.secrets` file (no extension), which is the format produced by
`scripts/publish.sh` for PyPI tokens. That made it possible to commit
secrets by accident on a fresh `dt init` project.

Tests stand up a tiny `git init`-ed tempdir, copy the template
`.gitignore` into it, materialise representative files, and ask
`git check-ignore` whether they are matched. No `dt init` and no real
template render needed — keeps the suite fast.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

TEMPLATE_GITIGNORE = (
    Path(__file__).parent.parent
    / 'src'
    / 'dreamteam'
    / 'template'
    / '.gitignore'
)

_GIT = shutil.which('git')
if _GIT is None:  # pragma: no cover — every supported dev env has git
    pytest.skip('git not available on PATH', allow_module_level=True)


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run `git <args>` in `cwd`, capture output, do not raise on non-zero."""
    assert _GIT is not None
    return subprocess.run(
        [_GIT, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Create a git repo at `tmp_path` with the template .gitignore."""
    assert _git('init', '-q', cwd=tmp_path).returncode == 0
    shutil.copy(TEMPLATE_GITIGNORE, tmp_path / '.gitignore')
    return tmp_path


def _is_ignored(repo: Path, filename: str) -> bool:
    """True iff `filename` (created inside `repo`) is matched by .gitignore."""
    (repo / filename).write_text('dummy', encoding='utf-8')
    result = _git('check-ignore', '--', filename, cwd=repo)
    return result.returncode == 0


def test_plain_dot_secrets_is_ignored(repo: Path) -> None:
    """`.secrets` (plain, no extension) — sourceable shell secrets format."""
    assert _is_ignored(repo, '.secrets'), (
        '`.secrets` plain file must be ignored — this is the format used by '
        'scripts/publish.sh and the gap T022 closes.'
    )


def test_dotted_secrets_variants_still_ignored(repo: Path) -> None:
    """Legacy patterns (`.secrets.toml`, `.secrets.env`) still match."""
    assert _is_ignored(repo, '.secrets.toml')
    assert _is_ignored(repo, '.secrets.env')


def test_dot_secrets_local_ignored(repo: Path) -> None:
    """A common per-environment variant `.secrets.local` is also covered."""
    assert _is_ignored(repo, '.secrets.local')


def test_dot_env_still_ignored(repo: Path) -> None:
    """`.env` is a separate class of file and stays explicitly listed."""
    assert _is_ignored(repo, '.env')


def test_secrets_env_without_leading_dot_ignored(repo: Path) -> None:
    """`secrets.env` (no leading dot) is the sh-export convention."""
    assert _is_ignored(repo, 'secrets.env')


def test_unrelated_file_not_ignored(repo: Path) -> None:
    """Sanity: a non-secret file is NOT touched by the secrets patterns."""
    assert not _is_ignored(repo, 'main.py')
    assert not _is_ignored(repo, 'README.md')
