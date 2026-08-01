"""
Session-layout recovery — pure, ``typer``- and ``git``-free.

``dt resume`` reads the registry T052 keeps (``sessions/<TASK_ID>.json``) and,
for each task the human was working on, emits the exact command that brings its
live session back after a reboot: ``cd <worktree> && claude --resume
<session_id>`` (design §372–388). This module is the pure half — deciding a
task's recovery *mode* from the record's age and rendering the table / tmux
script / JSON forms; the git facts and the wall clock come from the
:mod:`dreamteam.resume_cli` wrapper.

**Retention, without touching transcripts (ADR).** Claude Code prunes
transcripts after ``cleanupPeriodDays`` (30 by default), so ``claude --resume``
against a pruned session would fail (§388). We never stat the transcript file:
its on-disk path (``~/.claude/projects/<munged-cwd>/<id>.jsonl``) is an
undocumented internal layout, and acceptance §434/#8 forbids reading transcript
internals. Instead the record's ``last_seen`` age is the decoupled signal — a
record older than :data:`RETENTION_DAYS` is downgraded to ``claude`` plus a
Handover hint. See ``specs/T053-resume/spec.md``.
"""

from __future__ import annotations

import datetime
import shlex
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from pathlib import Path

    from dreamteam.dt.model import Task
    from dreamteam.dt.sessions import SessionRecord

# Default Claude Code transcript retention (`cleanupPeriodDays`); the age past
# which a registry record is assumed to have lost its transcript (design §388).
RETENTION_DAYS = 30
# Statuses whose tasks are *not* shown by the bare table / `--tmux` (Clarify Q2):
# a finished task's transcript is rarely wanted back after a reboot.
_INACTIVE_STATUSES = frozenset({'done', 'dropped'})

MODE_RESUME = 'resume'
MODE_STALE = 'stale'
MODE_CONTINUE = 'continue'

_STALE_HINT = 'транскрипт старше {days} дней — восстанови картину по Handover'
_EMPTY_TABLE = 'нет сессий для восстановления'
_TMUX_HEADER = (
    '#!/bin/sh',
    '# dt resume --tmux: раскладка сессий по активным задачам.',
    '# Прочитай и запусти ВНУТРИ работающего tmux — по окну на задачу.',
    '# dreamteam ничего не запускает сам; это просто текст скрипта.',
)


class ResumeEntry(NamedTuple):
    """One recoverable task: where its session lived and how to bring it back."""

    task_id: str
    status: str
    branch: str
    worktree: str
    session_id: str | None
    mode: str
    command: str


def _id_num(task_id: str) -> int:
    return int(task_id[1:])


def is_stale(
    last_seen: str,
    now: datetime.datetime,
    retention_days: int = RETENTION_DAYS,
) -> bool:
    """
    True iff ``last_seen`` is older than ``retention_days`` before ``now``.

    ``last_seen`` is the tz-aware ISO-8601 T052 writes. A value that fails to
    parse, or a naive one (which ``current_timestamp`` never emits, but a
    hand-edited registry might), is treated as **fresh** — better to offer a
    resume than silently hide a session. ``now`` is supplied by the caller
    (tz-aware) so this stays pure and testable.
    """
    try:
        seen = datetime.datetime.fromisoformat(last_seen)
    except ValueError:
        return False
    if seen.tzinfo is None:
        return False
    return now - seen > datetime.timedelta(days=retention_days)


def _resume_command(worktree: str, session_id: str) -> str:
    return f'cd {shlex.quote(worktree)} && claude --resume {shlex.quote(session_id)}'


def _stale_command(worktree: str, retention_days: int) -> str:
    hint = _STALE_HINT.format(days=retention_days)
    return f'cd {shlex.quote(worktree)} && claude  # {hint}'


def _continue_command(worktree: str) -> str:
    return f'cd {shlex.quote(worktree)} && claude --continue'


