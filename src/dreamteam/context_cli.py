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

import contextlib
import json
import os
import sys
from pathlib import Path
from typing import Annotated

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
from dreamteam.dt.sessions import (
    SessionRecord,
    current_timestamp,
    write_session_record,
)
from dreamteam.dt.tasks import TaskError

_EXIT_ERROR = 1
_DT_TASK_ENV = 'DT_TASK'
_HOOK_EVENT = 'SessionStart'
_BACKLOG_NAME = 'BACKLOG.md'
_BINDING_DIR = 'by-worktree'
_SESSIONS_DIR = 'sessions'
_CURRENT_TASK = 'current-task'
_CONTEXT_LINE = 'context.line'
# Documented SessionStart hook stdin fields we consume (verified against docs,
# design §441). `transcript_path` is deliberately never read (§358).
_HOOK_SESSION_ID = 'session_id'
_HOOK_CWD = 'cwd'


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


def _read_hook_input() -> dict[str, object]:
    """
    Parse the SessionStart hook's stdin JSON, tolerating empty/invalid input.

    Guards on ``isatty`` first: a human running ``dt context --hook`` in a
    terminal must not hang on ``read()`` waiting for EOF — the real hook always
    pipes JSON on stdin. Any glitch (no stdin, bad JSON, wrong shape) → ``{}``.
    """
    try:
        if sys.stdin.isatty():
            return {}
        raw = json.loads(sys.stdin.read())
    except OSError, ValueError, AttributeError:
        return {}
    return raw if isinstance(raw, dict) else {}


def _record_session(
    store: Path, model: ContextModel, hook_input: dict[str, object]
) -> None:
    """
    Best-effort write of ``sessions/<TASK_ID>.json`` — the registry (design §364).

    A no-op unless the session is bound *and* the hook supplied a ``session_id``
    (an unbound session has no ``<TASK_ID>`` key to write under). Any failure is
    swallowed: the registry is a convenience, never a reason to disturb the hook
    payload already emitted. BLE001 is globally ignored, so the broad catch is
    intentional.
    """
    if model.task is None:
        return
    session_id = hook_input.get(_HOOK_SESSION_ID)
    if not isinstance(session_id, str) or not session_id:
        return
    cwd = hook_input.get(_HOOK_CWD)
    cwd_str = cwd if isinstance(cwd, str) and cwd else str(Path.cwd())
    record = SessionRecord(
        session_id=session_id, cwd=cwd_str, last_seen=current_timestamp()
    )
    with contextlib.suppress(Exception):
        write_session_record(store / _SESSIONS_DIR, model.task.id, record)


def _emit_hook() -> None:
    """Print the SessionStart hook payload; never block the session (exit 0)."""
    hook_input = _read_hook_input()
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
    # Side effect after the payload is out: a registry failure can't cost context.
    _record_session(store, model, hook_input)


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
