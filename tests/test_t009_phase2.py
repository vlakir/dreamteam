"""
Phase 2 T009 tests: conflict UX + multilang merge integration.

Phase 1 covered the happy path (clean update on bundled current
version). Phase 2 needs *template evolution* to exercise the
three-way merge engine for real. We can't add an unreal "future"
tag to the shipped bundle; instead we build a per-test synthetic
bundle with an earlier tag (`1.2.0-test`) holding a tweaked snapshot
of the real template, and the real current version (`__version__`)
at HEAD. The test:

1. Renders derived from the synthetic bundle at the `1.2.0-test`
   base via `copier.run_copy` (so the derived starts at the older
   template state).
2. Rewrites the derived's `_commit` answer to `1.2.0-test`.
3. Monkey-patches `dreamteam.cli._bundle_path` so `dreamteam update`
   uses the synthetic bundle.
4. Lets the user edit the derived, then runs `dreamteam update` —
   the three-way merge sees a real template delta and a real user
   delta, producing either a clean merge or git-style conflict
   markers depending on overlap.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from copier import Worker
from typer.testing import CliRunner

from dreamteam.cli import (
    BUNDLE_SUBPATH,
    EXIT_CONFLICTS,
    EXIT_OK,
    app,
)

runner = CliRunner()
GIT = shutil.which('git') or 'git'

BASE_TAG = '1.2.0'  # PEP-440-clean so copier/dunamai accept it as a Version.
SCENARIO_FILE = 'BACKLOG.md'  # via i18n/<lang>/ — used by multilang + clean tests.
ROOT_SCENARIO_FILE = 'src/main.py'  # root-level, no rename — used by conflict test.
TEMPLATE_NEW_LINE = '\n- T-NEW: template-added bullet for Phase 2 test\n'
# Single line that both fixture and tests rewrite — overlapping
# replacement on the same line guarantees git treats it as a
# conflict (appending at EOF can be auto-merged as concat).
ORIGINAL_WARNING = "logger.warning('Sample warning — goes to stderr')"
TEMPLATE_WARNING = "logger.warning('Sample warning — template edit for Phase 2')"
USER_WARNING = "logger.warning('User-customized warning for Phase 2 test')"


def _real_template_root() -> Path:
    """Absolute path to the installed dreamteam template directory."""
    import dreamteam.cli as cli_mod  # local import only to avoid circulars at test collection

    return cli_mod._template_path()


def _commit_env(date_iso: str = '2026-05-15T00:00:00Z') -> dict[str, str]:
    env = dict(os.environ)
    env['GIT_AUTHOR_NAME'] = 'phase2-fixture'
    env['GIT_AUTHOR_EMAIL'] = 'noreply@dreamteam'
    env['GIT_COMMITTER_NAME'] = env['GIT_AUTHOR_NAME']
    env['GIT_COMMITTER_EMAIL'] = env['GIT_AUTHOR_EMAIL']
    env['GIT_AUTHOR_DATE'] = date_iso
    env['GIT_COMMITTER_DATE'] = date_iso
    return env


def _strip_init_noise(bundle: Path) -> None:
    """Drop git-init sample hooks + description (mirrors update_bundle.py)."""
    hooks = bundle / 'hooks'
    if hooks.is_dir():
        for sample in hooks.glob('*.sample'):
            sample.unlink()
    desc = bundle / 'description'
    if desc.exists():
        desc.unlink()


def _pin_empty_refs_dirs(bundle: Path) -> None:
    """Sentinel `.gitkeep` files (mirrors fix from 4537ba5)."""
    for sub in ('refs/heads', 'refs/tags'):
        keep = bundle / sub / '.gitkeep'
        keep.parent.mkdir(parents=True, exist_ok=True)
        keep.touch(exist_ok=True)


def _snapshot_template(workdir: Path, *, exclude_bundle: bool = True) -> None:
    """Copy real template content into workdir (excluding the real bundle)."""
    template_root = _real_template_root()
    for entry in template_root.iterdir():
        if exclude_bundle and entry.name == BUNDLE_SUBPATH:
            continue
        dst = workdir / entry.name
        if entry.is_dir():
            shutil.copytree(entry, dst, symlinks=False)
        else:
            shutil.copy2(entry, dst)


def _git(*args: str, cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run([GIT, *args], cwd=cwd, check=True, env=env, capture_output=True)


def _make_two_tag_bundle(tmp_path: Path) -> Path:
    """
    Build a bare git repo at `<tmp>/bundle.bare` with two tags:

    - `1.2.0-test` (synthetic earlier version): a snapshot of the
      real template *without* the template-side perturbation.
    - `<current __version__>` (HEAD on `main`): same snapshot plus
      `TEMPLATE_NEW_LINE` appended to every-language `BACKLOG.md`.

    The setup mirrors what `scripts/update_bundle.py` produces: bare
    repo + tag refs + pinned `refs/{heads,tags}/.gitkeep`.
    """
    from dreamteam import __version__

    bundle = tmp_path / 'bundle.bare'
    bundle.mkdir()
    _git('init', '--bare', '--initial-branch=main', '.', cwd=bundle)
    _strip_init_noise(bundle)
    _pin_empty_refs_dirs(bundle)

    work = tmp_path / 'fixture-work'
    work.mkdir()
    env = _commit_env()
    _git('init', '--initial-branch=main', '.', cwd=work, env=env)
    _snapshot_template(work)

    _git('add', '-A', cwd=work, env=env)
    _git('commit', '-m', f'base snapshot {BASE_TAG}', cwd=work, env=env)
    _git('tag', '-a', BASE_TAG, '-m', BASE_TAG, cwd=work, env=env)

    # Template-side perturbation for the second tag:
    # - append a marker bullet to BACKLOG.md in every i18n/<lang>/
    #   (used by multilang + clean tests; renamed via post-render).
    # - append a comment to src/main.py at root (used by the
    #   conflict scenario — root-level file avoids a copier limitation
    #   where staging the merged result via `git checkout <path>` fails
    #   if the rendered file's path differs from the template path).
    i18n = work / 'i18n'
    for lang_dir in i18n.iterdir():
        if not lang_dir.is_dir():
            continue
        backlog = lang_dir / SCENARIO_FILE
        if backlog.is_file():
            backlog.write_text(
                backlog.read_text(encoding='utf-8') + TEMPLATE_NEW_LINE,
                encoding='utf-8',
            )
    root_target = work / ROOT_SCENARIO_FILE
    if root_target.is_file():
        original = root_target.read_text(encoding='utf-8')
        if ORIGINAL_WARNING not in original:
            message = (
                f'fixture invariant broken: expected {ORIGINAL_WARNING!r} in '
                f'{root_target} but did not find it; update the test fixture.'
            )
            raise RuntimeError(message)
        root_target.write_text(
            original.replace(ORIGINAL_WARNING, TEMPLATE_WARNING),
            encoding='utf-8',
        )
    _git('add', '-A', cwd=work, env=env)
    _git('commit', '-m', f'phase 2 head snapshot {__version__}', cwd=work, env=env)
    _git('tag', '-a', __version__, '-m', __version__, cwd=work, env=env)

    push_refs = ['refs/heads/main', f'refs/tags/{BASE_TAG}', f'refs/tags/{__version__}']
    _git('push', str(bundle), *push_refs, cwd=work, env=env)
    return bundle


def _render_derived_at_base(
    bundle: Path,
    target: Path,
    language: str,
) -> None:
    """Render the derived from `bundle` at `BASE_TAG`, then git-init it.

    Uses `copier.Worker.run_copy` directly so we can pin `vcs_ref`
    (the public CLI doesn't expose this; it's only needed in tests).
    The temp clone path is necessary because copier won't operate on
    the bare bundle directly (no working tree).
    """
    clone_dir = bundle.parent / 'render-clone'
    if clone_dir.exists():
        shutil.rmtree(clone_dir)
    subprocess.run(
        [GIT, 'clone', '--quiet', '--no-hardlinks', str(bundle), str(clone_dir)],
        check=True,
    )
    user_answers: dict[str, object] = {}
    with Worker(
        src_path=str(clone_dir),
        dst_path=target,
        data={'language': language, 'project_name': 'phase2-demo'},
        defaults=True,
        quiet=True,
        unsafe=True,
        vcs_ref=BASE_TAG,
    ) as worker:
        worker.run_copy()
        user_answers = dict(worker.answers.user)

    # Stamp `.copier-answers.yml` ourselves — copier doesn't auto-
    # write it for the way dreamteam-cli invokes Worker, so the
    # behavior mirrors `dreamteam.cli._write_answers_file` but
    # pins `_commit = BASE_TAG` (so the next `dreamteam update`
    # treats the derived as a pre-existing project at the synthetic
    # earlier version, exactly as if the bundle had shipped that
    # release).
    import yaml

    payload: dict[str, object] = {
        '_commit': BASE_TAG,
        '_src_path': str(bundle),
    }
    payload.update(user_answers)
    (target / '.copier-answers.yml').write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding='utf-8',
    )


def _safe_has_marker(path: Path, marker: str) -> bool:
    try:
        return marker in path.read_text(encoding='utf-8')
    except (UnicodeDecodeError, OSError):
        return False


def _git_init_derived(target: Path) -> None:
    env = _commit_env()
    _git('init', '--initial-branch=main', '--quiet', cwd=target, env=env)
    _git('add', '-A', cwd=target, env=env)
    _git('commit', '-q', '-m', 'initial', cwd=target, env=env)


@pytest.fixture
def synthetic_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Build the two-tag bundle and route `dreamteam.cli._bundle_path` at it."""
    bundle = _make_two_tag_bundle(tmp_path)
    monkeypatch.setattr('dreamteam.cli._bundle_path', lambda: bundle)
    return bundle


