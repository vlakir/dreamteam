"""
``dt worktree`` CLI: ``root`` / ``path`` / ``list`` / ``prune``.

Thin Typer wrappers over the git-free core in :mod:`dreamteam.dt.worktrees` and
the git helpers in :mod:`dreamteam.dt.paths`. Kept out of the ``dt`` subpackage
(git/typer-free) and the scaffolding :mod:`dreamteam.cli`; mounted via
``add_typer`` in ``cli.py`` so the commands are reachable as ``dt worktree …``
and ``dreamteam worktree …``. See ``specs/T036-worktrees/spec.md``.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Annotated

import typer

from dreamteam.dt.paths import (
    DtHomeError,
    branch_merged,
    default_base_branch,
    delete_branch,
    ensure_store,
    list_worktrees,
    remove_worktree,
    store_dir,
    worktree_dirty,
    worktrees_dir,
)
from dreamteam.dt.tasks import TaskError, load_all_tasks
from dreamteam.dt.worktrees import (
    is_managed,
    partition_worktrees,
    prune_plan,
    resolve_branch,
    resolve_path,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from dreamteam.dt.paths import WorktreeInfo
    from dreamteam.dt.worktrees import PruneEntry, PruneSkip, WorktreeMatch

_EXIT_ERROR = 1

worktree_app = typer.Typer(
    name='worktree',
    help='Task worktree placement and lifecycle: root, path, list, prune.',
    no_args_is_help=True,
)


def _run[T](action: Callable[[], T]) -> T:
    """
    Run ``action``, mapping the expected failures to a clean exit 1.

    ``TaskError`` (missing task / no branch), ``DtHomeError`` (store or git
    resolution) and stray ``OSError`` all surface as a single stderr line and a
    non-zero code — no traceback, consistent with ``dt task``.
    """
    try:
        return action()
    except (TaskError, DtHomeError, OSError) as exc:
        typer.echo(f'dt worktree: {exc}', err=True)
        raise typer.Exit(code=_EXIT_ERROR) from exc


@worktree_app.command('root')
def _root(
    *,
    json_out: Annotated[
        bool, typer.Option('--json', help='Emit the root as JSON.')
    ] = False,
) -> None:
    """Print ``$DT_HOME/worktrees`` — where task worktrees are placed."""

    def action() -> str:
        ensure_store()
        return str(worktrees_dir())

    root = _run(action)
    typer.echo(
        json.dumps({'root': root}, ensure_ascii=False, indent=2) if json_out else root
    )


@worktree_app.command('path')
def _path(
    arg: Annotated[str, typer.Argument(help='Task ID (e.g. T034) or a branch name.')],
    *,
    json_out: Annotated[
        bool, typer.Option('--json', help='Emit branch, path and existence as JSON.')
    ] = False,
) -> None:
    """Print the worktree path for a task or branch (actual, else computed)."""

    def action() -> tuple[str, str, bool]:
        ensure_store()
        branch = resolve_branch(store_dir(), arg)
        path, exists = resolve_path(worktrees_dir(), branch, list_worktrees())
        return branch, str(path), exists

    branch, path, exists = _run(action)
    if json_out:
        payload = {'branch': branch, 'path': path, 'exists': exists}
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(path)


def _match_obj(match: WorktreeMatch, status: str) -> dict[str, str]:
    return {
        'task': match.task_id,
        'status': status,
        'branch': match.info.branch or '',
        'path': str(match.info.path),
    }


def _emit_list(
    matched: list[WorktreeMatch],
    orphaned: list[WorktreeInfo],
    statuses: dict[str, str],
    *,
    json_out: bool,
) -> None:
    if json_out:
        payload = {
            'matched': [_match_obj(m, statuses.get(m.task_id, '')) for m in matched],
            'orphaned': [
                {'branch': wt.branch or '', 'path': str(wt.path)} for wt in orphaned
            ],
        }
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if not matched and not orphaned:
        typer.echo('no task worktrees')
        return
    for match in matched:
        status = statuses.get(match.task_id, '?')
        typer.echo(
            f'{match.task_id}  [{status}]  {match.info.branch}  {match.info.path}'
        )
    for worktree in orphaned:
        label = worktree.branch or '(detached)'
        typer.echo(f'orphaned  {label}  {worktree.path}')


@worktree_app.command('list')
def _list(
    *,
    json_out: Annotated[
        bool, typer.Option('--json', help='Emit the mapping as JSON.')
    ] = False,
) -> None:
    """Map existing worktrees to tasks; flag orphaned managed worktrees."""

    def action() -> tuple[list[WorktreeMatch], list[WorktreeInfo], dict[str, str]]:
        ensure_store()
        tasks = load_all_tasks(store_dir())
        matched, orphaned = partition_worktrees(
            list_worktrees(), tasks, worktrees_dir()
        )
        statuses: dict[str, str] = {
            task_id: task.status for task_id, task in tasks.items()
        }
        return matched, orphaned, statuses

    matched, orphaned, statuses = _run(action)
    _emit_list(matched, orphaned, statuses, json_out=json_out)


def _prune_plan() -> tuple[list[PruneEntry], list[PruneSkip]]:
    """Gather git facts and compute the removable/skipped split (read-only)."""
    ensure_store()
    tasks = load_all_tasks(store_dir())
    root = worktrees_dir()
    worktrees = list_worktrees()
    base = default_base_branch()
    managed = [wt for wt in worktrees if is_managed(wt.path, root)]
    merged = {wt.branch: branch_merged(wt.branch, base) for wt in managed if wt.branch}
    dirty = {wt.path: worktree_dirty(wt.path) for wt in managed}
    return prune_plan(worktrees, tasks, root, merged, dirty)


def _emit_prune(
    removed: list[tuple[PruneEntry, str | None]],
    skipped: list[PruneSkip],
    errors: list[tuple[PruneEntry, str]],
    *,
    json_out: bool,
) -> None:
    if json_out:
        payload = {
            'removed': [
                {
                    'task': entry.task_id,
                    'branch': entry.info.branch or '',
                    'path': str(entry.info.path),
                    'branch_deleted': note is None,
                }
                for entry, note in removed
            ],
            'skipped': [
                {
                    'branch': skip.info.branch or '',
                    'path': str(skip.info.path),
                    'reasons': skip.reasons,
                }
                for skip in skipped
            ],
            'errors': [
                {'path': str(entry.info.path), 'error': message}
                for entry, message in errors
            ],
        }
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    for entry, note in removed:
        typer.echo(f'removed  {entry.task_id}  {entry.info.branch}  {entry.info.path}')
        if note is not None:
            typer.echo(f'  note: {note}', err=True)
    for skip in skipped:
        label = skip.info.branch or '(detached)'
        typer.echo(f'skipped  {label}  {skip.info.path}: {"; ".join(skip.reasons)}')
    for entry, message in errors:
        typer.echo(f'error  {entry.info.path}: {message}', err=True)
    if not removed and not skipped and not errors:
        typer.echo('nothing to prune')


@worktree_app.command('prune')
def _prune(
    *,
    json_out: Annotated[
        bool, typer.Option('--json', help='Emit removed/skipped/errors as JSON.')
    ] = False,
) -> None:
    """Remove managed worktrees of done/dropped tasks with merged, clean branches."""
    removable, skipped = _run(_prune_plan)
    removed: list[tuple[PruneEntry, str | None]] = []
    errors: list[tuple[PruneEntry, str]] = []
    for entry in removable:
        try:
            remove_worktree(entry.info.path)
        except (DtHomeError, OSError) as exc:
            errors.append((entry, f'worktree remove failed: {exc}'))
            continue
        note: str | None = None
        if entry.info.branch is not None:
            try:
                delete_branch(entry.info.branch)
            except (DtHomeError, OSError) as exc:
                note = f'branch {entry.info.branch} not deleted: {exc}'
        removed.append((entry, note))
    _emit_prune(removed, skipped, errors, json_out=json_out)
    if errors:
        raise typer.Exit(code=_EXIT_ERROR)
