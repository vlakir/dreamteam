"""T041 — task-state transfer (`dt state export` / `import`).

Two layers: the pure, git-free core in `dreamteam.dt.state` (export/serialize/
parse/import against an explicit temp store) and the Typer wrapper in
`dreamteam.state_cli`, driven via `CliRunner` with `DT_HOME` → `tmp_path`
(no git — state operates on the store only, including the `-` stdio path).
"""

from __future__ import annotations

import datetime
import json
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from dreamteam.cli import app
from dreamteam.dt.model import Task, TaskStatus, save_task
from dreamteam.dt.paths import ensure_store, store_dir
from dreamteam.dt.state import (
    STATE_VERSION,
    StateBundle,
    export_bundle,
    import_bundle,
    parse,
    serialize,
)
from dreamteam.dt.tasks import TaskError, load_all_tasks, read_counter

if TYPE_CHECKING:
    from pathlib import Path


def _write(
    store: Path,
    task_id: str,
    *,
    status: TaskStatus = 'todo',
    title: str | None = None,
    body: str = '',
    **extra: object,
) -> None:
    task = Task(id=task_id, title=title or f'task {task_id}', status=status, **extra)
    task.body = body
    save_task(store / 'tasks' / f'{task_id}.md', task)


@pytest.fixture
def store(tmp_path: Path) -> Path:
    root = tmp_path / 'store'
    (root / 'tasks').mkdir(parents=True)
    return root


# --------------------------------------------------------------------------- #
# export_bundle                                                                #
# --------------------------------------------------------------------------- #


def test_export_reads_records_and_counter(store: Path) -> None:
    _write(store, 'T001')
    _write(store, 'T002')
    (store / 'counter').write_text('7\n', encoding='utf-8')
    bundle = export_bundle(store)
    assert bundle.counter == 7
    assert [t.id for t in bundle.tasks] == ['T001', 'T002']


def test_export_sorts_numeric(store: Path) -> None:
    _write(store, 'T200')
    _write(store, 'T1000')
    _write(store, 'T099')
    assert [t.id for t in export_bundle(store).tasks] == ['T099', 'T200', 'T1000']


def test_export_ignores_sessions_and_bindings(store: Path) -> None:
    _write(store, 'T001')
    (store / 'sessions').mkdir()
    (store / 'sessions' / 'T001.json').write_text('{}', encoding='utf-8')
    (store / 'by-worktree').mkdir()
    (store / 'by-worktree' / 'abc').mkdir()
    (store / 'by-worktree' / 'abc' / 'current-task').write_text('T001\n')
    bundle = export_bundle(store)
    # only the task record crosses; machine-specific dirs are never read.
    assert [t.id for t in bundle.tasks] == ['T001']
    text = serialize(bundle)
    assert 'sessions' not in text
    assert 'by-worktree' not in text


# --------------------------------------------------------------------------- #
# serialize / parse round-trip                                                 #
# --------------------------------------------------------------------------- #


def test_roundtrip_preserves_body_and_unknown_fields(store: Path) -> None:
    _write(
        store,
        'T001',
        title='Задача',
        body='## Handover\n- сделано: старт\n',
        custom_flag='keep-me',  # unknown frontmatter field (extra='allow')
        created=datetime.date(2026, 7, 30),
    )
    bundle = export_bundle(store)
    restored = parse(serialize(bundle))
    task = restored.tasks[0]
    assert task.id == 'T001'
    assert task.title == 'Задача'
    assert task.body == '## Handover\n- сделано: старт\n'
    assert task.created == datetime.date(2026, 7, 30)
    # unknown field survives the round-trip (forward compatibility)
    assert task.model_dump()['custom_flag'] == 'keep-me'


def test_serialize_declares_version() -> None:
    payload = json.loads(serialize(StateBundle(counter=0, tasks=[])))
    assert payload['dt_state_version'] == STATE_VERSION
    assert payload['counter'] == 0
    assert payload['tasks'] == []


