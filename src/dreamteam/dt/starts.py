"""
Composite ``dt task start`` planning and side-effect-light helpers.

Pure over pre-gathered git facts (mirroring ``prune_plan`` from T036): given a
branch, its computed/actual path and two booleans, :func:`plan_start` decides
which git call is needed. The remaining helpers format the statusline
``context.line`` and extract the ``## Handover`` section for ``--json``, and
write the per-worktree binding. Git and record mutation live elsewhere
(``paths.py`` / ``tasks.py``); the Typer wrapper is ``dt task start``. See
``specs/T039-task-start/spec.md``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from pathlib import Path

    from dreamteam.dt.model import Task

_CURRENT_TASK_NAME = 'current-task'
_CONTEXT_LINE_NAME = 'context.line'
_HANDOVER_HEADING = '## Handover'


class StartPlan(NamedTuple):
    """
    What ``dt task start`` must do to reach a live branch + worktree.

    ``create_worktree`` is False when a worktree already sits on the branch
    (idempotent re-run). ``create_branch`` (the ``-b`` flag) is needed only when
    a fresh worktree is created *and* the branch does not exist locally yet.
    """

    branch: str
    path: Path
    create_worktree: bool
    create_branch: bool


def plan_start(
    branch: str, path: Path, *, worktree_exists: bool, branch_exists: bool
) -> StartPlan:
    """
    Decide worktree/branch creation from the two git facts (pure).

    Covers all four combinations of (worktree exists?) × (branch exists?):
    an existing worktree is reused as-is; otherwise a worktree is created, with
    ``-b`` only when the branch is not already present.
    """
    create_worktree = not worktree_exists
    create_branch = create_worktree and not branch_exists
    return StartPlan(
        branch=branch,
        path=path,
        create_worktree=create_worktree,
        create_branch=create_branch,
    )


def context_line(task: Task) -> str:
    """One-line statusline summary for ``context.line``: ``T034 [doing] Title``."""
    return f'{task.id} [{task.status}] {task.title}'


def extract_handover(body: str) -> str:
    """
    Return the text of the ``## Handover`` section of a task body, or ``''``.

    Reads from the ``## Handover`` heading to the next same-or-higher-level
    ``## ``/``# `` heading (or end of body), heading excluded, edges stripped.
    A body without the section yields an empty string (the ``--json`` contract).
    The stop test uses the **unstripped** line, so an *indented* ``#``-prefixed
    line (a comment/example inside the section, not a real column-0 markdown
    heading) does not prematurely truncate the extracted text.
    """
    lines = body.splitlines()
    collected: list[str] = []
    capturing = False
    for line in lines:
        if not capturing:
            if line.strip() == _HANDOVER_HEADING:
                capturing = True
            continue
        # Stop only at a real column-0 heading (`# `/`## `); indented `#`-lines
        # are section content, not boundaries.
        if line.startswith(('# ', '## ')):
            break
        collected.append(line)
    return '\n'.join(collected).strip()


def write_binding(by_worktree_root: Path, slug: str, task_id: str, line: str) -> None:
    """
    Write the per-worktree binding files under ``by-worktree/<slug>/``.

    ``current-task`` holds the task ID (resolution fallback for sessions off the
    task branch); ``context.line`` holds the statusline string. The slug
    directory is created if absent. Both files end with a trailing newline.
    """
    directory = by_worktree_root / slug
    directory.mkdir(parents=True, exist_ok=True)
    (directory / _CURRENT_TASK_NAME).write_text(f'{task_id}\n', encoding='utf-8')
    (directory / _CONTEXT_LINE_NAME).write_text(f'{line}\n', encoding='utf-8')
