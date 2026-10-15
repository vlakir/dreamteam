"""
Explicit recovery adapter for interrupted Ensemble 0.18.0 members.

Run beside the server. Reuse session/worktree; reconcile before acting.
Exactly-once external effects of interrupted tools cannot be guaranteed.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import time
from contextlib import closing
from http import HTTPStatus
from http.client import HTTPConnection, HTTPException
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit

from dreamteam.runtime import ENSEMBLE, TESTED_OPENCODE


def _request(
    server: str, path: str, body: dict[str, Any] | None = None
) -> dict[str, Any]:
    endpoint = urlsplit(server)
    if (
        endpoint.scheme != 'http'
        or endpoint.hostname not in {'localhost', '127.0.0.1', '::1'}
        or endpoint.path not in {'', '/'}
    ):
        message = 'Recovery requires the local server over loopback HTTP.'
        raise RuntimeError(message)
    try:
        with closing(
            HTTPConnection(endpoint.hostname, endpoint.port, timeout=30)
        ) as conn:
            data = json.dumps(body) if body is not None else None
            conn.request(
                'POST' if body is not None else 'GET',
                path,
                data,
                {'Content-Type': 'application/json'},
            )
            with conn.getresponse() as response:
                if response.status not in {
                    HTTPStatus.OK,
                    HTTPStatus.ACCEPTED,
                    HTTPStatus.NO_CONTENT,
                }:
                    message = (
                        f'OpenCode recovery request returned HTTP {response.status}.'
                    )
                    raise RuntimeError(message)
                raw = response.read()
                value = json.loads(raw) if raw else {}
    except (OSError, HTTPException, ValueError, TypeError) as exc:
        message = f'OpenCode recovery connection failed: {exc}'
        raise RuntimeError(message) from exc
    if not isinstance(value, dict):
        message = 'Unexpected server response shape.'
        raise TypeError(message)
    return value


def interrupted(project: Path, database: Path) -> list[dict[str, Any]]:
    """List interrupted members in this exact project, without writes."""
    if not database.is_file():
        return []
    with closing(sqlite3.connect(f'{database.as_uri()}?mode=ro', uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            'SELECT tm.*, t.lead_session_id, t.name AS team_name FROM team_member tm '
            'JOIN team t ON tm.team_id = t.id '
            "WHERE t.project_id = ? AND t.status = 'active' AND tm.status = 'error'",
            (str(project),),
        ).fetchall()
    return [dict(row) for row in rows]


def _git_value(project: Path, *args: str) -> str:
    binary = shutil.which('git')
    if binary is None:
        message = 'Git is required to verify the preserved worktree.'
        raise RuntimeError(message)
    result = subprocess.run(
        [binary, '-C', str(project), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    if result.returncode:
        message = 'Cannot verify the preserved Git worktree; recovery stopped.'
        raise RuntimeError(message)
    return result.stdout.strip()


def _owned_branch(project: Path, worktree: Path, stored: str | None) -> str:
    """Reject a repurposed worktree before restoring member ownership."""
    branch = _git_value(worktree, 'symbolic-ref', '--short', 'HEAD')
    if stored and stored.startswith('ensemble/preserved/'):
        # Ensemble substitutes a preserved ref at restart. The original OpenCode
        # 1.19.0 branch is derived from the generated worktree directory name.
        expected = f'opencode/{worktree.name}'
        if branch != expected:
            message = 'Preserved worktree branch changed; inspect before recovery.'
            raise RuntimeError(message)
        saved_head = _git_value(
            project, 'rev-parse', '--verify', f'refs/heads/{stored}'
        )
        current_head = _git_value(worktree, 'rev-parse', '--verify', 'HEAD')
        if saved_head != current_head:
            message = (
                'Worktree advanced beyond the preserved checkpoint; inspect first.'
            )
            raise RuntimeError(message)
    elif not stored or branch != stored:
        message = 'Worker no longer owns the checked-out branch; recovery stopped.'
        raise RuntimeError(message)
    return branch


def resume_member(
    project: Path,
    database: Path,
    *,
    server: str,
    member: str,
    lead_session: str,
    task: str,
    backup_dir: Path,
) -> str:
    """Resume one verified member/task without creating replacement work."""
    config = json.loads((project / 'opencode.json').read_text())
    if ENSEMBLE not in config.get('plugin', []):
        message = f'Recovery requires the pinned {ENSEMBLE} plugin.'
        raise RuntimeError(message)
    health = _request(server, '/global/health')
    if health.get('version') != TESTED_OPENCODE:
        message = f'Recovery requires OpenCode {TESTED_OPENCODE}.'
        raise RuntimeError(message)
    candidates = [
        row
        for row in interrupted(project, database)
        if row['name'] == member and row['lead_session_id'] == lead_session
    ]
    if len(candidates) != 1:
        message = 'Expected one interrupted member owned by this lead and project.'
        raise RuntimeError(message)
    row = candidates[0]
    session = row['session_id']
    child = _request(server, f'/session/{session}')
    lead = _request(server, f'/session/{lead_session}')
    if child.get('parentID') != lead_session or lead.get('directory') != str(project):
        message = 'Session ownership or server project differs; recovery stopped.'
        raise RuntimeError(message)
    statuses = _request(server, '/session/status')
    if statuses.get(session, {}).get('type', 'idle') != 'idle':
        message = 'Member is running; do not send a duplicate recovery prompt.'
        raise RuntimeError(message)
    worktree = Path(row['worktree_dir'] or '')
    if not worktree.is_absolute() or not worktree.is_dir():
        message = 'Preserved worktree is missing; inspect manually.'
        raise RuntimeError(message)
    common = _git_value(
        project, 'rev-parse', '--path-format=absolute', '--git-common-dir'
    )
    if (
        _git_value(worktree, 'rev-parse', '--path-format=absolute', '--git-common-dir')
        != common
    ):
        message = 'Worktree belongs to a different repository; recovery stopped.'
        raise RuntimeError(message)
    branch = _owned_branch(project, worktree, row['worktree_branch'])
    query = urlencode({'directory': str(project)})
    prompt = (
        f'Recovery after server interruption. Continue EXISTING task {task} '
        f'in the SAME worktree {worktree}. Inspect files, Git state and previous '
        'tool results BEFORE changing anything. Do not replay successful writes, '
        'commits or external actions. Reconcile uncertain side effects; stop and '
        'report if safety cannot be established. Finish the original contract, '
        'validate, commit in your own branch and notify the lead through '
        'team_message. Do not create replacement workers or worktrees.'
    )
    body: dict[str, Any] = {
        'parts': [{'type': 'text', 'text': prompt}],
        'agent': row['agent'],
    }
    if row['model']:
        provider, separator, model = row['model'].partition('/')
        if not separator or not provider or not model:
            message = 'Stored model must use provider/model-id; no state changed.'
            raise RuntimeError(message)
        body['model'] = {'providerID': provider, 'modelID': model}
    backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    backup = backup_dir / f'ensemble-{time.time_ns()}.sqlite'
    backup.touch(mode=0o600, exist_ok=False)
    with closing(
        sqlite3.connect(f'{database.as_uri()}?mode=rw', uri=True, timeout=10)
    ) as conn:
        conn.row_factory = sqlite3.Row
        with closing(sqlite3.connect(backup)) as snapshot:
            conn.backup(snapshot)
        backup.chmod(0o600)
        with conn:
            conn.execute('BEGIN IMMEDIATE')
            selected = conn.execute(
                'SELECT status, depends_on FROM team_task WHERE id = ? AND team_id = ?',
                (task, row['team_id']),
            ).fetchone()
            if selected is None or selected['status'] != 'pending':
                message = 'Task is missing or already claimed/completed.'
                raise RuntimeError(message)
            for dependency in json.loads(selected['depends_on'] or '[]'):
                state = conn.execute(
                    'SELECT status FROM team_task WHERE id = ? AND team_id = ?',
                    (dependency, row['team_id']),
                ).fetchone()
                if state is None or state['status'] != 'completed':
                    message = 'Task has unfinished dependencies.'
                    raise RuntimeError(message)
            changed = conn.execute(
                "UPDATE team_member SET status='ready', execution_status='idle', "
                'reported_to_lead=0, worktree_branch=?, time_updated=? '
                "WHERE team_id=? AND name=? AND status='error' "
                'AND EXISTS (SELECT 1 FROM team WHERE id=team_member.team_id '
                "AND status='active' AND project_id=? AND lead_session_id=?)",
                (
                    branch,
                    time.time_ns() // 1_000_000,
                    row['team_id'],
                    member,
                    str(project),
                    lead_session,
                ),
            ).rowcount
            if changed != 1:
                message = 'Member state changed concurrently; recovery stopped.'
                raise RuntimeError(message)
            conn.execute(
                "UPDATE team_task SET status='in_progress', assignee=?, time_updated=? "
                'WHERE id=? AND team_id=?',
                (member, time.time_ns() // 1_000_000, task, row['team_id']),
            )

    try:
        _request(server, f'/session/{session}/prompt_async?{query}', body)
    except RuntimeError as exc:
        message = (
            f'Delivery uncertain for {session}; inspect before retrying. '
            f'State retained to prevent duplicate delivery. Backup: {backup}'
        )
        raise RuntimeError(message) from exc
    return session
