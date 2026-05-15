"""
Maintainer tool: snapshot current template into the bundled bare git repo.

Initializes `src/dreamteam/template/.bundle/` as a bare git repo on
first run, then appends one annotated commit + tag per release. The
bundle ships inside the dreamteam-cli wheel and is what
`dreamteam update` clones to obtain the *base* state for the
three-way merge (T009 Phase 1).

Run before each release cut, after pyproject.toml version bump:

    uv run python scripts/update_bundle.py            # version from pyproject
    uv run python scripts/update_bundle.py --version v1.4.0
    uv run python scripts/update_bundle.py --date 2026-05-15  # override commit date

The script is idempotent: if the tag already exists in the bundle,
it exits 0 with a notice. Use `--force` to overwrite (rebuilds the
tag at the new content).

Commit dates are fixed (`GIT_AUTHOR_DATE` / `GIT_COMMITTER_DATE`)
so the bundle is reproducible across machines.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_ROOT = REPO_ROOT / 'src' / 'dreamteam' / 'template'
BUNDLE_PATH = TEMPLATE_ROOT / '.bundle'
PYPROJECT = REPO_ROOT / 'pyproject.toml'
GIT = shutil.which('git') or 'git'

# Files inside template that are not part of the bundled snapshot:
# .bundle itself (avoid recursion) and any user-rendering helpers
# that should remain stable across template versions.
BUNDLE_EXCLUDE = {'.bundle'}


def _read_version_from_pyproject() -> str:
    """Return version from [project] in pyproject.toml (PEP 440, no `v` prefix)."""
    data = tomllib.loads(PYPROJECT.read_text(encoding='utf-8'))
    try:
        return str(data['project']['version'])
    except (KeyError, TypeError) as exc:
        message = (
            f'{PYPROJECT} is missing [project].version; '
            'pass --version explicitly or fix pyproject.toml.'
        )
        raise ValueError(message) from exc


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    """Run a subprocess, raising on non-zero exit, no stdout capture."""
    subprocess.run(cmd, cwd=cwd, check=True, env=env)


def _git_env(date_iso: str) -> dict[str, str]:
    """Build env with fixed commit dates for reproducible builds."""
    env = dict(os.environ)
    env['GIT_AUTHOR_NAME'] = 'dreamteam-bundle'
    env['GIT_AUTHOR_EMAIL'] = 'noreply@dreamteam-cli'
    env['GIT_COMMITTER_NAME'] = env['GIT_AUTHOR_NAME']
    env['GIT_COMMITTER_EMAIL'] = env['GIT_AUTHOR_EMAIL']
    env['GIT_AUTHOR_DATE'] = date_iso
    env['GIT_COMMITTER_DATE'] = date_iso
    return env


def _strip_init_noise(bundle: Path) -> None:
    """
    Remove git-init artifacts that are not useful in a shipped bundle.

    `git init` creates sample hook scripts (*.sample) and a dummy
    `description` file. They are never executed from a bare repo
    that lives inside a wheel, so we drop them — saves ~20KB and
    keeps `unzip -l` output clean.
    """
    hooks_dir = bundle / 'hooks'
    if hooks_dir.is_dir():
        for sample in hooks_dir.glob('*.sample'):
            sample.unlink()
    description = bundle / 'description'
    if description.exists():
        description.unlink()


def _pin_empty_refs_dirs(bundle: Path) -> None:
    """
    Place `.gitkeep` sentinels in `refs/heads/` and `refs/tags/`.

    After `git gc --aggressive` packs all refs into `packed-refs`,
    these directories become empty and git does not track empty
    directories. Without sentinels they disappear after a fresh
    `git clone` of the outer repo — and a bundle without `refs/`
    is not recognized as a bare repo, so `git tag --list` walks
    up to the parent repo and returns nothing. The CI flake on
    PR #46 traced back here. `.gitkeep` files are zero-byte but
    tracked by outer git, so the directories survive cloning.
    """
    for sub in ('refs/heads', 'refs/tags'):
        keep = bundle / sub / '.gitkeep'
        keep.parent.mkdir(parents=True, exist_ok=True)
        keep.touch(exist_ok=True)


def _ensure_bundle_initialized(bundle: Path) -> None:
    """Create a bare git repo at `bundle` if it does not exist yet."""
    if bundle.exists():
        return
    bundle.mkdir(parents=True)
    _run([GIT, 'init', '--bare', '--initial-branch=main', '.'], cwd=bundle)
    _strip_init_noise(bundle)
    _pin_empty_refs_dirs(bundle)


def _tag_exists(bundle: Path, tag: str) -> bool:
    """Check whether the bundle already contains the given tag."""
    result = subprocess.run(
        [GIT, 'tag', '--list', tag],
        cwd=bundle,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() == tag


def _snapshot_template(workdir: Path) -> None:
    """Copy current template content into `workdir`, excluding self-references."""
    for entry in TEMPLATE_ROOT.iterdir():
        if entry.name in BUNDLE_EXCLUDE:
            continue
        dst = workdir / entry.name
        if entry.is_dir():
            shutil.copytree(entry, dst, symlinks=False)
        else:
            shutil.copy2(entry, dst)


def _commit_snapshot(
    bundle: Path,
    version_tag: str,
    date_iso: str,
    *,
    force: bool,
) -> None:
    """Snapshot template -> tempdir worktree -> commit -> push tag to bundle."""
    with tempfile.TemporaryDirectory(prefix='dreamteam-bundle-') as tmp:
        workdir = Path(tmp)
        env = _git_env(date_iso)
        _run([GIT, 'init', '--initial-branch=main', '.'], cwd=workdir, env=env)
        _snapshot_template(workdir)
        _run([GIT, 'add', '-A'], cwd=workdir, env=env)
        _run(
            [GIT, 'commit', '-m', f'dreamteam template snapshot {version_tag}'],
            cwd=workdir,
            env=env,
        )
        _run(
            [GIT, 'tag', '-a', version_tag, '-m', version_tag],
            cwd=workdir,
            env=env,
        )
        # Push both the main branch (so the bundle has a valid HEAD
        # after clone) and the version tag (for `copier.run_update`
        # to find the base state).
        #
        # `main` always advances to the new snapshot; --force-with-lease
        # is required because the bundle is single-writer (this script
        # is the only producer) and the previous main commit is a
        # different snapshot, not an ancestor. Tag push is non-fast-
        # forward only when --force is set (overwriting an existing
        # tag), so we gate tag forcing separately.
        push_args = [
            GIT,
            'push',
            '--force-with-lease=refs/heads/main',
            str(bundle),
            'refs/heads/main',
            f'refs/tags/{version_tag}',
        ]
        if force:
            push_args.append('--force')
        _run(push_args, cwd=workdir, env=env)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument(
        '--version',
        help=(
            'Tag to create (e.g. 1.4.0; PEP 440, no `v` prefix — '
            'dunamai inside copier looks up unprefixed tags). '
            'Defaults to pyproject.toml [project].version.'
        ),
    )
    parser.add_argument(
        '--date',
        default='2026-05-15T00:00:00Z',
        help='Fixed commit date (ISO 8601). Defaults to the bundle epoch date.',
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite the tag if it already exists.',
    )
    args = parser.parse_args(argv)

    version_tag = args.version or _read_version_from_pyproject()
    if version_tag.startswith('v'):
        sys.stderr.write(
            f'tag should be PEP 440 without `v` prefix (dunamai requirement); '
            f'got {version_tag!r}. Strip the leading `v` and retry.\n'
        )
        return 2

    _ensure_bundle_initialized(BUNDLE_PATH)

    if _tag_exists(BUNDLE_PATH, version_tag) and not args.force:
        sys.stdout.write(
            f'bundle already contains tag {version_tag}; nothing to do '
            '(use --force to overwrite)\n'
        )
        return 0

    _commit_snapshot(BUNDLE_PATH, version_tag, args.date, force=args.force)
    # Repack loose objects so wheel ships one tight pack rather than
    # many small blobs. Reproducible: --no-cruft + fixed dates.
    _run([GIT, 'gc', '--quiet', '--aggressive'], cwd=BUNDLE_PATH)
    _strip_init_noise(BUNDLE_PATH)
    # `git gc` empties refs/heads and refs/tags after packing — re-pin
    # them so the outer repo tracks the directories (see docstring of
    # `_pin_empty_refs_dirs`).
    _pin_empty_refs_dirs(BUNDLE_PATH)
    sys.stdout.write(f'bundle: tag {version_tag} added at {BUNDLE_PATH}\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
