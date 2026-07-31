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
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple, cast

from dreamteam.dt.model import (
    TASK_STATUSES,
    Task,
    load_task,
    save_task,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from dreamteam.dt.model import TaskStatus

_COUNTER_NAME = 'counter'
_ID_MIN_DIGITS = 3
# Canonical task ID: `T` + at least three ASCII digits. Validating every
# externally supplied ID before it reaches the filesystem keeps a crafted value
# like `../../repo/.git/x` from escaping `$DT_STORE/tasks` (path traversal) and
# honours the T033 invariant "never operate inside git". `[0-9]` (not `\d`) is
# deliberate: `\d` also matches unicode digits (e.g. `T۰۰۱`), which would yield
# a valid-but-surprising filename — robustness, not a security boundary.
_ID_RE = re.compile(r'^T[0-9]{3,}$')

_ISSUE_ERROR = 'error'
_ISSUE_WARNING = 'warning'


class CheckIssue(NamedTuple):
    """
    One integrity finding from :func:`check_tasks`.

    ``kind`` is ``'error'`` (fails the pre-push gate) or ``'warning'``
    (informational, exit 0). ``task_id`` anchors the finding to a record.
    """

    task_id: str
    kind: str
    message: str

    @property
    def is_error(self) -> bool:
        """True for a gate-failing finding (``kind == 'error'``)."""
        return self.kind == _ISSUE_ERROR


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


def start_task(
    store: Path,
    task_id: str,
    branch: str,
    *,
    today: datetime.date | None = None,
) -> Task:
    """
    Mark a task started: status → ``doing``, record its ``branch``, bump ``updated``.

    The record-mutation half of the composite ``dt task start`` (T039) — the
    git/worktree/binding/tmux effects are orchestrated by the CLI. Saves once.
    Allowed from any status (re-opening a ``done`` task is legitimate).
    """
    if today is None:
        today = _today()
    task = load_existing(store, task_id)
    task.status = 'doing'
    task.branch = branch
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


def _scan_records(store: Path) -> tuple[dict[str, Task], list[tuple[str, str]]]:
    """
    Parse the task records once: canonical dict plus ``id``-drift pairs.

    The filename stem is the canonical ID — it is the ``O_EXCL`` race arbiter
    (T034) and what ``show``/``start`` resolve a path from. Each record's ``id``
    is realigned to its stem so bulk consumers (``find``/``board``/``ready``)
    never emit an ID a follow-up command cannot open. A record whose raw
    frontmatter ``id`` drifted from its filename (a hand-edit) is collected as a
    ``(stem, raw_id)`` pair *before* realignment, so ``check`` can warn about it
    from this single parse — no second read. Stray, non-``T<NNN>`` files are
    ignored so a hand-dropped note never breaks the walk.
    """
    tasks_dir = _tasks_dir(store)
    if not tasks_dir.exists():
        return {}, []
    records: dict[str, Task] = {}
    drift: list[tuple[str, str]] = []
    for path in sorted(tasks_dir.glob('T*.md')):
        if not _ID_RE.match(path.stem):
            continue
        record = load_task(path)
        if record.id != path.stem:
            drift.append((path.stem, record.id))
        record.id = path.stem
        records[path.stem] = record
    return records, drift


def load_all_tasks(store: Path) -> dict[str, Task]:
    """
    Load every task record in ``$DT_STORE/tasks``, keyed by on-disk ID (stem).

    Thin wrapper over :func:`_scan_records` returning only the records (drift is
    for ``check``). Only ``T<NNN>`` stems are loaded and each ``id`` is
    canonicalized to its filename. Shared by ``check``, ``ready``, ``find`` and
    ``board``.
    """
    return _scan_records(store)[0]


def _dangling_ref_issues(tasks: dict[str, Task]) -> list[CheckIssue]:
    """Flag ``deps``/``parent`` pointing at IDs absent from the store."""
    issues: list[CheckIssue] = []
    for task_id in sorted(tasks):
        task = tasks[task_id]
        issues.extend(
            CheckIssue(task_id, _ISSUE_ERROR, f'dep {dep!r} references unknown task')
            for dep in task.deps
            if dep not in tasks
        )
        if task.parent is not None and task.parent not in tasks:
            issues.append(
                CheckIssue(
                    task_id,
                    _ISSUE_ERROR,
                    f'parent {task.parent!r} references unknown task',
                )
            )
    return issues


def _find_cycles(tasks: dict[str, Task]) -> list[list[str]]:
    """
    Return every distinct ``deps`` cycle as a node list (self-loop = length 1).

    Three-colour DFS over the edge "task → each of its ``deps``". Dangling deps
    are skipped here (reported separately). A back-edge to a node still on the
    stack marks a cycle; cycles are de-duplicated by node set so the same loop
    entered from different starts is reported once.
    """
    white, gray, black = 0, 1, 2
    color = dict.fromkeys(tasks, white)
    stack: list[str] = []
    cycles: list[list[str]] = []
    seen: set[frozenset[str]] = set()

    def visit(node: str) -> None:
        color[node] = gray
        stack.append(node)
        for nxt in tasks[node].deps:
            if nxt not in color:
                continue
            if color[nxt] == gray:
                cycle = stack[stack.index(nxt) :]
                key = frozenset(cycle)
                if key not in seen:
                    seen.add(key)
                    cycles.append(cycle)
            elif color[nxt] == white:
                visit(nxt)
        stack.pop()
        color[node] = black

    for node in sorted(tasks):
        if color[node] == white:
            visit(node)
    return cycles


def _cycle_issues(tasks: dict[str, Task]) -> list[CheckIssue]:
    """One error per distinct ``deps`` cycle, anchored to its smallest ID."""
    issues: list[CheckIssue] = []
    for cycle in _find_cycles(tasks):
        path = ' -> '.join([*cycle, cycle[0]])
        issues.append(CheckIssue(min(cycle), _ISSUE_ERROR, f'dependency cycle: {path}'))
    return sorted(issues)


def _spec_present(repo_root: Path, spec: str) -> bool:
    """
    True iff ``spec`` resolves to a real file **inside** ``repo_root``.

    ``spec`` must be repo-root-relative (the record contract). An absolute path
    or one escaping the root via ``..`` is rejected — otherwise
    ``repo_root / spec`` would silently drop the root (absolute) or point
    outside it, letting an unrelated out-of-repo file satisfy the check and
    mask a genuinely missing spec (a false negative in the CI gate).
    """
    rel = Path(spec)
    if rel.is_absolute():
        return False
    target = (repo_root / rel).resolve()
    return target.is_relative_to(repo_root.resolve()) and target.is_file()


def _spec_issues(
    tasks: dict[str, Task],
    repo_root: Path | None,
    current_branch: str | None,
) -> list[CheckIssue]:
    """
    Verify ``spec`` files (soft), escalating on the task's own branch.

    ``spec`` is a path relative to the repository root. A missing (or malformed:
    absolute / escaping) file is a warning — the spec may live only on its
    task's branch. It becomes an error only when that branch is the one
    currently checked out (the file should be here and is not). Without a git
    worktree (``repo_root is None``) the path cannot be resolved, so the check
    is skipped.
    """
    if repo_root is None:
        return []
    issues: list[CheckIssue] = []
    for task_id in sorted(tasks):
        task = tasks[task_id]
        if not task.spec or _spec_present(repo_root, task.spec):
            continue
        on_task_branch = (
            task.branch is not None
            and current_branch is not None
            and task.branch == current_branch
        )
        if on_task_branch:
            issues.append(
                CheckIssue(
                    task_id,
                    _ISSUE_ERROR,
                    f'spec file {task.spec!r} not found (task branch '
                    f'{current_branch!r} is checked out — it must be present here)',
                )
            )
        else:
            issues.append(
                CheckIssue(
                    task_id, _ISSUE_WARNING, f'spec file {task.spec!r} not found'
                )
            )
    return issues


def _id_mismatch_issues(drift: list[tuple[str, str]]) -> list[CheckIssue]:
    """
    Warn for each ``(stem, raw_id)`` where a record's frontmatter ``id`` drifted.

    The filename is authoritative — :func:`_scan_records` realigns ``id`` to the
    stem in memory, so the tool keeps working, but the on-disk record is
    inconsistent (usually a hand-edit). A warning (not an error): the store is
    self-healing, so it must not fail the pre-push gate; the user is told to fix
    the record. Drift is detected in the same single parse, not a second read.
    """
    return [
        CheckIssue(
            stem,
            _ISSUE_WARNING,
            f'frontmatter id {raw_id!r} differs from filename '
            '(the filename is authoritative — update the record)',
        )
        for stem, raw_id in drift
    ]


def check_tasks(
    store: Path,
    *,
    repo_root: Path | None = None,
    current_branch: str | None = None,
) -> list[CheckIssue]:
    """
    Validate the task graph: dangling refs, ``deps`` cycles, ``spec`` files,
    frontmatter-``id``/filename drift.

    Pure and git-free: the git context (``repo_root``, ``current_branch``) is
    supplied by the caller — the CLI resolves it via :func:`dreamteam.dt.paths`,
    tests pass it directly. Records are parsed once (``_scan_records``) for both
    the graph checks and the drift warning. Returns every finding (errors and
    warnings); the caller decides the exit code. See
    ``specs/T035-task-validation/spec.md``.
    """
    tasks, drift = _scan_records(store)
    return [
        *_dangling_ref_issues(tasks),
        *_cycle_issues(tasks),
        *_spec_issues(tasks, repo_root, current_branch),
        *_id_mismatch_issues(drift),
    ]


_W_TITLE = 3
_W_TAG = 2
_W_BRANCH = 2
_W_BODY = 1
# Common-prefix length at/above which two tokens match — crude morphology
# tolerance without a stemmer (`курсор`~`курсора`, `полноэкранный`~`полноэкранном`).
# Below it, only exact equality counts (so `cli` does not hit `client`).
_PREFIX_MIN = 4
_MIN_TOKEN_LEN = 2
_ACTIVE_STATUSES = frozenset({'todo', 'doing', 'review'})
_ACTIVE_FACTOR = 1.0
_INACTIVE_FACTOR = 0.5
_TOKEN_RE = re.compile(r'\w+')


class ScoredTask(NamedTuple):
    """A task with its relevance score from :func:`find_tasks` (score > 0)."""

    task: Task
    score: float


def _tokenize(text: str) -> list[str]:
    """Case-folded Unicode word tokens (Cyrillic included), ≥ 2 chars."""
    return [
        token
        for token in _TOKEN_RE.findall(text.casefold())
        if len(token) >= _MIN_TOKEN_LEN
    ]


def _token_hit(query: str, candidate: str) -> bool:
    """True iff two tokens match by shared prefix (≥ 4) or exact when shorter."""
    shared = len(os.path.commonprefix([query, candidate]))
    return shared >= _PREFIX_MIN or (shared == len(query) == len(candidate))


def _score(task: Task, query_tokens: list[str]) -> float:
    """
    Weighted relevance of ``task`` for the query tokens.

    Each query token contributes the *maximum* field weight among the fields it
    hits (title/tags/branch/body) — not the sum across fields, so a long body
    cannot outrank a title match. The total is scaled by a status factor
    (active tasks above finished ones). Returns 0.0 when nothing matches.
    """
    fields: tuple[tuple[list[str], int], ...] = (
        (_tokenize(task.title), _W_TITLE),
        (_tokenize(' '.join(task.tags)), _W_TAG),
        (_tokenize(task.branch or ''), _W_BRANCH),
        (_tokenize(task.body), _W_BODY),
    )
    total = 0
    for query in query_tokens:
        best = 0
        for tokens, weight in fields:
            if weight > best and any(_token_hit(query, token) for token in tokens):
                best = weight
        total += best
    if total == 0:
        return 0.0
    factor = _ACTIVE_FACTOR if task.status in _ACTIVE_STATUSES else _INACTIVE_FACTOR
    return total * factor


def find_tasks(store: Path, query: str) -> list[ScoredTask]:
    """
    Rank tasks against a free-text ``query`` (highest relevance first).

    Pure and git-free. Searches titles, tags, branches and bodies with field
    weights and morphology-tolerant prefix matching (see the module constants);
    keeps only positive scores. Ties break by ``updated`` (newest first) then
    ID. Empty/whitespace queries yield an empty list. See
    ``specs/T038-task-find/spec.md``.
    """
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []
    scored = [
        ScoredTask(task, score)
        for task in load_all_tasks(store).values()
        if (score := _score(task, query_tokens)) > 0
    ]
    scored.sort(
        key=lambda item: (
            -item.score,
            item.task.updated is None,
            _neg_ordinal(item.task.updated),
            item.task.id,
        )
    )
    return scored


def _neg_ordinal(day: datetime.date | None) -> int:
    """Negated ordinal for newest-first date sorting (``None`` → 0, sorted last)."""
    return 0 if day is None else -day.toordinal()


def ready_tasks(store: Path) -> list[Task]:
    """
    Tasks in ``todo`` whose every ``dep`` exists and is ``done`` (ID order).

    A task with no deps is ready. A dep that is absent from the store leaves the
    task un-ready (its ``done`` status cannot be confirmed) — the dangling
    reference itself is surfaced by :func:`check_tasks`, not here.
    """
    tasks = load_all_tasks(store)
    ready: list[Task] = []
    for task_id in sorted(tasks):
        task = tasks[task_id]
        if task.status != 'todo':
            continue
        if all(dep in tasks and tasks[dep].status == 'done' for dep in task.deps):
            ready.append(task)
    return ready
