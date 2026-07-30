"""T034 — base task operations (`dt task new/show/move/split`).

Two layers: the pure operations in `dreamteam.dt.tasks` (exercised against an
explicit temp store, no git needed) and the Typer wrappers in
`dreamteam.task_cli` (exercised via `CliRunner` with `DT_HOME` pointed at
`tmp_path`, so nothing touches a real sibling `.dt` directory).
"""

from __future__ import annotations

import datetime
import json
from typing import TYPE_CHECKING, get_args

import pytest
from typer.testing import CliRunner

from dreamteam.cli import app
from dreamteam.dt.model import TASK_STATUSES, TaskStatus, load_task, save_task
from dreamteam.dt.tasks import (
    TaskError,
    _normalize_refs,
    allocate_id,
    format_id,
    move_task,
    new_task,
    parse_status,
    show_task,
    split_task,
)
from dreamteam.task_cli import _human_show, _to_json

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

_TODAY = datetime.date(2026, 7, 30)
_LATER = datetime.date(2026, 8, 1)


@pytest.fixture
def store(tmp_path: Path) -> Path:
    """A ready store directory (`store/` with a `tasks/` subdir)."""
    root = tmp_path / 'store'
    (root / 'tasks').mkdir(parents=True)
    return root


@pytest.fixture
def cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CliRunner:
    """A CliRunner with `DT_HOME` pointed at `tmp_path` (no real `.dt` touched)."""
    monkeypatch.setenv('DT_HOME', str(tmp_path / 'home'))
    return CliRunner()


def _record(store: Path, task_id: str) -> Path:
    return store / 'tasks' / f'{task_id}.md'


# --------------------------------------------------------------------------- #
# format_id / parse_status / _normalize_refs                                  #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ('number', 'expected'),
    [(1, 'T001'), (34, 'T034'), (999, 'T999'), (1000, 'T1000')],
)
def test_format_id(number: int, expected: str) -> None:
    assert format_id(number) == expected


def test_task_statuses_match_literal_no_drift() -> None:
    assert set(TASK_STATUSES) == set(get_args(TaskStatus))


@pytest.mark.parametrize('value', ['todo', 'doing', 'review', 'done', 'dropped'])
def test_parse_status_accepts_valid(value: str) -> None:
    assert parse_status(value) == value


def test_parse_status_rejects_unknown() -> None:
    with pytest.raises(TaskError, match='allowed: todo, doing'):
        parse_status('bogus')


def test_normalize_refs_flattens_splits_and_dedupes() -> None:
    assert _normalize_refs(['T003,T005', ' T007 ', 'T003', '']) == [
        'T003',
        'T005',
        'T007',
    ]


# --------------------------------------------------------------------------- #
# allocate_id / counter                                                       #
# --------------------------------------------------------------------------- #


def test_allocate_id_sequential_from_empty(store: Path) -> None:
    first, first_path = allocate_id(store)
    second, _ = allocate_id(store)
    assert (first, second) == ('T001', 'T002')
    assert first_path == _record(store, 'T001')
    assert (store / 'counter').read_text(encoding='utf-8').strip() == '2'


def test_allocate_id_skips_occupied_number(store: Path) -> None:
    allocate_id(store)  # T001, counter=1
    _record(store, 'T002').write_text('x\n', encoding='utf-8')  # occupy T002
    third, _ = allocate_id(store)
    assert third == 'T003'


def test_counter_never_moves_backward(store: Path) -> None:
    allocate_id(store)  # counter -> 1
    (store / 'counter').write_text('9\n', encoding='utf-8')
    allocate_id(store)  # candidate 10 -> T010
    assert (store / 'counter').read_text(encoding='utf-8').strip() == '10'


def test_corrupt_counter_raises(store: Path) -> None:
    (store / 'counter').write_text('not-a-number\n', encoding='utf-8')
    with pytest.raises(TaskError, match='corrupt'):
        allocate_id(store)


# --------------------------------------------------------------------------- #
# new_task                                                                    #
# --------------------------------------------------------------------------- #


