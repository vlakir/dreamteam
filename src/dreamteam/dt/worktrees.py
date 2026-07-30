"""
Worktree placement and lifecycle logic — pure, ``typer``- and ``git``-free.

Computes where a task's working copy lives (``$DT_HOME/worktrees/<branch>``,
never stored — see design §«Размещение worktree»), maps existing worktrees to
tasks, and plans a ``prune`` over pre-gathered git facts. Every git call (list,
merged, dirty, remove, delete) is done by :mod:`dreamteam.dt.paths` and passed
in as data, mirroring the git-free ``check_tasks`` split from T035. The Typer
surface lives in :mod:`dreamteam.worktree_cli`. See ``specs/T036-worktrees/spec.md``.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, NamedTuple

from dreamteam.dt.tasks import TaskError, load_existing

if TYPE_CHECKING:
    from pathlib import Path

    from dreamteam.dt.model import Task
    from dreamteam.dt.paths import WorktreeInfo

# Exact task ID (`path` arg auto-detect): only these become a task-ID lookup;
# anything else is a literal branch name. `[0-9]` (not `\d`) mirrors T034 —
# ASCII digits only, no unicode-digit surprises.
_ID_EXACT_RE = re.compile(r'^T[0-9]{3,}$')
# `T<NNN>` prefix of a branch name — the fallback worktree↔task match when no
# record carries the branch in its `branch` field.
_ID_PREFIX_RE = re.compile(r'^(T[0-9]{3,})(?:-|$)')
_PRUNABLE_STATUSES = frozenset({'done', 'dropped'})


class WorktreeMatch(NamedTuple):
    """A worktree paired with the task it belongs to (``dt worktree list``)."""

    info: WorktreeInfo
    task_id: str


class PruneEntry(NamedTuple):
    """A worktree eligible for removal by ``dt worktree prune``."""

    info: WorktreeInfo
    task_id: str


class PruneSkip(NamedTuple):
    """A worktree ``prune`` left alone, with every applicable reason."""

    info: WorktreeInfo
    task_id: str | None
    reasons: list[str]


def classify_arg(arg: str) -> bool:
    """True iff ``arg`` is an exact task ID (else it is a literal branch name)."""
    return bool(_ID_EXACT_RE.match(arg))


def resolve_branch(store: Path, arg: str) -> str:
    """
    Resolve a ``dt worktree path`` argument to a branch name.

    An exact ``T<NNN>`` is a task ID: the record is loaded and its ``branch``
    field returned, raising :class:`TaskError` if the task is absent or has no
    branch yet (that is set by ``dt task start``, T039). Any other argument is
    taken as a literal branch name unchanged.
    """
    if not classify_arg(arg):
        return arg
    task = load_existing(store, arg)
    if not task.branch:
        message = (
            f'task {arg} has no branch yet; run `dt task start {arg}` to create '
            'its branch and worktree first, or pass a branch name directly'
        )
        raise TaskError(message)
    return task.branch


def resolve_path(
    managed_root: Path, branch: str, worktrees: list[WorktreeInfo]
) -> tuple[Path, bool]:
    """
    Actual path of the worktree on ``branch``, or the computed one if none exists.

    Returns ``(path, exists)``. When a live worktree is checked out on ``branch``
    its real location wins (it may have been created by hand elsewhere); otherwise
    the computed ``managed_root / branch`` is where it *would* be created.

    The *computed* path is confined to ``managed_root``: a literal branch argument
    is not a validated git ref, so an escaping value (``../x``, an absolute path)
    would otherwise print a location outside the managed root and misdirect
    automation that trusts it (spec Analyze A7). Such an argument is rejected.
    """
    for worktree in worktrees:
        if worktree.branch == branch:
            return worktree.path, True
    computed = managed_root / branch
    if not computed.resolve().is_relative_to(managed_root.resolve()):
        message = (
            f'branch name {branch!r} would place the worktree outside the managed '
            f'root {managed_root} — refusing (pass a plain branch name)'
        )
        raise TaskError(message)
    return computed, False


def is_managed(path: Path, managed_root: Path) -> bool:
    """True iff ``path`` lives under the managed ``$DT_HOME/worktrees/`` root."""
    return path.resolve().is_relative_to(managed_root.resolve())


def match_task_id(branch: str | None, tasks: dict[str, Task]) -> str | None:
    """
    Map a worktree branch to a task ID, or ``None``.

    Primary key is the record's ``branch`` field; the fallback parses a
    ``T<NNN>`` prefix of the branch name and accepts it if such a record exists.
    A detached worktree (``branch is None``) never matches.
    """
    if branch is None:
        return None
    for task_id, task in tasks.items():
        if task.branch == branch:
            return task_id
    prefix = _ID_PREFIX_RE.match(branch)
    if prefix is not None and prefix.group(1) in tasks:
        return prefix.group(1)
    return None


def partition_worktrees(
    worktrees: list[WorktreeInfo], tasks: dict[str, Task], managed_root: Path
) -> tuple[list[WorktreeMatch], list[WorktreeInfo]]:
    """
    Split worktrees into task-matched pairs and orphans.

    An *orphan* is a worktree under the managed root that maps to no task — a
    leftover to surface. Worktrees outside the managed root that match no task
    (the main copy, hand-made ones on non-task branches) are legitimate
    bystanders and excluded from both lists.
    """
    matched: list[WorktreeMatch] = []
    orphaned: list[WorktreeInfo] = []
    for worktree in worktrees:
        task_id = match_task_id(worktree.branch, tasks)
        if task_id is not None:
            matched.append(WorktreeMatch(worktree, task_id))
        elif is_managed(worktree.path, managed_root):
            orphaned.append(worktree)
    return matched, orphaned


def prune_plan(
    worktrees: list[WorktreeInfo],
    tasks: dict[str, Task],
    managed_root: Path,
    merged: dict[str, bool],
    dirty: dict[Path, bool],
) -> tuple[list[PruneEntry], list[PruneSkip]]:
    """
    Decide which managed worktrees may be removed and why the rest are skipped.

    Pure over pre-gathered git facts (``merged`` per branch, ``dirty`` per path,
    both supplied by the caller for the managed worktrees). Removal requires all
    of: a matched task in ``done``/``dropped``, a merged branch, a clean tree.
    Every failing condition is collected as a reason so the skip is fully
    explained. Non-managed worktrees are out of scope and ignored entirely.
    """
    removable: list[PruneEntry] = []
    skipped: list[PruneSkip] = []
    for worktree in worktrees:
        if not is_managed(worktree.path, managed_root):
            continue
        task_id = match_task_id(worktree.branch, tasks)
        reasons: list[str] = []
        if task_id is None:
            reasons.append('no matching task (orphaned worktree)')
        elif tasks[task_id].status not in _PRUNABLE_STATUSES:
            reasons.append(
                f'task {task_id} is {tasks[task_id].status} (not done/dropped)'
            )
        if worktree.branch is None:
            reasons.append('detached HEAD (no branch)')
        elif not merged.get(worktree.branch, False):
            reasons.append('branch not merged into base')
        if dirty.get(worktree.path, False):
            reasons.append('uncommitted changes')
        # `or task_id is None` is redundant at runtime (a None id always adds a
        # reason above) but lets the type checker narrow `task_id` to `str` in
        # the else branch, so `PruneEntry` gets a non-optional id without a cast.
        if reasons or task_id is None:
            skipped.append(PruneSkip(worktree, task_id, reasons))
        else:
            removable.append(PruneEntry(worktree, task_id))
    return removable, skipped