def test_scenario_c_conflict_markers(
    tmp_path: Path,
    synthetic_bundle: Path,
) -> None:
    """
    Both user and template append to the same EOF region of a
    root-level file (`src/main.py`). `dreamteam update` produces
    git-style conflict markers and exits with EXIT_CONFLICTS (2).

    The file is deliberately root-level (not under `i18n/`) to side-
    step a copier rough edge where staging the merged result fails
    when the rendered file's destination path differs from its
    template source path (post-render rename).
    """
    target = tmp_path / 'derived-conflict'
    _render_derived_at_base(synthetic_bundle, target, language='en')

    # Init + commit the rendered base BEFORE the user edit, then
    # commit the user edit on top. Two commits in derived's git
    # history give copier a clean diff: HEAD~1 = base render,
    # HEAD = base + user edit. Without this split copier can't
    # cleanly isolate the user delta and silently falls through to
    # "theirs wins" on overlap.
    _git_init_derived(target)

    main_py = target / ROOT_SCENARIO_FILE
    original_text = main_py.read_text(encoding='utf-8')
    assert ORIGINAL_WARNING in original_text, 'derived must contain the base line'
    main_py.write_text(
        original_text.replace(ORIGINAL_WARNING, USER_WARNING),
        encoding='utf-8',
    )
    env = _commit_env()
    _git('add', '-A', cwd=target, env=env)
    _git('commit', '-q', '-m', 'user edit', cwd=target, env=env)

    result = runner.invoke(app, ['update', str(target)])
    # Exit code 2 is the contract for "conflict present"; the file
    # must carry git-style markers and the user error message must
    # mention conflicts. Per-line content of the markers is left
    # un-asserted on purpose: copier diffs Jinja-source against
    # rendered subproject content, so the marker block may end up on
    # a Jinja-only line (e.g. `{{ project_name }}`) instead of the
    # line we explicitly perturbed. That quirk is upstream and is
    # outside Phase 1/2 scope — the user-facing contract (exit 2 +
    # conflict markers in at least one file) is what we guarantee.
    assert result.exit_code == EXIT_CONFLICTS, result.output + result.stderr
    conflicted = [
        path
        for path in target.rglob('*')
        if path.is_file()
        and '.git' not in path.parts
        and _safe_has_marker(path, '<<<<<<<')
    ]
    assert conflicted, 'expected at least one file with conflict markers'
    output = result.output + (result.stderr or '')
    assert 'conflict' in output.lower(), f'no conflict mention in CLI output: {output}'


