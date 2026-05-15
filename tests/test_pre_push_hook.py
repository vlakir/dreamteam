"""
Fast unit tests for the `template/hooks/pre-push` shell script.

The hook lives at `src/dreamteam/template/hooks/pre-push` and is shipped
to derived projects as package data. It rejects direct pushes to
`main`/`master`, except for the initial bootstrap push (detected by
`remote_sha == 40 zeros`, meaning the remote branch does not exist yet).

Tests invoke `bash hooks/pre-push` directly with a stub stdin matching
the format Git uses (`<local_ref> <local_sha> <remote_ref>
<remote_sha>`, one line per ref). No `dt init` and no real git repo
needed — keeps the suite fast.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

HOOK_PATH = (
    Path(__file__).parent.parent
    / 'src'
    / 'dreamteam'
    / 'template'
    / 'hooks'
    / 'pre-push'
)

ZERO_SHA = '0' * 40
REAL_SHA = 'a' * 40
ANOTHER_SHA = 'b' * 40

_BASH = shutil.which('bash')
if _BASH is None:  # pragma: no cover — every supported dev env has bash
    pytest.skip('bash not available on PATH', allow_module_level=True)


def _run_hook(stdin: str) -> subprocess.CompletedProcess[str]:
    """Invoke the pre-push hook with `stdin` and capture exit + stderr."""
    assert _BASH is not None
    return subprocess.run(
        [_BASH, str(HOOK_PATH)],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )


def test_initial_push_to_main_allowed() -> None:
    """Initial push (`remote_sha == 40 zeros`) into `main` is allowed."""
    stdin = f'refs/heads/main {REAL_SHA} refs/heads/main {ZERO_SHA}\n'
    result = _run_hook(stdin)
    assert result.returncode == 0, result.stderr
    assert 'Initial push detected' in result.stderr


def test_initial_push_to_master_allowed() -> None:
    """Initial push into `master` is allowed (legacy default branch name)."""
    stdin = f'refs/heads/master {REAL_SHA} refs/heads/master {ZERO_SHA}\n'
    result = _run_hook(stdin)
    assert result.returncode == 0, result.stderr
    assert 'Initial push detected' in result.stderr


def test_regular_push_to_main_rejected() -> None:
    """Push from a feature branch into existing `main` is rejected."""
    stdin = f'refs/heads/feat {REAL_SHA} refs/heads/main {ANOTHER_SHA}\n'
    result = _run_hook(stdin)
    assert result.returncode == 1
    assert "Direct push to 'main' is forbidden" in result.stderr


def test_regular_push_to_master_rejected() -> None:
    """Push into existing `master` is rejected."""
    stdin = f'refs/heads/feat {REAL_SHA} refs/heads/master {ANOTHER_SHA}\n'
    result = _run_hook(stdin)
    assert result.returncode == 1
    assert "Direct push to 'master' is forbidden" in result.stderr


def test_push_to_feature_branch_allowed() -> None:
    """Push into a non-protected branch passes regardless of `remote_sha`."""
    stdin = f'refs/heads/feat {REAL_SHA} refs/heads/feat {ANOTHER_SHA}\n'
    result = _run_hook(stdin)
    assert result.returncode == 0, result.stderr


def test_empty_stdin_allowed() -> None:
    """No refs to push (edge case) — hook exits cleanly."""
    result = _run_hook('')
    assert result.returncode == 0, result.stderr


def test_mixed_refs_initial_main_plus_feature() -> None:
    """`git push --all` style: initial main + feature branch — both pass."""
    stdin = (
        f'refs/heads/main {REAL_SHA} refs/heads/main {ZERO_SHA}\n'
        f'refs/heads/feat {ANOTHER_SHA} refs/heads/feat {ZERO_SHA}\n'
    )
    result = _run_hook(stdin)
    assert result.returncode == 0, result.stderr
    assert 'Initial push detected' in result.stderr


def test_mixed_refs_initial_feature_plus_regular_main_rejected() -> None:
    """Initial feature push bundled with regular main push — rejected."""
    stdin = (
        f'refs/heads/feat {REAL_SHA} refs/heads/feat {ZERO_SHA}\n'
        f'refs/heads/main {ANOTHER_SHA} refs/heads/main {REAL_SHA}\n'
    )
    result = _run_hook(stdin)
    assert result.returncode == 1
    assert "Direct push to 'main' is forbidden" in result.stderr
