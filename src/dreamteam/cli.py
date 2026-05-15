"""Command-line interface for dreamteam."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Annotated, Any

import typer
import yaml
from copier import Worker, run_copy

from dreamteam import __version__

ANSWERS_FILE = '.copier-answers.yml'
BUNDLE_SUBPATH = '.bundle'
# Legacy `_commit` prefix used by derived projects created on
# dreamteam-cli 1.0.0–1.2.0 (before T009 Phase 1). Kept for backward-
# compatible mapping in `_resolve_base_version_tag`.
LEGACY_COMMIT_PREFIX = 'dreamteam-'

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CONFLICTS = 2

app = typer.Typer(
    name='dreamteam',
    help='Project scaffolding CLI with built-in methodology.',
    no_args_is_help=True,
)


def _template_path() -> Path:
    return Path(__file__).parent / 'template'


def _bundle_path() -> Path:
    return _template_path() / BUNDLE_SUBPATH


def _has_git() -> bool:
    """Return True if `git` is available in PATH."""
    return shutil.which('git') is not None


def _resolve_base_version_tag(answers: dict[str, Any]) -> str | None:
    """
    Return the bundle tag (e.g. `1.3.0`) corresponding to `_commit`.

    Bundle tags follow PEP 440 without the `v` prefix because copier's
    `Template.version` uses `dunamai.Pattern.DefaultUnprefixed`.

    Accepts two formats:
    - **Current** (T009 Phase 1+): `_commit: 1.3.0` — used as-is.
    - **Legacy** (1.0.0–1.2.0): `_commit: dreamteam-1.2.0` — stripped
      to `1.2.0`. The bundle is unlikely to contain a tag this old,
      so the caller falls back to overwrite update; still mapped here
      so the warning message names the expected tag.

    Returns None if the answer is missing or unparseable.
    """
    commit = answers.get('_commit')
    if not isinstance(commit, str):
        return None
    commit = commit.strip()
    if commit.startswith(LEGACY_COMMIT_PREFIX):
        version = commit[len(LEGACY_COMMIT_PREFIX) :].strip()
        return version or None
    if commit and not commit.startswith('-'):
        return commit
    return None


def _git_binary() -> str:
    """
    Return absolute path to the `git` binary.

    Callers must check `_has_git()` first; this raises FileNotFoundError
    if git is absent.
    """
    found = shutil.which('git')
    if found is None:
        message = 'git binary not found on PATH'
        raise FileNotFoundError(message)
    return found


def _bundle_has_tag(bundle: Path, tag: str) -> bool:
    """Check whether the given tag exists in the bundle bare repo."""
    if not bundle.is_dir():
        return False
    result = subprocess.run(
        [_git_binary(), 'tag', '--list', tag],
        cwd=bundle,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == tag


def _clone_bundle(bundle: Path, dst: Path) -> None:
    """
    `git clone --local --no-hardlinks <bundle> <dst>` — normal working tree.

    `--local` enables optimizations for local bundle paths; `--no-hardlinks`
    forces object copy instead of hard-link (hard links fail across
    filesystems, e.g. `/home` ↔ `/tmp` on tmpfs).
    """
    subprocess.run(
        [
            _git_binary(),
            'clone',
            '--quiet',
            '--local',
            '--no-hardlinks',
            str(bundle),
            str(dst),
        ],
        check=True,
    )


def _write_answers_file(target: Path, user_answers: dict[str, Any]) -> None:
    """
    Persist `.copier-answers.yml` so that `dreamteam update` can replay.

    Copier does not auto-write the answers file for unversioned local
    templates (no VCS ref), so we materialize it manually:

    - `_commit` = current dreamteam version (PEP 440, no `v` prefix —
      matches dunamai's `DefaultUnprefixed` pattern used by copier).
    - `_src_path` = absolute path to the bundled bare git repo
      inside the installed package. Copier's `Subproject.template`
      reads this on update to construct the *base* template for
      three-way merge. If the bundle is missing (e.g. older wheel),
      falls back to the on-disk template path; `dreamteam update`
      will then take the overwrite fallback path.
    """
    bundle = _bundle_path()
    src_path = bundle if bundle.is_dir() else _template_path()
    payload: dict[str, Any] = {
        '_commit': __version__,
        '_src_path': str(src_path),
    }
    payload.update(user_answers)
    (target / ANSWERS_FILE).write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding='utf-8',
    )


def _read_full_answers(answers_file: Path) -> dict[str, Any]:
    """Read every key in the answers file (including `_commit`, `_src_path`)."""
    return yaml.safe_load(answers_file.read_text(encoding='utf-8'))


def _user_answers(answers: dict[str, Any]) -> dict[str, Any]:
    """Filter copier metadata (`_commit`, `_src_path`, …) out of answers."""
    return {k: v for k, v in answers.items() if not k.startswith('_')}


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


def _overwrite_update(
    target: Path,
    user_answers: dict[str, Any],
) -> None:
    """MVP fallback: re-apply template with overwrite=True (no merge)."""
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


def _three_way_update(
    target: Path,
    user_answers: dict[str, Any],
) -> None:
    """
    Three-way merge against the version tag recorded in `.copier-answers.yml`.

    Copier's `Subproject.template` reads `_src_path` from the answers
    file and constructs a `Template` from it. A bare bundle is not a
    usable template URL (no working tree, no commit checkout), so we
    clone the bundle into a tempdir and pre-populate the subproject's
    cached `last_answers` view to point at the clone — without
    touching the on-disk answers file (writing would make the derived
    project dirty and copier refuses to update dirty repos).

    The persistent answers on disk keep pointing at the bundle path,
    rewritten via `_write_answers_file` after a successful update so
    `_commit` reflects the new dreamteam version.
    """
    with tempfile.TemporaryDirectory(prefix='dreamteam-update-') as tmp:
        clone_dir = Path(tmp) / 'template'
        _clone_bundle(_bundle_path(), clone_dir)
        with Worker(
            src_path=str(clone_dir),
            dst_path=target,
            data=user_answers,
            defaults=True,
            overwrite=True,
            vcs_ref=__version__,
            quiet=False,
            unsafe=True,
        ) as worker:
            # Pre-cache the subproject's view of last_answers so its
            # Template points at the on-disk clone (which has a real
            # working tree) instead of the bare bundle. This bypasses
            # the file-write that would make the derived project dirty.
            answers_file = target / ANSWERS_FILE
            raw = yaml.safe_load(answers_file.read_text(encoding='utf-8')) or {}
            raw['_src_path'] = str(clone_dir)
            worker.subproject.__dict__['last_answers'] = {
                key: value
                for key, value in raw.items()
                if key in {'_src_path', '_commit'} or not key.startswith('_')
            }
            worker.run_update()
    _write_answers_file(target, user_answers)


def _conflict_count(target: Path) -> int:
    """
    Count files in target containing git-style conflict markers.

    Walks the project, looks for the unique `<<<<<<<` marker at the
    start of a line. Cheap heuristic; copier writes standard git
    markers when `run_update` produces conflicts.
    """
    count = 0
    for path in target.rglob('*'):
        if not path.is_file() or '.git' in path.parts:
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeDecodeError, OSError:
            continue
        for line in text.splitlines():
            if line.startswith('<<<<<<<'):
                count += 1
                break
    return count


@app.command()
def update(
    path: Annotated[
        Path,
        typer.Argument(help='Project path (default: current directory).'),
    ] = Path(),
    *,
    force: Annotated[
        bool,
        typer.Option(
            '--force',
            help=(
                'Skip three-way merge; overwrite template-managed files (MVP behavior).'
            ),
        ),
    ] = False,
) -> None:
    """
    Re-apply the dreamteam template to an existing project.

    Default: three-way merge against the base version recorded in
    `.copier-answers.yml`, preserving user edits and writing
    git-style conflict markers where the user and template both
    changed the same region.

    Fallbacks (warn + MVP `overwrite=True`):
    - `--force` flag explicitly requested by the user.
    - `git` not available in PATH.
    - Bundle missing from the installed package (older wheel).
    - Base version tag absent in bundle (derived project predates
      the bundled-history feature).

    Exit codes: 0 — clean update; 1 — error; 2 — conflicts present.
    """
    target = Path(path).expanduser().resolve()
    answers_file = target / ANSWERS_FILE
    if not answers_file.exists():
        typer.echo(
            f'No {ANSWERS_FILE} found in {target}. '
            'Is this a dreamteam-managed project?',
            err=True,
        )
        raise typer.Exit(code=EXIT_ERROR)
    full = _read_full_answers(answers_file)
    user_answers = _user_answers(full)

    if force:
        typer.echo('--force: applying MVP overwrite without merge.', err=True)
        _overwrite_update(target, user_answers)
        typer.echo(f'Project updated at {target} (overwrite mode).')
        raise typer.Exit(code=EXIT_OK)

    if not _has_git():
        typer.echo(
            'WARNING: git not found in PATH; falling back to overwrite update. '
            'Install git for three-way merge support.',
            err=True,
        )
        _overwrite_update(target, user_answers)
        typer.echo(f'Project updated at {target} (overwrite fallback).')
        raise typer.Exit(code=EXIT_OK)

    bundle = _bundle_path()
    if not bundle.is_dir():
        typer.echo(
            'WARNING: bundle missing from installed package; '
            'falling back to overwrite update.',
            err=True,
        )
        _overwrite_update(target, user_answers)
        typer.echo(f'Project updated at {target} (overwrite fallback).')
        raise typer.Exit(code=EXIT_OK)

    base_tag = _resolve_base_version_tag(full)
    if base_tag is None or not _bundle_has_tag(bundle, base_tag):
        typer.echo(
            f'WARNING: base version tag {base_tag!r} absent in bundle '
            '(derived project predates the bundled-history feature); '
            'falling back to overwrite update. Re-run with --force to '
            'suppress this warning.',
            err=True,
        )
        _overwrite_update(target, user_answers)
        typer.echo(f'Project updated at {target} (overwrite fallback).')
        raise typer.Exit(code=EXIT_OK)

    if not (target / '.git').is_dir():
        typer.echo(
            f'ERROR: {target} is not a git repository. Three-way merge '
            'requires the derived project to be git-tracked. Initialize it '
            "first (e.g. `git init && git add -A && git commit -m 'initial'`) "
            'or pass --force to fall back to overwrite update.',
            err=True,
        )
        raise typer.Exit(code=EXIT_ERROR)

    _three_way_update(target, user_answers)
    conflicts = _conflict_count(target)
    if conflicts:
        typer.echo(
            f'Project updated at {target} with {conflicts} conflict(s). '
            'Resolve git-style markers (<<<<<<< / ======= / >>>>>>>) '
            'in the affected files.',
            err=True,
        )
        raise typer.Exit(code=EXIT_CONFLICTS)
    typer.echo(f'Project updated at {target} (three-way merge, no conflicts).')