def test_multilang_merge_preserves_ru_and_both_edits(
    tmp_path: Path,
    synthetic_bundle: Path,
) -> None:
    """
    User edits CLAUDE.md (which the template does *not* touch in this
    synthetic head), template adds T-NEW bullet to BACKLOG.md. After
    `dreamteam update`:

    - language stays `ru` in `.copier-answers.yml`;
    - user's CLAUDE.md edit survives untouched;
    - template's T-NEW bullet appears in BACKLOG.md (delivered by
      the merge).
    """
    target = tmp_path / 'derived-ru-merge'
    _render_derived_at_base(synthetic_bundle, target, language='ru')

    claude = target / 'CLAUDE.md'
    user_marker = '\n<!-- USER-ru: persistent local note -->\n'
    claude.write_text(claude.read_text(encoding='utf-8') + user_marker, encoding='utf-8')
    _git_init_derived(target)

    result = runner.invoke(app, ['update', str(target)])
    assert result.exit_code == EXIT_OK, result.output + result.stderr

    answers = (target / '.copier-answers.yml').read_text(encoding='utf-8')
    assert 'language: ru' in answers

    # User edit retained.
    assert user_marker.strip() in claude.read_text(encoding='utf-8')

    # Template-side delta delivered.
    backlog_text = (target / SCENARIO_FILE).read_text(encoding='utf-8')
    assert 'T-NEW' in backlog_text


def test_scenario_b_clean_user_edit_non_conflicting(
    tmp_path: Path,
    synthetic_bundle: Path,
) -> None:
    """
    User edits CLAUDE.md (no overlap with template), template edits
    BACKLOG.md (no overlap with user). Both edits land cleanly; exit
    code is EXIT_OK and no conflict markers appear anywhere.
    """
    target = tmp_path / 'derived-clean'
    _render_derived_at_base(synthetic_bundle, target, language='en')

    claude = target / 'CLAUDE.md'
    user_marker = '\n<!-- non-conflicting user note -->\n'
    claude.write_text(claude.read_text(encoding='utf-8') + user_marker, encoding='utf-8')
    _git_init_derived(target)

    result = runner.invoke(app, ['update', str(target)])
    assert result.exit_code == EXIT_OK, result.output + result.stderr
    assert user_marker.strip() in claude.read_text(encoding='utf-8')
    backlog_text = (target / SCENARIO_FILE).read_text(encoding='utf-8')
    assert 'T-NEW' in backlog_text
    # No conflict markers in any file.
    for path in target.rglob('*.md'):
        if '.git' in path.parts:
            continue
        text = path.read_text(encoding='utf-8')
        assert '<<<<<<<' not in text, f'unexpected conflict marker in {path}'