def test_new_task_creates_todo_record(store: Path) -> None:
    task = new_task(store, 'First task', today=_TODAY)
    assert task.id == 'T001'
    assert task.status == 'todo'
    assert task.created == _TODAY
    assert task.updated == _TODAY
    assert load_task(_record(store, 'T001')).title == 'First task'


def test_new_task_with_deps_and_parent(store: Path) -> None:
    new_task(store, 'dep', today=_TODAY)  # T001
    new_task(store, 'parent', today=_TODAY)  # T002
    task = new_task(store, 'child', deps=['T001'], parent='T002', today=_TODAY)
    assert task.deps == ['T001']
    assert task.parent == 'T002'


def test_new_task_comma_separated_deps(store: Path) -> None:
    new_task(store, 'a', today=_TODAY)  # T001
    new_task(store, 'b', today=_TODAY)  # T002
    task = new_task(store, 'c', deps=['T001,T002'], today=_TODAY)
    assert task.deps == ['T001', 'T002']


def test_new_task_blocks_mutates_target(store: Path) -> None:
    new_task(store, 'target', today=_TODAY)  # T001
    blocker = new_task(store, 'blocker', blocks=['T001'], today=_LATER)  # T002
    target = load_task(_record(store, 'T001'))
    assert blocker.id == 'T002'
    assert target.deps == ['T002']
    assert target.updated == _LATER


def test_new_task_blocks_is_idempotent(store: Path) -> None:
    new_task(store, 'target', today=_TODAY)  # T001
    # Pre-seed T001 with the dep the blocker will add, to prove no duplication.
    target = load_task(_record(store, 'T001'))
    target.deps.append('T002')
    save_task(_record(store, 'T001'), target)
    new_task(store, 'blocker', blocks=['T001'], today=_LATER)  # T002
    assert load_task(_record(store, 'T001')).deps == ['T002']


@pytest.mark.parametrize('role', ['deps', 'parent', 'blocks'])
def test_new_task_unknown_reference_raises_and_reserves_nothing(
    store: Path, role: str
) -> None:
    kwargs = {'parent': 'T999'} if role == 'parent' else {role: ['T999']}
    with pytest.raises(TaskError, match='unknown task'):
        new_task(store, 'x', today=_TODAY, **kwargs)
    assert not _record(store, 'T001').exists()
    assert not (store / 'counter').exists()


def test_new_task_empty_title_raises(store: Path) -> None:
    with pytest.raises(TaskError, match='title must not be empty'):
        new_task(store, '   ', today=_TODAY)


# --------------------------------------------------------------------------- #
# show_task / move_task / split_task                                          #
# --------------------------------------------------------------------------- #


def test_show_task_missing_raises(store: Path) -> None:
    with pytest.raises(TaskError, match='not found'):
        show_task(store, 'T404')


def test_move_task_changes_status_and_updated(store: Path) -> None:
    new_task(store, 't', today=_TODAY)  # T001
    moved = move_task(store, 'T001', 'review', today=_LATER)
    assert moved.status == 'review'
    assert moved.updated == _LATER
    assert load_task(_record(store, 'T001')).status == 'review'


def test_move_task_unknown_status_raises(store: Path) -> None:
    new_task(store, 't', today=_TODAY)
    with pytest.raises(TaskError, match='unknown status'):
        move_task(store, 'T001', 'archived', today=_TODAY)


def test_move_task_missing_raises(store: Path) -> None:
    with pytest.raises(TaskError, match='not found'):
        move_task(store, 'T404', 'done', today=_TODAY)


def test_split_task_creates_child_and_leaves_parent(store: Path) -> None:
    parent = new_task(store, 'parent', today=_TODAY)  # T001
    child = split_task(store, 'T001', 'second half', today=_LATER)
    assert child.parent == 'T001'
    assert child.id == 'T002'
    # Parent record untouched: no deps added, `updated` unchanged.
    reloaded = load_task(_record(store, 'T001'))
    assert reloaded.deps == []
    assert reloaded.updated == parent.updated == _TODAY


