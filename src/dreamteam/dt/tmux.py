"""
Best-effort tmux window rename — the one dreamteam effect outside the repo.

``dt task start`` renames the current tmux window to the task ID so a glance at
the window list says which task each pane is on (design §414/§419). Running
outside tmux, without the ``tmux`` binary, or a failed rename are **not**
errors: the function reports what it did and never raises, so the composite
start command's exit code is unaffected. See ``specs/T039-task-start/spec.md``.
"""

from __future__ import annotations

import os
import shutil
import subprocess

_TMUX_ENV = 'TMUX'
_PANE_ENV = 'TMUX_PANE'
# A rename is near-instant; a bound keeps a wedged tmux server from ever hanging
# the composite `dt task start` (this effect is best-effort, never a blocker).
_RENAME_TIMEOUT_S = 3.0


def rename_window(name: str) -> bool:
    """
    Rename the current tmux window to ``name``; return ``True`` iff it happened.

    A no-op (returning ``False``) when not inside tmux (``$TMUX`` unset), when
    the ``tmux`` binary is absent, or when the rename fails for any reason.
    ``-t "$TMUX_PANE"`` targets the agent's own window even when it is not the
    active one (design §419); the flag is omitted only if ``$TMUX_PANE`` is
    unset (older tmux), letting tmux default to the current window.
    """
    if not os.environ.get(_TMUX_ENV):
        return False
    tmux = shutil.which('tmux')
    if tmux is None:
        return False
    pane = os.environ.get(_PANE_ENV)
    target = ['-t', pane] if pane else []
    try:
        result = subprocess.run(
            [tmux, 'rename-window', *target, name],
            check=False,
            capture_output=True,
            text=True,
            timeout=_RENAME_TIMEOUT_S,
        )
    except OSError, subprocess.TimeoutExpired:
        return False
    return result.returncode == 0
