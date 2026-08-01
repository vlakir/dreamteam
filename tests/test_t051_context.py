"""T051 — session orientation (`dt context`).

Two layers: the pure, git-free core in `dreamteam.dt.context` (resolution,
model building and rendering against explicit inputs) and the Typer wrapper in
`dreamteam.context_cli`, driven against a *real* temporary git repository so the
branch/worktree resolution, the main-copy BACKLOG divergence and the never-fail
`--hook` path are exercised end to end.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dreamteam.cli import app
from dreamteam.dt.backlog import BEGIN_MARKER, END_MARKER, BacklogDivergence
from dreamteam.dt.context import (
    ContextModel,
    build_context,
    context_json,
    render_hook_context,
    render_human,
    resolve_task_id,
)
from dreamteam.dt.model import Task, TaskStatus, save_task
from dreamteam.dt.paths import WorktreeInfo, ensure_store, store_dir


def _write(
    store: Path,
    task_id: str,
    *,
    status: TaskStatus = 'todo',
    title: str | None = None,
    deps: list[str] | None = None,
    branch: str | None = None,
    body: str = '',
) -> None:
    task = Task(
        id=task_id,
        title=title or f'task {task_id}',
        status=status,
        deps=deps or [],
        branch=branch,
    )
    task.body = body
    save_task(store / 'tasks' / f'{task_id}.md', task)


@pytest.fixture
def store(tmp_path: Path) -> Path:
    root = tmp_path / 'store'
    (root / 'tasks').mkdir(parents=True)
    return root


# --------------------------------------------------------------------------- #
# resolve_task_id — the shared resolution order (§309)                         #
# --------------------------------------------------------------------------- #


def test_resolve_prefers_dt_task() -> None:
    assert resolve_task_id(dt_task='T005', branch='T001-x', bound='T002') == 'T005'


def test_resolve_falls_to_branch() -> None:
    assert resolve_task_id(dt_task=None, branch='T001-slug', bound='T002') == 'T001'


def test_resolve_branch_exact() -> None:
    assert resolve_task_id(dt_task=None, branch='T001', bound=None) == 'T001'


def test_resolve_falls_to_bound() -> None:
    assert resolve_task_id(dt_task=None, branch='main', bound='T002') == 'T002'


def test_resolve_unbound() -> None:
    assert resolve_task_id(dt_task=None, branch='main', bound=None) is None


def test_resolve_skips_invalid_dt_task() -> None:
    # garbage DT_TASK is ignored, resolution continues to the branch
    assert resolve_task_id(dt_task='nope', branch='T001-x', bound=None) == 'T001'


# --------------------------------------------------------------------------- #
# build_context                                                                #
# --------------------------------------------------------------------------- #


def test_build_blockers_are_unfinished_deps(store: Path) -> None:
    _write(store, 'T001', deps=['T002', 'T003'])
    _write(store, 'T002', status='done')
    _write(store, 'T003', status='doing')
    model = build_context(
        store, resolved_id='T001', cwd=None, worktrees=[], main_backlog_text=''
    )
    assert model.task is not None
    assert [b.id for b in model.blockers] == ['T003']  # done dep excluded


def test_build_dangling_id_is_unbound(store: Path) -> None:
    _write(store, 'T009', status='doing')
    model = build_context(
        store, resolved_id='T099', cwd=None, worktrees=[], main_backlog_text=''
    )
    assert model.task is None
    assert model.dangling_id == 'T099'
    assert [t.id for t in model.doing] == ['T009']  # doing listed for unbound


def test_build_cwd_mismatch(store: Path, tmp_path: Path) -> None:
    _write(store, 'T001', status='doing', branch='T001-x')
    wt = tmp_path / 'wt'
    worktrees = [
        WorktreeInfo(path=wt, branch='T001-x', head='abc', bare=False, detached=False)
    ]
    model = build_context(
        store,
        resolved_id='T001',
        cwd=tmp_path / 'other',
        worktrees=worktrees,
        main_backlog_text='',
    )
    assert model.cwd_mismatch is True
    assert model.task_worktree == wt


def test_build_no_mismatch_when_in_worktree(store: Path, tmp_path: Path) -> None:
    _write(store, 'T001', status='doing', branch='T001-x')
    wt = tmp_path / 'wt'
    worktrees = [
        WorktreeInfo(path=wt, branch='T001-x', head='abc', bare=False, detached=False)
    ]
    model = build_context(
        store, resolved_id='T001', cwd=wt, worktrees=worktrees, main_backlog_text=''
    )
    assert model.cwd_mismatch is False


def test_build_divergence_needs_managed_block(store: Path) -> None:
    _write(store, 'T001', status='todo')
    # BACKLOG with a managed block that omits T001 → divergence added=[T001]
    with_block = f'# Backlog\n{BEGIN_MARKER}\n{END_MARKER}\n'
    model = build_context(
        store, resolved_id=None, cwd=None, worktrees=[], main_backlog_text=with_block
    )
    assert model.divergence is not None
    assert model.divergence.added == ['T001']


def test_build_divergence_skipped_without_block(store: Path) -> None:
    _write(store, 'T001', status='todo')
    # no managed block → project has not adopted `dt backlog sync` → no divergence
    model = build_context(
        store,
        resolved_id=None,
        cwd=None,
        worktrees=[],
        main_backlog_text='# Backlog\n- **T001** — prose only\n',
    )
    assert model.divergence is None


# --------------------------------------------------------------------------- #
# rendering                                                                    #
# --------------------------------------------------------------------------- #


def _bound_model(
    *,
    task: Task | None = None,
    blockers: list[Task] | None = None,
    divergence: BacklogDivergence | None = None,
    task_worktree: Path | None = None,
    cwd_mismatch: bool = False,
) -> ContextModel:
    """A bound ContextModel with sensible defaults; fields overridable per test."""
    return ContextModel(
        task=task
        or Task(id='T001', title='Заголовок', status='doing', branch='T001-x'),
        blockers=blockers or [],
        divergence=divergence,
        task_worktree=task_worktree,
        cwd=None,
        cwd_mismatch=cwd_mismatch,
        doing=[],
        dangling_id=None,
    )


def test_render_human_bound() -> None:
    text = render_human(_bound_model())
    assert 'T001 [doing] Заголовок' in text
    assert 'ветка: T001-x' in text


def test_render_human_unbound_lists_doing() -> None:
    doing = [Task(id='T007', title='в работе', status='doing')]
    model = ContextModel(
        task=None,
        blockers=[],
        divergence=None,
        task_worktree=None,
        cwd=None,
        cwd_mismatch=False,
        doing=doing,
        dangling_id=None,
    )
    text = render_human(model)
    assert 'непривязанная сессия' in text
    assert 'T007 в работе' in text


def test_render_human_full() -> None:
    task = Task(
        id='T001',
        title='Заголовок',
        status='doing',
        branch='T001-x',
        spec='specs/T001-x/spec.md',
        pr=42,
    )
    task.body = '## Handover\n- сделано: старт\n'
    model = _bound_model(
        task=task,
        blockers=[Task(id='T003', title='dep', status='doing')],
        divergence=BacklogDivergence(added=['T002'], removed=[]),
        task_worktree=Path('/wt/T001'),
        cwd_mismatch=True,
    )
    text = render_human(model)
    assert 'спека: specs/T001-x/spec.md' in text
    assert 'PR: #42' in text
    assert 'блокеры: T003 [doing]' in text
    assert '── Handover ──' in text
    assert '- сделано: старт' in text
    assert 'задача T001 живёт в /wt/T001' in text
    assert 'BACKLOG.md отстаёт: +1 заведено, -0 завершена' in text


def test_render_human_dangling() -> None:
    model = ContextModel(
        task=None,
        blockers=[],
        divergence=None,
        task_worktree=None,
        cwd=None,
        cwd_mismatch=False,
        doing=[],
        dangling_id='T099',
    )
    assert 'T099 не в store' in render_human(model)


def test_render_json_shape() -> None:
    payload = context_json(_bound_model())
    assert payload['unbound'] is False
    task = payload['task']
    assert isinstance(task, dict)
    assert task['id'] == 'T001'
    assert payload['backlog_divergence'] is None


def test_render_hook_truncates_to_budget() -> None:
    task = Task(id='T001', title='x' * 5000, status='doing')
    model = _bound_model(task=task)
    text = render_hook_context(model)
    assert len(text) <= 2000
    assert text.endswith('…')


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
    _git(root, 'add', '.')
    _git(root, 'commit', '-m', 'init')
    monkeypatch.delenv('DT_HOME', raising=False)
    monkeypatch.delenv('DT_TASK', raising=False)
    monkeypatch.chdir(root)
    ensure_store()
    return root


def test_cli_context_bound_via_branch(repo: Path) -> None:
    _write(store_dir(), 'T001', status='doing', title='Первая', branch='T001-x')
    _git(repo, 'checkout', '-q', '-b', 'T001-x')
    result = CliRunner().invoke(app, ['context'])
    assert result.exit_code == 0, result.output
    assert 'T001 [doing] Первая' in result.output
    # context.line refreshed for the current worktree
    slug_dirs = list((store_dir() / 'by-worktree').iterdir())
    assert slug_dirs
    line = (slug_dirs[0] / 'context.line').read_text(encoding='utf-8')
    assert 'T001 [doing] Первая' in line


def test_cli_context_unbound_on_main(repo: Path) -> None:
    _write(store_dir(), 'T007', status='doing', title='идёт')
    result = CliRunner().invoke(app, ['context'])
    assert result.exit_code == 0, result.output
    assert 'непривязанная сессия' in result.output
    assert 'T007 идёт' in result.output


def test_cli_context_dt_task_override_json(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(store_dir(), 'T001', status='doing', title='Первая', branch='T001-x')
    monkeypatch.setenv('DT_TASK', 'T001')
    result = CliRunner().invoke(app, ['context', '--json'])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload['task']['id'] == 'T001'
    assert payload['unbound'] is False


def test_cli_context_cwd_mismatch_line(repo: Path) -> None:
    # task lives in a separate worktree; run context from the main copy via DT_TASK
    wt = repo.parent / 'wt-T001'
    _git(repo, 'worktree', 'add', '-q', '-b', 'T001-x', str(wt))
    _write(store_dir(), 'T001', status='doing', title='Первая', branch='T001-x')
    result = CliRunner().invoke(app, ['context'], env={'DT_TASK': 'T001'})
    assert result.exit_code == 0, result.output
    assert 'живёт в' in result.output
    assert str(wt) in result.output


def test_cli_context_hook_always_exits_zero(repo: Path) -> None:
    _write(store_dir(), 'T001', status='doing', branch='T001-x')
    _git(repo, 'checkout', '-q', '-b', 'T001-x')
    result = CliRunner().invoke(app, ['context', '--hook'])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload['hookSpecificOutput']['hookEventName'] == 'SessionStart'
    assert 'T001' in payload['hookSpecificOutput']['additionalContext']


def test_cli_context_hook_outside_git_is_silent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path / 'nogit'
    outside.mkdir()
    monkeypatch.delenv('DT_HOME', raising=False)
    monkeypatch.delenv('DT_TASK', raising=False)
    monkeypatch.chdir(outside)
    result = CliRunner().invoke(app, ['context', '--hook'])
    # a hook never blocks: exit 0 even when the store can't be resolved
    assert result.exit_code == 0
    assert result.output.strip() == ''


def test_cli_context_outside_git_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # normal mode (not --hook) surfaces a clean exit 1 when the store is unresolvable
    outside = tmp_path / 'nogit'
    outside.mkdir()
    monkeypatch.delenv('DT_HOME', raising=False)
    monkeypatch.delenv('DT_TASK', raising=False)
    monkeypatch.chdir(outside)
    result = CliRunner().invoke(app, ['context'])
    assert result.exit_code == 1
    assert 'dt context:' in result.output


def test_cli_context_divergence_line(repo: Path) -> None:
    _write(store_dir(), 'T001', status='todo', title='Первая')
    # main-copy BACKLOG has a managed block that omits T001 → divergence
    (repo / 'BACKLOG.md').write_text(
        f'# Backlog\n{BEGIN_MARKER}\n{END_MARKER}\n', encoding='utf-8'
    )
    result = CliRunner().invoke(app, ['context'])
    assert result.exit_code == 0, result.output
    assert 'BACKLOG.md отстаёт: +1 заведено' in result.output
