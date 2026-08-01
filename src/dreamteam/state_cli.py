"""
``dt state`` CLI: ``export`` / ``import`` — move task state between machines.

Thin Typer wrapper over the git-free core in :mod:`dreamteam.dt.state`. This
layer resolves/creates the store, does the file or stdio I/O (a ``-`` argument
means stdout/stdin, for a direct ``… | ssh other 'dt state import -'`` pipe) and
maps errors to a clean exit 1; the merge logic and (de)serialization stay in the
pure core. Mounted onto the shared app in ``cli.py``, so it is reachable as both
``dt state …`` and ``dreamteam state …``. See ``specs/T041-state-transfer/spec.md``.
"""

from __future__ import annotations

import enum
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, cast

import typer

from dreamteam.dt.paths import DtHomeError, ensure_store, store_dir
from dreamteam.dt.state import (
    export_bundle,
    import_bundle,
    parse,
    serialize,
)
from dreamteam.dt.tasks import TaskError

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import NoReturn

    from dreamteam.dt.state import ImportResult, OnConflict

_EXIT_ERROR = 1
_STDIO = '-'

state_app = typer.Typer(
    name='state',
    help='Move task records and the counter between machines.',
    no_args_is_help=True,
)


class ConflictPolicy(enum.StrEnum):
    """How ``dt state import`` resolves an ID that already exists locally."""

    skip = 'skip'
    overwrite = 'overwrite'


def _die(message: str) -> NoReturn:
    """Print a plain error to stderr and exit 1 (no traceback), like the rest of dt."""
    typer.echo(f'dt state: {message}', err=True)
    raise typer.Exit(code=_EXIT_ERROR)


def _run[T](action: Callable[[Path], T]) -> T:
    """Resolve/create the store, run ``action`` against it, map errors to exit 1."""
    try:
        ensure_store()
        return action(store_dir())
    except (TaskError, DtHomeError, OSError) as exc:
        _die(str(exc))


def _write_output(destination: str, text: str) -> None:
    if destination == _STDIO:
        typer.echo(text, nl=False)  # `text` already ends with a newline
        return
    try:
        Path(destination).write_text(text, encoding='utf-8')
    except OSError as exc:
        _die(str(exc))
    typer.echo(f'exported to {destination}', err=True)


def _read_input(source: str) -> str:
    if source == _STDIO:
        return sys.stdin.read()
    try:
        return Path(source).read_text(encoding='utf-8')
    except OSError as exc:
        _die(str(exc))


@state_app.command('export')
def _export(
    file: Annotated[str, typer.Argument(help="Output path, or '-' for stdout.")],
) -> None:
    """Write task records and the counter to a portable JSON bundle."""
    text = _run(lambda store: serialize(export_bundle(store)))
    _write_output(file, text)


def _emit_import(result: ImportResult, *, json_out: bool) -> None:
    if json_out:
        typer.echo(json.dumps(result._asdict(), ensure_ascii=False, indent=2))
        return
    typer.echo(
        f'imported: {len(result.added)} added, '
        f'{len(result.overwritten)} overwritten, '
        f'{len(result.skipped)} skipped; counter={result.counter}'
    )


@state_app.command('import')
def _import(
    file: Annotated[str, typer.Argument(help="Input path, or '-' for stdin.")],
    *,
    on_conflict: Annotated[
        ConflictPolicy | None,
        typer.Option(
            '--on-conflict',
            help='Resolve ID clashes; without it, import aborts and lists them.',
        ),
    ] = None,
    json_out: Annotated[
        bool, typer.Option('--json', help='Emit the import result as JSON.')
    ] = False,
) -> None:
    """Merge a bundle into the store; ID clashes need ``--on-conflict``."""
    text = _read_input(file)
    policy = cast('OnConflict | None', on_conflict.value if on_conflict else None)
    result = _run(lambda store: import_bundle(store, parse(text), policy))
    _emit_import(result, json_out=json_out)
