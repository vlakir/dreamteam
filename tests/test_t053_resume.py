"""T053 — `dt resume` session-layout recovery.

Two layers: the pure core in `dreamteam.dt.resume` (staleness from record age,
entry building, table / tmux / JSON rendering — all over hand-built data), and
the `dt resume` CLI wrapper driven through `CliRunner`. Wrapper tests that never
touch worktree resolution use a `DT_HOME` override (no git needed); the one
`claude --continue` degradation test builds a real git repo with a managed
worktree. The store is pre-created in fixtures so the one-time `ensure_store`
stderr line never mixes into `result.output` (click 8.3 merges the streams).
"""

from __future__ import annotations

import datetime
import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dreamteam.cli import app
from dreamteam.dt.model import Task, TaskStatus, save_task
from dreamteam.dt.paths import ensure_store, store_dir, worktrees_dir
from dreamteam.dt.resume import (
    build_entries,
    continue_entry,
    entries_json,
    is_stale,
    render_table,
    render_tmux,
    resume_entry,
)
from dreamteam.dt.sessions import (
    SessionRecord,
    current_timestamp,
    write_session_record,
)

NOW = datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC)
FRESH = '2026-07-30T10:00:00+00:00'  # 2 days before NOW
STALE = '2026-06-01T00:00:00+00:00'  # 61 days before NOW


def _task(task_id: str = 'T001', status: TaskStatus = 'doing', branch: str = 'T001-x') -> Task:
    return Task(id=task_id, title=f'task {task_id}', status=status, branch=branch)


def _rec(session_id: str = 'S1', cwd: str = '/w/T001', last_seen: str = FRESH) -> SessionRecord:
    return SessionRecord(session_id=session_id, cwd=cwd, last_seen=last_seen)


# --------------------------------------------------------------------------- #
# dt.resume — staleness                                                       #
# --------------------------------------------------------------------------- #


def test_is_stale_fresh() -> None:
    assert is_stale(FRESH, NOW) is False


def test_is_stale_old() -> None:
    assert is_stale(STALE, NOW) is True


def test_is_stale_boundary_exactly_retention_is_fresh() -> None:
    seen = (NOW - datetime.timedelta(days=30)).isoformat()
    assert is_stale(seen, NOW) is False


def test_is_stale_one_day_past_retention() -> None:
    seen = (NOW - datetime.timedelta(days=31)).isoformat()
    assert is_stale(seen, NOW) is True


def test_is_stale_unparseable_is_fresh() -> None:
    assert is_stale('not-a-date', NOW) is False


def test_is_stale_naive_is_fresh() -> None:
    # a hand-edited naive timestamp must not raise on aware/naive subtraction
    assert is_stale('2026-06-01T00:00:00', NOW) is False


# --------------------------------------------------------------------------- #
# dt.resume — entry building                                                  #
# --------------------------------------------------------------------------- #


def test_resume_entry_fresh() -> None:
    entry = resume_entry(_task(), _rec(last_seen=FRESH), now=NOW)
    assert entry.mode == 'resume'
    assert entry.session_id == 'S1'
    assert entry.command == 'cd /w/T001 && claude --resume S1'


def test_resume_entry_stale_downgrades() -> None:
    entry = resume_entry(_task(), _rec(last_seen=STALE), now=NOW)
    assert entry.mode == 'stale'
    assert '--resume' not in entry.command
    assert entry.command.startswith('cd /w/T001 && claude')
    assert 'Handover' in entry.command


def test_resume_entry_quotes_path_with_space() -> None:
    entry = resume_entry(_task(), _rec(cwd='/w/T 1', last_seen=FRESH), now=NOW)
    assert "'/w/T 1'" in entry.command


def test_continue_entry() -> None:
    entry = continue_entry(_task(), Path('/w/T001'))
    assert entry.mode == 'continue'
    assert entry.session_id is None
    assert entry.command == 'cd /w/T001 && claude --continue'


