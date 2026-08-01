"""
``dt context`` CLI — session orientation ("where am I, what am I working on").

Thin Typer wrapper over the git-free core in :mod:`dreamteam.dt.context`. This
layer gathers the git facts (current branch, worktree list, the main copy's
BACKLOG text, the ``current-task`` binding) and feeds them to the pure builder,
then renders human / ``--json`` / ``--hook`` output and refreshes the current
worktree's ``context.line``. The ``--hook`` mode never blocks session start:
any error yields exit 0 with empty output (design §356). Registered as a
top-level command in ``cli.py``. See ``specs/T051-context/spec.md``.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Annotated

import typer

from dreamteam.dt.context import (
    ContextModel,
    build_context,
    context_json,
    render_hook_context,
    render_human,
    resolve_task_id,
    status_line,
)
from dreamteam.dt.paths import (
    DtHomeError,
    ensure_store,
    git_context,
    list_worktrees,
    main_worktree,
    store_dir,
    worktree_slug,
)
from dreamteam.dt.tasks import TaskError

if TYPE_CHECKING:
    from pathlib import Path

_EXIT_ERROR = 1
_DT_TASK_ENV = 'DT_TASK'
_HOOK_EVENT = 'SessionStart'
_BACKLOG_NAME = 'BACKLOG.md'
_BINDING_DIR = 'by-worktree'
_CURRENT_TASK = 'current-task'
_CONTEXT_LINE = 'context.line'


def _read_current_task(store: Path, slug: str | None) -> str | None:
    if slug is None:
        return None
    path = store / _BINDING_DIR / slug / _CURRENT_TASK
    try:
        return path.read_text(encoding='utf-8').strip() or None
    except OSError:
        return None


def _read_main_backlog() -> str:
    try:
        path = main_worktree() / _BACKLOG_NAME
    except DtHomeError:
        return ''  # not inside git — no reference copy to diverge against
    try:
        return path.read_text(encoding='utf-8')
    except OSError:
        return ''


def _gather(store: Path) -> tuple[ContextModel, str | None]:
    """Resolve the task from git facts and build the context; return (model, slug)."""
    cwd, branch = git_context()
    slug = worktree_slug(cwd) if cwd is not None else None
    resolved = resolve_task_id(
        dt_task=os.environ.get(_DT_TASK_ENV),
        branch=branch,
        bound=_read_current_task(store, slug),
    )
    worktrees = list_worktrees() if cwd is not None else []
    model = build_context(
        store,
        resolved_id=resolved,
        cwd=cwd,
        worktrees=worktrees,
        main_backlog_text=_read_main_backlog(),
    )
    return model, slug


def _refresh_context_line(store: Path, model: ContextModel, slug: str | None) -> None:
    """Rewrite the current worktree's ``context.line`` when a task is bound."""
    if model.task is None or slug is None:
        return
    directory = store / _BINDING_DIR / slug
    directory.mkdir(parents=True, exist_ok=True)
    (directory / _CONTEXT_LINE).write_text(
        f'{status_line(model.task)}\n', encoding='utf-8'
    )


def _emit_hook() -> None:
    """Print the SessionStart hook payload; never block the session (exit 0)."""
    try:
        ensure_store()
        store = store_dir()
        model, slug = _gather(store)
        _refresh_context_line(store, model, slug)
        additional = render_hook_context(model)
    except Exception:
        # A hook must never block session start: any error → exit 0, empty output
        # (design §356). BLE001 is globally ignored, so the broad catch is fine.
        raise typer.Exit(code=0) from None
    payload = {
        'hookSpecificOutput': {
            'hookEventName': _HOOK_EVENT,
            'additionalContext': additional,
        }
    }
    typer.echo(json.dumps(payload, ensure_ascii=False))


def context(
    *,
    json_out: Annotated[
        bool, typer.Option('--json', help='Emit the context as JSON.')
    ] = False,
    hook: Annotated[
        bool,
        typer.Option('--hook', help='Emit a SessionStart hook payload (never fails).'),
    ] = False,
) -> None:
    """Orient the session: resolve the current task and print what it is."""
    if hook:
        _emit_hook()
        return
    try:
        ensure_store()
        store = store_dir()
        model, slug = _gather(store)
        _refresh_context_line(store, model, slug)
    except (DtHomeError, OSError, TaskError) as exc:
        typer.echo(f'dt context: {exc}', err=True)
        raise typer.Exit(code=_EXIT_ERROR) from exc
    if json_out:
        typer.echo(json.dumps(context_json(model), ensure_ascii=False, indent=2))
    else:
        typer.echo(render_human(model))
