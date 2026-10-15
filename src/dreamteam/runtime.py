"""Validate and launch the required OpenCode runtime."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from contextlib import closing
from http import HTTPStatus
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from typing import TYPE_CHECKING
from urllib.parse import urlencode, urlsplit

if TYPE_CHECKING:
    from pathlib import Path

TESTED_OPENCODE = '1.19.0'
ENSEMBLE = '@hueyexe/opencode-ensemble@0.18.0'
VERSION_PATTERN = re.compile(r'(?m)^v?(\d+\.\d+\.\d+)\s*$')


def inspect_runtime() -> tuple[str, str]:
    """Return the executable and tested version, or explain the mismatch."""
    binary = shutil.which('opencode')
    if binary is None:
        message = (
            f'OpenCode {TESTED_OPENCODE} is required; install it and add it to PATH.'
        )
        raise RuntimeError(message)
    try:
        result = subprocess.run(
            [binary, '--version'],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        message = f'Cannot inspect OpenCode: {exc}'
        raise RuntimeError(message) from exc
    match = VERSION_PATTERN.search(result.stdout)
    if result.returncode or match is None:
        message = 'OpenCode did not return a valid version.'
        raise RuntimeError(message)
    version = match[1]
    if version != TESTED_OPENCODE:
        message = (
            f'OpenCode {version} found; dreamteam currently requires {TESTED_OPENCODE}.'
        )
        raise RuntimeError(message)
    return binary, version


def launch(
    project: Path,
    *,
    session: str | None = None,
    server: str = 'http://127.0.0.1:4096',
) -> int:
    """Attach to the persistent OpenCode server, optionally resuming a session."""
    binary, _version = inspect_runtime()
    # --dir names a directory on the server, which may not exist on this client.
    inspect_ensemble(server, project)
    args = [binary, 'attach', server, '--dir', str(project)]
    if session:
        args.extend(['--session', session])
    return subprocess.run(args, check=False).returncode


def inspect_ensemble(server: str, project: Path) -> list[str]:
    """Verify that a running OpenCode server loaded Ensemble tools for a project."""
    endpoint = urlsplit(server)
    if endpoint.scheme not in ('http', 'https') or not endpoint.hostname:
        message = 'OpenCode server must use HTTP or HTTPS.'
        raise RuntimeError(message)
    query = urlencode({'directory': str(project)})
    path = f'{endpoint.path.rstrip("/")}/experimental/tool/ids?{query}'
    connection_class = HTTPSConnection if endpoint.scheme == 'https' else HTTPConnection
    try:
        connection = connection_class(endpoint.hostname, endpoint.port, timeout=30)
        with closing(connection) as client:
            client.request('GET', path)
            with client.getresponse() as response:
                if response.status != HTTPStatus.OK:
                    message = f'OpenCode server returned HTTP {response.status}.'
                    raise RuntimeError(message)
                tools = json.load(response)
    except (OSError, HTTPException, ValueError) as exc:
        message = f'Cannot inspect Ensemble tools: {exc}'
        raise RuntimeError(message) from exc
    required = {'team_create', 'team_spawn', 'team_message', 'team_tasks_list'}
    if not isinstance(tools, list) or not required.issubset(
        item for item in tools if isinstance(item, str)
    ):
        message = (
            'Ensemble tools are missing; check plugin installation and server logs.'
        )
        raise RuntimeError(message)
    return sorted(
        item for item in tools if isinstance(item, str) and item.startswith('team_')
    )


def serve(project: Path, *, port: int = 4096) -> int:
    """Run one persistent OpenCode server; clients attach instead of reinitializing."""
    binary, _version = inspect_runtime()
    if not (project / 'opencode.json').is_file():
        message = 'No opencode.json found; initialize or update the project first.'
        raise RuntimeError(message)
    args = [binary, 'serve', '--hostname', '127.0.0.1', '--port', str(port)]
    return subprocess.run(args, cwd=project, check=False).returncode
