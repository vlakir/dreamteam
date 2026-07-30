"""
Board model — pure, ``typer``- and ``git``-free.

Assembles the kanban model once (read records, drop ``dropped``, sort by
``updated`` descending) and groups it into status columns. Split from any
rendering so the graphical board (E10, design §604) reuses the exact same
model — the text view in :mod:`dreamteam.board_cli` and a future web view
render the same data differently. See ``specs/T037-board/spec.md``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dreamteam.dt.model import TASK_STATUSES
from dreamteam.dt.tasks import load_all_tasks

if TYPE_CHECKING:
    from pathlib import Path

    from dreamteam.dt.model import Task, TaskStatus

_DROPPED: TaskStatus = 'dropped'
# Board columns in flow order — every status except `dropped` (which never
# appears on the board). Derived from `TASK_STATUSES` so the two never drift.
BOARD_STATUSES: tuple[TaskStatus, ...] = tuple(
    status for status in TASK_STATUSES if status != _DROPPED
)


def _sort_key(task: Task) -> tuple[int, int, str]:
    """
    Order key: dated tasks first (newest ``updated`` first), undated last.

    A record without ``updated`` must not read as "freshest"; it sorts after
    every dated one. Within each group ties break by ID for a stable order.
    """
    if task.updated is None:
        return (1, 0, task.id)
    return (0, -task.updated.toordinal(), task.id)


def board_model(store: Path) -> list[Task]:
    """
    The board model: active records sorted by ``updated`` (newest first).

    Reads every task, drops ``dropped`` (never shown), sorts by recency. Pure
    over the store — no git, no worktree traversal (one store per repository).
    This is the single reusable unit the graphical board (E10) shares.
    """
    active = [
        task for task in load_all_tasks(store).values() if task.status != _DROPPED
    ]
    return sorted(active, key=_sort_key)


def board_columns(model: list[Task]) -> dict[TaskStatus, list[Task]]:
    """
    Group a board model into status columns (flow order, model order within).

    Every :data:`BOARD_STATUSES` column is present (empty ones included, for a
    stable board shape); the model's recency order is preserved inside each.
    """
    columns: dict[TaskStatus, list[Task]] = {status: [] for status in BOARD_STATUSES}
    for task in model:
        if task.status in columns:
            columns[task.status].append(task)
    return columns
