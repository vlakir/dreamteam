"""Tests for the dreamteam CLI."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dreamteam import __version__
from dreamteam.cli import (
    EXIT_CONFLICTS,
    EXIT_ERROR,
    EXIT_OK,
    LEGACY_COMMIT_PREFIX,
    TEAM_ROLES_IMPORT,
    _emit_dryrun_diff,
    _ensure_team_roles_import,
    _has_git,
    _relfiles,
    _resolve_base_version_tag,
    _restore_git,
    app,
)

runner = CliRunner()


def _git_init(target: Path) -> None:
    """Initialize a derived project as a git repo with one commit."""
    git = shutil.which('git')
    assert git is not None, 'git required for tests'
    subprocess.run([git, 'init', '--initial-branch=main', '--quiet'], cwd=target, check=True)
    subprocess.run([git, 'add', '-A'], cwd=target, check=True)
    subprocess.run(
        [git, '-c', 'user.email=t@t', '-c', 'user.name=t', 'commit', '-q', '-m', 'initial'],
        cwd=target,
        check=True,
    )


def test_version_flag_prints_version() -> None:
    """`dreamteam --version` prints the version and exits 0."""
    result = runner.invoke(app, ['--version'])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_init_creates_project(tmp_path: Path) -> None:
    """`dreamteam init <path> --defaults` creates a full project skeleton."""
    target = tmp_path / 'my-project'
    result = runner.invoke(app, ['init', str(target), '--defaults'])
    assert result.exit_code == 0, result.output
    assert target.is_dir()
    expected_files = [
        'README.md',
        'CLAUDE.md',
        'CONCEPT.md',
        'DECISIONS.md',
        'CHANGELOG.md',
        'BACKLOG.md',
        'BOARD.md',
        'pyproject.toml',
        'hooks/pre-push',
        'specs/spec-template.md',
        'src/main.py',
        'tests/test_main.py',
    ]
    for relative in expected_files:
        assert (target / relative).exists(), f'missing {relative}'
    # `.bundle/` is internal machinery — must never be copied into derived.
    assert not (target / '.bundle').exists(), '.bundle leaked into derived'
    readme = (target / 'README.md').read_text(encoding='utf-8')
    assert 'my-project' in readme
    pyproject = (target / 'pyproject.toml').read_text(encoding='utf-8')
    assert 'name = "my-project"' in pyproject
    main_py = (target / 'src' / 'main.py').read_text(encoding='utf-8')
    assert 'Hello from my-project!' in main_py


def test_init_target_appears_in_output(tmp_path: Path) -> None:
    """`dreamteam init` prints the resolved target path."""
    target = tmp_path / 'another-project'
    result = runner.invoke(app, ['init', str(target), '--defaults'])
    assert result.exit_code == 0
    assert str(target) in result.output


def test_update_after_init_clean(tmp_path: Path) -> None:
    """
    `dreamteam update` on a git-tracked derived project with no edits
    performs a clean three-way merge against the bundled v<version>
    snapshot and exits 0.
    """
    target = tmp_path / 'updatable'
    init_result = runner.invoke(app, ['init', str(target), '--defaults'])
    assert init_result.exit_code == 0, init_result.output
    assert (target / '.copier-answers.yml').exists()
    _git_init(target)
    update_result = runner.invoke(app, ['update', str(target)])
    assert update_result.exit_code == EXIT_OK, update_result.output
    assert 'three-way merge' in update_result.output.lower()


def test_update_force_uses_overwrite(tmp_path: Path) -> None:
    """`dreamteam update --force` bypasses three-way merge (MVP overwrite)."""
    target = tmp_path / 'forced'
    init_result = runner.invoke(app, ['init', str(target), '--defaults'])
    assert init_result.exit_code == 0, init_result.output
    # No git init needed: --force skips the merge path entirely.
    update_result = runner.invoke(app, ['update', str(target), '--force'])
    assert update_result.exit_code == EXIT_OK, update_result.output
    assert 'overwrite' in update_result.output.lower()


def test_update_without_git_repo_fails(tmp_path: Path) -> None:
    """
    Without `git init` on derived (and without --force), update fails
    with a clear error pointing the user to init the repo.
    """
    target = tmp_path / 'no-git'
    init_result = runner.invoke(app, ['init', str(target), '--defaults'])
    assert init_result.exit_code == 0, init_result.output
    update_result = runner.invoke(app, ['update', str(target)])
    assert update_result.exit_code == EXIT_ERROR
    assert 'not a git repository' in (update_result.output + update_result.stderr)


def test_update_without_answers_file_fails(tmp_path: Path) -> None:
    """`dreamteam update` errors if no `.copier-answers.yml` is present."""
    target = tmp_path / 'no-answers'
    target.mkdir()
    result = runner.invoke(app, ['update', str(target)])
    assert result.exit_code == EXIT_ERROR
    assert 'No .copier-answers.yml' in (result.output + result.stderr)


def test_help_lists_subcommands() -> None:
    """`dreamteam --help` shows the available subcommands."""
    result = runner.invoke(app, ['--help'])
    assert result.exit_code == 0
    assert 'init' in result.output
    assert 'update' in result.output


def test_no_args_shows_help() -> None:
    """`dreamteam` without args shows help and exits non-zero."""
    result = runner.invoke(app, [])
    assert result.exit_code != 0
    assert 'init' in result.output or 'Commands' in result.output


def test_resolve_base_version_tag_current() -> None:
    """Current format `_commit: 1.3.0` is returned as-is."""
    assert _resolve_base_version_tag({'_commit': '1.3.0'}) == '1.3.0'
    assert _resolve_base_version_tag({'_commit': '2.0.0rc1'}) == '2.0.0rc1'


def test_resolve_base_version_tag_legacy() -> None:
    """Legacy `dreamteam-1.2.0` is stripped of the prefix."""
    legacy = f'{LEGACY_COMMIT_PREFIX}1.2.0'
    assert _resolve_base_version_tag({'_commit': legacy}) == '1.2.0'


def test_resolve_base_version_tag_missing() -> None:
    """Missing `_commit` or malformed values return None."""
    assert _resolve_base_version_tag({}) is None
    assert _resolve_base_version_tag({'_commit': None}) is None
    assert _resolve_base_version_tag({'_commit': ''}) is None
    assert _resolve_base_version_tag({'_commit': '-broken'}) is None
    assert _resolve_base_version_tag({'_commit': LEGACY_COMMIT_PREFIX}) is None


def test_has_git_runtime() -> None:
    """`_has_git()` returns True when git is on PATH (precondition of the test suite)."""
    assert _has_git() is True


def test_exit_code_constants() -> None:
    """Public exit codes match the spec: 0 clean / 1 error / 2 conflicts."""
    assert (EXIT_OK, EXIT_ERROR, EXIT_CONFLICTS) == (0, 1, 2)


def test_data_invalid_format_rejected(tmp_path: Path) -> None:
    """`dreamteam init --data foo` (no `=`) is a usage error."""
    target = tmp_path / 'bad-data'
    result = runner.invoke(app, ['init', str(target), '--defaults', '--data', 'novalue'])
    assert result.exit_code != 0


def test_no_unused_pytest_import() -> None:
    """Smoke: pytest module is the test framework, not unused."""
    assert pytest.__version__


def test_console_script_aliases_registered() -> None:
    """
    `pip install dreamteam-cli` must register both `dreamteam` and `dt`
    console scripts pointing at the same Typer app (T016 alias).
    """
    from importlib.metadata import entry_points

    scripts = {
        ep.name: ep.value
        for ep in entry_points(group='console_scripts')
        if ep.name in {'dreamteam', 'dt'}
    }
    assert scripts.get('dreamteam') == 'dreamteam.cli:app'
    assert scripts.get('dt') == 'dreamteam.cli:app', (
        '`dt` alias missing or wired to wrong callable'
    )


def test_update_preserves_user_edit(tmp_path: Path) -> None:
    """
    Scenario B (light): user adds a bullet to BACKLOG.md, then runs
    `dreamteam update`. Template version is unchanged, so the merge
    is effectively no-op for template-side; the user edit must be
    preserved.
    """
    target = tmp_path / 'edit-keep'
    init_result = runner.invoke(app, ['init', str(target), '--defaults'])
    assert init_result.exit_code == 0, init_result.output

    backlog = target / 'BACKLOG.md'
    user_marker = '- T999: my custom note that must survive update'
    backlog.write_text(
        backlog.read_text(encoding='utf-8') + '\n' + user_marker + '\n',
        encoding='utf-8',
    )

    _git_init(target)

    update_result = runner.invoke(app, ['update', str(target)])
    assert update_result.exit_code == EXIT_OK, update_result.output
    assert user_marker in backlog.read_text(encoding='utf-8')


def test_update_language_preserved(tmp_path: Path) -> None:
    """
    Scenario D: init derived with language=ru → update → answers
    still record language=ru, narrative still in Russian.
    """
    target = tmp_path / 'ru-stable'
    init_result = runner.invoke(
        app, ['init', str(target), '--defaults', '--data', 'language=ru'],
    )
    assert init_result.exit_code == 0, init_result.output
    _git_init(target)

    update_result = runner.invoke(app, ['update', str(target)])
    assert update_result.exit_code == EXIT_OK, update_result.output

    answers = (target / '.copier-answers.yml').read_text(encoding='utf-8')
    assert 'language: ru' in answers
    # Marker from i18n/ru/CLAUDE.md body — must remain after update.
    claude_text = (target / 'CLAUDE.md').read_text(encoding='utf-8')
    assert 'проектные правила для Claude' in claude_text


def test_dry_run_leaves_target_untouched(tmp_path: Path) -> None:
    """
    `dreamteam update --dry-run` must not modify the target: file
    contents, mtime of user-edited files, and `.copier-answers.yml`
    all stay exactly as they were before the invocation.
    """
    target = tmp_path / 'dry-untouched'
    runner.invoke(app, ['init', str(target), '--defaults'])
    user_marker = '<!-- dry-run sentinel that must survive -->'
    claude = target / 'CLAUDE.md'
    claude.write_text(claude.read_text(encoding='utf-8') + user_marker, encoding='utf-8')
    _git_init(target)

    snapshot_claude = claude.read_text(encoding='utf-8')
    snapshot_answers = (target / '.copier-answers.yml').read_text(encoding='utf-8')

    result = runner.invoke(app, ['update', str(target), '--dry-run'])
    assert result.exit_code in (EXIT_OK, EXIT_CONFLICTS), result.output

    assert claude.read_text(encoding='utf-8') == snapshot_claude
    assert (target / '.copier-answers.yml').read_text(encoding='utf-8') == snapshot_answers


def test_dry_run_prints_summary_line(tmp_path: Path) -> None:
    """The trailing summary line must list all five buckets."""
    target = tmp_path / 'dry-summary'
    runner.invoke(app, ['init', str(target), '--defaults'])
    _git_init(target)

    result = runner.invoke(app, ['update', str(target), '--dry-run'])
    assert result.exit_code == EXIT_OK, result.output

    assert 'dreamteam update --dry-run:' in result.output
    for bucket in ('would change', 'unchanged', 'added', 'removed', 'conflicts'):
        assert bucket in result.output, f'missing {bucket!r} in summary'


def test_dry_run_with_force_warns(tmp_path: Path) -> None:
    """
    `--dry-run --force` is contradictory: dry-run previews the merge
    flow with its full fallback chain, force skips it. The CLI emits
    a warning to stderr and still produces a preview.
    """
    target = tmp_path / 'dry-and-force'
    runner.invoke(app, ['init', str(target), '--defaults'])
    _git_init(target)

    result = runner.invoke(app, ['update', str(target), '--dry-run', '--force'])
    assert result.exit_code in (EXIT_OK, EXIT_CONFLICTS), result.output
    combined = result.output + (result.stderr or '')
    assert '--force has no effect' in combined.lower() or 'no effect under --dry-run' in combined.lower()


def test_relfiles_excludes_git_and_yields_relative_paths(tmp_path: Path) -> None:
    """`_relfiles` walks rglob, drops anything under `.git`, returns rel paths."""
    root = tmp_path / 'tree'
    (root / '.git').mkdir(parents=True)
    (root / '.git' / 'config').write_text('x')
    (root / 'a.md').write_text('hello')
    (root / 'sub').mkdir()
    (root / 'sub' / 'b.txt').write_text('world')

    files = _relfiles(root)
    assert files == {Path('a.md'), Path('sub/b.txt')}


def test_emit_dryrun_diff_counts_buckets(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """`_emit_dryrun_diff` classifies files into changed/unchanged/added/removed."""
    target = tmp_path / 'target'
    preview = tmp_path / 'preview'
    target.mkdir()
    preview.mkdir()

    # Unchanged file (present in both, identical content).
    (target / 'same.txt').write_text('identical\n')
    (preview / 'same.txt').write_text('identical\n')
    # Changed file (different content).
    (target / 'changed.txt').write_text('before\n')
    (preview / 'changed.txt').write_text('after\n')
    # Removed (only in target).
    (target / 'gone.txt').write_text('orphan\n')
    # Added (only in preview).
    (preview / 'new.txt').write_text('fresh\n')

    conflicts = _emit_dryrun_diff(target, preview)
    out = capsys.readouterr().out

    assert conflicts == 0
    # Summary numbers.
    assert '1 would change' in out
    assert '1 unchanged' in out
    assert '1 added' in out
    assert '1 removed' in out
    # Unified-diff markers for the changed file.
    assert '--- a/changed.txt' in out
    assert '+++ b/changed.txt' in out
    # Added / removed markers.
    assert '+++ b/new.txt' in out
    assert '--- a/gone.txt' in out


def test_emit_dryrun_diff_detects_conflict_markers(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """A preview file containing `<<<<<<<` increments the conflict count."""
    target = tmp_path / 'target'
    preview = tmp_path / 'preview'
    target.mkdir()
    preview.mkdir()
    (target / 'x.txt').write_text('hello\n')
    (preview / 'x.txt').write_text(
        '<<<<<<< before updating\nhello\n=======\nworld\n>>>>>>> after updating\n',
    )

    conflicts = _emit_dryrun_diff(target, preview)
    captured = capsys.readouterr()
    assert conflicts == 1
    assert '1 conflicts' in captured.out


def test_dry_run_without_answers_fails(tmp_path: Path) -> None:
    """`--dry-run` on a non-dreamteam dir still fails with EXIT_ERROR."""
    target = tmp_path / 'no-answers-dry'
    target.mkdir()
    result = runner.invoke(app, ['update', str(target), '--dry-run'])
    assert result.exit_code == EXIT_ERROR


def test_update_legacy_commit_falls_back_to_overwrite(tmp_path: Path) -> None:
    """
    Scenario for pre-1.3.0 derived projects: their `_commit` carries
    the legacy `dreamteam-<X.Y.Z>` prefix and the bundle has no such
    tag → fallback to overwrite update with a WARNING.
    """
    target = tmp_path / 'legacy'
    init_result = runner.invoke(app, ['init', str(target), '--defaults'])
    assert init_result.exit_code == 0, init_result.output
    answers_file = target / '.copier-answers.yml'
    text = answers_file.read_text(encoding='utf-8')
    # Rewrite `_commit` to a legacy version not in the bundle.
    text = text.replace(f'_commit: {__version__}', f'_commit: {LEGACY_COMMIT_PREFIX}1.0.0')
    answers_file.write_text(text, encoding='utf-8')
    _git_init(target)

    update_result = runner.invoke(app, ['update', str(target)])
    assert update_result.exit_code == EXIT_OK, update_result.output
    output = update_result.output + update_result.stderr
    assert 'overwrite' in output.lower()
    assert '1.0.0' in output


# ---------------------------------------------------------------------------
# T026 §6.3 — `_ensure_team_roles_import` post-update hook
# ---------------------------------------------------------------------------


def _make_team_roles(target: Path) -> None:
    """Place `.claude/team-roles.md` — the hook only wires the import if present."""
    roles = target / '.claude' / 'team-roles.md'
    roles.parent.mkdir(parents=True, exist_ok=True)
    roles.write_text('# Team roles\n', encoding='utf-8')


def test_ensure_team_roles_import_appends_when_absent(tmp_path: Path) -> None:
    """A CLAUDE.md lacking the import line gets the block appended once."""
    _make_team_roles(tmp_path)
    claude_md = tmp_path / 'CLAUDE.md'
    claude_md.write_text('# My rules\n\nHand-written.\n', encoding='utf-8')
    _ensure_team_roles_import(tmp_path)
    text = claude_md.read_text(encoding='utf-8')
    assert TEAM_ROLES_IMPORT in text
    assert text.count(TEAM_ROLES_IMPORT) == 1
    # Original content is preserved.
    assert text.startswith('# My rules\n\nHand-written.\n')


def test_ensure_team_roles_import_idempotent(tmp_path: Path) -> None:
    """Running the hook twice does not duplicate the import line."""
    _make_team_roles(tmp_path)
    claude_md = tmp_path / 'CLAUDE.md'
    claude_md.write_text('# Rules\n', encoding='utf-8')
    _ensure_team_roles_import(tmp_path)
    once = claude_md.read_text(encoding='utf-8')
    _ensure_team_roles_import(tmp_path)
    twice = claude_md.read_text(encoding='utf-8')
    assert once == twice
    assert twice.count(TEAM_ROLES_IMPORT) == 1


def test_ensure_team_roles_import_noop_when_present(tmp_path: Path) -> None:
    """A CLAUDE.md that already imports the file is left untouched."""
    _make_team_roles(tmp_path)
    claude_md = tmp_path / 'CLAUDE.md'
    original = f'# Rules\n\n## Team roles\n\n{TEAM_ROLES_IMPORT}\n'
    claude_md.write_text(original, encoding='utf-8')
    _ensure_team_roles_import(tmp_path)
    assert claude_md.read_text(encoding='utf-8') == original


def test_ensure_team_roles_import_noop_when_no_claude_md(tmp_path: Path) -> None:
    """No CLAUDE.md → no-op; the hook never creates one itself."""
    _make_team_roles(tmp_path)
    _ensure_team_roles_import(tmp_path)
    assert not (tmp_path / 'CLAUDE.md').exists()


def test_ensure_team_roles_import_noop_without_roles_file(tmp_path: Path) -> None:
    """No `.claude/team-roles.md` → no dangling import is written (hardening)."""
    claude_md = tmp_path / 'CLAUDE.md'
    claude_md.write_text('# My rules\n\nHand-written.\n', encoding='utf-8')
    _ensure_team_roles_import(tmp_path)
    # The roles file is absent, so the import must NOT be added.
    assert TEAM_ROLES_IMPORT not in claude_md.read_text(encoding='utf-8')


def test_ensure_team_roles_import_appends_newline_when_missing(tmp_path: Path) -> None:
    """A CLAUDE.md without a trailing newline still yields a clean append."""
    _make_team_roles(tmp_path)
    claude_md = tmp_path / 'CLAUDE.md'
    claude_md.write_text('# Rules (no trailing newline)', encoding='utf-8')
    _ensure_team_roles_import(tmp_path)
    text = claude_md.read_text(encoding='utf-8')
    assert '# Rules (no trailing newline)\n' in text
    assert text.endswith(f'{TEAM_ROLES_IMPORT}\n')
    assert TEAM_ROLES_IMPORT in text


# ---------------------------------------------------------------------------
# T028 — `_restore_git` (git snapshot/restore for `dreamteam update`)
# ---------------------------------------------------------------------------


def test_restore_git_swaps_mutated_for_backup_and_cleans(tmp_path: Path) -> None:
    """Mutated `.git` is replaced by the backup, and the backup dir is removed."""
    git_dir = tmp_path / '.git'
    git_dir.mkdir()
    (git_dir / 'MUTATED').write_text('copier state', encoding='utf-8')
    backup_root = tmp_path / 'bk'
    backup_root.mkdir()
    backup = backup_root / 'git'
    backup.mkdir()
    (backup / 'ORIGINAL').write_text('user history', encoding='utf-8')

    _restore_git(git_dir, backup, backup_root)

    assert (git_dir / 'ORIGINAL').read_text(encoding='utf-8') == 'user history'
    assert not (git_dir / 'MUTATED').exists(), 'backup was nested, not swapped'
    assert not backup_root.exists(), 'backup dir not cleaned after success'


def test_restore_git_when_git_dir_already_gone(tmp_path: Path) -> None:
    """If copier removed `.git`, the backup is moved into place cleanly."""
    git_dir = tmp_path / '.git'  # intentionally absent
    backup_root = tmp_path / 'bk'
    backup_root.mkdir()
    backup = backup_root / 'git'
    backup.mkdir()
    (backup / 'ORIGINAL').write_text('user history', encoding='utf-8')

    _restore_git(git_dir, backup, backup_root)

    assert (git_dir / 'ORIGINAL').read_text(encoding='utf-8') == 'user history'
    assert not backup_root.exists()