def test_build_entries_filters_inactive_and_dangling_and_sorts() -> None:
    records = {
        'T003': _rec('S3', '/w/T003'),
        'T001': _rec('S1', '/w/T001'),
        'T002': _rec('S2', '/w/T002'),
        'T009': _rec('S9', '/w/T009'),  # dangling — no task record
    }
    tasks = {
        'T001': _task('T001', 'doing'),
        'T002': _task('T002', 'done'),  # inactive → filtered
        'T003': _task('T003', 'review'),  # active
    }
    entries = build_entries(records, tasks, now=NOW)
    assert [e.task_id for e in entries] == ['T001', 'T003']


# --------------------------------------------------------------------------- #
# dt.resume — rendering                                                       #
# --------------------------------------------------------------------------- #


def test_render_table_empty() -> None:
    assert render_table([]) == 'нет сессий для восстановления'


def test_render_table_row() -> None:
    entry = resume_entry(_task(), _rec(last_seen=FRESH), now=NOW)
    line = render_table([entry])
    assert line == 'T001  [doing]  T001-x  /w/T001  cd /w/T001 && claude --resume S1'


def test_render_tmux_empty() -> None:
    out = render_tmux([])
    assert out.startswith('#!/bin/sh')
    assert '# нет сессий для восстановления' in out


def test_render_tmux_window_per_task() -> None:
    entry = resume_entry(_task(), _rec(last_seen=FRESH), now=NOW)
    out = render_tmux([entry])
    assert out.startswith('#!/bin/sh')
    assert 'tmux new-window -n T001 -c /w/T001' in out
    assert 'tmux send-keys -t T001' in out


def test_render_tmux_quotes_path_with_space() -> None:
    entry = resume_entry(_task(), _rec(cwd='/w/T 1', last_seen=FRESH), now=NOW)
    out = render_tmux([entry])
    assert "-c '/w/T 1'" in out


def test_entries_json_shape() -> None:
    entry = resume_entry(_task(), _rec(last_seen=FRESH), now=NOW)
    obj = entries_json([entry])
    assert obj == [
        {
            'task_id': 'T001',
            'status': 'doing',
            'branch': 'T001-x',
            'worktree': '/w/T001',
            'session_id': 'S1',
            'mode': 'resume',
            'command': 'cd /w/T001 && claude --resume S1',
        }
    ]


