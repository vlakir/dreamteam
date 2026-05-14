"""Command-line interface for dreamteam."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from copier import run_copy

from dreamteam import __version__

app = typer.Typer(
    name='dreamteam',
    help='Project scaffolding CLI with built-in methodology.',
    no_args_is_help=True,
)


def _template_path() -> Path:
    return Path(__file__).parent / 'template'


def _version_callback(*, value: bool) -> None:
    if value:
        typer.echo(f'dreamteam {__version__}')
        raise typer.Exit


@app.callback()
def _main(
    *,
    version: Annotated[
        bool,
        typer.Option(
            '--version',
            callback=_version_callback,
            is_eager=True,
            help='Show version and exit.',
        ),
    ] = False,
) -> None:
    """Dreamteam — project scaffolding CLI."""


@app.command()
def init(
    path: Path,
    *,
    defaults: Annotated[
        bool,
        typer.Option(
            '--defaults',
            help='Use default values for all prompts (non-interactive).',
        ),
    ] = False,
) -> None:
    """Initialize a new project from the dreamteam template."""
    target = Path(path).expanduser().resolve()
    run_copy(
        src_path=str(_template_path()),
        dst_path=str(target),
        defaults=defaults,
        quiet=False,
    )
    typer.echo(f'Project initialized at {target}')


@app.command()
def update() -> None:
    """Update an existing dreamteam-managed project to the latest template (stub)."""
    typer.echo('Stub: would run copier update in current directory')
