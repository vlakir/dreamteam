"""Command-line interface for dreamteam."""

from __future__ import annotations

import difflib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Annotated, Any

import typer
import yaml
from copier import Worker, run_copy

from dreamteam import __version__

ANSWERS_FILE = '.copier-answers.yml'
BUNDLE_SUBPATH = '.bundle'
# T026 §6.3: the roles methodology is delivered as a separate file
# (.claude/team-roles.md) that CLAUDE.md must import. `_ensure_team_roles_import`
# guarantees this line on `dreamteam update` even when the user rewrote
# their CLAUDE.md — see the function docstring.
CLAUDE_MD = 'CLAUDE.md'
TEAM_ROLES_FILE = '.claude/team-roles.md'
TEAM_ROLES_IMPORT = f'@{TEAM_ROLES_FILE}'
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
    """
    Check whether the given tag exists in the bundle bare repo.

    Raises RuntimeError if the `git` invocation itself fails (e.g.
    corrupt bundle) — callers must not silently treat that as
    "tag absent", which could clobber user edits via the overwrite
    fallback (CodeRabbit #46/3).
    """
    if not bundle.is_dir():
        return False
    result = subprocess.run(
        [_git_binary(), 'tag', '--list', tag],
        cwd=bundle,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or 'unknown git failure'
        message = f'cannot inspect bundle at {bundle}: {detail}'
        raise RuntimeError(message)
    return result.stdout.strip() == tag


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


def _ensure_team_roles_import(target: Path) -> None:
    """
    Guarantee CLAUDE.md imports the roles methodology (T026 §6.3).

    `dreamteam update` re-applies the template via run_copy / run_update.
    The template's CLAUDE.md carries an `@.claude/team-roles.md` import
    line, but a user who rewrote their own CLAUDE.md may not receive it
    through the three-way merge. Copier's `_migrations` would be the
    usual delivery hook, but they only fire on `run_update` — not the
    run_copy-based overwrite path this CLI also uses — so the guarantee
    lives here instead.

    Idempotent: the import block is appended only when the line is
    absent, so a fresh render that already carries it, or a second
    `update`, never produces a duplicate. If CLAUDE.md is missing
    (nothing to import into) it is a no-op — the template render, not
    this hook, is what creates CLAUDE.md.

    Guarded on the roles file's presence: the import is added only when
    `.claude/team-roles.md` actually exists in the project. Otherwise —
    e.g. a dreamteam-cli whose bundle predates T026 and did not deliver
    team-roles.md — we would write a dangling `@import` to a missing
    file. In the real §6.3 case team-roles.md always arrives as a new
    file, so the import is still added.
    """
    if not (target / TEAM_ROLES_FILE).is_file():
        return
    claude_md = target / CLAUDE_MD
    if not claude_md.is_file():
        return
    text = claude_md.read_text(encoding='utf-8')
    if TEAM_ROLES_IMPORT in text:
        return
    separator = '' if text.endswith('\n') else '\n'
    block = (
        f'{separator}\n## Team roles (Architect + Designer) — dreamteam\n\n'
        f'{TEAM_ROLES_IMPORT}\n'
    )
    claude_md.write_text(text + block, encoding='utf-8')


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
    _ensure_team_roles_import(target)


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
    _ensure_team_roles_import(target)


def _relfiles(root: Path) -> set[Path]:
    """Relative paths of every file under `root`, excluding `.git`."""
    return {
        path.relative_to(root)
        for path in root.rglob('*')
        if path.is_file() and '.git' not in path.parts
    }


def _emit_dryrun_diff(target: Path, preview: Path) -> int:
    """
    Print per-file unified diff (target → preview) and a summary line.

    Returns the number of files in the preview that contain git-style
    conflict markers (`<<<<<<<`). The caller uses that count to pick
    the exit code: 0 if zero conflicts, EXIT_CONFLICTS otherwise.
    """
    target_files = _relfiles(target)
    preview_files = _relfiles(preview)

    updated: list[Path] = []
    unchanged: list[Path] = []
    added: list[Path] = []
    removed: list[Path] = []

    for rel in sorted(target_files | preview_files, key=str):
        in_target = rel in target_files
        in_preview = rel in preview_files
        if in_target and not in_preview:
            removed.append(rel)
            typer.echo(f'--- a/{rel}\n+++ /dev/null')
            continue
        if in_preview and not in_target:
            added.append(rel)
            typer.echo(f'--- /dev/null\n+++ b/{rel}')
            continue
        t_path = target / rel
        p_path = preview / rel
        try:
            t_text = t_path.read_text(encoding='utf-8')
            p_text = p_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            if t_path.read_bytes() != p_path.read_bytes():
                updated.append(rel)
                typer.echo(f'Binary files a/{rel} and b/{rel} differ')
            else:
                unchanged.append(rel)
            continue
        if t_text == p_text:
            unchanged.append(rel)
            continue
        updated.append(rel)
        diff = ''.join(
            difflib.unified_diff(
                t_text.splitlines(keepends=True),
                p_text.splitlines(keepends=True),
                fromfile=f'a/{rel}',
                tofile=f'b/{rel}',
            )
        )
        typer.echo(diff, nl=False)

    conflicts = _conflict_count(preview)
    typer.echo(
        f'\ndreamteam update --dry-run: '
        f'{len(updated)} would change, '
        f'{len(unchanged)} unchanged, '
        f'{len(added)} added, '
        f'{len(removed)} removed, '
        f'{conflicts} conflicts.'
    )
    return conflicts


def _dry_run(
    target: Path,
    user_answers: dict[str, Any],
) -> int:
    """
    Render what `dreamteam update` would produce, without writing to target.

    Copies the derived (minus `.git`) into a tempdir, re-inits the copy
    as a git repo so copier accepts it as a tracked subproject, runs
    the same update flow as production (three-way merge or overwrite
    fallback per the same chain), then diffs the preview against the
    original target. The target itself is never touched.

    Returns the number of would-be conflict files (drives the exit
    code in `update --dry-run`).
    """
    with tempfile.TemporaryDirectory(prefix='dreamteam-dryrun-') as tmp:
        preview = Path(tmp) / 'preview'
        shutil.copytree(target, preview, ignore=shutil.ignore_patterns('.git'))

        # Re-init preview as git so the three-way merge path is
        # usable. If git is absent we degrade to overwrite preview.
        git_ok = _has_git()
        if git_ok:
            git = _git_binary()
            try:
                subprocess.run(
                    [git, 'init', '--initial-branch=main', '--quiet'],
                    cwd=preview,
                    check=True,
                )
                subprocess.run([git, 'add', '-A'], cwd=preview, check=True)
                subprocess.run(
                    [
                        git,
                        '-c',
                        'user.email=dryrun@dreamteam',
                        '-c',
                        'user.name=dryrun',
                        'commit',
                        '-q',
                        '-m',
                        'dryrun base',
                    ],
                    cwd=preview,
                    check=True,
                )
            except subprocess.CalledProcessError:
                git_ok = False

        bundle = _bundle_path()
        full = _read_full_answers(target / ANSWERS_FILE)
        base_tag = _resolve_base_version_tag(full)
        can_merge = (
            git_ok
            and bundle.is_dir()
            and base_tag is not None
            and _bundle_has_tag(bundle, base_tag)
        )

        if can_merge:
            try:
                _three_way_update(preview, user_answers)
            except Exception:
                # Three-way merge failed mid-flight in preview; rebuild
                # the preview as an overwrite-only snapshot so the user
                # still gets a sensible diff. Production update has its
                # own fallback chain; here we just want the report.
                shutil.rmtree(preview)
                shutil.copytree(target, preview, ignore=shutil.ignore_patterns('.git'))
                _overwrite_update(preview, user_answers)
        else:
            _overwrite_update(preview, user_answers)

        return _emit_dryrun_diff(target, preview)


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
    dry_run: Annotated[
        bool,
        typer.Option(
            '--dry-run',
            help=(
                'Preview the update: per-file unified diff + summary, '
                'no writes to the target.'
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

    if dry_run:
        if force:
            typer.echo(
                '--force has no effect under --dry-run; previewing the '
                'default merge flow (with fallback chain).',
                err=True,
            )
        conflicts = _dry_run(target, user_answers)
        raise typer.Exit(code=EXIT_CONFLICTS if conflicts else EXIT_OK)

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
    try:
        has_base_tag = base_tag is not None and _bundle_has_tag(bundle, base_tag)
    except RuntimeError as exc:
        typer.echo(f'ERROR: cannot inspect bundled history: {exc}', err=True)
        raise typer.Exit(code=EXIT_ERROR) from exc
    if not has_base_tag:
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


# ---------------------------------------------------------------------------
# `dt apply` command (T018) — layer dreamteam template on top of an existing
# project that was scaffolded by something else (PyCharm new-project wizard,
# `poetry new`, `hatch new`, manual `mkdir`). Per-file 4-way conflict prompt
# in TTY mode; `--on-conflict <keep|overwrite|save-as-new>` for non-interactive.
# ---------------------------------------------------------------------------

CONFLICT_CHOICES = ('keep', 'overwrite', 'save-as-new')


def _print_file_diff(target_file: Path, preview_file: Path, rel: Path) -> None:
    """Write unified diff (target → preview) for one file to stdout."""
    try:
        t_text = target_file.read_text(encoding='utf-8')
        p_text = preview_file.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        typer.echo(f'Binary files a/{rel} and b/{rel} differ', nl=True)
        return
    diff = ''.join(
        difflib.unified_diff(
            t_text.splitlines(keepends=True),
            p_text.splitlines(keepends=True),
            fromfile=f'a/{rel}',
            tofile=f'b/{rel}',
        )
    )
    typer.echo(diff, nl=False)


def _prompt_conflict_choice(rel: Path, target_file: Path, preview_file: Path) -> str:
    """
    Interactive 4-way conflict prompt: keep / overwrite / diff / save-as-new.

    `diff` loops back to the prompt (informational only); the three other
    options are terminal and return the action string used by
    `_execute_apply_decisions`. Defaults to `keep` if the user hits Enter
    without typing anything (least-destructive default).
    """
    while True:
        choice = (
            typer.prompt(
                f'{rel}: conflict — [k]eep / [o]verwrite / [d]iff / [s]ave-as-new',
                default='k',
            )
            .strip()
            .lower()
        )
        if choice in ('k', 'keep', ''):
            return 'keep'
        if choice in ('o', 'overwrite'):
            return 'overwrite'
        if choice in ('s', 'save', 'save-as-new'):
            return 'save-as-new'
        if choice in ('d', 'diff'):
            _print_file_diff(target_file, preview_file, rel)
            continue
        typer.echo(f'unknown choice {choice!r}; expected k/o/d/s')


def _resolve_conflict(
    rel: Path,
    target_file: Path,
    preview_file: Path,
    on_conflict: str | None,
) -> str:
    """Return one of 'keep' / 'overwrite' / 'save-as-new' for a conflict."""
    if on_conflict is not None:
        return on_conflict
    return _prompt_conflict_choice(rel, target_file, preview_file)


def _files_equal(target_file: Path, preview_file: Path) -> bool:
    """Compare two files; tolerate binary content."""
    try:
        return target_file.read_text(encoding='utf-8') == preview_file.read_text(
            encoding='utf-8',
        )
    except UnicodeDecodeError:
        return target_file.read_bytes() == preview_file.read_bytes()


def _classify_apply_files(
    target: Path,
    preview: Path,
    on_conflict: str | None,
    *,
    dry_run: bool,
) -> list[tuple[Path, str]]:
    """
    Walk the preview tree and decide per file what to do.

    Returns a list of (rel_path, action). Actions:
    - 'create'        — target file absent, create from preview.
    - 'unchanged'     — both exist with identical content; no-op.
    - 'keep'          — conflict, user chose to keep target as-is.
    - 'overwrite'     — conflict, user chose template version.
    - 'save-as-new'   — conflict, write preview to `<file>.dt-new`.
    - 'conflict-dry'  — dry-run only; would prompt.
    """
    decisions: list[tuple[Path, str]] = []
    for rel in sorted(_relfiles(preview), key=str):
        target_file = target / rel
        preview_file = preview / rel
        if not target_file.exists():
            decisions.append((rel, 'create'))
            continue
        if _files_equal(target_file, preview_file):
            decisions.append((rel, 'unchanged'))
            continue
        if dry_run:
            decisions.append((rel, 'conflict-dry'))
            continue
        action = _resolve_conflict(rel, target_file, preview_file, on_conflict)
        decisions.append((rel, action))
    return decisions


def _execute_apply_decisions(
    target: Path,
    preview: Path,
    decisions: list[tuple[Path, str]],
    *,
    dry_run: bool,
) -> dict[str, int]:
    """Apply decisions to the target (skip writes on dry-run); return summary."""
    summary: dict[str, int] = {
        'create': 0,
        'unchanged': 0,
        'keep': 0,
        'overwrite': 0,
        'save-as-new': 0,
        'conflict-dry': 0,
    }
    for rel, action in decisions:
        summary[action] = summary.get(action, 0) + 1
        if dry_run:
            continue
        target_file = target / rel
        preview_file = preview / rel
        if action in ('create', 'overwrite'):
            target_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(preview_file, target_file)
        elif action == 'save-as-new':
            new_path = target_file.with_name(target_file.name + '.dt-new')
            shutil.copy2(preview_file, new_path)
        # 'keep' / 'unchanged' — no-op
    return summary


def _print_apply_summary(summary: dict[str, int], *, dry_run: bool) -> None:
    """One-line summary in the same shape as `dt update --dry-run`."""
    label = 'dreamteam apply --dry-run' if dry_run else 'dreamteam apply'
    parts = [
        f'{summary["create"]} created',
        f'{summary["unchanged"]} unchanged',
        f'{summary["keep"]} kept',
        f'{summary["overwrite"]} overwritten',
        f'{summary["save-as-new"]} saved as .dt-new',
    ]
    if dry_run and summary.get('conflict-dry'):
        parts.append(f'{summary["conflict-dry"]} would conflict')
    typer.echo(f'{label}: ' + ', '.join(parts) + '.')


def _render_apply_preview(
    preview: Path,
    extra_data: dict[str, str],
    *,
    defaults: bool,
) -> dict[str, Any]:
    """Run copier into `preview`; return captured user answers."""
    with Worker(
        src_path=str(_template_path()),
        dst_path=preview,
        data=extra_data,
        defaults=defaults,
        quiet=True,
        unsafe=True,
    ) as worker:
        worker.run_copy()
        return dict(worker.answers.user)


@app.command()
def apply(
    path: Annotated[
        Path,
        typer.Argument(help='Project path (default: current directory).'),
    ] = Path(),
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
    dry_run: Annotated[
        bool,
        typer.Option(
            '--dry-run',
            help='Plan only; print decision counts without writing files.',
        ),
    ] = False,
    on_conflict: Annotated[
        str | None,
        typer.Option(
            '--on-conflict',
            help=(
                'How to resolve conflicts non-interactively: '
                'keep | overwrite | save-as-new. Required when stdin '
                'is not a TTY (e.g. CI).'
            ),
        ),
    ] = None,
) -> None:
    """
    Apply the dreamteam template on top of an existing project.

    Use this when the target was scaffolded by something else (PyCharm,
    `poetry new`, `hatch new`, manual `mkdir`) and you want to layer
    dreamteam's methodology + tooling on top. Conflicts on files that
    already exist in the target are resolved per-file: kept as-is,
    overwritten with the template version, or saved next to the original
    as `<file>.dt-new` for manual merge.

    For a brand-new empty directory `dt init` is the simpler choice; for
    a target that was already `dt init`-ed (carries `.copier-answers.yml`)
    use `dt update`.
    """
    target = Path(path).expanduser().resolve()
    if target.exists() and not target.is_dir():
        typer.echo(f'ERROR: {target} is not a directory.', err=True)
        raise typer.Exit(code=EXIT_ERROR)
    if not target.exists():
        target.mkdir(parents=True)

    answers_file = target / ANSWERS_FILE
    if answers_file.exists():
        typer.echo(
            f'{target} already has {ANSWERS_FILE}; this is a dreamteam-managed '
            'project. Use `dt update` instead of `dt apply`.',
            err=True,
        )
        raise typer.Exit(code=EXIT_ERROR)

    if on_conflict is not None and on_conflict not in CONFLICT_CHOICES:
        typer.echo(
            f'ERROR: --on-conflict must be one of: {", ".join(CONFLICT_CHOICES)}.',
            err=True,
        )
        raise typer.Exit(code=EXIT_ERROR)

    if not dry_run and on_conflict is None and not sys.stdin.isatty():
        typer.echo(
            'ERROR: stdin is not a TTY; pass --on-conflict '
            f'<{"|".join(CONFLICT_CHOICES)}> for non-interactive runs.',
            err=True,
        )
        raise typer.Exit(code=EXIT_ERROR)

    extra_data = _parse_data(data or [])

    with tempfile.TemporaryDirectory(prefix='dreamteam-apply-') as tmp:
        preview = Path(tmp) / 'preview'
        user_answers = _render_apply_preview(
            preview,
            extra_data,
            defaults=defaults,
        )
        decisions = _classify_apply_files(
            target,
            preview,
            on_conflict,
            dry_run=dry_run,
        )
        summary = _execute_apply_decisions(
            target,
            preview,
            decisions,
            dry_run=dry_run,
        )

    if not dry_run:
        _write_answers_file(target, user_answers)

    _print_apply_summary(summary, dry_run=dry_run)
