"""
T026 Phase 9 — update acceptance: the §6 auto-pickup requirement.

A project created by a *pre-T026* DreamTeam release must, after
`dreamteam update`, receive the Architect subagent, the roles
methodology, and the design brief — as clean new files — and the
`@.claude/team-roles.md` import in CLAUDE.md, without conflict markers
on files the user did not touch, idempotently.

The shipped `.bundle` only carries released tags (all pre-T026 today),
so — like `test_t009_phase2` — we build a synthetic two-tag bundle:

- `BASE_TAG`: the current template with the T026-added files *stripped*
  (a genuine pre-T026 snapshot);
- `<__version__>` at HEAD: the full current template (with T026).

A derived project is rendered at BASE_TAG, then `dreamteam update`
(routed at the synthetic bundle) is exercised for real.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest
import yaml
from copier import Worker
from typer.testing import CliRunner

from dreamteam import __version__
from dreamteam.cli import BUNDLE_SUBPATH, EXIT_OK, TEAM_ROLES_IMPORT, _template_path, app

if TYPE_CHECKING:
    from pathlib import Path

# Integration-grade: builds a bare bundle via subprocess git + drives
# copier end-to-end. Reserved for `pytest -m integration`.
pytestmark = pytest.mark.integration

runner = CliRunner()
GIT = shutil.which('git') or 'git'
BASE_TAG = '1.4.0'  # PEP-440-clean, earlier than __version__.


def _commit_env() -> dict[str, str]:
    env = dict(os.environ)
    env['GIT_AUTHOR_NAME'] = 't026-fixture'
    env['GIT_AUTHOR_EMAIL'] = 'noreply@dreamteam'
    env['GIT_COMMITTER_NAME'] = env['GIT_AUTHOR_NAME']
    env['GIT_COMMITTER_EMAIL'] = env['GIT_AUTHOR_EMAIL']
    env['GIT_AUTHOR_DATE'] = '2026-07-05T00:00:00Z'
    env['GIT_COMMITTER_DATE'] = env['GIT_AUTHOR_DATE']
    return env


def _git(*args: str, cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run([GIT, *args], cwd=cwd, check=True, env=env, capture_output=True)


def _strip_init_noise(bundle: Path) -> None:
    hooks = bundle / 'hooks'
    if hooks.is_dir():
        for sample in hooks.glob('*.sample'):
            sample.unlink()
    desc = bundle / 'description'
    if desc.exists():
        desc.unlink()


def _pin_empty_refs_dirs(bundle: Path) -> None:
    for sub in ('refs/heads', 'refs/tags'):
        keep = bundle / sub / '.gitkeep'
        keep.parent.mkdir(parents=True, exist_ok=True)
        keep.touch(exist_ok=True)


def _snapshot_template(workdir: Path) -> None:
    """Copy the real template into workdir, excluding the shipped bundle."""
    template_root = _template_path()
    for entry in template_root.iterdir():
        if entry.name == BUNDLE_SUBPATH:
            continue
        dst = workdir / entry.name
        if entry.is_dir():
            shutil.copytree(entry, dst, symlinks=False)
        else:
            shutil.copy2(entry, dst)


def _strip_team_roles_section(text: str) -> str:
    """Drop the trailing `## …team roles…` section that ends in the import."""
    lines = text.splitlines(keepends=True)
    idx = next(
        (i for i, line in enumerate(lines) if TEAM_ROLES_IMPORT in line),
        None,
    )
    if idx is None:
        return text
    heading = idx
    while heading >= 0 and not lines[heading].lstrip().startswith('## '):
        heading -= 1
    if heading < 0:
        return text
    return ''.join(lines[:heading]).rstrip('\n') + '\n'


def _strip_t026(workdir: Path) -> None:
    """Remove every T026-added output file to simulate a pre-T026 template."""
    (workdir / '.claude' / 'agents' / 'architect.md').unlink(missing_ok=True)
    shutil.rmtree(workdir / 'partials', ignore_errors=True)
    for lang_dir in (workdir / 'i18n').iterdir():
        if not lang_dir.is_dir():
            continue
        (lang_dir / '.claude' / 'team-roles.md').unlink(missing_ok=True)
        (lang_dir / 'specs' / 'design-brief-template.md').unlink(missing_ok=True)
        claude = lang_dir / 'CLAUDE.md'
        if claude.is_file():
            claude.write_text(
                _strip_team_roles_section(claude.read_text(encoding='utf-8')),
                encoding='utf-8',
            )


def _clear_worktree(work: Path) -> None:
    for entry in work.iterdir():
        if entry.name == '.git':
            continue
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()


def _make_bundle(tmp_path: Path) -> Path:
    """Two-tag bundle: BASE_TAG (pre-T026) + __version__ (full template)."""
    bundle = tmp_path / 'bundle.bare'
    bundle.mkdir()
    _git('init', '--bare', '--initial-branch=main', '.', cwd=bundle)
    _strip_init_noise(bundle)
    _pin_empty_refs_dirs(bundle)

    work = tmp_path / 'work'
    work.mkdir()
    env = _commit_env()
    _git('init', '--initial-branch=main', '.', cwd=work, env=env)

    # BASE_TAG: pre-T026 snapshot.
    _snapshot_template(work)
    _strip_t026(work)
    _git('add', '-A', cwd=work, env=env)
    _git('commit', '-m', f'base {BASE_TAG}', cwd=work, env=env)
    _git('tag', '-a', BASE_TAG, '-m', BASE_TAG, cwd=work, env=env)

    # HEAD / __version__: full current template (T026 files present).
    _clear_worktree(work)
    _snapshot_template(work)
    _git('add', '-A', cwd=work, env=env)
    _git('commit', '-m', f'head {__version__}', cwd=work, env=env)
    _git('tag', '-a', __version__, '-m', __version__, cwd=work, env=env)

    _git(
        'push',
        str(bundle),
        'refs/heads/main',
        f'refs/tags/{BASE_TAG}',
        f'refs/tags/{__version__}',
        cwd=work,
        env=env,
    )
    return bundle


def _render_derived_at_base(bundle: Path, target: Path, language: str) -> None:
    """Render a derived project at BASE_TAG and stamp its answers file."""
    clone = bundle.parent / 'render-clone'
    if clone.exists():
        shutil.rmtree(clone)
    subprocess.run(
        [GIT, 'clone', '--quiet', '--no-hardlinks', str(bundle), str(clone)],
        check=True,
    )
    with Worker(
        src_path=str(clone),
        dst_path=target,
        data={'language': language, 'project_name': 't026-demo'},
        defaults=True,
        quiet=True,
        unsafe=True,
        vcs_ref=BASE_TAG,
    ) as worker:
        worker.run_copy()
        user_answers = dict(worker.answers.user)
    payload: dict[str, object] = {'_commit': BASE_TAG, '_src_path': str(bundle)}
    payload.update(user_answers)
    (target / '.copier-answers.yml').write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding='utf-8',
    )


def _git_init_derived(target: Path) -> None:
    env = _commit_env()
    _git('init', '--initial-branch=main', '--quiet', cwd=target, env=env)
    _git('add', '-A', cwd=target, env=env)
    _git('commit', '-q', '-m', 'initial', cwd=target, env=env)


def _git_commit_all(target: Path) -> None:
    """Commit the working tree — copier refuses to update a dirty repo."""
    env = _commit_env()
    _git('add', '-A', cwd=target, env=env)
    _git('commit', '-q', '-m', 'apply update', cwd=target, env=env)


def _has_conflict_markers(root: Path) -> list[Path]:
    hits: list[Path] = []
    for path in root.rglob('*'):
        if not path.is_file() or '.git' in path.parts:
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        if '<<<<<<<' in text:
            hits.append(path)
    return hits


@pytest.fixture
def synthetic_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    bundle = _make_bundle(tmp_path)
    monkeypatch.setattr('dreamteam.cli._bundle_path', lambda: bundle)
    return bundle


def test_update_delivers_t026_files_cleanly(
    tmp_path: Path,
    synthetic_bundle: Path,
) -> None:
    """A pre-T026 project gets the new files + import line, no conflicts, idempotent."""
    target = tmp_path / 'derived'
    _render_derived_at_base(synthetic_bundle, target, language='en')

    # Precondition: the base project has none of the T026 artifacts.
    assert not (target / '.claude' / 'agents' / 'architect.md').exists()
    assert not (target / '.claude' / 'team-roles.md').exists()
    assert not (target / 'specs' / 'design-brief-template.md').exists()
    assert TEAM_ROLES_IMPORT not in (target / 'CLAUDE.md').read_text(encoding='utf-8')

    _git_init_derived(target)
    result = runner.invoke(app, ['update', str(target)])
    assert result.exit_code == EXIT_OK, result.output + result.stderr

    # New files delivered cleanly.
    architect = target / '.claude' / 'agents' / 'architect.md'
    assert architect.is_file()
    architect_text = architect.read_text(encoding='utf-8')
    assert architect_text.startswith('---\n')
    assert architect_text.count('\n---\n') == 1
    assert (target / '.claude' / 'team-roles.md').is_file()
    assert (target / 'specs' / 'design-brief-template.md').is_file()

    # Import line delivered, no conflict markers anywhere.
    claude_text = (target / 'CLAUDE.md').read_text(encoding='utf-8')
    assert TEAM_ROLES_IMPORT in claude_text
    assert _has_conflict_markers(target) == []

    # Commit the delivered changes (as a user would) before re-updating —
    # copier refuses a dirty repo.
    _git_commit_all(target)

    # Idempotent: a second update stays clean and does not duplicate the line.
    result2 = runner.invoke(app, ['update', str(target)])
    assert result2.exit_code == EXIT_OK, result2.output + result2.stderr
    assert (target / 'CLAUDE.md').read_text(encoding='utf-8').count(
        TEAM_ROLES_IMPORT,
    ) == 1


def test_update_import_survives_rewritten_claude_md(
    tmp_path: Path,
    synthetic_bundle: Path,
) -> None:
    """Even a fully rewritten CLAUDE.md ends up with the import line (§6.3 hook)."""
    target = tmp_path / 'derived-rewritten'
    _render_derived_at_base(synthetic_bundle, target, language='en')

    (target / 'CLAUDE.md').write_text(
        '# My own rules\n\nTotally custom, nothing from the template.\n',
        encoding='utf-8',
    )
    _git_init_derived(target)

    # The merge may conflict on CLAUDE.md; the guarantee is the import
    # line's presence, delivered by the post-update hook regardless.
    runner.invoke(app, ['update', str(target)])
    assert TEAM_ROLES_IMPORT in (target / 'CLAUDE.md').read_text(encoding='utf-8')


def _git_out(target: Path, *args: str) -> str:
    """Return trimmed stdout of a git command in `target` (empty on failure)."""
    return subprocess.run(
        [GIT, *args],
        cwd=target,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()


def test_update_preserves_target_git_state(
    tmp_path: Path,
    synthetic_bundle: Path,
) -> None:
    """
    Regression (data-loss bug): `dreamteam update` must not touch the
    target's git. copier's run_update, left to operate on the real repo,
    repointed `origin`, moved the branch, detached HEAD and converted the
    repo to a partial clone. The update must leave branch / HEAD / remotes
    / config exactly as they were, delivering the changes only as an
    uncommitted working-tree diff.
    """
    target = tmp_path / 'derived-gitsafe'
    _render_derived_at_base(synthetic_bundle, target, language='en')
    # Simulate a real user project: drop copier's render-`.git` and make a
    # clean repo with the user's own remote + a hand-written file.
    shutil.rmtree(target / '.git', ignore_errors=True)
    env = _commit_env()
    _git('init', '--initial-branch=main', '--quiet', cwd=target, env=env)
    (target / 'MY_NOTES.md').write_text('hand-written, not from template\n', encoding='utf-8')
    _git('add', '-A', cwd=target, env=env)
    _git('commit', '-q', '-m', 'real project', cwd=target, env=env)
    fake_origin = 'https://example.com/user/myproject.git'
    _git('remote', 'add', 'origin', fake_origin, cwd=target, env=env)

    before_branch = _git_out(target, 'rev-parse', '--abbrev-ref', 'HEAD')
    before_head = _git_out(target, 'rev-parse', 'HEAD')
    assert before_branch == 'main'

    result = runner.invoke(app, ['update', str(target)])
    assert result.exit_code == EXIT_OK, result.output + result.stderr

    # Git state must be byte-for-byte what it was.
    assert _git_out(target, 'symbolic-ref', '-q', 'HEAD') != '', 'HEAD is detached'
    assert _git_out(target, 'rev-parse', '--abbrev-ref', 'HEAD') == before_branch
    assert _git_out(target, 'rev-parse', 'HEAD') == before_head, 'branch tip moved'
    assert _git_out(target, 'remote', 'get-url', 'origin') == fake_origin
    assert _git_out(target, 'config', '--get', 'remote.origin.promisor') == ''
    assert _git_out(target, 'config', '--get', 'remote.origin.partialclonefilter') == ''

    # ...while the update still happened in the working tree.
    assert (target / 'MY_NOTES.md').is_file(), 'user file lost'
    assert (target / '.claude' / 'team-roles.md').is_file(), 'template file not delivered'
    assert TEAM_ROLES_IMPORT in (target / 'CLAUDE.md').read_text(encoding='utf-8')