def test_split_task_unknown_parent_raises(store: Path) -> None:
    with pytest.raises(TaskError, match='parent task'):
        split_task(store, 'T404', 'x', today=_TODAY)


# --------------------------------------------------------------------------- #
# ID validation / path-traversal / counter hardening                          #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize('bad', ['../x', 'T001/../x', 't001', 'T12', 'foo', 'T001.md'])
def test_invalid_id_rejected_on_show(store: Path, bad: str) -> None:
    with pytest.raises(TaskError, match='invalid'):
        show_task(store, bad)


def test_invalid_id_rejected_on_move_and_split(store: Path) -> None:
    with pytest.raises(TaskError, match='invalid'):
        move_task(store, '../evil', 'done', today=_TODAY)
    with pytest.raises(TaskError, match='invalid'):
        split_task(store, '../evil', 'x', today=_TODAY)


def test_invalid_reference_rejected_on_new_reserves_nothing(store: Path) -> None:
    with pytest.raises(TaskError, match='invalid'):
        new_task(store, 'x', deps=['../evil'], today=_TODAY)
    assert not (store / 'counter').exists()


def test_negative_counter_is_corrupt(store: Path) -> None:
    (store / 'counter').write_text('-5\n', encoding='utf-8')
    with pytest.raises(TaskError, match='negative'):
        allocate_id(store)


def test_cli_invalid_id_exits_nonzero(cli: CliRunner) -> None:
    result = cli.invoke(app, ['task', 'show', '../evil'])
    assert result.exit_code == 1
    assert 'invalid' in result.output


# --------------------------------------------------------------------------- #
# CLI formatting helpers                                                       #
# --------------------------------------------------------------------------- #


def test_to_json_includes_body(store: Path) -> None:
    task = new_task(store, 'json me', today=_TODAY)
    task.body = 'context here\n'
    payload = json.loads(_to_json(task))
    assert payload['id'] == 'T001'
    assert payload['body'] == 'context here\n'
    assert payload['created'] == '2026-07-30'  # date serialized as ISO string


def test_human_show_renders_fields_and_body(store: Path) -> None:
    task = new_task(store, 'title', today=_TODAY)
    task.parent = 'T009'
    task.tags = ['core', 'cli']
    task.body = 'the body'
    text = _human_show(task)
    assert 'T001  [todo]  title' in text
    assert 'parent  T009' in text
    assert 'tags    core, cli' in text
    assert 'the body' in text


# --------------------------------------------------------------------------- #
# CLI end-to-end (CliRunner, DT_HOME -> tmp_path)                              #
# --------------------------------------------------------------------------- #


def test_cli_new_show_move_roundtrip(cli: CliRunner) -> None:
    created = cli.invoke(app, ['task', 'new', 'My task'])
    assert created.exit_code == 0
    assert 'created T001' in created.output

    shown = cli.invoke(app, ['task', 'show', 'T001', '--json'])
    assert shown.exit_code == 0
    payload = json.loads(shown.output)
    assert payload['id'] == 'T001'
    assert payload['status'] == 'todo'

    moved = cli.invoke(app, ['task', 'move', 'T001', 'doing'])
    assert moved.exit_code == 0
    assert 'T001 → doing' in moved.output


def test_cli_split(cli: CliRunner) -> None:
    cli.invoke(app, ['task', 'new', 'parent'])
    result = cli.invoke(app, ['task', 'split', 'T001', 'child'])
    assert result.exit_code == 0
    assert 'created T002 (parent T001)' in result.output


def test_cli_unknown_task_exits_nonzero(cli: CliRunner) -> None:
    result = cli.invoke(app, ['task', 'show', 'T404'])
    assert result.exit_code == 1
    assert 'not found' in result.output


def test_cli_new_json_and_blocks(cli: CliRunner) -> None:
    cli.invoke(app, ['task', 'new', 'target'])  # T001
    result = cli.invoke(app, ['task', 'new', 'blocker', '--blocks', 'T001', '--json'])
    assert result.exit_code == 0
    assert json.loads(result.output)['id'] == 'T002'
