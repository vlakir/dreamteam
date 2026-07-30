"""
``$DT_HOME`` resolution, worktree ``<slug>`` and lazy store creation.

The operational state layer lives in a sibling directory ``<repo>.dt``
(``$DT_HOME``), outside git. This module resolves that root, derives the
store subdirectory layout, computes the per-worktree ``<slug>`` and creates
the directory tree lazily on first use.

``$DT_HOME`` is resolved from the git *common* directory (shared by every
linked worktree), so the same root is returned regardless of which worktree
the call originates from — worktree-independence by construction. See
``specs/T033-store-core/spec.md`` §3.

Note: a tiny ``git`` invocation helper is duplicated here rather than imported
from ``dreamteam.cli`` on purpose — the operational layer must stay importable
without pulling in copier/typer.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

DT_HOME_ENV = 'DT_HOME'
_DT_SUFFIX = '.dt'
_SLUG_LENGTH = 8
_BRANCH_REF_PREFIX = 'refs/heads/'


class DtHomeError(Exception):
    """
    Raised when ``$DT_HOME`` cannot be resolved or the store is unwritable.

    The message is agent- and human-readable and points at the ``DT_HOME``
    override as the escape hatch; callers map it to a non-zero exit code.
    """


def _git_binary() -> str:
    """Return the absolute path to ``git`` or raise :class:`DtHomeError`."""
    found = shutil.which('git')
    if found is None:
        message = (
            'git binary not found on PATH; set the DT_HOME environment '
            'variable to point at the operational state directory explicitly'
        )
        raise DtHomeError(message)
    return found


def _run_git(*args: str, cwd: Path | None = None) -> str:
    """Run ``git <args>`` and return stripped stdout, or raise DtHomeError."""
    try:
        result = subprocess.run(
            [_git_binary(), *args],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        # `cwd` missing/unreadable, or the resolved git binary vanished between
        # `shutil.which` and exec — surface as a DtHomeError, not a raw OSError.
        message = (
            f'failed to run git ({exc}); set the DT_HOME environment variable '
            'to resolve the operational state directory'
        )
        raise DtHomeError(message) from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or 'unknown git failure'
        message = (
            f'not inside a git repository ({detail}); set the DT_HOME '
            'environment variable to resolve the operational state directory'
        )
        raise DtHomeError(message)
    return result.stdout.strip()


def _main_worktree(cwd: Path | None = None) -> Path:
    """
    Root of the *main* working copy (parent of the shared ``.git``).

    Uses the git common directory, which every linked worktree shares. For a
    normal repository the common dir is ``<main-worktree>/.git`` and the main
    worktree is its parent. For a bare repository the common dir *is* the repo
    (basename ``!= .git``), and it is taken as the root directly.
    """
    common_dir = Path(
        _run_git('rev-parse', '--path-format=absolute', '--git-common-dir', cwd=cwd)
    )
    if common_dir.name == '.git':
        return common_dir.parent
    return common_dir


def dt_home(cwd: Path | None = None) -> Path:
    """
    Resolve ``$DT_HOME`` = ``${DT_HOME:-<main-worktree>.dt}``.

    The ``DT_HOME`` environment variable overrides the computed value and is
    the emergency escape hatch (bare repos, non-standard layouts).
    """
    override = os.environ.get(DT_HOME_ENV)
    if override:
        return Path(override)
    main = _main_worktree(cwd=cwd)
    return main.parent / (main.name + _DT_SUFFIX)


def worktree_slug(path: Path | None = None) -> str:
    """
    Eight hex chars of sha1 over a worktree's absolute path.

    Defaults to the *current* working copy (``git rev-parse --show-toplevel``).
    Keys the ``by-worktree/<slug>/`` directory so parallel worktrees never
    collide on their ``current-task`` / ``context.line`` files.
    """
    if path is None:
        path = Path(_run_git('rev-parse', '--show-toplevel'))
    resolved = str(path.resolve())
    # sha1 is a non-cryptographic content hash here (slug key), not a security
    # primitive — `usedforsecurity=False` states that intent to the API.
    digest = hashlib.sha1(resolved.encode(), usedforsecurity=False).hexdigest()
    return digest[:_SLUG_LENGTH]


def git_context(cwd: Path | None = None) -> tuple[Path | None, str | None]:
    """
    Best-effort ``(repo_toplevel, current_branch)`` for the current worktree.

    Returns ``(None, None)`` when not inside a git repository — callers that
    only need the operational store (``DT_HOME`` override, hooks) degrade
    gracefully rather than failing. A detached ``HEAD`` yields a ``None``
    branch (there is no task branch to match against). Used by ``dt task
    check`` to resolve ``spec`` paths and decide the warning/error escalation.
    """
    try:
        toplevel = Path(_run_git('rev-parse', '--show-toplevel', cwd=cwd))
        branch = _run_git('rev-parse', '--abbrev-ref', 'HEAD', cwd=cwd)
    except DtHomeError:
        return None, None
    return toplevel, (None if branch == 'HEAD' else branch)


def store_dir(cwd: Path | None = None) -> Path:
    """``$DT_STORE`` = ``$DT_HOME/store`` — task records, counter, sessions."""
    return dt_home(cwd=cwd) / 'store'


def tasks_dir(cwd: Path | None = None) -> Path:
    """``$DT_STORE/tasks`` — one ``T<NNN>.md`` record per task."""
    return store_dir(cwd=cwd) / 'tasks'


def sessions_dir(cwd: Path | None = None) -> Path:
    """``$DT_STORE/sessions`` — ``<TASK_ID>.json`` session registry (T052)."""
    return store_dir(cwd=cwd) / 'sessions'


def by_worktree_dir(cwd: Path | None = None) -> Path:
    """``$DT_STORE/by-worktree`` — per-worktree ``current-task`` / status line."""
    return store_dir(cwd=cwd) / 'by-worktree'


def worktrees_dir(cwd: Path | None = None) -> Path:
    """``$DT_HOME/worktrees`` — auto-managed task working copies."""
    return dt_home(cwd=cwd) / 'worktrees'


def _create_root(home: Path) -> bool:
    """
    Create ``home`` atomically; return True iff *this* call created it.

    ``exist_ok=False`` makes creation the race arbiter: concurrent callers all
    attempt it, exactly one succeeds, the rest get ``FileExistsError``. Other
    ``OSError``s (permissions, IO) propagate to the caller's mapping.
    """
    try:
        home.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        return False
    return True


def ensure_store(cwd: Path | None = None) -> Path:
    """
    Create ``$DT_HOME`` and its subdirectories, idempotently.

    Prints exactly one informational line to stderr the very first time the
    root is created (i.e. when it did not exist). A non-writable parent yields
    a :class:`DtHomeError` with a ``DT_HOME`` hint rather than a traceback.
    """
    home = dt_home(cwd=cwd)
    # Derive the tree from the already-resolved `home` — the public path
    # helpers each re-resolve `dt_home()` (a git call when DT_HOME is unset),
    # which we must not repeat six times per initialization.
    store = home / 'store'
    subdirs = [
        store,
        store / 'tasks',
        store / 'sessions',
        store / 'by-worktree',
        home / 'worktrees',
    ]
    try:
        first_creation = _create_root(home)
        for directory in subdirs:
            directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        message = (
            f'cannot create the operational state directory at {home}: {exc}; '
            'set the DT_HOME environment variable to a writable location'
        )
        raise DtHomeError(message) from exc
    if first_creation:
        sys.stderr.write(f'dreamteam: created operational state directory {home}\n')
    return home


class WorktreeInfo(NamedTuple):
    """
    One parsed record from ``git worktree list --porcelain``.

    ``branch`` is the short name (``refs/heads/`` stripped) or ``None`` for a
    detached or bare worktree. ``head`` is the commit SHA (``None`` for a bare
    repository). Consumed by the git-free worktree logic in
    :mod:`dreamteam.dt.worktrees`.
    """

    path: Path
    branch: str | None
    head: str | None
    bare: bool
    detached: bool


def _git_returncode(*args: str, cwd: Path | None = None) -> tuple[int, str]:
    """
    Run ``git <args>`` for its exit *code* and stderr; raise on exec failure.

    Some git queries (notably ``merge-base --is-ancestor``) signal their answer
    through the exit code — 0/1 are both valid results, not errors — so they
    cannot go through :func:`_run_git` (which raises on any non-zero). Returns
    ``(returncode, stripped stderr)`` so callers can tell a real answer from a
    git failure (rc 128); a genuine failure to *launch* git still surfaces as
    :class:`DtHomeError`.
    """
    try:
        result = subprocess.run(
            [_git_binary(), *args],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        message = (
            f'failed to run git ({exc}); set the DT_HOME environment variable '
            'to resolve the operational state directory'
        )
        raise DtHomeError(message) from exc
    return result.returncode, result.stderr.strip()


def _parse_worktree_porcelain(porcelain: str) -> list[WorktreeInfo]:
    """Parse ``git worktree list --porcelain`` blocks into :class:`WorktreeInfo`."""
    infos: list[WorktreeInfo] = []
    for raw_block in porcelain.split('\n\n'):
        block = raw_block.strip('\n')
        if not block:
            continue
        path: Path | None = None
        branch: str | None = None
        head: str | None = None
        bare = False
        detached = False
        for line in block.split('\n'):
            if line.startswith('worktree '):
                path = Path(line.removeprefix('worktree '))
            elif line.startswith('HEAD '):
                head = line.removeprefix('HEAD ')
            elif line.startswith('branch '):
                ref = line.removeprefix('branch ')
                branch = ref.removeprefix(_BRANCH_REF_PREFIX)
            elif line == 'detached':
                detached = True
            elif line == 'bare':
                bare = True
        if path is not None:
            infos.append(
                WorktreeInfo(
                    path=path, branch=branch, head=head, bare=bare, detached=detached
                )
            )
    return infos


def list_worktrees(cwd: Path | None = None) -> list[WorktreeInfo]:
    """All worktrees of the current repository (``git worktree list --porcelain``)."""
    return _parse_worktree_porcelain(
        _run_git('worktree', 'list', '--porcelain', cwd=cwd)
    )


def default_base_branch(cwd: Path | None = None) -> str:
    """
    Best-effort local base branch to test "merged" against.

    Prefers the remote default (``origin/HEAD`` → e.g. ``main``); falls back to
    the first existing local ``main``/``master``; defaults to ``main``. The name
    is *local* so merged-ness is checked offline without a fetch.
    """
    try:
        ref = _run_git('symbolic-ref', '--quiet', 'refs/remotes/origin/HEAD', cwd=cwd)
        return ref.rsplit('/', 1)[-1]
    except DtHomeError:
        pass
    for candidate in ('main', 'master'):
        code, _ = _git_returncode(
            'rev-parse', '--verify', '--quiet', f'refs/heads/{candidate}', cwd=cwd
        )
        if code == 0:
            return candidate
    return 'main'


def branch_merged(branch: str, base: str, cwd: Path | None = None) -> bool:
    """
    True iff ``branch`` is an ancestor of ``base`` (fully merged, no squash).

    Uses ``git merge-base --is-ancestor`` (exit 0 = ancestor, 1 = not). Correct
    for merge- and rebase-workflows; a squash-merged branch is *not* an ancestor
    and reads as not-merged — the safe, conservative answer for ``prune``. Any
    other exit code (e.g. 128 — a missing ``branch``/``base`` ref) is a real git
    failure and is raised as :class:`DtHomeError` rather than masked as
    "not merged", so ``prune`` surfaces the cause instead of a misleading skip.
    """
    code, stderr = _git_returncode('merge-base', '--is-ancestor', branch, base, cwd=cwd)
    if code in (0, 1):
        return code == 0
    detail = stderr or 'unknown git failure'
    message = (
        f'cannot determine whether {branch!r} is merged into {base!r} '
        f'(git merge-base exited {code}: {detail})'
    )
    raise DtHomeError(message)


def worktree_dirty(path: Path) -> bool:
    """True iff the worktree at ``path`` has uncommitted changes."""
    return bool(_run_git('status', '--porcelain', cwd=path))


def remove_worktree(path: Path, cwd: Path | None = None) -> None:
    """Remove the worktree at ``path`` (``git worktree remove``); raise on failure."""
    _run_git('worktree', 'remove', str(path), cwd=cwd)


def delete_branch(branch: str, cwd: Path | None = None) -> None:
    """Safe-delete a merged local ``branch`` (``git branch -d``); raise if refused."""
    _run_git('branch', '-d', branch, cwd=cwd)