# --------------------------------------------------------------------------- #
# parse — malformed input                                                      #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ('text', 'fragment'),
    [
        ('not json {', 'not valid JSON'),
        ('[]', 'must be a JSON object'),
        ('{"counter": 1, "tasks": []}', 'dt_state_version'),
        ('{"dt_state_version": 999, "counter": 1, "tasks": []}', 'newer than'),
        ('{"dt_state_version": 1, "counter": -1, "tasks": []}', '`counter`'),
        ('{"dt_state_version": 1, "counter": 1, "tasks": {}}', '`tasks` must be a list'),
        ('{"dt_state_version": 1, "counter": 1, "tasks": [1]}', 'must be an object'),
    ],
)
def test_parse_rejects_malformed(text: str, fragment: str) -> None:
    with pytest.raises(TaskError, match=fragment):
        parse(text)


def test_parse_rejects_non_string_body() -> None:
    text = (
        '{"dt_state_version": 1, "counter": 1, '
        '"tasks": [{"id": "T001", "title": "x", "body": 42}]}'
    )
    with pytest.raises(TaskError, match='`body` must be a string'):
        parse(text)


def test_parse_rejects_invalid_task_record() -> None:
    # `status` outside the allowed literal → pydantic ValidationError → TaskError
    text = (
        '{"dt_state_version": 1, "counter": 1, '
        '"tasks": [{"id": "T001", "title": "x", "status": "bogus"}]}'
    )
    with pytest.raises(TaskError, match='invalid task record'):
        parse(text)


# --------------------------------------------------------------------------- #
# import_bundle                                                                #
# --------------------------------------------------------------------------- #


def test_import_into_empty_store(store: Path, tmp_path: Path) -> None:
    src = tmp_path / 'src'
    (src / 'tasks').mkdir(parents=True)
    _write(src, 'T001', title='первая')
    _write(src, 'T005', title='пятая')
    (src / 'counter').write_text('5\n', encoding='utf-8')
    result = import_bundle(store, export_bundle(src), None)
    assert result.added == ['T001', 'T005']
    assert set(load_all_tasks(store)) == {'T001', 'T005'}
    assert read_counter(store) == 5


def test_import_conflict_aborts_without_flag(store: Path, tmp_path: Path) -> None:
    _write(store, 'T001', title='локальная')
    src = tmp_path / 'src'
    (src / 'tasks').mkdir(parents=True)
    _write(src, 'T001', title='чужая')
    _write(src, 'T002', title='новая')
    with pytest.raises(TaskError, match='T001'):
        import_bundle(store, export_bundle(src), None)
    # nothing written: the local record is untouched and T002 not created
    assert load_all_tasks(store)['T001'].title == 'локальная'
    assert 'T002' not in load_all_tasks(store)


def test_import_skip_keeps_local(store: Path, tmp_path: Path) -> None:
    _write(store, 'T001', title='локальная')
    src = tmp_path / 'src'
    (src / 'tasks').mkdir(parents=True)
    _write(src, 'T001', title='чужая')
    _write(src, 'T002', title='новая')
    result = import_bundle(store, export_bundle(src), 'skip')
    assert result.skipped == ['T001']
    assert result.added == ['T002']
    assert load_all_tasks(store)['T001'].title == 'локальная'
    assert load_all_tasks(store)['T002'].title == 'новая'


def test_import_overwrite_replaces(store: Path, tmp_path: Path) -> None:
    _write(store, 'T001', title='локальная')
    src = tmp_path / 'src'
    (src / 'tasks').mkdir(parents=True)
    _write(src, 'T001', title='чужая')
    result = import_bundle(store, export_bundle(src), 'overwrite')
    assert result.overwritten == ['T001']
    assert load_all_tasks(store)['T001'].title == 'чужая'


def test_import_bumps_counter_over_local(store: Path, tmp_path: Path) -> None:
    (store / 'counter').write_text('3\n', encoding='utf-8')
    src = tmp_path / 'src'
    (src / 'tasks').mkdir(parents=True)
    _write(src, 'T010', title='высокая')
    (src / 'counter').write_text('10\n', encoding='utf-8')
    import_bundle(store, export_bundle(src), None)
    # counter = max(local 3, bundle 10, highest imported id 10)
    assert read_counter(store) == 10


def test_import_never_lowers_counter(store: Path, tmp_path: Path) -> None:
    (store / 'counter').write_text('42\n', encoding='utf-8')
    src = tmp_path / 'src'
    (src / 'tasks').mkdir(parents=True)
    _write(src, 'T001')
    (src / 'counter').write_text('1\n', encoding='utf-8')
    import_bundle(store, export_bundle(src), None)
    assert read_counter(store) == 42


