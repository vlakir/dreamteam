"""
``dt backlog`` CLI: ``sync`` — regenerate BACKLOG.md from the task store.

Thin Typer wrapper over the git-free projection in :mod:`dreamteam.dt.backlog`.
This layer resolves the git context (repo root, current branch, default base)
via :mod:`dreamteam.dt.paths` and passes it into the pure core, mirroring
``board_cli`` / ``task_cli``. Mounted onto the shared app in ``cli.py``, so it
is reachable as both ``dt backlog …`` and ``dreamteam backlog …``. See
``specs/T040-backlog-sync/spec.md``.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Annotated

import typer

from dreamteam.dt.backlog import backlog_items, sync_backlog
from dreamteam.dt.paths import (
    DtHomeError,
    default_base_branch,
    ensure_store,
    git_context,
    store_dir,
)

if TYPE_CHECKING:
    from pathlib import Path
    from typing import NoReturn

    from dreamteam.dt.model import Task

_EXIT_ERROR = 1
_BACKLOG_NAME = 'BACKLOG.md'

backlog_app = typer.Typer(
    name='backlog',
    help='Project the task store into BACKLOG.md.',
    no_args_is_help=True,
)


def _die(message: str) -> NoReturn:
    """Print a plain error to stderr and exit 1 (no traceback), like the rest of dt."""
    typer.echo(f'dt backlog: {message}', err=True)
    raise typer.Exit(code=_EXIT_ERROR)


def _require_main_branch(current_branch: str | None, *, force: bool) -> None:
    """
    Refuse to run off the default branch unless ``--force`` (design §216).

    Syncing on a task branch is exactly what reintroduces the merge conflict the
    operational layer removes: two branches each rewriting BACKLOG.md. The base
    is resolved locally (no fetch). A detached HEAD (``current_branch is None``)
    is treated as "not the main branch".
    """
    if force:
        return
    base = default_base_branch()
    if current_branch == base:
        return
    where = current_branch if current_branch is not None else 'a detached HEAD'
    _die(
        f'refusing to sync on {where!r}: BACKLOG.md is synced only on the '
        f'{base!r} branch (use --force to override)'
    )


def _do_sync(repo_root: Path, store: Path) -> tuple[Path, int]:
    """Rewrite the managed block of ``repo_root/BACKLOG.md``; return (path, count)."""
    items: list[Task] = backlog_items(store)
    path = repo_root / _BACKLOG_NAME
    existing = path.read_text(encoding='utf-8') if path.exists() else ''
    path.write_text(sync_backlog(existing, items), encoding='utf-8')
    return path, len(items)


@backlog_app.command('sync')
def _sync(
    *,
    force: Annotated[
        bool,
        typer.Option('--force', help='Sync even when off the default branch.'),
    ] = False,
    json_out: Annotated[
        bool, typer.Option('--json', help='Emit the sync result as JSON.')
    ] = False,
) -> None:
    """Rebuild BACKLOG.md's managed block from unfinished task records."""
    repo_root, current_branch = git_context()
    if repo_root is None:
        _die(
            'not inside a git repository; BACKLOG.md is written to the '
            'repository root (set DT_HOME only resolves the store, not the repo)'
        )
    _require_main_branch(current_branch, force=force)
    try:
        ensure_store()
        path, count = _do_sync(repo_root, store_dir())
    except (DtHomeError, OSError) as exc:
        _die(str(exc))
    if json_out:
        typer.echo(
            json.dumps(
                {'backlog': str(path), 'tasks': count}, ensure_ascii=False, indent=2
            )
        )
    else:
        typer.echo(f'synced {count} task(s) to {path}')
