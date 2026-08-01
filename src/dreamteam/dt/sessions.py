"""
Session registry — pure, ``typer``- and ``git``-free.

The SessionStart hook (T052) records "which live session works this task, in
which directory" so ``dt resume`` (T053) can rebuild the layout after a reboot.
One file per task (``$DT_STORE/sessions/<TASK_ID>.json``): parallel hooks for
different tasks never contend, and a whole-file atomic replace keeps a
concurrent ``dt resume`` from reading a half-written record (design §360–388).
The binding key lives in the *filename* (``<TASK_ID>``), so it is not repeated
inside the JSON. FS access is fine here — the module stays clear of ``typer``
and ``git`` (the repo's "pure core" invariant), like :mod:`dreamteam.dt.tasks`.
See ``specs/T052-session-registry/spec.md``.
"""

from __future__ import annotations

import datetime
import json
import os
import re
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from pathlib import Path

_SESSION_ID = 'session_id'
_CWD = 'cwd'
_LAST_SEEN = 'last_seen'
# Canonical task ID (mirrors `tasks._ID_RE`): validate before interpolating into
# a filename so a crafted `task_id` like `../../repo/.git/x` cannot escape
# `sessions/` (path traversal). `[0-9]` (not `\d`) rejects unicode digits.
# Duplicated locally rather than imported to keep this core module standalone.
_ID_RE = re.compile(r'^T[0-9]{3,}$')


class SessionRecord(NamedTuple):
    """One live session bound to a task: what to ``--resume`` and where."""

    session_id: str
    cwd: str
    last_seen: str


def current_timestamp() -> str:
    """A tz-aware ISO-8601 ``last_seen`` (local offset; ``flake8-datetimez``)."""
    return datetime.datetime.now(tz=datetime.UTC).astimezone().isoformat()


def _serialize(record: SessionRecord) -> str:
    payload = {
        _SESSION_ID: record.session_id,
        _CWD: record.cwd,
        _LAST_SEEN: record.last_seen,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + '\n'


def write_session_record(
    sessions_dir: Path, task_id: str, record: SessionRecord
) -> Path:
    """
    Write ``<sessions_dir>/<task_id>.json`` atomically; return its path.

    The whole file is replaced — last writer wins, which is correct: a worktree
    hosts one task, so ``last_seen`` simply advances. The temp file sits in the
    same directory so ``os.replace`` is a same-filesystem rename (atomic); a
    concurrent ``dt resume`` reads either the old or the new file, never a torn
    one. The temp name carries the pid so two hooks for the *same* task never
    clash on the scratch file.

    Raises :class:`ValueError` on a non-canonical ``task_id`` — writing under a
    crafted key must fail loudly, never escape ``sessions_dir`` (path traversal).
    """
    if not _ID_RE.match(task_id):
        message = f'invalid task id {task_id!r}'
        raise ValueError(message)
    sessions_dir.mkdir(parents=True, exist_ok=True)
    path = sessions_dir / f'{task_id}.json'
    tmp = sessions_dir / f'.{task_id}.json.{os.getpid()}.tmp'
    tmp.write_text(_serialize(record), encoding='utf-8')
    tmp.replace(path)
    return path


def read_session_record(sessions_dir: Path, task_id: str) -> SessionRecord | None:
    """
    Read ``<task_id>.json`` tolerantly; ``None`` if absent or malformed.

    Groundwork for ``dt resume`` (T053): unknown fields are ignored and a missing
    file, bad JSON, a wrong shape, or a non-canonical ``task_id`` (path-traversal
    guard) yields ``None`` rather than raising — a stale or auto-cleaned registry,
    or a bad user-supplied ID, must never crash resume.
    """
    if not _ID_RE.match(task_id):
        return None
    path = sessions_dir / f'{task_id}.json'
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except OSError, json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    session_id = raw.get(_SESSION_ID)
    cwd = raw.get(_CWD)
    last_seen = raw.get(_LAST_SEEN)
    if not (
        isinstance(session_id, str)
        and isinstance(cwd, str)
        and isinstance(last_seen, str)
    ):
        return None
    return SessionRecord(session_id=session_id, cwd=cwd, last_seen=last_seen)
