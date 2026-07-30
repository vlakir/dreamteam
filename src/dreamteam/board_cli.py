"""
``dt board`` CLI — text kanban of the task store.

Thin Typer wrapper over the git-free model in :mod:`dreamteam.dt.board`.
Registered as a top-level command (``app.command('board')`` in ``cli.py``), so
it is reachable as ``dt board`` and ``dreamteam board``. Renders stacked status
sections; ``--json`` emits the column model. See ``specs/T037-board/spec.md``.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Annotated

import typer

from dreamteam.dt.board import BOARD_STATUSES, board_columns, board_model
from dreamteam.dt.paths import DtHomeError, ensure_store, store_dir

if TYPE_CHECKING:
    from dreamteam.dt.model import Task, TaskStatus

_EXIT_ERROR = 1


def _task_obj(task: Task) -> dict[str, object]:
    data = task.model_dump(mode='json')
    data['body'] = task.body
    return data


def _render_human(columns: dict[TaskStatus, list[Task]]) -> str:
    blocks: list[str] = []
    for status in BOARD_STATUSES:
        # `status` is a `TaskStatus` literal; annotate so the header seed does
        # not narrow `lines` to `list[TaskStatus]` and reject the `str` rows.
        lines: list[str] = [status]
        lines.extend(
            f'  {task.id}  [{task.status}]  {task.title}' for task in columns[status]
        )
        blocks.append('\n'.join(lines))
    return '\n\n'.join(blocks)


def board(
    *,
    json_out: Annotated[
        bool, typer.Option('--json', help='Emit the board columns as JSON.')
    ] = False,
) -> None:
    """Print the task board — stacked status sections, or columns as JSON."""
    try:
        ensure_store()
        columns = board_columns(board_model(store_dir()))
    except (DtHomeError, OSError) as exc:
        typer.echo(f'dt board: {exc}', err=True)
        raise typer.Exit(code=_EXIT_ERROR) from exc
    if json_out:
        payload = {
            'columns': {
                status: [_task_obj(task) for task in columns[status]]
                for status in BOARD_STATUSES
            }
        }
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(_render_human(columns))
