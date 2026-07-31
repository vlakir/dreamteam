"""T040 — BACKLOG.md sync (`dt backlog sync`).

Two layers: the pure, git-free projection in `dreamteam.dt.backlog`
(`backlog_items` / `render_item` / `sync_backlog` / `parse_block_ids` /
`backlog_divergence` against an explicit temp store) and the Typer wrapper in
`dreamteam.backlog_cli`, driven against a *real* temporary git repository so the
main-branch guard and the repo-root write path are exercised end to end.
"""

from __future__ import annotations

import datetime
import json
import subprocess
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from dreamteam.cli import app
from dreamteam.dt.backlog import (
    BEGIN_MARKER,
    END_MARKER,
    backlog_divergence,
    backlog_items,
    parse_block_ids,
    render_block,
    render_item,
    sync_backlog,
)
from dreamteam.dt.model import Task, TaskStatus, save_task
from dreamteam.dt.paths import ensure_store, store_dir

if TYPE_CHECKING:
    from pathlib import Path


def _write(
    store: Path,
    task_id: str,
    *,
    status: TaskStatus = 'todo',
    title: str | None = None,
    deps: list[str] | None = None,
    spec: str | None = None,
    created: datetime.date | None = None,
) -> None:
    task = Task(
        id=task_id,
        title=title or f'task {task_id}',
        status=status,
        deps=deps or [],
        spec=spec,
        created=created,
    )
    save_task(store / 'tasks' / f'{task_id}.md', task)


@pytest.fixture
def store(tmp_path: Path) -> Path:
    root = tmp_path / 'store'
    (root / 'tasks').mkdir(parents=True)
    return root


# --------------------------------------------------------------------------- #
# backlog_items — projection                                                   #
# --------------------------------------------------------------------------- #


def test_backlog_items_keeps_unfinished_only(store: Path) -> None:
    _write(store, 'T001', status='todo')
    _write(store, 'T002', status='doing')
    _write(store, 'T003', status='review')
    _write(store, 'T004', status='done')
    _write(store, 'T005', status='dropped')
    assert [t.id for t in backlog_items(store)] == ['T001', 'T002', 'T003']


def test_backlog_items_sorts_numeric_not_lexical(store: Path) -> None:
    _write(store, 'T200', status='todo')
    _write(store, 'T1000', status='todo')
    _write(store, 'T099', status='todo')
    # numeric order: 99 < 200 < 1000 (lexical would wrongly place T1000 first).
    assert [t.id for t in backlog_items(store)] == ['T099', 'T200', 'T1000']


def test_backlog_items_empty(store: Path) -> None:
    assert backlog_items(store) == []


# --------------------------------------------------------------------------- #
# render_item / render_block                                                   #
# --------------------------------------------------------------------------- #


def test_render_item_full() -> None:
    task = Task(
        id='T040',
        title='Синхронизация BACKLOG.md',
        deps=['T034'],
        spec='specs/T040-backlog-sync/spec.md',
        created=datetime.date(2026, 7, 30),
    )
    assert render_item(task) == (
        '- **T040** — [2026-07-30] Синхронизация BACKLOG.md '
        '(deps: T034; spec: specs/T040-backlog-sync/spec.md)'
    )


def test_render_item_minimal_no_date_no_meta() -> None:
    task = Task(id='T041', title='Перенос состояния')
    assert render_item(task) == '- **T041** — Перенос состояния'


def test_render_item_deps_only() -> None:
    task = Task(id='T042', title='Миграция', deps=['T034', 'T040'])
    assert render_item(task) == '- **T042** — Миграция (deps: T034, T040)'


def test_render_block_empty_is_just_markers() -> None:
    assert render_block([]) == f'{BEGIN_MARKER}\n{END_MARKER}'


def test_render_block_lists_items(store: Path) -> None:
    _write(store, 'T001', status='todo', title='один')
    _write(store, 'T002', status='doing', title='два')
    block = render_block(backlog_items(store))
    assert block.startswith(BEGIN_MARKER + '\n')
    assert block.endswith('\n' + END_MARKER)
    assert '- **T001** — один' in block
    assert '- **T002** — два' in block