def test_import_rejects_traversal_id(store: Path) -> None:
    evil = StateBundle(counter=1, tasks=[Task(id='../../evil', title='x')])
    with pytest.raises(TaskError, match='invalid'):
        import_bundle(store, evil, None)
    # no file escaped the tasks dir
    assert not (store.parent / 'evil.md').exists()


def test_import_rejects_duplicate_id(store: Path) -> None:
    dup = StateBundle(
        counter=2,
        tasks=[Task(id='T001', title='a'), Task(id='T001', title='b')],
    )
    with pytest.raises(TaskError, match='duplicate'):
        import_bundle(store, dup, None)


# --------------------------------------------------------------------------- #
# CLI layer                                                                    #
# --------------------------------------------------------------------------- #


@pytest.fixture
def cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CliRunner:
    monkeypatch.setenv('DT_HOME', str(tmp_path / 'home'))
    # Pre-create the store so the one-shot "created …" stderr line does not mix
    # into CliRunner output and trip the JSON assertions.
    ensure_store()
    return CliRunner()


def test_cli_export_to_file_then_import(cli: CliRunner, tmp_path: Path) -> None:
    _write(store_dir(), 'T001', title='первая')
    out = tmp_path / 'state.json'
    result = cli.invoke(app, ['state', 'export', str(out)])
    assert result.exit_code == 0, result.output
    payload = json.loads(out.read_text(encoding='utf-8'))
    assert payload['tasks'][0]['id'] == 'T001'


def test_cli_export_stdout_dash(cli: CliRunner) -> None:
    _write(store_dir(), 'T001')
    result = cli.invoke(app, ['state', 'export', '-'])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload['dt_state_version'] == STATE_VERSION
    assert payload['tasks'][0]['id'] == 'T001'


def test_cli_import_from_stdin_dash(cli: CliRunner) -> None:
    bundle = (
        '{"dt_state_version": 1, "counter": 4, '
        '"tasks": [{"id": "T004", "title": "из stdin", "status": "todo", '
        '"deps": [], "tags": [], "body": ""}]}'
    )
    result = cli.invoke(app, ['state', 'import', '-', '--json'], input=bundle)
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload['added'] == ['T004']
    assert payload['counter'] == 4
    assert 'T004' in load_all_tasks(store_dir())


def test_cli_import_conflict_aborts(cli: CliRunner) -> None:
    _write(store_dir(), 'T001', title='локальная')
    bundle = (
        '{"dt_state_version": 1, "counter": 1, '
        '"tasks": [{"id": "T001", "title": "чужая", "status": "todo", '
        '"deps": [], "tags": [], "body": ""}]}'
    )
    result = cli.invoke(app, ['state', 'import', '-'], input=bundle)
    assert result.exit_code == 1
    assert 'T001' in result.output
    assert '--on-conflict' in result.output
    assert load_all_tasks(store_dir())['T001'].title == 'локальная'


def test_cli_import_overwrite(cli: CliRunner) -> None:
    _write(store_dir(), 'T001', title='локальная')
    bundle = (
        '{"dt_state_version": 1, "counter": 1, '
        '"tasks": [{"id": "T001", "title": "чужая", "status": "todo", '
        '"deps": [], "tags": [], "body": ""}]}'
    )
    result = cli.invoke(
        app, ['state', 'import', '-', '--on-conflict', 'overwrite'], input=bundle
    )
    assert result.exit_code == 0, result.output
    assert load_all_tasks(store_dir())['T001'].title == 'чужая'


def test_cli_import_bad_file(cli: CliRunner, tmp_path: Path) -> None:
    result = cli.invoke(app, ['state', 'import', str(tmp_path / 'missing.json')])
    assert result.exit_code == 1
    assert 'dt state:' in result.output


def test_cli_export_write_error(cli: CliRunner, tmp_path: Path) -> None:
    _write(store_dir(), 'T001')
    # a directory path is not writable as a file → OSError, surfaced as exit 1.
    target = tmp_path / 'adir'
    target.mkdir()
    result = cli.invoke(app, ['state', 'export', str(target)])
    assert result.exit_code == 1
    assert 'dt state:' in result.output
