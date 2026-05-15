"""Command-line interface for dreamteam."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer
import yaml
from copier import Worker, run_copy

from dreamteam import __version__

ANSWERS_FILE = '.copier-answers.yml'

app = typer.Typer(
    name='dreamteam',
    help='Project scaffolding CLI with built-in methodology.',
    no_args_is_help=True,
)


def _template_path() -> Path:
    return Path(__file__).parent / 'template'


def _write_answers_file(target: Path, user_answers: dict[str, Any]) -> None:
    """
    Persist `.copier-answers.yml` so that `dreamteam update` can replay.

    Copier does not auto-write the answers file for unversioned local
    templates (no VCS ref), so we materialize it manually with
    `_commit` (dreamteam package version) and `_src_path` (current
    package template path).
    """
    payload: dict[str, Any] = {
        '_commit': f'dreamteam-{__version__}',
        '_src_path': str(_template_path()),
    }
    payload.update(user_answers)
    (target / ANSWERS_FILE).write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding='utf-8',
    )


def _read_user_answers(answers_file: Path) -> dict[str, Any]:
    """Read user answers (everything except keys starting with `_`)."""
    data = yaml.safe_load(answers_file.read_text(encoding='utf-8'))
    return {k: v for k, v in data.items() if not k.startswith('_')}


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


def _parse_data(items: list[str]) -> dict[str, str]:
    """Parse repeated `--data key=value` options into a dict."""
    parsed: dict[str, str] = {}
    for item in items:
        if '=' not in item:
            message = f"--data expects 'key=value', got '{item}'"
            raise typer.BadParameter(message)
        key, _, value = item.partition('=')
        parsed[key.strip()] = value
    return parsed


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
    data: Annotated[
        list[str] | None,
        typer.Option(
            '--data',
            help='Set a copier answer: --data key=value (repeatable).',
        ),
    ] = None,
) -> None:
    """Initialize a new project from the dreamteam template."""
    target = Path(path).expanduser().resolve()
    extra_data = _parse_data(data or [])
    # Worker (instead of run_copy) is used to capture user answers
    # for the subsequent answers-file write. run_copy returns None,
    # so we cannot extract answers from it.
    # Worker is marked as internal API in copier — accept deprecation
    # warning until upstream provides a public way to capture answers.
    with Worker(
        src_path=str(_template_path()),
        dst_path=target,
        data=extra_data,
        defaults=defaults,
        quiet=False,
        # Template is shipped as package-data; trust _tasks (multilang
        # post-render script). Without unsafe=True copier refuses any
        # template using _tasks / extensions / jinja extras.
        unsafe=True,
    ) as worker:
        worker.run_copy()
        user_answers = dict(worker.answers.user)
    _write_answers_file(target, user_answers)
    typer.echo(f'Project initialized at {target}.')


@app.command()
def update(
    path: Annotated[
        Path,
        typer.Argument(help='Project path (default: current directory).'),
    ] = Path(),
) -> None:
    """
    Re-apply the dreamteam template to an existing project.

    MVP behavior: re-renders all template files with stored answers,
    overwriting local changes to template-managed files. Use with
    caution. Full diff/merge update (copier.run_update) requires
    git-tracked template, which is non-trivial for PyPI-distributed
    packages — planned as a follow-up.
    """
    target = Path(path).expanduser().resolve()
    answers_file = target / ANSWERS_FILE
    if not answers_file.exists():
        typer.echo(
            f'No {ANSWERS_FILE} found in {target}. '
            'Is this a dreamteam-managed project?',
            err=True,
        )
        raise typer.Exit(code=1)
    user_answers = _read_user_answers(answers_file)
    run_copy(
        src_path=str(_template_path()),
        dst_path=str(target),
        data=user_answers,
        defaults=True,
        overwrite=True,
        quiet=False,
        unsafe=True,
    )
    _write_answers_file(target, user_answers)
    typer.echo(f'Project updated at {target} (template re-applied).')