def resume_entry(
    task: Task,
    record: SessionRecord,
    *,
    now: datetime.datetime,
    retention_days: int = RETENTION_DAYS,
) -> ResumeEntry:
    """
    Build the entry for a task that *has* a registry record.

    The ``cd`` target is the record's ``cwd`` — literally the directory the
    session ran in. A fresh record yields ``claude --resume <id>``; a stale one
    (transcript likely pruned) downgrades to ``claude`` + Handover hint.
    """
    worktree = record.cwd
    if is_stale(record.last_seen, now, retention_days):
        mode = MODE_STALE
        command = _stale_command(worktree, retention_days)
    else:
        mode = MODE_RESUME
        command = _resume_command(worktree, record.session_id)
    return ResumeEntry(
        task_id=task.id,
        status=task.status,
        branch=task.branch or '',
        worktree=worktree,
        session_id=record.session_id,
        mode=mode,
        command=command,
    )


def continue_entry(task: Task, worktree: Path) -> ResumeEntry:
    """
    Build the entry for an address-form task with **no** registry record.

    Degrades to ``claude --continue`` (design §384), which picks the last
    session in the worktree — under "one worktree, one task" the same result.
    """
    path = str(worktree)
    return ResumeEntry(
        task_id=task.id,
        status=task.status,
        branch=task.branch or '',
        worktree=path,
        session_id=None,
        mode=MODE_CONTINUE,
        command=_continue_command(path),
    )


def build_entries(
    records: dict[str, SessionRecord],
    tasks: dict[str, Task],
    *,
    now: datetime.datetime,
    retention_days: int = RETENTION_DAYS,
) -> list[ResumeEntry]:
    """
    Assemble the recovery entries for the bare table / ``--tmux`` forms.

    Only **active** tasks appear (status not done/dropped, Clarify Q2). A record
    whose ``<TASK_ID>`` is absent from the store (dangling — task deleted) is
    skipped: its status is unknown, so it cannot be judged active. Ordered by the
    numeric part of the task ID so the layout is deterministic (``glob`` is not).
    """
    entries: list[ResumeEntry] = []
    for task_id, record in records.items():
        task = tasks.get(task_id)
        if task is None or task.status in _INACTIVE_STATUSES:
            continue
        entries.append(
            resume_entry(task, record, now=now, retention_days=retention_days)
        )
    entries.sort(key=lambda entry: _id_num(entry.task_id))
    return entries


def render_table(entries: list[ResumeEntry]) -> str:
    """Render entries as one human-readable row per task (or an empty note)."""
    if not entries:
        return _EMPTY_TABLE
    return '\n'.join(
        f'{e.task_id}  [{e.status}]  {e.branch}  {e.worktree}  {e.command}'
        for e in entries
    )


def render_tmux(entries: list[ResumeEntry]) -> str:
    """
    Render a one-shot shell script: one tmux window per active task.

    The human reads and runs it inside a live tmux (design §386); dreamteam never
    executes it — it is only text (the "not a process dispatcher" boundary,
    §619). Each task gets ``tmux new-window -n <TASK_ID> -c <worktree>`` (window
    name = task ID, §414) and ``send-keys`` of its recovery command. Every path
    and the command are ``shlex.quote``-d — a worktree path may hold spaces.
    """
    lines = list(_TMUX_HEADER)
    if not entries:
        lines.append('# нет сессий для восстановления')
        return '\n'.join(lines)
    for entry in entries:
        window = shlex.quote(entry.task_id)
        lines.append('')
        lines.append(f'tmux new-window -n {window} -c {shlex.quote(entry.worktree)}')
        lines.append(f'tmux send-keys -t {window} {shlex.quote(entry.command)} Enter')
    return '\n'.join(lines)


def entries_json(entries: list[ResumeEntry]) -> list[dict[str, object]]:
    """Render entries as a list of plain objects for ``--json``."""
    return [
        {
            'task_id': e.task_id,
            'status': e.status,
            'branch': e.branch,
            'worktree': e.worktree,
            'session_id': e.session_id,
            'mode': e.mode,
            'command': e.command,
        }
        for e in entries
    ]
