"""T037 — text board (`dt board`).

Two layers: the pure model in `dreamteam.dt.board` (`board_model`/`board_columns`
against an explicit temp store) and the Typer wrapper in `dreamteam.board_cli`
(via `CliRunner` with `DT_HOME` → `tmp_path`). No git is involved — the board
reads the store only.
"""

from __future__ import annotations

import datetime
import json
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from dreamteam.cli import app
from dreamteam.dt.board import BOARD_STATUSES, board_columns, board_model
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
    updated: datetime.date | None = None,
) -> None:
    task = Task(
        id=task_id,
        title=title or f'task {task_id}',
        status=status,
        updated=updated,
    )
    save_task(store / 'tasks' / f'{task_id}.md', task)


@pytest.fixture
def store(tmp_path: Path) -> Path:
    root = tmp_path / 'store'
    (root / 'tasks').mkdir(parents=True)
    return root


# --------------------------------------------------------------------------- #
# board_model                                                                  #
# --------------------------------------------------------------------------- #


def test_board_model_drops_dropped(store: Path) -> None:
    _write(store, 'T001', status='todo')
    _write(store, 'T002', status='dropped')
    ids = [task.id for task in board_model(store)]
    assert ids == ['T001']


def test_board_model_sorts_updated_desc(store: Path) -> None:
    _write(store, 'T001', updated=datetime.date(2026, 7, 10))
    _write(store, 'T002', updated=datetime.date(2026, 7, 30))
    _write(store, 'T003', updated=datetime.date(2026, 7, 20))
    assert [t.id for t in board_model(store)] == ['T002', 'T003', 'T001']


def test_board_model_undated_last(store: Path) -> None:
    _write(store, 'T001', updated=None)
    _write(store, 'T002', updated=datetime.date(2026, 7, 30))
    _write(store, 'T003', updated=None)
    # dated first, then undated by ID.
    assert [t.id for t in board_model(store)] == ['T002', 'T001', 'T003']


def test_board_model_empty(store: Path) -> None:
    assert board_model(store) == []


# --------------------------------------------------------------------------- #
# board_columns                                                                #
# --------------------------------------------------------------------------- #


def test_board_columns_all_statuses_present(store: Path) -> None:
    columns = board_columns([])
    assert tuple(columns.keys()) == BOARD_STATUSES
    assert 'dropped' not in columns
    assert all(v == [] for v in columns.values())


def test_board_columns_group_preserves_model_order(store: Path) -> None:
    _write(store, 'T001', status='done', updated=datetime.date(2026, 7, 10))
    _write(store, 'T002', status='done', updated=datetime.date(2026, 7, 30))
    _write(store, 'T003', status='todo', updated=datetime.date(2026, 7, 20))
    columns = board_columns(board_model(store))
    assert [t.id for t in columns['done']] == ['T002', 'T001']
    assert [t.id for t in columns['todo']] == ['T003']


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #


@pytest.fixture
def cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CliRunner:
    monkeypatch.setenv('DT_HOME', str(tmp_path / 'home'))
    # Pre-create the store so the one-shot "created …" stderr line does not mix
    # into CliRunner output and trip the JSON/section assertions.
    ensure_store()
    return CliRunner()


def test_cli_board_empty(cli: CliRunner) -> None:
    result = cli.invoke(app, ['board'])
    assert result.exit_code == 0
    for status in BOARD_STATUSES:
        assert status in result.output


def test_cli_board_human(cli: CliRunner) -> None:
    tasks = store_dir()
    _write(tasks, 'T001', status='done', title='каркас хранилища')
    _write(tasks, 'T002', status='doing', title='базовые операции')
    _write(tasks, 'T003', status='dropped', title='выброшенная')
    result = cli.invoke(app, ['board'])
    assert result.exit_code == 0
    assert 'T001  [done]  каркас хранилища' in result.output
    assert 'T002  [doing]  базовые операции' in result.output
    assert 'выброшенная' not in result.output  # dropped never shown


def test_cli_board_json(cli: CliRunner) -> None:
    tasks = store_dir()
    _write(tasks, 'T001', status='done')
    _write(tasks, 'T002', status='todo')
    result = cli.invoke(app, ['board', '--json'])
    payload = json.loads(result.output)
    assert list(payload['columns'].keys()) == list(BOARD_STATUSES)
    assert [t['id'] for t in payload['columns']['done']] == ['T001']
    assert [t['id'] for t in payload['columns']['todo']] == ['T002']
    # full record shape, including body.
    assert 'body' in payload['columns']['done'][0]
