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
    WorktreeInfo,
    branch_merged,
    by_worktree_dir,
    default_base_branch,
    delete_branch,
    dt_home,
    ensure_store,
    list_worktrees,
    remove_worktree,
    sessions_dir,
    store_dir,
    tasks_dir,
    worktree_dirty,
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
from dreamteam.dt.worktrees import (
    PruneEntry,
    PruneSkip,
    WorktreeMatch,
    classify_arg,
    is_managed,
    match_task_id,
    partition_worktrees,
    prune_plan,
    resolve_branch,
    resolve_path,
)

__all__ = [
    'TASK_STATUSES',
    'DtHomeError',
    'PruneEntry',
    'PruneSkip',
    'Task',
    'TaskError',
    'TaskStatus',
    'WorktreeInfo',
    'WorktreeMatch',
    'allocate_id',
    'branch_merged',
    'by_worktree_dir',
    'classify_arg',
    'default_base_branch',
    'delete_branch',
    'dt_home',
    'dump_task',
    'ensure_store',
    'format_id',
    'is_managed',
    'list_worktrees',
    'load_task',
    'match_task_id',
    'move_task',
    'new_task',
    'parse_status',
    'parse_task',
    'partition_worktrees',
    'prune_plan',
    'remove_worktree',
    'resolve_branch',
    'resolve_path',
    'save_task',
    'sessions_dir',
    'show_task',
    'split_task',
    'store_dir',
    'tasks_dir',
    'worktree_dirty',
    'worktree_slug',
    'worktrees_dir',
]
