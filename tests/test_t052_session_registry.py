"""T052 — SessionStart hook and session registry.

Three layers: the pure registry core in `dreamteam.dt.sessions` (serialize /
atomic write / tolerant read against a temp dir), the `dt context --hook`
wrapper driven end to end against a real temporary git repo with the hook's
stdin JSON piped in, and a shape check on the template's shipped
`.claude/settings.json`.
"""

from __future__ import annotations

import datetime
import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

import dreamteam.context_cli as context_cli
from dreamteam.cli import _template_path, app
from dreamteam.dt.model import Task, TaskStatus, save_task
from dreamteam.dt.paths import ensure_store, store_dir
from dreamteam.dt.sessions import (
    SessionRecord,
    current_timestamp,
    read_session_record,
    write_session_record,
)

# --------------------------------------------------------------------------- #
# dt.sessions — pure registry core                                            #
# --------------------------------------------------------------------------- #


def _record() -> SessionRecord:
    return SessionRecord(session_id='S1', cwd='/w/T001', last_seen='2026-08-01T10:00:00+00:00')


def test_write_read_round_trip(tmp_path: Path) -> None:
    path = write_session_record(tmp_path, 'T001', _record())
    assert path == tmp_path / 'T001.json'
    assert read_session_record(tmp_path, 'T001') == _record()


def test_write_creates_missing_dir(tmp_path: Path) -> None:
    sessions = tmp_path / 'sessions'  # does not exist yet
    write_session_record(sessions, 'T001', _record())
    assert (sessions / 'T001.json').is_file()


def test_write_is_json_with_expected_fields(tmp_path: Path) -> None:
    write_session_record(tmp_path, 'T001', _record())
    raw = json.loads((tmp_path / 'T001.json').read_text(encoding='utf-8'))
    assert raw == {
        'session_id': 'S1',
        'cwd': '/w/T001',
        'last_seen': '2026-08-01T10:00:00+00:00',
    }


def test_write_overwrites_last_writer_wins(tmp_path: Path) -> None:
    write_session_record(tmp_path, 'T001', _record())
    newer = SessionRecord(session_id='S2', cwd='/w/T001', last_seen='2026-08-02T00:00:00+00:00')
    write_session_record(tmp_path, 'T001', newer)
    assert read_session_record(tmp_path, 'T001') == newer


def test_write_leaves_no_temp_file(tmp_path: Path) -> None:
    write_session_record(tmp_path, 'T001', _record())
    assert [p.name for p in tmp_path.iterdir()] == ['T001.json']


def test_read_missing_is_none(tmp_path: Path) -> None:
    assert read_session_record(tmp_path, 'T404') is None


def test_read_bad_json_is_none(tmp_path: Path) -> None:
    (tmp_path / 'T001.json').write_text('{not json', encoding='utf-8')
    assert read_session_record(tmp_path, 'T001') is None


def test_read_wrong_shape_is_none(tmp_path: Path) -> None:
    (tmp_path / 'T001.json').write_text('[1, 2, 3]', encoding='utf-8')
    assert read_session_record(tmp_path, 'T001') is None


def test_read_missing_field_is_none(tmp_path: Path) -> None:
    (tmp_path / 'T001.json').write_text(
        json.dumps({'session_id': 'S1', 'cwd': '/w'}), encoding='utf-8'
    )
    assert read_session_record(tmp_path, 'T001') is None  # no last_seen


def test_read_ignores_unknown_fields(tmp_path: Path) -> None:
    (tmp_path / 'T001.json').write_text(
        json.dumps(
            {'session_id': 'S1', 'cwd': '/w', 'last_seen': 'x', 'extra': 42}
        ),
        encoding='utf-8',
    )
    rec = read_session_record(tmp_path, 'T001')
    assert rec == SessionRecord(session_id='S1', cwd='/w', last_seen='x')


def test_current_timestamp_is_tz_aware() -> None:
    stamp = current_timestamp()
    assert datetime.datetime.fromisoformat(stamp).tzinfo is not None


@pytest.mark.parametrize('bad_id', ['../evil', 'T1/../x', 'nope', 'T۰۰۱', ''])
def test_write_rejects_non_canonical_id(tmp_path: Path, bad_id: str) -> None:
    # a crafted task_id must never escape sessions_dir (path traversal)
    with pytest.raises(ValueError, match='invalid task id'):
        write_session_record(tmp_path, bad_id, _record())


@pytest.mark.parametrize('bad_id', ['../evil', 'T1/../x', 'nope'])
def test_read_non_canonical_id_is_none(tmp_path: Path, bad_id: str) -> None:
    assert read_session_record(tmp_path, bad_id) is None


