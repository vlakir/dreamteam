"""T036 — worktree placement and lifecycle (`dt worktree`).

Two layers, mirroring T035: the pure, git-free core in `dreamteam.dt.worktrees`
(fabricated `WorktreeInfo` + task dicts, no git) and the Typer wrappers in
`dreamteam.worktree_cli` driven against a *real* temporary git repository — that
end-to-end path is what exercises the git helpers added to `dreamteam.dt.paths`
(`list_worktrees`, `branch_merged`, `worktree_dirty`, `remove_worktree`, …).
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from dreamteam.cli import app
from dreamteam.dt.model import Task, TaskStatus, save_task
from dreamteam.dt.paths import (
    DtHomeError,
    WorktreeInfo,
    _parse_worktree_porcelain,
    branch_merged,
    default_base_branch,
    ensure_store,
    store_dir,
    worktrees_dir,
)
from dreamteam.dt.tasks import TaskError
from dreamteam.dt.worktrees import (
    classify_arg,
    is_managed,
    match_task_id,
    partition_worktrees,
    prune_plan,
    resolve_branch,
    resolve_path,
)

if TYPE_CHECKING:
    from pathlib import Path


# --------------------------------------------------------------------------- #
# helpers                                                                      #
# --------------------------------------------------------------------------- #


def _wt(
    path: Path,
    branch: str | None = None,
    *,
    bare: bool = False,
    detached: bool = False,
    head: str | None = 'abc123',
) -> WorktreeInfo:
    return WorktreeInfo(
        path=path, branch=branch, head=head, bare=bare, detached=detached
    )


def _task(
    task_id: str,
    *,
    status: TaskStatus = 'todo',
    branch: str | None = None,
) -> Task:
    return Task(id=task_id, title=f'task {task_id}', status=status, branch=branch)


# --------------------------------------------------------------------------- #
# _parse_worktree_porcelain                                                    #
# --------------------------------------------------------------------------- #


def test_parse_porcelain_branch_detached_bare() -> None:
    porcelain = (
        'worktree /repo/main\n'
        'HEAD 1111111\n'
        'branch refs/heads/main\n'
        '\n'
        'worktree /repo.dt/worktrees/T034-x\n'
        'HEAD 2222222\n'
        'branch refs/heads/T034-x\n'
        '\n'
        'worktree /repo/detached\n'
        'HEAD 3333333\n'
        'detached\n'
        '\n'
        'worktree /repo/bare\n'
        'bare\n'
    )
    infos = _parse_worktree_porcelain(porcelain)
    assert [i.branch for i in infos] == ['main', 'T034-x', None, None]
    assert infos[2].detached is True
    assert infos[3].bare is True and infos[3].head is None


def test_parse_porcelain_empty() -> None:
    assert _parse_worktree_porcelain('') == []


# --------------------------------------------------------------------------- #
# classify_arg / resolve_branch / resolve_path / is_managed                    #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ('arg', 'expected'),
    [
        ('T034', True),
        ('T1000', True),
        ('T034-cursor', False),
        ('feature/x', False),
        ('T۰۳۴', False),  # unicode digits are not an ASCII task ID
    ],
)
def test_classify_arg(arg: str, expected: bool) -> None:
    assert classify_arg(arg) is expected


def test_resolve_branch_literal_passthrough(tmp_path: Path) -> None:
    assert resolve_branch(tmp_path, 'feature/login') == 'feature/login'


def test_resolve_branch_task_id_reads_branch_field(tmp_path: Path) -> None:
    tasks = tmp_path / 'tasks'
    tasks.mkdir()
    save_task(tasks / 'T034.md', _task('T034', branch='T034-cursor'))
    assert resolve_branch(tmp_path, 'T034') == 'T034-cursor'


def test_resolve_branch_task_id_without_branch_errors(tmp_path: Path) -> None:
    tasks = tmp_path / 'tasks'
    tasks.mkdir()
    save_task(tasks / 'T034.md', _task('T034'))
    with pytest.raises(TaskError, match='has no branch yet'):
        resolve_branch(tmp_path, 'T034')


def test_resolve_branch_task_id_missing_errors(tmp_path: Path) -> None:
    (tmp_path / 'tasks').mkdir()
    with pytest.raises(TaskError, match='not found'):
        resolve_branch(tmp_path, 'T999')


def test_resolve_path_actual_wins(tmp_path: Path) -> None:
    actual = tmp_path / 'somewhere' / 'T034-x'
    worktrees = [_wt(actual, 'T034-x')]
    path, exists = resolve_path(tmp_path / 'worktrees', 'T034-x', worktrees)
    assert (path, exists) == (actual, True)


def test_resolve_path_computed_when_absent(tmp_path: Path) -> None:
    root = tmp_path / 'worktrees'
    path, exists = resolve_path(root, 'T034-x', [])
    assert (path, exists) == (root / 'T034-x', False)


def test_resolve_path_allows_slash_branch(tmp_path: Path) -> None:
    root = tmp_path / 'worktrees'
    path, exists = resolve_path(root, 'feature/login', [])
    assert (path, exists) == (root / 'feature' / 'login', False)


@pytest.mark.parametrize('escape', ['..', '../x', '/tmp/x'])
def test_resolve_path_rejects_escape(tmp_path: Path, escape: str) -> None:
    with pytest.raises(TaskError, match='outside the managed root'):
        resolve_path(tmp_path / 'worktrees', escape, [])


def test_is_managed(tmp_path: Path) -> None:
    root = tmp_path / 'worktrees'
    assert is_managed(root / 'T034-x', root) is True
    assert is_managed(tmp_path / 'elsewhere', root) is False


# --------------------------------------------------------------------------- #
# match_task_id                                                                #
# --------------------------------------------------------------------------- #


def test_match_by_branch_field() -> None:
    tasks = {'T034': _task('T034', branch='feat-cursor')}
    assert match_task_id('feat-cursor', tasks) == 'T034'


def test_match_by_prefix_fallback() -> None:
    tasks = {'T034': _task('T034')}  # no branch field set
    assert match_task_id('T034-cursor', tasks) == 'T034'


def test_match_prefix_ignored_when_no_such_task() -> None:
    assert match_task_id('T099-x', {'T034': _task('T034')}) is None


def test_match_detached_never_matches() -> None:
    assert match_task_id(None, {'T034': _task('T034')}) is None


# --------------------------------------------------------------------------- #
# partition_worktrees                                                          #
# --------------------------------------------------------------------------- #


def test_partition_matched_orphan_and_bystander(tmp_path: Path) -> None:
    root = tmp_path / 'worktrees'
    tasks = {'T034': _task('T034', branch='T034-x')}
    matched_wt = _wt(root / 'T034-x', 'T034-x')
    orphan_wt = _wt(root / 'T099-gone', 'T099-gone')  # managed, no task
    bystander = _wt(tmp_path / 'main', 'main')  # not managed, no task
    matched, orphaned = partition_worktrees(
        [matched_wt, orphan_wt, bystander], tasks, root
    )
    assert [m.task_id for m in matched] == ['T034']
    assert orphaned == [orphan_wt]


# --------------------------------------------------------------------------- #
# prune_plan                                                                   #
# --------------------------------------------------------------------------- #


def test_prune_plan_removable(tmp_path: Path) -> None:
    root = tmp_path / 'worktrees'
    wt = _wt(root / 'T034-x', 'T034-x')
    tasks = {'T034': _task('T034', status='done', branch='T034-x')}
    removable, skipped = prune_plan(
        [wt], tasks, root, {'T034-x': True}, {wt.path: False}
    )
    assert [e.task_id for e in removable] == ['T034']
    assert skipped == []


def test_prune_plan_dropped_is_removable(tmp_path: Path) -> None:
    root = tmp_path / 'worktrees'
    wt = _wt(root / 'T034-x', 'T034-x')
    tasks = {'T034': _task('T034', status='dropped', branch='T034-x')}
    removable, _ = prune_plan([wt], tasks, root, {'T034-x': True}, {wt.path: False})
    assert len(removable) == 1


def test_prune_plan_collects_all_reasons(tmp_path: Path) -> None:
    root = tmp_path / 'worktrees'
    wt = _wt(root / 'T034-x', 'T034-x')
    tasks = {'T034': _task('T034', status='doing', branch='T034-x')}
    # not done/dropped, not merged, and dirty — every guard fails at once.
    removable, skipped = prune_plan(
        [wt], tasks, root, {'T034-x': False}, {wt.path: True}
    )
    assert removable == []
    reasons = skipped[0].reasons
    assert any('doing' in r for r in reasons)
    assert any('not merged' in r for r in reasons)
    assert any('uncommitted' in r for r in reasons)


def test_prune_plan_skips_orphan_and_detached(tmp_path: Path) -> None:
    root = tmp_path / 'worktrees'
    orphan = _wt(root / 'T099-x', 'T099-x')  # managed, no task
    detached = _wt(root / 'det', None, detached=True)
    removable, skipped = prune_plan(
        [orphan, detached], {}, root, {'T099-x': True}, {}
    )
    assert removable == []
    assert {s.info.path for s in skipped} == {orphan.path, detached.path}
    assert any('no matching task' in r for r in skipped[0].reasons)


def test_prune_plan_ignores_non_managed(tmp_path: Path) -> None:
    root = tmp_path / 'worktrees'
    outside = _wt(tmp_path / 'elsewhere' / 'T034-x', 'T034-x')
    tasks = {'T034': _task('T034', status='done', branch='T034-x')}
    removable, skipped = prune_plan([outside], tasks, root, {'T034-x': True}, {})
    assert (removable, skipped) == ([], [])


# --------------------------------------------------------------------------- #
# CLI layer — real temporary git repository                                    #
# --------------------------------------------------------------------------- #


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ['git', *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
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
    monkeypatch.chdir(root)
    # Pre-create the store so the one-shot "created …" stderr line (emitted on
    # first creation) does not land in the CliRunner's merged output and trip
    # the JSON/equality assertions below.
    ensure_store()
    return root


def _write_task(status: TaskStatus, branch: str) -> str:
    """Create a task record in the resolved store; return its ID."""
    ensure_store()
    task_id = 'T034'
    save_task(
        store_dir() / 'tasks' / f'{task_id}.md',
        _task(task_id, status=status, branch=branch),
    )
    return task_id


def _add_worktree(repo: Path, branch: str, *, commit: bool = False) -> Path:
    """Add a managed worktree on a fresh `branch`; optionally give it a commit."""
    path = worktrees_dir() / branch
    _git(repo, 'worktree', 'add', '-b', branch, str(path))
    if commit:
        (path / 'change.txt').write_text('work\n', encoding='utf-8')
        _git(path, 'add', '.')
        _git(path, 'commit', '-m', 'wip')
    return path


def test_cli_root(repo: Path) -> None:
    result = CliRunner().invoke(app, ['worktree', 'root'])
    assert result.exit_code == 0
    assert result.output.strip() == str(repo.parent / 'proj.dt' / 'worktrees')


def test_cli_root_json(repo: Path) -> None:
    result = CliRunner().invoke(app, ['worktree', 'root', '--json'])
    assert json.loads(result.output)['root'].endswith('proj.dt/worktrees')


def test_cli_path_computed_for_branch(repo: Path) -> None:
    result = CliRunner().invoke(app, ['worktree', 'path', 'T034-cursor', '--json'])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload['exists'] is False
    assert payload['path'].endswith('proj.dt/worktrees/T034-cursor')


def test_cli_path_human(repo: Path) -> None:
    result = CliRunner().invoke(app, ['worktree', 'path', 'T034-cursor'])
    assert result.exit_code == 0
    assert result.output.strip().endswith('proj.dt/worktrees/T034-cursor')


def test_cli_path_actual_for_existing(repo: Path) -> None:
    path = _add_worktree(repo, 'T034-live')
    result = CliRunner().invoke(app, ['worktree', 'path', 'T034-live', '--json'])
    payload = json.loads(result.output)
    assert payload['exists'] is True
    assert payload['path'] == str(path)


def test_cli_path_task_id_without_branch_fails(repo: Path) -> None:
    _write_task('todo', branch='')  # branch empty
    result = CliRunner().invoke(app, ['worktree', 'path', 'T034'])
    assert result.exit_code == 1
    assert 'has no branch' in result.output


def test_cli_list_matched_and_orphan(repo: Path) -> None:
    _write_task('doing', branch='T034-live')
    _add_worktree(repo, 'T034-live')  # matches task by branch field
    _add_worktree(repo, 'T099-gone')  # managed, no task -> orphan
    result = CliRunner().invoke(app, ['worktree', 'list', '--json'])
    payload = json.loads(result.output)
    assert [m['task'] for m in payload['matched']] == ['T034']
    assert [o['branch'] for o in payload['orphaned']] == ['T099-gone']
    # the main worktree (branch `main`, not managed) is a bystander, unlisted.
    assert all(m['branch'] != 'main' for m in payload['matched'])


def test_cli_list_human(repo: Path) -> None:
    _write_task('doing', branch='T034-live')
    _add_worktree(repo, 'T034-live')
    _add_worktree(repo, 'T099-gone')
    result = CliRunner().invoke(app, ['worktree', 'list'])
    assert result.exit_code == 0
    assert 'T034  [doing]  T034-live' in result.output
    assert 'orphaned  T099-gone' in result.output


def test_cli_prune_removes_done_merged_clean(repo: Path) -> None:
    branch = 'T034-live'
    _write_task('done', branch=branch)
    path = _add_worktree(repo, branch)  # no commit -> ancestor of main -> merged
    result = CliRunner().invoke(app, ['worktree', 'prune', '--json'])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert [r['task'] for r in payload['removed']] == ['T034']
    assert payload['removed'][0]['branch_deleted'] is True
    assert not path.exists()
    # branch is gone too (safe-deleted).
    assert branch not in _git(repo, 'branch', '--format=%(refname:short)').split()


def test_cli_prune_skips_unmerged(repo: Path) -> None:
    branch = 'T034-wip'
    _write_task('done', branch=branch)
    path = _add_worktree(repo, branch, commit=True)  # a commit -> not ancestor
    result = CliRunner().invoke(app, ['worktree', 'prune', '--json'])
    payload = json.loads(result.output)
    assert payload['removed'] == []
    assert any('not merged' in r for r in payload['skipped'][0]['reasons'])
    assert path.exists()


def test_cli_prune_skips_dirty(repo: Path) -> None:
    branch = 'T034-dirty'
    _write_task('done', branch=branch)
    path = _add_worktree(repo, branch)
    (path / 'scratch.txt').write_text('uncommitted\n', encoding='utf-8')
    result = CliRunner().invoke(app, ['worktree', 'prune', '--json'])
    payload = json.loads(result.output)
    assert payload['removed'] == []
    assert any('uncommitted' in r for r in payload['skipped'][0]['reasons'])
    assert path.exists()


def test_cli_prune_human_removed(repo: Path) -> None:
    branch = 'T034-live'
    _write_task('done', branch=branch)
    path = _add_worktree(repo, branch)
    result = CliRunner().invoke(app, ['worktree', 'prune'])
    assert result.exit_code == 0
    assert f'removed  T034  {branch}' in result.output
    assert not path.exists()


def test_cli_prune_human_skip(repo: Path) -> None:
    branch = 'T034-wip'
    _write_task('done', branch=branch)
    _add_worktree(repo, branch, commit=True)
    result = CliRunner().invoke(app, ['worktree', 'prune'])
    assert f'skipped  {branch}' in result.output
    assert 'not merged' in result.output


def test_cli_prune_nothing(repo: Path) -> None:
    result = CliRunner().invoke(app, ['worktree', 'prune'])
    assert result.exit_code == 0
    assert 'nothing to prune' in result.output


def test_cli_list_empty(repo: Path) -> None:
    result = CliRunner().invoke(app, ['worktree', 'list'])
    assert 'no task worktrees' in result.output


# --------------------------------------------------------------------------- #
# git helpers directly                                                         #
# --------------------------------------------------------------------------- #


def test_default_base_branch_no_remote(repo: Path) -> None:
    assert default_base_branch() == 'main'


def test_branch_merged_true_for_ancestor(repo: Path) -> None:
    _git(repo, 'branch', 'sidecar')  # at main's commit -> ancestor
    assert branch_merged('sidecar', 'main') is True


def test_branch_merged_false_for_diverged(repo: Path) -> None:
    _git(repo, 'checkout', '-b', 'ahead')
    (repo / 'more.txt').write_text('x\n', encoding='utf-8')
    _git(repo, 'add', '.')
    _git(repo, 'commit', '-m', 'ahead')
    _git(repo, 'checkout', 'main')
    assert branch_merged('ahead', 'main') is False


def test_branch_merged_raises_on_missing_ref(repo: Path) -> None:
    # A non-existent branch makes `merge-base --is-ancestor` fail (rc 128) — a
    # real git error, surfaced rather than masked as "not merged".
    with pytest.raises(DtHomeError, match='cannot determine whether'):
        branch_merged('no-such-branch', 'main')
