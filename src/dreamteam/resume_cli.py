"""
``dt resume`` CLI — rebuild the session layout after a reboot.

Thin Typer wrapper over the git-free core in :mod:`dreamteam.dt.resume`. This
layer gathers the git facts (worktree list) and the wall clock, reads the
registry T052 keeps (``sessions/<TASK_ID>.json``), and renders one of three
forms: a table (bare), a one-shot tmux script (``--tmux``), or a single recovery
command for one task (``dt resume T034``). ``--json`` emits the machine form.
Registered as a top-level command in ``cli.py``. See
``specs/T053-resume/spec.md``.
"""

from __future__ import annotations

import datetime
import json
from typing import TYPE_CHECKING, Annotated

import typer

from dreamteam.dt.paths import (
    DtHomeError,
    ensure_store,
    list_worktrees,
    store_dir,
    worktrees_dir,
)
from dreamteam.dt.resume import (
    build_entries,
    continue_entry,
    entries_json,
    render_table,
    render_tmux,
    resume_entry,
)
from dreamteam.dt.sessions import read_all_session_records, read_session_record
from dreamteam.dt.tasks import TaskError, load_all_tasks
from dreamteam.dt.worktrees import resolve_path

if TYPE_CHECKING:
    from pathlib import Path

    from dreamteam.dt.model import Task
    from dreamteam.dt.resume import ResumeEntry

_EXIT_ERROR = 1
_SESSIONS_DIR = 'sessions'


def _address_entry(
    store: Path, tasks: dict[str, Task], task_id: str, now: datetime.datetime
) -> ResumeEntry:
    """
    Build the single entry for ``dt resume T034`` (status-unrestricted).

    With a registry record → resume/stale as usual. Without one → degrade to
    ``claude --continue`` in the task's worktree, but only if that worktree
    actually exists; a task that never started (no branch, or no live worktree)
    has nothing to resume and raises a clear :class:`TaskError`.
    """
    task = tasks.get(task_id)
    if task is None:
        message = f'task {task_id} not found in store'
        raise TaskError(message)
    record = read_session_record(store / _SESSIONS_DIR, task_id)
    if record is not None:
        return resume_entry(task, record, now=now)
    if not task.branch:
        message = (
            f'task {task_id} has no branch/worktree yet; run '
            f'`dt task start {task_id}` first (nothing to resume)'
        )
        raise TaskError(message)
    path, exists = resolve_path(worktrees_dir(), task.branch, list_worktrees())
    if not exists:
        message = (
            f'no live worktree for {task_id} at {path}; run '
            f'`dt task start {task_id}` (nothing to resume)'
        )
        raise TaskError(message)
    return continue_entry(task, path)


def _gather(
    store: Path, task_id: str | None, now: datetime.datetime
) -> list[ResumeEntry]:
    """Resolve the entries for the requested form (one task, or the whole registry)."""
    tasks = load_all_tasks(store)
    if task_id is not None:
        return [_address_entry(store, tasks, task_id, now)]
    records = read_all_session_records(store / _SESSIONS_DIR)
    return build_entries(records, tasks, now=now)


def _emit(
    entries: list[ResumeEntry], *, tmux: bool, json_out: bool, addressed: bool
) -> None:
    if json_out:
        typer.echo(json.dumps(entries_json(entries), ensure_ascii=False, indent=2))
    elif tmux:
        typer.echo(render_tmux(entries))
    elif addressed:
        typer.echo(entries[0].command)
    else:
        typer.echo(render_table(entries))


def resume(
    task_id: Annotated[
        str | None,
        typer.Argument(help='Resume one task by ID (e.g. T034); default: all active.'),
    ] = None,
    *,
    tmux: Annotated[
        bool,
        typer.Option('--tmux', help='Emit a one-shot tmux layout script to run.'),
    ] = False,
    json_out: Annotated[
        bool, typer.Option('--json', help='Emit the recovery entries as JSON.')
    ] = False,
) -> None:
    """Print how to bring live sessions back after a reboot (design §372–388)."""
    if tmux and json_out:
        typer.echo('dt resume: --tmux и --json взаимоисключающие', err=True)
        raise typer.Exit(code=_EXIT_ERROR)
    try:
        ensure_store()
        store = store_dir()
        now = datetime.datetime.now(tz=datetime.UTC)
        entries = _gather(store, task_id, now)
    except (DtHomeError, OSError, TaskError) as exc:
        typer.echo(f'dt resume: {exc}', err=True)
        raise typer.Exit(code=_EXIT_ERROR) from exc
    _emit(entries, tmux=tmux, json_out=json_out, addressed=task_id is not None)