# --------------------------------------------------------------------------- #
# sync_backlog — managed block insertion / replacement                         #
# --------------------------------------------------------------------------- #


def test_sync_appends_block_when_absent() -> None:
    existing = '# Backlog\n\nintro prose\n'
    task = Task(id='T001', title='первая')
    result = sync_backlog(existing, [task])
    assert result.startswith('# Backlog\n\nintro prose\n\n')
    assert BEGIN_MARKER in result
    assert '- **T001** — первая' in result
    assert result.endswith(END_MARKER + '\n')


def test_sync_empty_file_yields_block_only() -> None:
    result = sync_backlog('', [])
    assert result == f'{BEGIN_MARKER}\n{END_MARKER}\n'


def test_sync_replaces_only_managed_block() -> None:
    existing = (
        f'# Backlog\n\nkeep me\n\n{BEGIN_MARKER}\n'
        '- **T001** — старая\n'
        f'{END_MARKER}\n\ntrailing prose\n'
    )
    result = sync_backlog(existing, [Task(id='T002', title='новая')])
    assert 'keep me' in result
    assert 'trailing prose' in result
    assert '- **T001** — старая' not in result
    assert '- **T002** — новая' in result


def test_sync_is_idempotent() -> None:
    existing = '# Backlog\n\nprose\n'
    tasks = [Task(id='T001', title='a'), Task(id='T002', title='b')]
    once = sync_backlog(existing, tasks)
    twice = sync_backlog(once, tasks)
    assert once == twice


def test_sync_title_with_backslash_is_literal() -> None:
    # A regex *string* replacement would interpret `\g`/backslashes; the function
    # replacement must keep the title verbatim.
    task = Task(id='T001', title=r'path\to \1 thing')
    result = sync_backlog(f'{BEGIN_MARKER}\n{END_MARKER}\n', [task])
    assert r'- **T001** — path\to \1 thing' in result


def test_sync_status_change_does_not_change_file() -> None:
    # todo → doing → review must leave the file byte-identical (status-independent).
    todo = [Task(id='T001', title='x', status='todo')]
    doing = [Task(id='T001', title='x', status='doing')]
    base = sync_backlog('# Backlog\n', todo)
    assert sync_backlog(base, doing) == base


# --------------------------------------------------------------------------- #
# parse_block_ids / backlog_divergence                                         #
# --------------------------------------------------------------------------- #


def test_parse_block_ids_only_inside_block() -> None:
    text = (
        '# Backlog\n\n- **T999** — prose mention, not in block\n\n'
        f'{BEGIN_MARKER}\n- **T001** — a\n- **T002** — b\n{END_MARKER}\n'
    )
    assert parse_block_ids(text) == ['T001', 'T002']


def test_parse_block_ids_no_block() -> None:
    assert parse_block_ids('# Backlog\n- **T001** — a\n') == []


def test_divergence_added_and_removed(store: Path) -> None:
    _write(store, 'T001', status='todo')  # in store, not in block → added
    _write(store, 'T002', status='doing')  # in store and block → neither
    _write(store, 'T003', status='done')  # finished, listed in block → removed
    backlog_text = (
        f'{BEGIN_MARKER}\n- **T002** — b\n- **T003** — c\n{END_MARKER}\n'
    )
    div = backlog_divergence(store, backlog_text)
    assert div.added == ['T001']
    assert div.removed == ['T003']


def test_divergence_clean_when_synced(store: Path) -> None:
    _write(store, 'T001', status='todo')
    _write(store, 'T002', status='review')
    synced = sync_backlog('', backlog_items(store))
    div = backlog_divergence(store, synced)
    assert div == ([], [])


def test_divergence_sorts_numeric(store: Path) -> None:
    _write(store, 'T1000', status='todo')
    _write(store, 'T200', status='todo')
    div = backlog_divergence(store, f'{BEGIN_MARKER}\n{END_MARKER}\n')
    assert div.added == ['T200', 'T1000']


