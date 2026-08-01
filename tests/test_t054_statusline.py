"""T054 — statusline reader + ``dt task move`` line refresh.

Three layers:

* pure ``dreamteam.dt.starts`` helpers (``write_context_line``,
  ``read_current_task``) in isolation;
* the shipped shell reader ``template/.claude/statusline.sh`` driven as a real
  subprocess against a temporary git repo + store — this proves the shell's
  ``<slug>`` / ``$DT_HOME`` computation is bit-for-bit identical to the Python
  ``worktree_slug`` / ``dt_home`` (it must read the very file Python wrote);
* the Typer ``dt task move`` command's guarded ``context.line`` refresh
  (design §778) against a real git repo.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

import dreamteam
from dreamteam.cli import app
from dreamteam.dt.model import Task, save_task
from dreamteam.dt.paths import (
    by_worktree_dir,
    ensure_store,
    store_dir,
    worktree_slug,
)
from dreamteam.dt.starts import (
    context_line,
    read_current_task,
    write_binding,
    write_context_line,
)
from dreamteam.task_cli import _refresh_line_after_move

_SCRIPT = Path(dreamteam.__file__).parent / 'template' / '.claude' / 'statusline.sh'
_TEMPLATE = Path(dreamteam.__file__).parent / 'template'
_HAS_SHA1 = bool(shutil.which('sha1sum') or shutil.which('shasum'))


# --------------------------------------------------------------------------- #
# pure helpers                                                                 #
# --------------------------------------------------------------------------- #


def test_write_context_line_leaves_current_task_untouched(tmp_path: Path) -> None:
    write_context_line(tmp_path, 'abc123', 'T054 [doing] X')
    directory = tmp_path / 'abc123'
    assert (directory / 'context.line').read_text(encoding='utf-8') == 'T054 [doing] X\n'
    assert not (directory / 'current-task').exists()


def test_read_current_task_roundtrip_and_absence(tmp_path: Path) -> None:
    assert read_current_task(tmp_path, 'nope') is None
    write_binding(tmp_path, 'slug8', 'T054', 'T054 [doing] X')
    assert read_current_task(tmp_path, 'slug8') == 'T054'
    # an empty file reads as unbound, not ''
    (tmp_path / 'slug8' / 'current-task').write_text('  \n', encoding='utf-8')
    assert read_current_task(tmp_path, 'slug8') is None


def test_write_binding_still_writes_both(tmp_path: Path) -> None:
    write_binding(tmp_path, 'slug8', 'T054', 'T054 [todo] X')
    directory = tmp_path / 'slug8'
    assert (directory / 'current-task').read_text(encoding='utf-8') == 'T054\n'
    assert (directory / 'context.line').read_text(encoding='utf-8') == 'T054 [todo] X\n'


# --------------------------------------------------------------------------- #
# template wiring                                                              #
# --------------------------------------------------------------------------- #


def test_settings_json_wires_statusline() -> None:
    data = json.loads((_TEMPLATE / '.claude' / 'settings.json').read_text('utf-8'))
    status = data['statusLine']
    assert status['type'] == 'command'
    assert 'statusline.sh' in status['command']
    # the SessionStart hook (T052) must survive alongside statusLine
    assert data['hooks']['SessionStart']


def test_statusline_script_has_no_jinja_artifacts_and_is_executable() -> None:
    text = _SCRIPT.read_text(encoding='utf-8')
    # `_templates_suffix: ""` renders every file as Jinja — the script must
    # carry no Jinja delimiters that copier would try to evaluate.
    for token in ('{{', '{%', '{#'):
        assert token not in text
    assert os.access(_SCRIPT, os.X_OK)


# --------------------------------------------------------------------------- #
# shell reader — real subprocess against a temp git repo                       #
# --------------------------------------------------------------------------- #


def _git(repo: Path, *args: str) -> None:
    subprocess.run(['git', *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A real git repo (one commit on ``main``), made the process CWD."""
    root = tmp_path / 'proj'
    root.mkdir()
    _git(root, 'init', '-b', 'main')
    _git(root, 'config', 'user.email', 'test@example.com')
    _git(root, 'config', 'user.name', 'Test')
    (root / 'README.md').write_text('hello\n', encoding='utf-8')
    _git(root, 'add', '.')
    _git(root, 'commit', '-m', 'init')
    monkeypatch.delenv('DT_HOME', raising=False)
    monkeypatch.delenv('TMUX', raising=False)
    monkeypatch.chdir(root)
    ensure_store()
    return root


