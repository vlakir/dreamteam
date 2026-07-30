"""T035 — task-graph validation and readiness (`dt task check` / `ready`).

Two layers: the pure functions in `dreamteam.dt.tasks` (exercised against an
explicit temp store, git context passed in directly) and the Typer wrappers in
`dreamteam.task_cli` (via `CliRunner` with `DT_HOME` -> `tmp_path`). The git
context helper `git_context` is covered both on its not-a-repo degrade path and
implicitly through the CLI (which runs inside this repo).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from dreamteam.cli import app
from dreamteam.dt.model import Task, TaskStatus, save_task
from dreamteam.dt.paths import git_context
from dreamteam.dt.tasks import (
    TaskError,
    check_tasks,
    load_all_tasks,
    ready_tasks,
    show_task,
)

if TYPE_CHECKING:
    from pathlib import Path

_UNICODE_DIGIT_ID = 'T۰۰۱'  # 'T۰۰۱' — Arabic-Indic digits


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


def _write(
    store: Path,
    task_id: str,
    *,
    status: TaskStatus = 'todo',
    deps: list[str] | None = None,
    parent: str | None = None,
    spec: str | None = None,
    branch: str | None = None,
) -> None:
    task = Task(
        id=task_id,
        title=f'task {task_id}',
        status=status,
        deps=deps or [],
        parent=parent,
        spec=spec,
        branch=branch,
    )
    save_task(store / 'tasks' / f'{task_id}.md', task)


# --------------------------------------------------------------------------- #
# load_all_tasks                                                              #
# --------------------------------------------------------------------------- #


def test_load_all_tasks_ignores_stray_files(store: Path) -> None:
    _write(store, 'T001')
    _write(store, 'T002')
    (store / 'tasks' / 'README.md').write_text('notes\n', encoding='utf-8')
    (store / 'tasks' / 'T99.md').write_text('too short\n', encoding='utf-8')
    assert set(load_all_tasks(store)) == {'T001', 'T002'}


def test_load_all_tasks_missing_dir_is_empty(tmp_path: Path) -> None:
    assert load_all_tasks(tmp_path / 'nope' / 'store') == {}


# --------------------------------------------------------------------------- #
# check_tasks — dangling references                                           #
# --------------------------------------------------------------------------- #


def test_check_clean_graph_has_no_issues(store: Path) -> None:
    _write(store, 'T001', status='done')
    _write(store, 'T002', deps=['T001'], parent='T001')
    assert check_tasks(store) == []


def test_check_dangling_dep_is_error(store: Path) -> None:
    _write(store, 'T001', deps=['T999'])
    issues = check_tasks(store)
    assert [(i.task_id, i.kind) for i in issues] == [('T001', 'error')]
    assert 'unknown task' in issues[0].message


def test_check_dangling_parent_is_error(store: Path) -> None:
    _write(store, 'T001', parent='T999')
    issues = check_tasks(store)
    assert issues[0].task_id == 'T001'
    assert issues[0].is_error
    assert "parent 'T999'" in issues[0].message


# --------------------------------------------------------------------------- #
# check_tasks — cycles                                                        #
# --------------------------------------------------------------------------- #


def test_check_detects_mutual_cycle(store: Path) -> None:
    _write(store, 'T001', deps=['T002'])
    _write(store, 'T002', deps=['T001'])
    issues = check_tasks(store)
    cycles = [i for i in issues if 'cycle' in i.message]
    assert len(cycles) == 1
    assert cycles[0].task_id == 'T001'  # anchored to the smallest ID
    assert cycles[0].is_error


def test_check_detects_self_cycle(store: Path) -> None:
    _write(store, 'T001', deps=['T001'])
    issues = check_tasks(store)
    assert any('cycle: T001 -> T001' in i.message for i in issues)


def test_check_reports_each_cycle_once(store: Path) -> None:
    # Two independent 2-cycles; each must be reported exactly once.
    _write(store, 'T001', deps=['T002'])
    _write(store, 'T002', deps=['T001'])
    _write(store, 'T003', deps=['T004'])
    _write(store, 'T004', deps=['T003'])
    cycles = [i for i in check_tasks(store) if 'cycle' in i.message]
    assert sorted(i.task_id for i in cycles) == ['T001', 'T003']


# --------------------------------------------------------------------------- #
# check_tasks — spec files (soft, git-aware escalation)                       #
# --------------------------------------------------------------------------- #


def test_check_spec_present_is_ok(store: Path, tmp_path: Path) -> None:
    (tmp_path / 'specs').mkdir()
    (tmp_path / 'specs' / 'x.md').write_text('spec\n', encoding='utf-8')
    _write(store, 'T001', spec='specs/x.md')
    assert check_tasks(store, repo_root=tmp_path) == []


def test_check_spec_missing_off_branch_is_warning(store: Path, tmp_path: Path) -> None:
    _write(store, 'T001', spec='specs/x.md', branch='T001-x')
    issues = check_tasks(store, repo_root=tmp_path, current_branch='main')
    assert [(i.task_id, i.kind) for i in issues] == [('T001', 'warning')]


def test_check_spec_missing_on_task_branch_is_error(store: Path, tmp_path: Path) -> None:
    _write(store, 'T001', spec='specs/x.md', branch='T001-x')
    issues = check_tasks(store, repo_root=tmp_path, current_branch='T001-x')
    assert issues[0].kind == 'error'
    assert 'checked out' in issues[0].message


def test_check_spec_missing_no_repo_root_is_skipped(store: Path) -> None:
    _write(store, 'T001', spec='specs/x.md', branch='T001-x')
    assert check_tasks(store, repo_root=None, current_branch='T001-x') == []


def test_check_spec_missing_detached_head_is_warning(store: Path, tmp_path: Path) -> None:
    # No current branch (detached HEAD): missing spec never escalates.
    _write(store, 'T001', spec='specs/x.md', branch='T001-x')
    issues = check_tasks(store, repo_root=tmp_path, current_branch=None)
    assert issues[0].kind == 'warning'


def test_check_spec_absolute_path_is_not_present(store: Path, tmp_path: Path) -> None:
    # An absolute spec pointing at a real file outside the repo must not satisfy
    # the check: `repo_root / absolute` drops repo_root (a CI-gate false
    # negative). It falls through to the missing-spec warning.
    repo_root = tmp_path / 'repo'
    repo_root.mkdir()
    outside = tmp_path / 'evil.md'
    outside.write_text('not a spec\n', encoding='utf-8')
    _write(store, 'T001', spec=str(outside))
    issues = check_tasks(store, repo_root=repo_root, current_branch='main')
    assert [(i.task_id, i.kind) for i in issues] == [('T001', 'warning')]


def test_check_spec_escaping_path_is_not_present(store: Path, tmp_path: Path) -> None:
    # A `..` spec escaping repo_root to a real file must not satisfy the check.
    repo_root = tmp_path / 'repo'
    repo_root.mkdir()
    (tmp_path / 'evil.md').write_text('x\n', encoding='utf-8')
    _write(store, 'T001', spec='../evil.md')
    issues = check_tasks(store, repo_root=repo_root)
    assert issues and issues[0].kind == 'warning'


# --------------------------------------------------------------------------- #
# ready_tasks                                                                 #
# --------------------------------------------------------------------------- #


def test_ready_lists_todo_with_all_deps_done(store: Path) -> None:
    _write(store, 'T001', status='done')
    _write(store, 'T002', status='todo', deps=['T001'])  # ready
    _write(store, 'T003', status='todo')  # ready (no deps)
    _write(store, 'T004', status='todo', deps=['T005'])  # blocked (T005 not done)
    _write(store, 'T005', status='doing')  # not todo -> excluded
    _write(store, 'T006', status='todo', deps=['T999'])  # dangling dep -> not ready
    assert [t.id for t in ready_tasks(store)] == ['T002', 'T003']


def test_ready_empty_store(store: Path) -> None:
    assert ready_tasks(store) == []


# --------------------------------------------------------------------------- #
# ID micro-nit — unicode digits rejected                                      #
# --------------------------------------------------------------------------- #


def test_unicode_digit_id_rejected_pure(store: Path) -> None:
    with pytest.raises(TaskError, match='invalid'):
        show_task(store, _UNICODE_DIGIT_ID)


def test_unicode_digit_id_rejected_cli(cli: CliRunner) -> None:
    result = cli.invoke(app, ['task', 'show', _UNICODE_DIGIT_ID])
    assert result.exit_code == 1
    assert 'invalid' in result.output


# --------------------------------------------------------------------------- #
# git_context                                                                 #
# --------------------------------------------------------------------------- #


def test_git_context_outside_repo_degrades(tmp_path: Path) -> None:
    root, branch = git_context(cwd=tmp_path)
    assert (root, branch) == (None, None)


# --------------------------------------------------------------------------- #
# CLI end-to-end (CliRunner, DT_HOME -> tmp_path)                              #
# --------------------------------------------------------------------------- #


def test_cli_check_ok_on_empty_store(cli: CliRunner) -> None:
    result = cli.invoke(app, ['task', 'check'])
    assert result.exit_code == 0
    assert 'check: ok' in result.output


def test_cli_check_error_exits_nonzero(cli: CliRunner, tmp_path: Path) -> None:
    cli.invoke(app, ['task', 'new', 'seed'])  # creates the store + T001
    tasks_dir = tmp_path / 'home' / 'store' / 'tasks'
    save_task(
        tasks_dir / 'T002.md',
        Task(id='T002', title='bad', deps=['T999']),
    )
    result = cli.invoke(app, ['task', 'check'])
    assert result.exit_code == 1
    assert 'unknown task' in result.output


def test_cli_check_json(cli: CliRunner, tmp_path: Path) -> None:
    cli.invoke(app, ['task', 'new', 'seed'])
    tasks_dir = tmp_path / 'home' / 'store' / 'tasks'
    save_task(tasks_dir / 'T002.md', Task(id='T002', title='bad', parent='T999'))
    result = cli.invoke(app, ['task', 'check', '--json'])
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload['errors'][0]['task'] == 'T002'
    assert payload['warnings'] == []


def test_cli_ready_lists_and_json(cli: CliRunner) -> None:
    cli.invoke(app, ['task', 'new', 'a'])  # T001
    cli.invoke(app, ['task', 'move', 'T001', 'done'])
    cli.invoke(app, ['task', 'new', 'b', '--deps', 'T001'])  # T002 ready

    human = cli.invoke(app, ['task', 'ready'])
    assert human.exit_code == 0
    assert 'T002' in human.output
    assert 'T001' not in human.output  # done, not todo

    as_json = cli.invoke(app, ['task', 'ready', '--json'])
    payload = json.loads(as_json.output)
    assert [t['id'] for t in payload] == ['T002']


def test_cli_ready_empty(cli: CliRunner) -> None:
    result = cli.invoke(app, ['task', 'ready'])
    assert result.exit_code == 0
    assert 'no ready tasks' in result.output