# --------------------------------------------------------------------------- #
# dt context --hook — registry write, real git repo + piped stdin             #
# --------------------------------------------------------------------------- #


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ['git', *args], cwd=repo, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _write_task(
    store: Path, task_id: str, *, status: TaskStatus = 'doing', branch: str | None = None
) -> None:
    task = Task(id=task_id, title=f'task {task_id}', status=status, branch=branch)
    save_task(store / 'tasks' / f'{task_id}.md', task)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A real git repo (one commit on `main`), made the process CWD."""
    root = tmp_path / 'proj'
    root.mkdir()
    _git(root, 'init', '-b', 'main')
    _git(root, 'config', 'user.email', 'test@example.com')
    _git(root, 'config', 'user.name', 'Test')
    (root / 'README.md').write_text('hello\n', encoding='utf-8')
    _git(root, 'add', '.')
    _git(root, 'commit', '-m', 'init')
    monkeypatch.delenv('DT_HOME', raising=False)
    monkeypatch.delenv('DT_TASK', raising=False)
    monkeypatch.chdir(root)
    ensure_store()
    return root


def _hook_stdin(session_id: str = 'S-abc', cwd: str = '/w/T001') -> str:
    return json.dumps(
        {
            'session_id': session_id,
            'cwd': cwd,
            'source': 'startup',
            'hook_event_name': 'SessionStart',
        }
    )


def test_hook_writes_registry_for_bound_session(repo: Path) -> None:
    _write_task(store_dir(), 'T001', branch='T001-x')
    _git(repo, 'checkout', '-q', '-b', 'T001-x')
    result = CliRunner().invoke(app, ['context', '--hook'], input=_hook_stdin())
    assert result.exit_code == 0, result.output
    # payload still emitted
    payload = json.loads(result.output)
    assert payload['hookSpecificOutput']['hookEventName'] == 'SessionStart'
    # registry entry written under the task ID
    rec = read_session_record(store_dir() / 'sessions', 'T001')
    assert rec is not None
    assert rec.session_id == 'S-abc'
    assert rec.cwd == '/w/T001'
    assert datetime.datetime.fromisoformat(rec.last_seen).tzinfo is not None


def test_hook_no_registry_for_unbound_session(repo: Path) -> None:
    _write_task(store_dir(), 'T007', status='doing')  # exists but session on main
    result = CliRunner().invoke(app, ['context', '--hook'], input=_hook_stdin())
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)['hookSpecificOutput']  # payload present
    assert list((store_dir() / 'sessions').iterdir()) == []  # nothing recorded


def test_hook_no_registry_without_session_id(repo: Path) -> None:
    _write_task(store_dir(), 'T001', branch='T001-x')
    _git(repo, 'checkout', '-q', '-b', 'T001-x')
    # empty stdin (no session_id) — bound task, but nothing to key on
    result = CliRunner().invoke(app, ['context', '--hook'], input='')
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)['hookSpecificOutput']
    assert list((store_dir() / 'sessions').iterdir()) == []


def test_hook_registry_uses_process_cwd_when_stdin_cwd_absent(repo: Path) -> None:
    _write_task(store_dir(), 'T001', branch='T001-x')
    _git(repo, 'checkout', '-q', '-b', 'T001-x')
    stdin = json.dumps({'session_id': 'S9', 'source': 'startup'})  # no cwd
    result = CliRunner().invoke(app, ['context', '--hook'], input=stdin)
    assert result.exit_code == 0, result.output
    rec = read_session_record(store_dir() / 'sessions', 'T001')
    assert rec is not None
    assert rec.cwd == str(repo)  # fell back to the process CWD


def test_hook_registry_overwrites_on_resume(repo: Path) -> None:
    _write_task(store_dir(), 'T001', branch='T001-x')
    _git(repo, 'checkout', '-q', '-b', 'T001-x')
    CliRunner().invoke(app, ['context', '--hook'], input=_hook_stdin('S-first'))
    CliRunner().invoke(app, ['context', '--hook'], input=_hook_stdin('S-second'))
    rec = read_session_record(store_dir() / 'sessions', 'T001')
    assert rec is not None
    assert rec.session_id == 'S-second'


def test_hook_registry_failure_does_not_drop_payload(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_task(store_dir(), 'T001', branch='T001-x')
    _git(repo, 'checkout', '-q', '-b', 'T001-x')

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError('disk on fire')

    monkeypatch.setattr(context_cli, 'write_session_record', _boom)
    result = CliRunner().invoke(app, ['context', '--hook'], input=_hook_stdin())
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)['hookSpecificOutput']  # context still injected
    assert list((store_dir() / 'sessions').iterdir()) == []


# --------------------------------------------------------------------------- #
# template — shipped .claude/settings.json                                    #
# --------------------------------------------------------------------------- #


def test_template_settings_wire_the_sessionstart_hook() -> None:
    settings = _template_path() / '.claude' / 'settings.json'
    assert settings.is_file(), 'template .claude/settings.json missing'
    # no Jinja braces → the rendered file equals the source (verify it parses)
    data = json.loads(settings.read_text(encoding='utf-8'))
    session_start = data['hooks']['SessionStart']
    assert isinstance(session_start, list) and session_start
    commands = [
        h['command']
        for group in session_start
        for h in group['hooks']
        if h.get('type') == 'command'
    ]
    assert 'dt context --hook' in commands
    # no matcher → fires on every `source` (design §353)
    assert all('matcher' not in group for group in session_start)