def _run_script(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ['sh', str(_SCRIPT), *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.skipif(not _HAS_SHA1, reason='needs sha1sum or shasum')
def test_script_prints_dir_and_context_line(repo: Path) -> None:
    slug = worktree_slug(repo)
    write_binding(
        by_worktree_dir(), slug, 'T054', context_line(Task(id='T054', title='SL', status='doing'))
    )
    result = _run_script(repo)
    assert result.returncode == 0
    assert result.stdout == 'proj · T054 [doing] SL\n'


@pytest.mark.skipif(not _HAS_SHA1, reason='needs sha1sum or shasum')
def test_script_accepts_toplevel_arg(repo: Path) -> None:
    """The settings.json bootstrap passes the toplevel as $1 — same result."""
    slug = worktree_slug(repo)
    write_context_line(by_worktree_dir(), slug, 'T054 [doing] SL')
    result = _run_script(repo, str(repo))
    assert result.returncode == 0
    assert result.stdout == 'proj · T054 [doing] SL\n'


@pytest.mark.skipif(not _HAS_SHA1, reason='needs sha1sum or shasum')
def test_script_slug_parity_wrong_slug_reads_nothing(repo: Path) -> None:
    """Proof of slug parity: a line filed under any *other* slug is not read."""
    write_context_line(by_worktree_dir(), 'deadbeef', 'T054 [doing] SL')
    result = _run_script(repo)
    assert result.returncode == 0
    assert result.stdout == ''


@pytest.mark.skipif(not _HAS_SHA1, reason='needs sha1sum or shasum')
def test_script_missing_file_is_empty_exit_zero(repo: Path) -> None:
    result = _run_script(repo)
    assert result.returncode == 0
    assert result.stdout == ''


@pytest.mark.skipif(not _HAS_SHA1, reason='needs sha1sum or shasum')
def test_script_empty_file_is_empty_exit_zero(repo: Path) -> None:
    slug = worktree_slug(repo)
    directory = by_worktree_dir() / slug
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'context.line').write_text('\n', encoding='utf-8')
    result = _run_script(repo)
    assert result.returncode == 0
    assert result.stdout == ''


@pytest.mark.skipif(not _HAS_SHA1, reason='needs sha1sum or shasum')
def test_script_emits_single_line_for_multiline_file(repo: Path) -> None:
    """A context.line carrying an embedded newline must not add rows (qodo #2)."""
    slug = worktree_slug(repo)
    directory = by_worktree_dir() / slug
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'context.line').write_text(
        'T054 [doing] first\nSECOND LINE\n', encoding='utf-8'
    )
    result = _run_script(repo)
    assert result.returncode == 0
    assert result.stdout == 'proj · T054 [doing] first\n'


