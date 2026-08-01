"""
Task-state transfer between machines — pure, ``typer``- and ``git``-free.

The operational state layer (``$DT_STORE``) deliberately does not travel with
git (design §233): it is not cloned, pushed or auto-synced, which is the price
for having no state merge-conflicts. ``dt state export``/``import`` is the
explicit manual channel that moves it between the Developer's machines.

Only **task records and the counter** cross (design §209). The session registry
(``sessions/``) and worktree bindings (``by-worktree/``) describe one specific
machine — another machine's ``session_id`` and paths are useless there — so they
are excluded by construction (this module reads only ``load_all_tasks`` + the
counter). The bundle is a single self-describing JSON document; import resolves
ID clashes by an explicit policy and never lowers the counter. See
``specs/T041-state-transfer/spec.md``.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Literal, NamedTuple

from pydantic import ValidationError

from dreamteam.dt.model import Task, save_task
from dreamteam.dt.tasks import (
    TaskError,
    advance_counter,
    load_all_tasks,
    read_counter,
    record_path,
)

if TYPE_CHECKING:
    from pathlib import Path
    from typing import NoReturn

# Bumped when the on-disk bundle shape changes incompatibly. A file declaring a
# newer version than we understand is rejected rather than misread.
STATE_VERSION = 1
_VERSION_KEY = 'dt_state_version'

OnConflict = Literal['skip', 'overwrite']


class StateBundle(NamedTuple):
    """A portable snapshot: the counter plus every task record."""

    counter: int
    tasks: list[Task]


class ImportResult(NamedTuple):
    """
    Outcome of :func:`import_bundle` for reporting.

    ``added`` — new records written; ``overwritten`` — conflicts replaced;
    ``skipped`` — conflicts kept local; ``counter`` — the counter after import.
    """

    added: list[str]
    overwritten: list[str]
    skipped: list[str]
    counter: int


def _id_num(task_id: str) -> int:
    """Numeric ID part (``T041`` → 41); the caller has validated the format."""
    return int(task_id[1:])


def export_bundle(store: Path) -> StateBundle:
    """
    Read every task record (by canonical ID) and the counter into a bundle.

    Pure over the store — ``sessions/`` and ``by-worktree/`` are never touched,
    so they are excluded automatically (design §209). Records carry their full
    frontmatter (including unknown fields) and body.
    """
    tasks = sorted(load_all_tasks(store).values(), key=lambda task: _id_num(task.id))
    return StateBundle(counter=read_counter(store), tasks=tasks)


def _task_to_dict(task: Task) -> dict[str, object]:
    # `body` is excluded from the model dump (not frontmatter); the bundle keeps
    # the whole record, so re-attach it, mirroring `task_cli._task_obj`.
    data = task.model_dump(mode='json')
    data['body'] = task.body
    return data


def serialize(bundle: StateBundle) -> str:
    r"""Render a bundle as a stable, human-readable JSON document (trailing ``\n``)."""
    payload = {
        _VERSION_KEY: STATE_VERSION,
        'counter': bundle.counter,
        'tasks': [_task_to_dict(task) for task in bundle.tasks],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + '\n'


def _bad(message: str) -> NoReturn:
    """Raise a :class:`TaskError` — a call site so ``mypy`` narrows after it."""
    raise TaskError(message)


def parse(text: str) -> StateBundle:
    """
    Parse a bundle document, raising :class:`TaskError` on anything malformed.

    Validates the version (a newer one is rejected, not misread), the ``counter``
    and ``tasks`` shapes, then reconstructs each :class:`Task` (pydantic coerces
    ISO dates back and restores unknown fields). No filesystem access — a bad
    file fails before :func:`import_bundle` writes anything.
    """
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        message = f'state file is not valid JSON: {exc}'
        raise TaskError(message) from exc
    if not isinstance(raw, dict):
        _bad('state file must be a JSON object')
    version = raw.get(_VERSION_KEY)
    if not isinstance(version, int) or isinstance(version, bool):
        _bad(f'state file is missing an integer {_VERSION_KEY!r}')
    if version > STATE_VERSION:
        _bad(f'state file version {version} is newer than supported ({STATE_VERSION})')
    counter = raw.get('counter')
    if not isinstance(counter, int) or isinstance(counter, bool) or counter < 0:
        _bad('state file `counter` must be a non-negative integer')
    raw_tasks = raw.get('tasks')
    if not isinstance(raw_tasks, list):
        _bad('state file `tasks` must be a list')
    tasks = [_parse_task(entry) for entry in raw_tasks]
    return StateBundle(counter=counter, tasks=tasks)


def _parse_task(entry: object) -> Task:
    if not isinstance(entry, dict):
        _bad('each entry in `tasks` must be an object')
    data = dict(entry)
    body = data.pop('body', '')
    if not isinstance(body, str):
        _bad('task `body` must be a string')
    try:
        return Task(**data, body=body)
    except (ValidationError, TypeError) as exc:
        message = f'invalid task record in state file: {exc}'
        raise TaskError(message) from exc


def import_bundle(
    store: Path, bundle: StateBundle, on_conflict: OnConflict | None
) -> ImportResult:
    """
    Merge a bundle into ``store`` under an ID-conflict policy.

    Every ID is validated and the bundle is checked for duplicates **before** any
    write; without ``on_conflict`` a clash aborts with the full conflict list and
    nothing is written (design §211). ``skip`` keeps local records, ``overwrite``
    replaces them; non-conflicting records are always written. The counter is
    then raised to ``max(local, bundle counter, highest imported ID)`` so
    ``allocate_id`` never reuses a number.
    """
    paths = _validate_ids(store, bundle)
    local_ids = set(load_all_tasks(store))
    conflicts = sorted(
        (task.id for task in bundle.tasks if task.id in local_ids), key=_id_num
    )
    if conflicts and on_conflict is None:
        listed = ', '.join(conflicts)
        message = (
            f'import would clash on {len(conflicts)} existing ID(s): {listed} '
            '(use --on-conflict skip|overwrite)'
        )
        raise TaskError(message)

    added, overwritten, skipped = [], [], []
    for task in bundle.tasks:
        if task.id in local_ids:
            if on_conflict == 'skip':
                skipped.append(task.id)
                continue
            save_task(paths[task.id], task)
            overwritten.append(task.id)
        else:
            save_task(paths[task.id], task)
            added.append(task.id)

    high = max((_id_num(task.id) for task in bundle.tasks), default=0)
    advance_counter(store, max(bundle.counter, high))
    return ImportResult(
        added=added,
        overwritten=overwritten,
        skipped=skipped,
        counter=read_counter(store),
    )


def _validate_ids(store: Path, bundle: StateBundle) -> dict[str, Path]:
    """Validate every bundle ID and reject duplicates, before any write occurs."""
    paths: dict[str, Path] = {}
    for task in bundle.tasks:
        if task.id in paths:
            message = f'duplicate task id in state file: {task.id}'
            raise TaskError(message)
        # `record_path` validates `T[0-9]{3,}` → guards against path traversal
        # from a crafted bundle before it is ever used as a filename.
        paths[task.id] = record_path(store, task.id)
    return paths
