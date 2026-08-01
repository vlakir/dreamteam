"""
Session orientation — pure, ``typer``- and ``git``-free.

``dt context`` answers "where am I and what am I working on" after the live
process is gone (reboot, ``/clear``). The binding key is the branch/worktree
(design §299): the branch name already encodes the task ID (``T<NNN>-slug``) and
survives both reboot and context-clear. The task is resolved by the order shared
across every command (§309): ``DT_TASK`` → branch → ``by-worktree/<slug>/
current-task`` → unbound (a legal mode, not an error).

This module is the pure half: :func:`resolve_task_id` applies the order,
:func:`build_context` assembles a :class:`ContextModel` from the store plus
pre-fetched git facts (the worktree list, the main copy's BACKLOG text), and the
renderers produce the human, JSON and hook forms. The git side lives in the
:mod:`dreamteam.context_cli` wrapper. See ``specs/T051-context/spec.md``.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, NamedTuple

from dreamteam.dt.backlog import backlog_divergence, has_managed_block
from dreamteam.dt.starts import context_line, extract_handover
from dreamteam.dt.tasks import load_all_tasks

if TYPE_CHECKING:
    from pathlib import Path

    from dreamteam.dt.backlog import BacklogDivergence
    from dreamteam.dt.model import Task
    from dreamteam.dt.paths import WorktreeInfo

# A whole task ID, and the leading-ID prefix of a `T<NNN>-slug` branch name.
_EXACT_ID_RE = re.compile(r'T[0-9]{3,}$')
_BRANCH_ID_RE = re.compile(r'(T[0-9]{3,})(?:-|$)')
_DONE = 'done'
_DOING = 'doing'
# Hook `additionalContext` budget (design §354: 2000 of a documented 10000).
HOOK_BUDGET = 2000


class ContextModel(NamedTuple):
    """Assembled orientation for one session (bound or unbound)."""

    task: Task | None
    blockers: list[Task]
    divergence: BacklogDivergence | None
    task_worktree: Path | None
    cwd: Path | None
    cwd_mismatch: bool
    doing: list[Task]
    dangling_id: str | None


def _id_num(task_id: str) -> int:
    return int(task_id[1:])


def _branch_task(branch: str | None) -> str | None:
    """Leading ``T<NNN>`` of a ``T<NNN>-slug`` branch, or ``None``."""
    if not branch:
        return None
    match = _BRANCH_ID_RE.match(branch)
    return match.group(1) if match else None


def resolve_task_id(
    *, dt_task: str | None, branch: str | None, bound: str | None
) -> str | None:
    """
    Resolve the session's task by the shared order (design §309).

    ``DT_TASK`` → branch prefix → ``current-task`` binding → ``None`` (unbound).
    A candidate counts only if it is a whole ``T<NNN>`` ID; a non-matching source
    is skipped to the next. Pure: the caller supplies the three raw values.
    """
    for candidate in (dt_task, _branch_task(branch), bound):
        if candidate and _EXACT_ID_RE.fullmatch(candidate):
            return candidate
    return None


def build_context(
    store: Path,
    *,
    resolved_id: str | None,
    cwd: Path | None,
    worktrees: list[WorktreeInfo],
    main_backlog_text: str,
) -> ContextModel:
    """
    Assemble a :class:`ContextModel` from the store and pre-fetched git facts.

    A resolved ID absent from the store is treated as unbound with a dangling-ID
    note (never an error). Blockers are the task's ``deps`` not yet ``done``. The
    task's worktree is matched from ``worktrees`` by branch; ``cwd_mismatch`` is
    set when the session runs outside it. BACKLOG divergence is computed only
    when the main copy carries a managed block and the delta is non-zero.
    """
    tasks = load_all_tasks(store)
    task = tasks.get(resolved_id) if resolved_id else None
    dangling_id = resolved_id if resolved_id and task is None else None

    blockers: list[Task] = []
    task_worktree: Path | None = None
    cwd_mismatch = False
    if task is not None:
        blockers = [
            tasks[dep]
            for dep in task.deps
            if dep in tasks and tasks[dep].status != _DONE
        ]
        task_worktree = _match_worktree(worktrees, task.branch)
        if task_worktree is not None and cwd is not None:
            cwd_mismatch = task_worktree.resolve() != cwd.resolve()

    divergence: BacklogDivergence | None = None
    if has_managed_block(main_backlog_text):
        delta = backlog_divergence(store, main_backlog_text)
        if delta.added or delta.removed:
            divergence = delta

    doing = (
        []
        if task is not None
        else sorted(
            (t for t in tasks.values() if t.status == _DOING),
            key=lambda t: _id_num(t.id),
        )
    )
    return ContextModel(
        task=task,
        blockers=blockers,
        divergence=divergence,
        task_worktree=task_worktree,
        cwd=cwd,
        cwd_mismatch=cwd_mismatch,
        doing=doing,
        dangling_id=dangling_id,
    )


def _match_worktree(worktrees: list[WorktreeInfo], branch: str | None) -> Path | None:
    if branch is None:
        return None
    return next((wt.path for wt in worktrees if wt.branch == branch), None)


def _divergence_line(divergence: BacklogDivergence) -> str:
    return (
        f'BACKLOG.md отстаёт: +{len(divergence.added)} заведено, '
        f'-{len(divergence.removed)} завершена'
    )


def render_human(model: ContextModel) -> str:
    """Render the orientation as a compact human-readable block."""
    lines: list[str] = []
    if model.task is not None:
        lines.extend(_render_task(model.task, model))
    else:
        lines.extend(_render_unbound(model))
    if model.divergence is not None:
        lines.append(_divergence_line(model.divergence))
    return '\n'.join(lines)


def _render_task(task: Task, model: ContextModel) -> list[str]:
    lines = [f'{task.id} [{task.status}] {task.title}']
    for label, value in (
        ('ветка', task.branch),
        ('спека', task.spec),
        ('PR', f'#{task.pr}' if task.pr is not None else None),
    ):
        if value:
            lines.append(f'  {label}: {value}')
    if model.blockers:
        blockers = ', '.join(f'{b.id} [{b.status}]' for b in model.blockers)
        lines.append(f'  блокеры: {blockers}')
    handover = extract_handover(task.body)
    if handover:
        lines.append('  ── Handover ──')
        lines.extend(f'  {line}' for line in handover.splitlines())
    if model.cwd_mismatch and model.task_worktree is not None:
        lines.append(f'  задача {task.id} живёт в {model.task_worktree}')
    return lines


def _render_unbound(model: ContextModel) -> list[str]:
    if model.dangling_id is not None:
        lines = [f'непривязанная сессия (задача {model.dangling_id} не в store)']
    else:
        lines = ['непривязанная сессия']
    if model.doing:
        lines.append('  в работе (doing):')
        lines.extend(f'    {t.id} {t.title}' for t in model.doing)
    return lines


def _task_summary(task: Task) -> dict[str, object]:
    return {'id': task.id, 'status': task.status, 'title': task.title}


def context_json(model: ContextModel) -> dict[str, object]:
    """Render the orientation as a structured object for ``--json``."""
    task = model.task
    return {
        'unbound': task is None,
        'dangling_id': model.dangling_id,
        'task': (
            {
                **_task_summary(task),
                'branch': task.branch,
                'spec': task.spec,
                'pr': task.pr,
                'handover': extract_handover(task.body),
            }
            if task is not None
            else None
        ),
        'blockers': [_task_summary(b) for b in model.blockers],
        'doing': [_task_summary(t) for t in model.doing],
        'cwd_mismatch': model.cwd_mismatch,
        'task_worktree': (
            str(model.task_worktree) if model.task_worktree is not None else None
        ),
        'backlog_divergence': (
            {'added': model.divergence.added, 'removed': model.divergence.removed}
            if model.divergence is not None
            else None
        ),
    }


def render_hook_context(model: ContextModel) -> str:
    """Human render capped at :data:`HOOK_BUDGET` characters for the hook payload."""
    text = render_human(model)
    if len(text) <= HOOK_BUDGET:
        return text
    return text[: HOOK_BUDGET - 1] + '…'


def status_line(task: Task) -> str:
    """The statusline string for ``task`` (re-exported ``context_line``, T039)."""
    return context_line(task)
