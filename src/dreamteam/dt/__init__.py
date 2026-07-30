"""
Operational state layer (``dt``) — T033 storage skeleton.

This subpackage hosts the stateful ``dt`` surface (task records, worktree
placement, board, context, resume, run) that lives beside the repository in
``$DT_HOME`` (``<repo>.dt``), outside git. T033 delivers only the foundation:
``$DT_HOME`` resolution, lazy store-directory creation, worktree ``<slug>``
computation and the task record model with unknown-field-preserving I/O.

See ``specs/T033-store-core/spec.md`` and ``specs/roadmap-v0.3-v1.0/design.md``.
"""

from __future__ import annotations

from dreamteam.dt.model import (
    TASK_STATUSES,
    Task,
    TaskStatus,
    dump_task,
    load_task,
    parse_task,
    save_task,
)
from dreamteam.dt.paths import (
    DtHomeError,
    by_worktree_dir,
    dt_home,
    ensure_store,
    sessions_dir,
    store_dir,
    tasks_dir,
    worktree_slug,
    worktrees_dir,
)
from dreamteam.dt.tasks import (
    TaskError,
    allocate_id,
    format_id,
    move_task,
    new_task,
    parse_status,
    show_task,
    split_task,
)

__all__ = [
    'TASK_STATUSES',
    'DtHomeError',
    'Task',
    'TaskError',
    'TaskStatus',
    'allocate_id',
    'by_worktree_dir',
    'dt_home',
    'dump_task',
    'ensure_store',
    'format_id',
    'load_task',
    'move_task',
    'new_task',
    'parse_status',
    'parse_task',
    'save_task',
    'sessions_dir',
    'show_task',
    'split_task',
    'store_dir',
    'tasks_dir',
    'worktree_slug',
    'worktrees_dir',
]
