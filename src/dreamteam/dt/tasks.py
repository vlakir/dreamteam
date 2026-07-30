"""
Task record operations: ID allocation and create / show / move / split.

Pure operational layer atop the T033 store and model — no ``typer``/``copier``
imports, so hooks and the statusline can call it directly. The user-facing
``dt task …`` CLI wrappers live in :mod:`dreamteam.task_cli`.

ID allocation is race-safe by construction: the record file is created with
``O_CREAT | O_EXCL`` as the arbiter, so two parallel worktrees can never claim
the same number. ``counter`` is a high-water-mark hint, not the source of
truth. See ``specs/T034-task-ops/spec.md``.
"""

from __future__ import annotations

import datetime
import os
import re
from typing import TYPE_CHECKING, cast

from dreamteam.dt.model import (
    TASK_STATUSES,
    Task,
    load_task,
    save_task,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

    from dreamteam.dt.model import TaskStatus

_COUNTER_NAME = 'counter'
_ID_MIN_DIGITS = 3
# Canonical task ID: `T` + at least three digits. Validating every externally
# supplied ID before it reaches the filesystem keeps a crafted value like
# `../../repo/.git/x` from escaping `$DT_STORE/tasks` (path traversal) and
# honours the T033 invariant "never operate inside git".
_ID_RE = re.compile(r'^T\d{3,}$')


def _today() -> datetime.date:
    """
    Local calendar date for ``created``/``updated`` stamps.

    Goes through a tz-aware ``now`` and back to local time so ``flake8-datetimez``
    stays satisfied (bare ``date.today()`` is flagged); ``.astimezone()`` yields
    the system-local date rather than UTC, which is what a task tracker wants.
    """
    return datetime.datetime.now(tz=datetime.UTC).astimezone().date()


class TaskError(Exception):
    """
    Raised on task-operation failures.

    Covers a missing task, a reference to an unknown ID, a corrupt counter and
    an invalid status. Distinct from ``DtHomeError`` (store-root resolution):
    this is the record-operations layer. The CLI maps both to a non-zero exit
    code with a plain message, no traceback.
    """


def _tasks_dir(store: Path) -> Path:
    return store / 'tasks'


def _counter_path(store: Path) -> Path:
    return store / _COUNTER_NAME


def _record_path(store: Path, task_id: str) -> Path:
    return _tasks_dir(store) / f'{task_id}.md'


def format_id(number: int) -> str:
    """``T`` + zero-padded number (min 3 digits): 1 → ``T001``, 1000 → ``T1000``."""
    return f'T{number:0{_ID_MIN_DIGITS}d}'


def parse_status(value: str) -> TaskStatus:
    """
    Validate ``value`` against the allowed statuses, returning the typed value.

    ``TASK_STATUSES`` is a plain tuple, so a runtime membership test does not
    narrow ``str`` to the ``TaskStatus`` literal for the type checker — the
    ``cast`` states the invariant the check has just guaranteed.
    """
    if value not in TASK_STATUSES:
        allowed = ', '.join(TASK_STATUSES)
        message = f'unknown status {value!r}; allowed: {allowed}'
        raise TaskError(message)
    return cast('TaskStatus', value)


def _ensure_valid_id(task_id: str, *, role: str = 'task id') -> None:
    """Reject anything that is not a canonical ``T<NNN>`` before path use."""
    if not _ID_RE.match(task_id):
        message = (
            f'invalid {role} {task_id!r}; expected `T` followed by at least '
            'three digits (e.g. T034)'
        )
        raise TaskError(message)


def _read_counter(store: Path) -> int:
    path = _counter_path(store)
    try:
        text = path.read_text(encoding='utf-8').strip()
    except FileNotFoundError:
        return 0
    try:
        value = int(text)
    except ValueError as exc:
        message = f'counter file {path} is corrupt (not an integer): {text!r}'
        raise TaskError(message) from exc
    if value < 0:
        message = f'counter file {path} is corrupt (negative): {value}'
        raise TaskError(message)
    return value


def _write_counter(store: Path, number: int) -> None:
    """Advance ``counter`` to ``max(current, number)`` — never move it back."""
    _counter_path(store).write_text(
        f'{max(_read_counter(store), number)}\n', encoding='utf-8'
    )


def allocate_id(store: Path) -> tuple[str, Path]:
    """
    Reserve the next free task ID atomically; return ``(id, empty record path)``.

    The candidate starts at ``counter + 1``; creating the record file with
    ``O_CREAT | O_EXCL`` is the race arbiter — a taken number raises
    ``FileExistsError``, so we bump and retry (skipping occupied numbers).
    ``counter`` is then advanced to the new high-water mark.
    """
    number = _read_counter(store) + 1
    while True:
        path = _record_path(store, format_id(number))
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            number += 1
            continue
        os.close(fd)
        _write_counter(store, number)
        return format_id(number), path


def _normalize_refs(refs: Iterable[str]) -> list[str]:
    """
    Flatten repeatable + comma-separated option values into clean IDs.

    ``['T003,T005', 'T007']`` → ``['T003', 'T005', 'T007']``. Strips whitespace,
    drops empties, de-duplicates while preserving first-seen order.
    """
    out: list[str] = []
    for raw in refs:
        for token in raw.split(','):
            stripped = token.strip()
            if stripped and stripped not in out:
                out.append(stripped)
    return out


def _require_exists(store: Path, task_id: str, *, role: str) -> None:
    _ensure_valid_id(task_id, role=f'{role} reference')
    if not _record_path(store, task_id).exists():
        message = f'{role} references unknown task {task_id!r}'
        raise TaskError(message)


def load_existing(store: Path, task_id: str) -> Task:
    """Load a task record by ID, or raise :class:`TaskError` if it is absent."""
    _ensure_valid_id(task_id)
    path = _record_path(store, task_id)
    if not path.exists():
        message = f'task {task_id!r} not found in {_tasks_dir(store)}'
        raise TaskError(message)
    return load_task(path)


def show_task(store: Path, task_id: str) -> Task:
    """Load a task record by ID for ``dt task show`` (raises if absent)."""
    return load_existing(store, task_id)


def new_task(
    store: Path,
    title: str,
    *,
    deps: Sequence[str] = (),
    blocks: Sequence[str] = (),
    parent: str | None = None,
    today: datetime.date | None = None,
) -> Task:
    """
    Create a new ``todo`` task record and return it.

    Every reference (``deps``, ``blocks``, ``parent``) is validated to exist
    **before** an ID is allocated, so a typo never leaves a reserved-but-unwritten
    hole in the numbering. Each ``blocks`` target gains a dependency on the new
    task (the new task blocks it) and has its ``updated`` bumped.
    """
    if today is None:
        today = _today()
    if not title.strip():
        message = 'task title must not be empty'
        raise TaskError(message)
    dep_ids = _normalize_refs(deps)
    block_ids = _normalize_refs(blocks)
    for dep in dep_ids:
        _require_exists(store, dep, role='--deps')
    for blocked in block_ids:
        _require_exists(store, blocked, role='--blocks')
    if parent is not None:
        _require_exists(store, parent, role='--parent')

    task_id, path = allocate_id(store)
    task = Task(
        id=task_id,
        title=title,
        status='todo',
        deps=dep_ids,
        parent=parent,
        created=today,
        updated=today,
    )
    save_task(path, task)
    for blocked in block_ids:
        blocked_path = _record_path(store, blocked)
        blocked_task = load_task(blocked_path)
        if task_id not in blocked_task.deps:
            blocked_task.deps.append(task_id)
            blocked_task.updated = today
            save_task(blocked_path, blocked_task)
    return task


def move_task(
    store: Path,
    task_id: str,
    status: str,
    *,
    today: datetime.date | None = None,
) -> Task:
    """Set ``status`` (validated) and bump ``updated``; return the record."""
    if today is None:
        today = _today()
    new_status = parse_status(status)
    task = load_existing(store, task_id)
    task.status = new_status
    task.updated = today
    save_task(_record_path(store, task_id), task)
    return task


def split_task(
    store: Path,
    parent_id: str,
    title: str,
    *,
    today: datetime.date | None = None,
) -> Task:
    """
    Create a new task with ``parent: <parent_id>`` and return it.

    Child only: narrowing the parent's own scope is recorded in the parent's
    body by the agent/methodology, not automated here (design §E9.2).
    """
    _ensure_valid_id(parent_id, role='parent')
    if not _record_path(store, parent_id).exists():
        message = f'parent task {parent_id!r} not found in {_tasks_dir(store)}'
        raise TaskError(message)
    return new_task(store, title, parent=parent_id, today=today)
