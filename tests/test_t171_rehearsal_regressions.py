"""Regressions discovered by independent installed-artifact rehearsal."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

import pytest
import yaml
from typer.testing import CliRunner

from dreamteam.cli import _bundle_path, _clone_bundle, _copier_render_at, app


LEGACY_FACT = 'Keep project source modules under the src directory.'
DESTINATION_FACT = 'Keep individual modules below the agreed size limit.'
ROLE_FACT = 'Custom review invariant: verify the retained audit trail.'
COMMAND_FACT = 'Check the retained project acceptance evidence.'
ROLE_REFERENCE = '.opencode/team-roles.md'
RUNNER = CliRunner()


def snapshot(root: Path) -> dict:
    """Compare all bytes, modes, directories and link references without traversal."""
    result = {}
    pending = [root]
    while pending:
        for path in pending.pop().iterdir():
            name = str(path.relative_to(root))
            mode = stat.S_IMODE(path.lstat().st_mode)
            if path.is_symlink():
                result[name] = ('link', os.readlink(path), mode)
            elif path.is_dir():
                result[name] = ('dir', mode)
                pending.append(path)
            else:
                result[name] = ('file', path.read_bytes(), mode)
    return result


@pytest.fixture
def controlled_170_both(tmp_path, monkeypatch):
    """Verified 1.7 baseline with rewritten neutral rules, not appended boilerplate."""
    home = tmp_path / 'home'
    home.mkdir(mode=0o700)
    monkeypatch.setenv('HOME', str(home))
    for kind, suffix in (
        ('STATE', 'state'), ('CONFIG', 'config'), ('DATA', 'data'), ('CACHE', 'cache')
    ):
        monkeypatch.setenv(f'XDG_{kind}_HOME', str(home / suffix))
    binaries = tmp_path / 'bin'
    binaries.mkdir()
    probe = binaries / 'opencode'
    probe.write_text(f'#!{sys.executable}\nprint("1.19.0")\n')
    probe.chmod(0o700)
    git = shutil.which('git')
    assert git is not None
    (binaries / 'git').symlink_to(git)
    monkeypatch.setenv('PATH', str(binaries))
    root = tmp_path / 'project'
    root.mkdir(mode=0o700)
    bundle = tmp_path / 'released-bundle'
    _clone_bundle(_bundle_path(), bundle)
    answers = {
        'language': 'en',
        'project_name': 'rehearsal-regression',
        'architect_model': 'inherit',
    }
    _copier_render_at(root, answers, clone=bundle, ref='1.7.0')
    (root / '.copier-answers.yml').write_text(
        yaml.safe_dump({'_commit': '1.7.0', **answers})
    )
    (root / 'CLAUDE.md').write_text(LEGACY_FACT + '\n')
    (root / 'AGENTS.md').write_text(DESTINATION_FACT + '\n')
    role = root / '.claude/agents/architect.md'
    role.write_text(role.read_text() + '\n' + ROLE_FACT + '\n')
    command = root / '.claude/commands/rehearsal-check.md'
    command.parent.mkdir(parents=True, exist_ok=True)
    command.write_text(COMMAND_FACT + '\n')
    command.chmod(0o640)
    protected = root / '.claude/worktrees/retained'
    protected.mkdir(parents=True)
    (protected / 'sentinel').write_text('Excluded worktree sentinel.\n')
    (protected / 'link').symlink_to('sentinel')
    subprocess.run([git, 'init', '--quiet', str(root)], check=True, capture_output=True)
    return root, home


def test_rewritten_both_first_result_is_canonical_and_second_update_is_exact_noop(
    controlled_170_both,
):
    root, home = controlled_170_both
    excluded = snapshot(root / '.claude/worktrees')
    first = RUNNER.invoke(app, ['update', str(root)])
    assert first.exit_code == 0, first.output + str(first.exception)
    rules = (root / 'AGENTS.md').read_text()
    assert rules.count(LEGACY_FACT) == 1
    assert rules.count(DESTINATION_FACT) == 1
    assert rules.count(ROLE_REFERENCE) == 1, 'first result must already be canonical'
    assert rules.count('## Team roles — dreamteam') == 1
    assert (root / '.opencode/agents/architect.md').read_text().count(ROLE_FACT) == 1
    assert (
        root / '.opencode/commands/rehearsal-check.md'
    ).read_text().count(COMMAND_FACT) == 1
    assert yaml.safe_load((root / '.copier-answers.yml').read_text())['_commit'] == '2.0.0'
    assert not (root / 'CLAUDE.md').exists()
    assert not (root / '.claude/agents/architect.md').exists()
    assert not (root / '.claude/commands/rehearsal-check.md').exists()
    assert snapshot(root / '.claude/worktrees') == excluded
    before, recovery = snapshot(root), snapshot(home)
    second = RUNNER.invoke(app, ['update', str(root)])
    assert second.exit_code == 0, second.output + str(second.exception)
    assert snapshot(root) == before, 'normal second update must be an exact no-op'
    assert snapshot(home) == recovery, 'completed migration must not churn recovery'


@pytest.mark.parametrize('flags', [('--dry-run',), ()])
def test_inside_project_vendor_state_rejected_before_executable_can_write(
    controlled_170_both, monkeypatch, flags,
):
    root, home = controlled_170_both
    monkeypatch.setenv('XDG_STATE_HOME', str(root / 'vendor-state'))
    probe = Path(os.environ['PATH']) / 'opencode'
    probe.write_text(
        f'#!{sys.executable}\n'
        'import os\n'
        'from pathlib import Path\n'
        'Path(os.environ["XDG_STATE_HOME"], "opencode").mkdir(parents=True)\n'
        'print("1.19.0")\n'
    )
    before, outside = snapshot(root), snapshot(home)
    result = RUNNER.invoke(app, ['update', str(root), *flags])
    assert snapshot(root) == before, 'vendor probe must not mutate selected project'
    assert snapshot(home) == outside
    assert result.exit_code == 1, result.output + str(result.exception)