# --------------------------------------------------------------------------- #
# CLI layer — real temporary git repository                                    #
# --------------------------------------------------------------------------- #


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ['git', *args], cwd=repo, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A real git repo (one commit on `main`), made the process CWD."""
    root = tmp_path / 'proj'
    root.mkdir()
    _git(root, 'init', '-b', 'main')
    _git(root, 'config', 'user.email', 'test@example.com')
    _git(root, 'config', 'user.name', 'Test')
    (root / 'README.md').write_text('hello\n', encoding='utf-8')
    (root / 'BACKLOG.md').write_text('# Backlog\n\nintro\n', encoding='utf-8')
    _git(root, 'add', '.')
    _git(root, 'commit', '-m', 'init')
    monkeypatch.delenv('DT_HOME', raising=False)
    monkeypatch.chdir(root)
    # Pre-create the store so the one-shot "created …" stderr line does not land
    # in the CliRunner's merged output and trip assertions.
    ensure_store()
    return root


def test_cli_sync_on_main(repo: Path) -> None:
    tasks = store_dir()
    _write(tasks, 'T001', status='todo', title='первая')
    _write(tasks, 'T002', status='done', title='закрытая')
    result = CliRunner().invoke(app, ['backlog', 'sync'])
    assert result.exit_code == 0, result.output
    text = (repo / 'BACKLOG.md').read_text(encoding='utf-8')
    assert 'intro' in text  # prose preserved
    assert '- **T001** — первая' in text
    assert 'закрытая' not in text  # done excluded


def test_cli_sync_json(repo: Path) -> None:
    _write(store_dir(), 'T001', status='todo')
    result = CliRunner().invoke(app, ['backlog', 'sync', '--json'])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload['tasks'] == 1
    assert payload['backlog'].endswith('BACKLOG.md')


def test_cli_sync_refuses_off_main(repo: Path) -> None:
    _git(repo, 'checkout', '-b', 'T001-feature')
    _write(store_dir(), 'T001', status='todo')
    before = (repo / 'BACKLOG.md').read_text(encoding='utf-8')
    result = CliRunner().invoke(app, ['backlog', 'sync'])
    assert result.exit_code == 1
    assert '--force' in result.output
    # file untouched
    assert (repo / 'BACKLOG.md').read_text(encoding='utf-8') == before


def test_cli_sync_force_off_main(repo: Path) -> None:
    _git(repo, 'checkout', '-b', 'T001-feature')
    _write(store_dir(), 'T001', status='todo', title='форс')
    result = CliRunner().invoke(app, ['backlog', 'sync', '--force'])
    assert result.exit_code == 0, result.output
    assert '- **T001** — форс' in (repo / 'BACKLOG.md').read_text(encoding='utf-8')


def test_cli_sync_idempotent(repo: Path) -> None:
    _write(store_dir(), 'T001', status='todo')
    first = CliRunner().invoke(app, ['backlog', 'sync'])
    assert first.exit_code == 0
    after_first = (repo / 'BACKLOG.md').read_text(encoding='utf-8')
    second = CliRunner().invoke(app, ['backlog', 'sync'])
    assert second.exit_code == 0
    assert (repo / 'BACKLOG.md').read_text(encoding='utf-8') == after_first


def test_cli_sync_outside_git_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No git and no DT_HOME → repo root cannot be resolved to write BACKLOG.md.
    outside = tmp_path / 'nogit'
    outside.mkdir()
    monkeypatch.delenv('DT_HOME', raising=False)
    monkeypatch.chdir(outside)
    result = CliRunner().invoke(app, ['backlog', 'sync'])
    assert result.exit_code == 1
    assert 'not inside a git repository' in result.output


def test_cli_sync_reports_write_error(repo: Path) -> None:
    # BACKLOG.md replaced by a directory → read/write raises OSError, surfaced
    # as a clean exit 1 (no traceback), not an escaping exception.
    (repo / 'BACKLOG.md').unlink()
    (repo / 'BACKLOG.md').mkdir()
    _write(store_dir(), 'T001', status='todo')
    result = CliRunner().invoke(app, ['backlog', 'sync'])
    assert result.exit_code == 1
    assert 'dt backlog:' in result.output
