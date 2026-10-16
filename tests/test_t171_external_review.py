"""Independent external-review regressions using only synthetic offline data."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
from unittest.mock import patch

import pytest

from dreamteam.runtime import inspect_runtime
from tests.test_t171_migration import RULE, SECRET, invoke, put, sandbox, snapshot


@pytest.mark.parametrize('flags', [[], ['--force'], ['--dry-run']])
def test_legacy_update_without_answers_is_actionable_and_read_only(sandbox, flags):
    root, home, _, probe = sandbox
    before, state = snapshot(root), snapshot(home)
    with patch('typer.prompt', side_effect=AssertionError('unexpected prompt')):
        result = invoke(root, 'update', *flags)
    assert result.exit_code == 1, result.output + str(result.exception)
    assert 'dt apply' in result.output
    assert not isinstance(result.exception, (FileNotFoundError, AssertionError))
    if probe.exists():
        assert all(
            json.loads(line)['argv'] == ['--version']
            for line in probe.read_text().splitlines()
        )
    assert snapshot(root) == before
    assert snapshot(home) == state


@pytest.mark.parametrize('mode', ['ok', 'nonzero', 'malformed', 'missing'])
def test_relative_path_binary_is_really_executed_only_for_version(
    sandbox, monkeypatch, mode
):
    root, _, binary, log = sandbox
    relative_bin = root / 'node_modules/.bin'
    relative_bin.mkdir(parents=True)
    installed = relative_bin / 'opencode'
    binary.rename(installed)
    monkeypatch.chdir(root)
    monkeypatch.setenv('PATH', './node_modules/.bin')
    monkeypatch.setenv('T171_PROBE_MODE', mode)
    if mode == 'missing':
        installed.unlink()
    if mode == 'ok':
        actual, version = inspect_runtime()
        assert Path(actual).is_absolute()
        assert Path(actual).samefile(installed)
        assert version == '1.19.0'
    else:
        with pytest.raises(RuntimeError) as caught:
            inspect_runtime()
        assert SECRET not in str(caught.value)
    if mode == 'missing':
        assert not log.exists()
    else:
        records = [json.loads(line) for line in log.read_text().splitlines()]
        assert records == [{'argv': ['--version'], 'cwd': '/'}]


def test_private_home_protects_shared_state_without_chmod_and_keeps_private_recovery(
    sandbox,
):
    root, home, _, _ = sandbox
    home.chmod(0o700)
    state = home / '.local/state'
    state.mkdir(parents=True)
    state.chmod(0o775)
    subprocess.run(['git', 'init', '--quiet', str(root)], check=True, capture_output=True)
    original = (root / 'CLAUDE.md').read_bytes()
    result = invoke(root)
    assert result.exit_code == 0, result.output + str(result.exception)
    assert RULE in (root / 'AGENTS.md').read_text()
    assert not (root / 'CLAUDE.md').exists()
    assert stat.S_IMODE(home.stat().st_mode) == 0o700
    assert stat.S_IMODE(state.stat().st_mode) == 0o775
    recovery = state / 'dreamteam/migrations'
    assert recovery.is_dir()
    for path in recovery.rglob('*'):
        assert not path.is_symlink()
        assert stat.S_IMODE(path.stat().st_mode) == (0o700 if path.is_dir() else 0o600)
    journals = list(recovery.rglob('operation.json'))
    assert len(journals) == 1
    data = json.loads(journals[0].read_text())
    entry = next(item for item in data['entries'] if item['path'] == 'CLAUDE.md')
    assert base64.b64decode(entry['before'], validate=True) == original
    before, stored = snapshot(root), snapshot(home)
    again = invoke(root, 'update')
    assert again.exit_code == 0, again.output + str(again.exception)
    assert snapshot(root) == before
    assert snapshot(home) == stored


@pytest.fixture
def public_state(sandbox, monkeypatch):
    """Only our own top is chmod'ed; no pytest or developer parents are touched."""
    # Resolve and validate the actual shared system temp, not pytest's private
    # basetemp. Fail rather than silently claiming an unsafe ancestry fixture.
    parent = Path('/tmp').resolve(strict=True)
    info = parent.stat()
    assert parent.is_dir() and info.st_uid == 0
    assert stat.S_IMODE(info.st_mode) & stat.S_ISVTX
    with tempfile.TemporaryDirectory(prefix='dt-t171-public-', dir=parent) as owned:
        top = Path(owned)
        top.chmod(0o755)
        home = top / 'home'
        home.mkdir(mode=0o755)
        home.chmod(0o755)
        state = home / 'state'
        state.mkdir(mode=0o700)
        state.chmod(0o777)
        assert not any(
            ancestor.stat().st_uid == os.getuid()
            and not stat.S_IMODE(ancestor.stat().st_mode) & 0o077
            for ancestor in state.parents
        ), 'fixture must have no owner-private protecting ancestor'
        monkeypatch.setenv('HOME', str(home))
        monkeypatch.setenv('XDG_STATE_HOME', str(state))
        for variable, name in {
            'XDG_CONFIG_HOME': 'config',
            'XDG_DATA_HOME': 'data',
            'XDG_CACHE_HOME': 'cache',
        }.items():
            monkeypatch.setenv(variable, str(home / name))
        yield top, state


@pytest.mark.parametrize('command', ['apply', 'update'])
def test_public_writable_state_blocks_before_probe_and_any_mutation(
    sandbox, public_state, command
):
    root, _, _, log = sandbox
    top, state = public_state
    if command == 'update':
        put(root, '.copier-answers.yml', '_commit: 1.7.0\nlanguage: en\n')
    before, outside = snapshot(root), snapshot(top)
    result = invoke(root, command)
    assert result.exit_code == 1, result.output + str(result.exception)
    assert 'unsafe recovery' in result.output.lower()
    assert not log.exists(), 'unsafe storage must block before runtime probe'
    assert snapshot(root) == before
    assert snapshot(top) == outside
    assert stat.S_IMODE(state.stat().st_mode) == 0o777
