"""T038 — task search by phrase (`dt task find`).

Two layers: the pure ranking in `dreamteam.dt.tasks` (`find_tasks` plus the
token helpers, against an explicit temp store) and the Typer wrapper in
`dreamteam.task_cli` (via `CliRunner` with `DT_HOME` → `tmp_path`). No git.
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
from dreamteam.dt.tasks import _token_hit, _tokenize, find_tasks

if TYPE_CHECKING:
    from pathlib import Path


def _write(
    store: Path,
    task_id: str,
    *,
    title: str = '',
    status: TaskStatus = 'todo',
    body: str = '',
    tags: list[str] | None = None,
    branch: str | None = None,
    updated: datetime.date | None = None,
) -> None:
    task = Task(
        id=task_id,
        title=title or f'task {task_id}',
        status=status,
        body=body,
        tags=tags or [],
        branch=branch,
        updated=updated,
    )
    save_task(store / 'tasks' / f'{task_id}.md', task)


@pytest.fixture
def store(tmp_path: Path) -> Path:
    root = tmp_path / 'store'
    (root / 'tasks').mkdir(parents=True)
    return root


# --------------------------------------------------------------------------- #
# _tokenize / _token_hit                                                       #
# --------------------------------------------------------------------------- #


def test_tokenize_casefold_and_min_len() -> None:
    assert _tokenize('Курсор, В Режиме!') == ['курсор', 'режиме']  # 'в' dropped (<2)


def test_tokenize_keeps_digits_and_ascii() -> None:
    assert _tokenize('T034-cursor Fix') == ['t034', 'cursor', 'fix']


@pytest.mark.parametrize(
    ('query', 'candidate', 'expected'),
    [
        ('курсор', 'курсора', True),  # shared prefix ≥ 4
        ('полноэкранный', 'полноэкранном', True),  # shared prefix 11
        ('cli', 'client', False),  # short token, not exact
        ('cli', 'cli', True),  # short token, exact
        ('программа', 'проект', False),  # prefix 'про' (3) < 4
    ],
)
def test_token_hit(query: str, candidate: str, expected: bool) -> None:
    assert _token_hit(query, candidate) is expected


# --------------------------------------------------------------------------- #
# find_tasks                                                                    #
# --------------------------------------------------------------------------- #


def test_find_morphology_prefix(store: Path) -> None:
    _write(store, 'T001', title='Изменить вид курсора в полноэкранном режиме')
    results = find_tasks(store, 'курсор полноэкранный режим')
    assert [r.task.id for r in results] == ['T001']


def test_find_title_outranks_body(store: Path) -> None:
    _write(store, 'T001', title='worktree lifecycle')
    _write(store, 'T002', title='unrelated', body='mentions worktree once in body')
    results = find_tasks(store, 'worktree')
    assert [r.task.id for r in results] == ['T001', 'T002']
    assert results[0].score > results[1].score


def test_find_active_outranks_done(store: Path) -> None:
    _write(store, 'T001', title='worktree', status='done')
    _write(store, 'T002', title='worktree', status='todo')
    results = find_tasks(store, 'worktree')
    # same textual match, but active task ranks first (×1.0 vs ×0.5).
    assert [r.task.id for r in results] == ['T002', 'T001']
    assert results[0].score == 3.0
    assert results[1].score == 1.5


def test_find_matches_tags_and_branch(store: Path) -> None:
    _write(store, 'T001', title='alpha', tags=['storage', 'core'])
    _write(store, 'T002', title='beta', branch='T002-storage-layer')
    ids = {r.task.id for r in find_tasks(store, 'storage')}
    assert ids == {'T001', 'T002'}


def test_find_empty_query(store: Path) -> None:
    _write(store, 'T001', title='anything')
    assert find_tasks(store, '   ') == []


def test_find_no_match(store: Path) -> None:
    _write(store, 'T001', title='worktree')
    assert find_tasks(store, 'zzzznonexistent') == []


def test_find_outputs_filename_stem_not_frontmatter_id(store: Path) -> None:
    # A hand-edited record whose frontmatter `id` drifted from its filename:
    # find must emit the actionable filename stem, not the stale frontmatter id.
    task = Task(id='T999', title='worktree drift', status='todo')
    save_task(store / 'tasks' / 'T001.md', task)
    results = find_tasks(store, 'worktree')
    assert [r.task.id for r in results] == ['T001']


def test_find_ties_break_by_updated_then_id(store: Path) -> None:
    _write(store, 'T001', title='worktree', updated=datetime.date(2026, 7, 10))
    _write(store, 'T002', title='worktree', updated=datetime.date(2026, 7, 30))
    _write(store, 'T003', title='worktree', updated=None)
    # equal score → newest updated first, undated last.
    assert [r.task.id for r in find_tasks(store, 'worktree')] == ['T002', 'T001', 'T003']


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #


@pytest.fixture
def cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CliRunner:
    monkeypatch.setenv('DT_HOME', str(tmp_path / 'home'))
    ensure_store()  # pre-create so the one-shot stderr line does not mix into output
    return CliRunner()


def test_cli_find_human(cli: CliRunner) -> None:
    tasks = store_dir()
    _write(tasks, 'T001', title='worktree prune', branch='T001-worktree')
    result = cli.invoke(app, ['task', 'find', 'worktree'])
    assert result.exit_code == 0
    assert 'T001  [todo]  worktree prune  (T001-worktree)' in result.output


def test_cli_find_json_has_score(cli: CliRunner) -> None:
    tasks = store_dir()
    _write(tasks, 'T001', title='worktree')
    result = cli.invoke(app, ['task', 'find', 'worktree', '--json'])
    payload = json.loads(result.output)
    assert payload[0]['id'] == 'T001'
    assert payload[0]['score'] == 3.0
    assert 'body' in payload[0]


def test_cli_find_no_matches(cli: CliRunner) -> None:
    result = cli.invoke(app, ['task', 'find', 'nothingmatches'])
    assert result.exit_code == 0
    assert 'no matches' in result.output