# --------------------------------------------------------------------------- #
# dt resume — CLI wrapper (DT_HOME override, no git)                          #
# --------------------------------------------------------------------------- #


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A pre-created store under a DT_HOME override (no git repository needed)."""
    monkeypatch.setenv('DT_HOME', str(tmp_path / 'home'))
    monkeypatch.delenv('DT_TASK', raising=False)
    ensure_store()  # pre-create so the CLI's ensure_store emits no stderr line
    return store_dir()


def _write_task(
    store: Path, task_id: str, *, status: TaskStatus = 'doing', branch: str | None = None
) -> None:
    save_task(
        store / 'tasks' / f'{task_id}.md',
        Task(id=task_id, title=f'task {task_id}', status=status, branch=branch),
    )


def _write_rec(
    store: Path, task_id: str, *, session_id: str = 'S', cwd: str, last_seen: str
) -> None:
    write_session_record(
        store / 'sessions',
        task_id,
        SessionRecord(session_id=session_id, cwd=cwd, last_seen=last_seen),
    )


def test_cli_bare_table_active_only(store: Path) -> None:
    _write_task(store, 'T001', status='doing', branch='T001-x')
    _write_task(store, 'T002', status='done', branch='T002-y')
    _write_rec(store, 'T001', session_id='S1', cwd='/w/T001', last_seen=current_timestamp())
    _write_rec(store, 'T002', session_id='S2', cwd='/w/T002', last_seen=current_timestamp())
    res = CliRunner().invoke(app, ['resume'])
    assert res.exit_code == 0, res.output
    assert 'claude --resume S1' in res.output
    assert 'T002' not in res.output  # done task hidden


def test_cli_bare_empty(store: Path) -> None:
    res = CliRunner().invoke(app, ['resume'])
    assert res.exit_code == 0, res.output
    assert 'нет сессий' in res.output


def test_cli_stale_row(store: Path) -> None:
    _write_task(store, 'T001', status='doing', branch='T001-x')
    _write_rec(store, 'T001', session_id='S1', cwd='/w/T001', last_seen=STALE)
    res = CliRunner().invoke(app, ['resume'])
    assert res.exit_code == 0, res.output
    assert 'claude --resume' not in res.output
    assert 'Handover' in res.output


def test_cli_address_with_record(store: Path) -> None:
    _write_task(store, 'T001', status='doing', branch='T001-x')
    _write_rec(store, 'T001', session_id='S1', cwd='/w/T001', last_seen=current_timestamp())
    res = CliRunner().invoke(app, ['resume', 'T001'])
    assert res.exit_code == 0, res.output
    assert res.output.strip() == 'cd /w/T001 && claude --resume S1'


def test_cli_address_not_found(store: Path) -> None:
    res = CliRunner().invoke(app, ['resume', 'T404'])
    assert res.exit_code == 1
    assert 'not found' in res.output


def test_cli_address_no_branch(store: Path) -> None:
    _write_task(store, 'T001', status='doing', branch=None)  # never started
    res = CliRunner().invoke(app, ['resume', 'T001'])
    assert res.exit_code == 1
    assert 'dt task start' in res.output


def test_cli_tmux_json_conflict(store: Path) -> None:
    res = CliRunner().invoke(app, ['resume', '--tmux', '--json'])
    assert res.exit_code == 1
    assert 'взаимоисключающ' in res.output


def test_cli_json_output(store: Path) -> None:
    _write_task(store, 'T001', status='doing', branch='T001-x')
    _write_rec(store, 'T001', session_id='S1', cwd='/w/T001', last_seen=current_timestamp())
    res = CliRunner().invoke(app, ['resume', '--json'])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data[0]['task_id'] == 'T001'
    assert data[0]['mode'] == 'resume'


def test_cli_tmux_output(store: Path) -> None:
    _write_task(store, 'T001', status='doing', branch='T001-x')
    _write_rec(store, 'T001', session_id='S1', cwd='/w/T001', last_seen=current_timestamp())
    res = CliRunner().invoke(app, ['resume', '--tmux'])
    assert res.exit_code == 0, res.output
    assert 'tmux new-window -n T001' in res.output


# --------------------------------------------------------------------------- #
# dt resume T034 — `claude --continue` degradation (real git worktree)        #
# --------------------------------------------------------------------------- #


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ['git', *args], cwd=repo, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


@pytest.fixture
def gitrepo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A real git repo (one commit on `main`), CWD, computed sibling DT_HOME."""
    root = tmp_path / 'proj'
    root.mkdir()
    _git(root, 'init', '-b', 'main')
    _git(root, 'config', 'user.email', 'test@example.com')
    _git(root, 'config', 'user.name', 'Test')
    (root / 'README.md').write_text('hello\n', encoding='utf-8')
    _git(root, 'add', '.')
    _git(root, 'commit', '-m', 'init')
    monkeypatch.delenv('DT_HOME', raising=False)
    monkeypatch.delenv('DT_TASK', raising=False)
    monkeypatch.chdir(root)
    ensure_store()  # pre-create (computed sibling .dt) so no CLI stderr line
    return root


def test_cli_address_continue_when_no_record(gitrepo: Path) -> None:
    store = store_dir()
    _write_task(store, 'T001', status='doing', branch='T001-x')
    worktree = worktrees_dir() / 'T001-x'
    _git(gitrepo, 'worktree', 'add', str(worktree), '-b', 'T001-x')
    res = CliRunner().invoke(app, ['resume', 'T001'])
    assert res.exit_code == 0, res.output
    assert res.output.strip().endswith('&& claude --continue')
    assert 'T001-x' in res.output


def test_cli_address_no_live_worktree(gitrepo: Path) -> None:
    # branch recorded but the worktree was never created (or pruned) → nothing to
    # resume, a clear error rather than a `cd` into a non-existent directory.
    _write_task(store_dir(), 'T002', status='doing', branch='T002-y')
    res = CliRunner().invoke(app, ['resume', 'T002'])
    assert res.exit_code == 1
    assert 'no live worktree' in res.output
