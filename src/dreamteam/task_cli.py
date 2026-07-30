"""
``dt task`` CLI: ``new`` / ``show`` / ``move`` / ``split``.

Thin Typer wrappers over :mod:`dreamteam.dt.tasks`. Kept out of the ``dt``
subpackage (which stays ``typer``-free, so hooks and the statusline can import
it) and out of the large scaffolding :mod:`dreamteam.cli`. Mounted onto the
shared app via ``add_typer`` in ``cli.py``, so the commands are reachable both
as ``dt task …`` and ``dreamteam task …``. See ``specs/T034-task-ops/spec.md``.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Annotated

import typer

from dreamteam.dt.model import TASK_STATUSES
from dreamteam.dt.paths import DtHomeError, ensure_store, store_dir
from dreamteam.dt.tasks import (
    TaskError,
    move_task,
    new_task,
    show_task,
    split_task,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from dreamteam.dt.model import Task

_EXIT_ERROR = 1

task_app = typer.Typer(
    name='task',
    help='Operational task records: create, inspect, move, split.',
    no_args_is_help=True,
)


def _run(action: Callable[[Path], Task]) -> Task:
    """
    Resolve/create the store, run ``action`` against it, map errors to exit 1.

    ``TaskError``, ``DtHomeError`` and any stray filesystem ``OSError`` all
    surface as a plain stderr line and a non-zero exit code — no traceback,
    consistent with the rest of ``dt``. ``OSError`` is caught because a record
    or counter write can fail (permissions, full disk) below ``TaskError``.
    """
    try:
        ensure_store()
        return action(store_dir())
    except (TaskError, DtHomeError, OSError) as exc:
        typer.echo(f'dt task: {exc}', err=True)
        raise typer.Exit(code=_EXIT_ERROR) from exc


def _to_json(task: Task) -> str:
    # `body` is excluded from the model dump (it is not frontmatter); the
    # agent-facing JSON contract includes it, so re-attach it explicitly.
    data = task.model_dump(mode='json')
    data['body'] = task.body
    return json.dumps(data, ensure_ascii=False, indent=2)


def _human_show(task: Task) -> str:
    lines = [f'{task.id}  [{task.status}]  {task.title}']
    fields = (
        ('deps', ', '.join(task.deps) if task.deps else ''),
        ('parent', task.parent or ''),
        ('spec', task.spec or ''),
        ('branch', task.branch or ''),
        ('pr', str(task.pr) if task.pr is not None else ''),
        ('tags', ', '.join(task.tags) if task.tags else ''),
    )
    lines.extend(f'  {name:<7} {value}' for name, value in fields if value)
    dates = [
        label
        for label, value in (
            (f'created {task.created}', task.created),
            (f'updated {task.updated}', task.updated),
        )
        if value is not None
    ]
    if dates:
        lines.append(f'  {"  ".join(dates)}')
    body = task.body.strip()
    if body:
        lines.extend(('', body))
    return '\n'.join(lines)


def _emit(task: Task, *, json_out: bool, human: str) -> None:
    typer.echo(_to_json(task) if json_out else human)


@task_app.command('new')
def _new(
    title: Annotated[str, typer.Argument(help='Task title.')],
    *,
    deps: Annotated[
        list[str] | None,
        typer.Option(
            '--deps',
            help='Blocking task IDs (repeatable or comma-separated).',
        ),
    ] = None,
    blocks: Annotated[
        list[str] | None,
        typer.Option(
            '--blocks',
            help='Tasks this new task blocks (they gain a dependency on it).',
        ),
    ] = None,
    parent: Annotated[
        str | None,
        typer.Option('--parent', help='Parent task ID this one was born from.'),
    ] = None,
    json_out: Annotated[
        bool, typer.Option('--json', help='Emit the created record as JSON.')
    ] = False,
) -> None:
    """Allocate an ID and create a new task record in status ``todo``."""
    task = _run(
        lambda store: new_task(
            store, title, deps=deps or [], blocks=blocks or [], parent=parent
        )
    )
    detail = f' (parent {parent})' if parent else ''
    _emit(task, json_out=json_out, human=f'created {task.id}{detail}  {task.title}')


@task_app.command('show')
def _show(
    task_id: Annotated[str, typer.Argument(help='Task ID, e.g. T034.')],
    *,
    json_out: Annotated[
        bool, typer.Option('--json', help='Emit the record as JSON.')
    ] = False,
) -> None:
    """Print a task record — human-readable, or full JSON with ``--json``."""
    task = _run(lambda store: show_task(store, task_id))
    _emit(task, json_out=json_out, human=_human_show(task))


@task_app.command('move')
def _move(
    task_id: Annotated[str, typer.Argument(help='Task ID, e.g. T034.')],
    status: Annotated[
        str, typer.Argument(help=f'New status: {", ".join(TASK_STATUSES)}.')
    ],
    *,
    json_out: Annotated[
        bool, typer.Option('--json', help='Emit the updated record as JSON.')
    ] = False,
) -> None:
    """Change a task's status and bump its ``updated`` date."""
    task = _run(lambda store: move_task(store, task_id, status))
    _emit(task, json_out=json_out, human=f'{task.id} → {task.status}')


@task_app.command('split')
def _split(
    parent_id: Annotated[str, typer.Argument(help='Parent task ID to split.')],
    title: Annotated[str, typer.Argument(help='Title of the new child task.')],
    *,
    json_out: Annotated[
        bool, typer.Option('--json', help='Emit the created record as JSON.')
    ] = False,
) -> None:
    """Create a child task with ``parent`` set; the parent record is untouched."""
    task = _run(lambda store: split_task(store, parent_id, title))
    _emit(
        task,
        json_out=json_out,
        human=f'created {task.id} (parent {parent_id})  {task.title}',
    )