@pytest.mark.skipif(not _HAS_SHA1, reason='needs sha1sum or shasum')
def test_script_outside_git_is_empty_exit_zero(tmp_path: Path) -> None:
    outside = tmp_path / 'nogit'
    outside.mkdir()
    result = subprocess.run(
        ['sh', str(_SCRIPT)], cwd=outside, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0
    assert result.stdout == ''


@pytest.mark.skipif(not _HAS_SHA1, reason='needs sha1sum or shasum')
def test_script_respects_dt_home_override(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug = worktree_slug(repo)
    override = tmp_path / 'elsewhere.dt'
    directory = override / 'store' / 'by-worktree' / slug
    directory.mkdir(parents=True)
    (directory / 'context.line').write_text('T054 [review] SL\n', encoding='utf-8')
    monkeypatch.setenv('DT_HOME', str(override))
    result = _run_script(repo)
    assert result.returncode == 0
    assert result.stdout == 'proj · T054 [review] SL\n'


# --------------------------------------------------------------------------- #
# dt task move — guarded context.line refresh (design §778)                    #
# --------------------------------------------------------------------------- #


def _line_for(repo: Path) -> str | None:
    path = by_worktree_dir() / worktree_slug(repo) / 'context.line'
    return path.read_text(encoding='utf-8') if path.exists() else None


def _new_task(title: str) -> str:
    result = CliRunner().invoke(app, ['task', 'new', title, '--json'])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)['id']


def test_move_refreshes_bound_worktree(repo: Path) -> None:
    task_id = _new_task('Задача')
    slug = worktree_slug(repo)
    # bind this worktree to the task, statusline currently says [todo]
    write_binding(by_worktree_dir(), slug, task_id, f'{task_id} [todo] Задача')
    result = CliRunner().invoke(app, ['task', 'move', task_id, 'doing'])
    assert result.exit_code == 0, result.output
    assert _line_for(repo) == f'{task_id} [doing] Задача\n'
    # the binding itself is untouched — only the status line changed
    assert read_current_task(by_worktree_dir(), slug) == task_id


def test_move_of_unrelated_task_does_not_clobber(repo: Path) -> None:
    bound_id = _new_task('Задача в руках')
    other_id = _new_task('Другая задача')
    slug = worktree_slug(repo)
    kept = f'{bound_id} [doing] Задача в руках'
    write_binding(by_worktree_dir(), slug, bound_id, kept)
    result = CliRunner().invoke(app, ['task', 'move', other_id, 'done'])
    assert result.exit_code == 0, result.output
    # the statusline of the task in hand is preserved
    assert _line_for(repo) == f'{kept}\n'


def test_move_bound_worktree_ignores_shared_branch_match(repo: Path) -> None:
    """An existing binding wins over a shared branch value (qodo #1).

    The worktree is bound to A; B carries the *same* branch as the current
    HEAD (``main``). Moving B must NOT overwrite A's status line — the branch
    test is a fallback only for an *unbound* worktree.
    """
    bound_id = _new_task('Задача A')
    slug = worktree_slug(repo)
    kept = f'{bound_id} [doing] Задача A'
    write_binding(by_worktree_dir(), slug, bound_id, kept)
    other_id = 'T099'
    save_task(
        store_dir() / 'tasks' / f'{other_id}.md',
        Task(id=other_id, title='Задача B', status='todo', branch='main'),
    )
    result = CliRunner().invoke(app, ['task', 'move', other_id, 'doing'])
    assert result.exit_code == 0, result.output
    assert _line_for(repo) == f'{kept}\n'


def test_move_refreshes_on_task_branch_without_binding(repo: Path) -> None:
    """HEAD on the task's branch counts even with no ``current-task`` file."""
    task_id = 'T099'
    save_task(
        store_dir() / 'tasks' / f'{task_id}.md',
        Task(id=task_id, title='На ветке', status='todo', branch='main'),
    )
    # no binding written; the repo sits on `main` == task.branch
    result = CliRunner().invoke(app, ['task', 'move', task_id, 'doing'])
    assert result.exit_code == 0, result.output
    assert _line_for(repo) == f'{task_id} [doing] На ветке\n'


def test_move_outside_git_with_override_is_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With DT_HOME set but no git around, move still succeeds; refresh no-ops."""
    override = tmp_path / 'store.dt'
    outside = tmp_path / 'plain'
    outside.mkdir()
    monkeypatch.setenv('DT_HOME', str(override))
    monkeypatch.chdir(outside)
    # pre-create the store so the one-shot "created …" stderr line does not
    # merge into the CliRunner output and trip json.loads (click 8.3 quirk).
    ensure_store()
    task_id = _new_task('Без git')
    result = CliRunner().invoke(app, ['task', 'move', task_id, 'doing'])
    assert result.exit_code == 0, result.output
    assert json.loads(
        CliRunner().invoke(app, ['task', 'show', task_id, '--json']).output
    )['status'] == 'doing'


def test_refresh_helper_noop_when_cwd_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Direct unit test of the outside-git branch (git_context → (None, None))."""
    monkeypatch.setattr('dreamteam.task_cli.git_context', lambda: (None, None))
    # must not raise, must not touch the filesystem
    _refresh_line_after_move(Task(id='T054', title='X', status='doing'))
