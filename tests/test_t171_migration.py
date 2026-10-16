"""Independent T171 acceptance: public CLI outcomes, not planner implementation."""

from __future__ import annotations

import json
import hashlib
from importlib import import_module
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
from unittest.mock import patch

import pytest
import yaml
from typer.testing import CliRunner

from dreamteam.cli import _bundle_path, _clone_bundle, _copier_render_at, app
from dreamteam.runtime import inspect_runtime


RUNNER = CliRunner()
FIXTURES = Path(__file__).parent / 'fixtures'
SECRET = 'T171_SYNTHETIC_SECRET_NEVER_PRINT_THIS'
RULE = 'Project invariant: migration must preserve the audit trail.'


def snapshot(root: Path) -> dict:
    """Capture bytes, links, modes and directories without following links."""
    result = {}
    if not root.exists():
        return result
    pending = [root]
    while pending:
        directory = pending.pop()
        for path in directory.iterdir():
            rel = str(path.relative_to(root))
            if path.is_symlink():
                result[rel] = ('link', os.readlink(path))
            elif path.is_dir():
                result[rel] = ('dir', stat.S_IMODE(path.stat().st_mode))
                pending.append(path)
            else:
                result[rel] = (
                    'file',
                    path.read_bytes(),
                    stat.S_IMODE(path.stat().st_mode),
                )
    return result


def put(root: Path, name: str, content: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


def invoke(root: Path, command: str = 'apply', *flags: str):
    args = [command, str(root)]
    if command == 'apply':
        args += ['--defaults', '--on-conflict', 'keep']
    return RUNNER.invoke(app, args + list(flags))


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Real local version executable; never use personal OpenCode or state."""
    home = tmp_path / 'home'
    home.mkdir()
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setenv('XDG_STATE_HOME', str(home / '.local/state'))
    monkeypatch.setenv('XDG_CONFIG_HOME', str(home / '.config'))
    monkeypatch.setenv('XDG_DATA_HOME', str(home / '.local/share'))
    monkeypatch.setenv('XDG_CACHE_HOME', str(home / '.cache'))
    binary_dir = tmp_path / 'bin'
    binary_dir.mkdir()
    probe_log = tmp_path / 'probe.jsonl'
    monkeypatch.setenv('T171_PROBE_LOG', str(probe_log))
    binary = put(
        binary_dir,
        'opencode',
        (
            f'#!{sys.executable}\n'
            'import json, os, sys, time\n'
            'with open(os.environ["T171_PROBE_LOG"], "a") as log:\n'
            '    log.write(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd()}) + "\\n")\n'
            'mode = os.environ.get("T171_PROBE_MODE", "ok")\n'
            'if mode == "timeout": time.sleep(30)\n'
            'if mode == "nonzero":\n'
            '    print("T171_SYNTHETIC_SECRET_NEVER_PRINT_THIS", file=sys.stderr)\n'
            '    sys.exit(7)\n'
            'print({"ok":"1.19.0", "old":"1.18.0", "future":"1.20.0", '
            '"malformed":"T171_SYNTHETIC_SECRET_NEVER_PRINT_THIS"}.get(mode, "1.19.0"))\n'
        ),
    )
    binary.chmod(0o700)
    # Keep only git from the original PATH. Missing OpenCode must really mean missing.
    git = shutil.which('git')
    if git:
        (binary_dir / 'git').symlink_to(git)
    monkeypatch.setenv('PATH', str(binary_dir))
    project = tmp_path / 'project'
    project.mkdir()
    put(project, 'CLAUDE.md', RULE + '\n')
    return project, home, binary, probe_log


@pytest.mark.parametrize('command', ['update', 'apply'])
@pytest.mark.parametrize(
    'mode',
    [
        'missing',
        'nonexecutable',
        'broken',
        'nonzero',
        'old',
        'future',
        'malformed',
    ],
)
def test_runtime_failure_before_all_project_and_recovery_writes(
    sandbox, monkeypatch, command, mode
):
    root, home, binary, _ = sandbox
    if command == 'update':
        put(root, '.copier-answers.yml', '_commit: 1.7.0\nlanguage: en\n')
    if mode == 'missing':
        binary.unlink()
    elif mode == 'nonexecutable':
        binary.chmod(0o600)
    elif mode == 'broken':
        binary.write_text('#!/no/such/interpreter\n')
    else:
        monkeypatch.setenv('T171_PROBE_MODE', mode)
    before, state = snapshot(root), snapshot(home)
    # Assert a prerequisite failure never even attempts target writes/prompts.
    original_mkdir = Path.mkdir
    original_write = Path.write_bytes

    def guard_mkdir(path, *args, **kwargs):
        assert not path.is_relative_to(root), f'prerequisite mkdir: {path}'
        return original_mkdir(path, *args, **kwargs)

    def guard_write(path, *args, **kwargs):
        assert not path.is_relative_to(root), f'prerequisite write: {path}'
        return original_write(path, *args, **kwargs)

    with (
        patch.object(Path, 'mkdir', guard_mkdir),
        patch.object(Path, 'write_bytes', guard_write),
        patch('typer.prompt', side_effect=AssertionError('prerequisite prompt')),
    ):
        result = invoke(root, command, *(['--force'] if command == 'update' else []))
    assert result.exit_code == 1, result.output + str(result.exception)
    assert not isinstance(result.exception, AssertionError), str(result.exception)
    assert 'opencode' in result.output.lower(), result.output
    assert SECRET not in result.output + result.stderr + str(result.exception)
    assert snapshot(root) == before
    assert snapshot(home) == state


@pytest.mark.parametrize('command', ['update', 'apply'])
def test_real_probe_timeout_is_bounded_and_nondestructive(
    sandbox, monkeypatch, command
):
    root, home, _, _ = sandbox
    if command == 'update':
        put(root, '.copier-answers.yml', '_commit: 1.7.0\nlanguage: en\n')
    monkeypatch.setenv('T171_PROBE_MODE', 'timeout')
    before, state = snapshot(root), snapshot(home)
    result = subprocess.run(
        [
            sys.executable,
            '-c',
            'from dreamteam.cli import app; app()',
            command,
            str(root),
        ],
        capture_output=True,
        text=True,
        timeout=12,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert 'opencode' in (result.stdout + result.stderr).lower()
    assert snapshot(root) == before
    assert snapshot(home) == state


def test_native_absent_apply_dryrun_does_not_create_directory(sandbox):
    root, home, binary, _ = sandbox
    binary.unlink()
    absent = root / 'absent'
    before, state = snapshot(root), snapshot(home)
    result = invoke(absent, 'apply', '--dry-run')
    assert result.exit_code == 0, result.output
    assert not absent.exists()
    assert snapshot(root) == before
    assert snapshot(home) == state


@pytest.mark.parametrize('command', ['update', 'apply'])
@pytest.mark.parametrize('state_kind', ['relative', 'inside-project', 'writable'])
def test_native_dryrun_without_journal_ignores_unrelated_migration_state_policy(
    sandbox, monkeypatch, command, state_kind
):
    root, home, binary, _ = sandbox
    (root / 'CLAUDE.md').unlink()
    initialized = RUNNER.invoke(app, ['init', str(root), '--defaults'])
    assert initialized.exit_code == 0, initialized.output
    if command == 'apply':
        # Exercise native unmanaged apply, not its unrelated managed-root refusal.
        (root / '.copier-answers.yml').unlink()
    subprocess.run(
        ['git', 'init', '--quiet', str(root)], check=True, capture_output=True
    )
    binary.unlink()
    if state_kind == 'relative':
        state = Path('relative-state')
    elif state_kind == 'inside-project':
        state = root / 'unused-migration-state'
    else:
        state = home / 'writable-state'
        state.mkdir(mode=0o777)
        state.chmod(0o777)
    monkeypatch.setenv('XDG_STATE_HOME', str(state))
    before, outside = snapshot(root), snapshot(home)
    result = invoke(root, command, '--dry-run')
    assert result.exit_code == 0, result.output + str(result.exception)
    assert snapshot(root) == before
    assert snapshot(home) == outside


@pytest.mark.parametrize(
    'command,dry_run',
    [
        ('update', False),
        ('update', True),
        ('apply', False),
        ('apply', True),
        ('migration-recover', False),
    ],
)
def test_legacy_migration_requires_platform_capabilities_before_writes(
    sandbox, command, dry_run
):
    root, home, _, _ = sandbox
    if command == 'update':
        put(root, '.copier-answers.yml', '_commit: 1.7.0\nlanguage: en\n')
    before, outside = snapshot(root), snapshot(home)
    store = import_module('dreamteam.migration_store')
    with patch.object(store.os, 'getuid', None):
        result = invoke(root, command, *(['--dry-run'] if dry_run else []))
    assert result.exit_code == 1, result.output + str(result.exception)
    assert 'posix' in result.output.lower(), result.output
    assert 'unsupported' in result.output.lower(), result.output
    assert not isinstance(result.exception, (TypeError, AttributeError))
    assert snapshot(root) == before
    assert snapshot(home) == outside


def test_runtime_probe_passes_exact_five_second_timeout_and_safe_cwd(sandbox):
    _, _, binary, _ = sandbox
    with patch(
        'dreamteam.runtime.subprocess.run',
        return_value=subprocess.CompletedProcess([], 0, '1.19.0\n', ''),
    ) as run:
        assert inspect_runtime() == (str(binary), '1.19.0')
    run.assert_called_once_with(
        [str(binary), '--version'],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
        cwd=Path('/'),
    )


def test_probe_uses_only_version_and_safe_cwd_without_server(sandbox):
    root, _, _, log = sandbox
    result = invoke(root, 'apply', '--dry-run')
    assert result.exit_code == 0, result.output + str(result.exception)
    assert log.exists(), 'migration must execute OpenCode, not only shutil.which'
    records = [json.loads(line) for line in log.read_text().splitlines()]
    assert records
    for record in records:
        assert record['argv'] == ['--version']
        assert not Path(record['cwd']).is_relative_to(root)


@pytest.mark.parametrize('policy', ['keep', 'overwrite', 'save-as-new'])
def test_unmanaged_neutral_artifacts_verified_before_source_deletion(sandbox, policy):
    root, _, _, _ = sandbox
    artifacts = {
        'agents/auditor.md': '---\nname: auditor\ndescription: Audit trails\n---\nCheck invariants.\n',
        'commands/check.md': '---\nname: check\ndescription: Review contract\n---\nCheck acceptance.\n',
        'skills/check/SKILL.md': '---\nname: check\ndescription: Review contract\n---\nRetain traceability.\n',
    }
    for rel, text in artifacts.items():
        put(root, '.claude/' + rel, text)
    put(root, '.claude/settings.json', '{}\n')
    result = RUNNER.invoke(
        app,
        [
            'apply',
            str(root),
            '--defaults',
            '--on-conflict',
            policy,
        ],
    )
    assert result.exit_code == 0, result.output + str(result.exception)
    assert RULE in (root / 'AGENTS.md').read_text()
    assert not (root / 'CLAUDE.md').exists()
    for rel, text in artifacts.items():
        transferred = (root / '.opencode' / rel).read_text()
        old_header, old_body = text.split('---', 2)[1:]
        new_header, new_body = transferred.split('---', 2)[1:]
        old_fields = yaml.safe_load(old_header)
        new_fields = yaml.safe_load(new_header)
        assert new_body == old_body
        assert new_fields['description'] == old_fields['description']
        if rel.startswith('agents/'):
            assert new_fields.get('mode', 'subagent') == 'subagent'
            assert not {'model', 'tools', 'hooks'} & new_fields.keys()
        else:
            assert new_fields['name'] == old_fields['name']
        assert not (root / '.claude' / rel).exists()
    assert not (root / '.claude/settings.json').exists()
    assert (root / '.copier-answers.yml').is_file()


@pytest.mark.parametrize(
    'artifact,content',
    [
        ('settings.json', '{"unknown": true}'),
        ('settings.json', '{not-json'),
        ('settings.local.json', '{"env": {"TOKEN": "' + SECRET + '"}}'),
        ('agents/custom.md', '---\nname: custom\ntools: Bash\n---\nCustom role\n'),
        ('agents/custom.md', '---\nname: custom\nmodel: opus\n---\nCustom role\n'),
        ('agents/custom.md', '---\nname: different\n---\nCustom role\n'),
        ('hooks/pre-task.sh', '#!/bin/sh\nexit 0\n'),
        ('skills/custom/SKILL.md', '---\nname: custom\nhooks: {}\n---\nCustom skill\n'),
        ('commands/custom.md', 'Run `claude --dangerously-skip-permissions`.\n'),
    ],
)
@pytest.mark.parametrize('dry_run', [False, True])
def test_unsupported_blocks_entire_apply_without_secret_leak_or_metadata(
    sandbox, artifact, content, dry_run
):
    root, home, _, _ = sandbox
    put(root, '.claude/' + artifact, content)
    before, state = snapshot(root), snapshot(home)
    result = invoke(root, 'apply', *(['--dry-run'] if dry_run else []))
    assert result.exit_code == 1, result.output + str(result.exception)
    assert snapshot(root) == before
    assert snapshot(home) == state
    assert SECRET not in result.output + result.stderr + str(result.exception)
    assert not (root / '.copier-answers.yml').exists()


@pytest.mark.parametrize('force', [False, True])
def test_managed_missing_base_cannot_overwrite_legacy_even_with_force(sandbox, force):
    root, home, _, _ = sandbox
    put(root, '.copier-answers.yml', '_commit: missing-baseline\nlanguage: en\n')
    put(root, 'AGENTS.md', 'Independent destination policy.\n')
    before, state = snapshot(root), snapshot(home)
    result = invoke(root, 'update', *(['--force'] if force else []))
    assert result.exit_code == 1, result.output
    assert snapshot(root) == before
    assert snapshot(home) == state


@pytest.mark.parametrize(
    'instruction', ['Run `claude "fix audit"`.\n', 'Run `claude review`.\n']
)
@pytest.mark.parametrize('entry', ['CLAUDE.md', '.claude/commands/custom.md'])
@pytest.mark.parametrize('dry_run', [False, True])
def test_active_legacy_cli_prompt_blocks_before_mutation(
    sandbox, instruction, entry, dry_run
):
    root, home, _, _ = sandbox
    put(root, entry, RULE + '\n' + instruction)
    before, state = snapshot(root), snapshot(home)
    result = invoke(root, 'apply', *(['--dry-run'] if dry_run else []))
    assert result.exit_code == 1, result.output + str(result.exception)
    assert snapshot(root) == before
    assert snapshot(home) == state
    assert SECRET not in result.output + result.stderr + str(result.exception)


@pytest.fixture
def released_170(sandbox, tmp_path):
    """Read the immutable shipped 1.7 tag, never synthesize a current baseline."""
    root, home, binary, log = sandbox
    clone = tmp_path / 'historical-bundle'
    _clone_bundle(_bundle_path(), clone)

    def render(model='inherit'):
        # Use ORIGINAL answers; normalizing aliases before base render is a bug.
        answers = {
            'language': 'en',
            'project_name': 'migration-fixture',
            'architect_model': model,
        }
        (root / 'CLAUDE.md').unlink(missing_ok=True)
        _copier_render_at(root, answers, clone=clone, ref='1.7.0')
        put(
            root, '.copier-answers.yml', yaml.safe_dump({'_commit': '1.7.0', **answers})
        )
        subprocess.run(
            ['git', 'init', '--quiet', str(root)], check=True, capture_output=True
        )
        return root, home, binary, log

    return render


@pytest.mark.parametrize('model', ['inherit', 'opus', 'sonnet', 'haiku'])
def test_exact_170_recipe_preserves_rules_and_architect_body_edits(released_170, model):
    root, _, _, _ = released_170(model)
    rules = root / 'CLAUDE.md'
    rules.write_text(rules.read_text() + '\n' + RULE + '\n')
    architect = root / '.claude/agents/architect.md'
    assert architect.is_file(), 'historical fixture must contain actual legacy role'
    architect.write_text(
        architect.read_text() + '\nCustom review invariant: verify audit logs.\n'
    )
    result = invoke(root, 'update')
    assert result.exit_code == 0, result.output + str(result.exception)
    assert RULE in (root / 'AGENTS.md').read_text()
    text = (root / '.opencode/agents/architect.md').read_text()
    assert 'Custom review invariant: verify audit logs.' in text
    fields = yaml.safe_load(text.split('---', 2)[1])
    assert fields['permission']['*'] == 'deny'
    assert 'model' not in fields
    assert not architect.exists()
    assert not rules.exists()
    completed = yaml.safe_load((root / '.copier-answers.yml').read_text())
    assert completed['_commit'] != '1.7.0'


@pytest.mark.parametrize('mutation', ['tools', 'model', 'unknown-key'])
def test_changed_170_role_control_fields_are_not_silently_dropped(
    released_170, mutation
):
    root, home, _, _ = released_170('opus')
    role = root / '.claude/agents/architect.md'
    raw = role.read_text()
    _, header, body = raw.split('---', 2)
    fields = yaml.safe_load(header)
    if mutation == 'tools':
        fields['tools'] = 'Read, Bash'
    elif mutation == 'model':
        fields['model'] = 'custom-provider/custom-model'
    else:
        fields['customControl'] = True
    role.write_text('---\n' + yaml.safe_dump(fields) + '---' + body)
    before, state = snapshot(root), snapshot(home)
    result = invoke(root, 'update', '--force')
    assert result.exit_code == 1, result.output + str(result.exception)
    assert snapshot(root) == before
    assert snapshot(home) == state


def test_managed_both_appended_rules_from_both_sides_survive(released_170):
    root, _, _, _ = released_170()
    rules = root / 'CLAUDE.md'
    rules.write_text(
        rules.read_text() + '\nLegacy audit policy: retain seven revisions.\n'
    )
    put(
        root,
        'AGENTS.md',
        'Destination accessibility policy: keyboard navigation required.\n',
    )
    result = invoke(root, 'update')
    assert result.exit_code == 0, result.output + str(result.exception)
    result_rules = (root / 'AGENTS.md').read_text()
    assert 'Legacy audit policy: retain seven revisions.' in result_rules
    assert (
        'Destination accessibility policy: keyboard navigation required.'
        in result_rules
    )
    assert not rules.exists()


@pytest.mark.parametrize('command', ['update', 'apply'])
def test_legacy_dryrun_does_not_create_recovery_or_advance_answers(sandbox, command):
    root, home, _, _ = sandbox
    if command == 'update':
        put(root, '.copier-answers.yml', '_commit: 1.7.0\nlanguage: en\n')
    put(root, '.claude/commands/custom.md', 'Keep audit procedure.\n')
    before, state = snapshot(root), snapshot(home)
    result = invoke(root, command, '--dry-run')
    assert result.exit_code == 0, result.output + str(result.exception)
    assert snapshot(root) == before
    assert snapshot(home) == state


@pytest.mark.parametrize('command', ['update', 'apply'])
@pytest.mark.parametrize(
    'kind', ['source-leaf', 'source-parent', 'destination-leaf', 'destination-parent']
)
def test_required_symlinks_block_without_reading_or_modifying_outside(
    sandbox, command, kind
):
    root, home, _, _ = sandbox
    external = root.parent / 'external'
    external.mkdir()
    put(external, 'sentinel.md', SECRET)
    if command == 'update':
        put(root, '.copier-answers.yml', '_commit: 1.7.0\nlanguage: en\n')
    if kind == 'source-leaf':
        (root / 'CLAUDE.md').unlink()
        (root / 'CLAUDE.md').symlink_to(external / 'sentinel.md')
    elif kind == 'source-parent':
        (root / '.claude').symlink_to(external, target_is_directory=True)
    elif kind == 'destination-leaf':
        (root / 'AGENTS.md').symlink_to(external / 'sentinel.md')
    else:
        (root / '.opencode').symlink_to(external, target_is_directory=True)
    before, outside, state = snapshot(root), snapshot(external), snapshot(home)
    original_read_bytes, original_read_text = Path.read_bytes, Path.read_text

    def guard_bytes(path, *args, **kwargs):
        assert not path.resolve().is_relative_to(external), 'followed external link'
        return original_read_bytes(path, *args, **kwargs)

    def guard_text(path, *args, **kwargs):
        assert not path.resolve().is_relative_to(external), 'followed external link'
        return original_read_text(path, *args, **kwargs)

    with (
        patch.object(Path, 'read_bytes', guard_bytes),
        patch.object(Path, 'read_text', guard_text),
    ):
        result = invoke(root, command, '--dry-run')
    assert result.exit_code == 1, result.output + str(result.exception)
    assert not isinstance(result.exception, AssertionError)
    assert SECRET not in result.output + result.stderr + str(result.exception)
    assert snapshot(root) == before
    assert snapshot(external) == outside
    assert snapshot(home) == state


def test_worktrees_git_and_external_links_are_excluded_and_parent_retained(sandbox):
    root, _, _, _ = sandbox
    put(root, '.claude/worktrees/active/CLAUDE.md', SECRET)
    put(root, '.git/private-record', SECRET)
    outside = root.parent / 'outside'
    outside.mkdir()
    put(outside, 'private', SECRET)
    (root / '.claude/worktrees/external').symlink_to(outside, target_is_directory=True)
    protected = snapshot(root / '.claude/worktrees')
    git = snapshot(root / '.git')
    result = invoke(root)
    assert result.exit_code == 0, result.output + str(result.exception)
    assert snapshot(root / '.claude/worktrees') == protected
    assert snapshot(root / '.git') == git
    assert (root / '.claude').is_dir()
    assert SECRET not in result.output + result.stderr


@pytest.mark.parametrize('entry', ['CLAUDE.md', '.claude/commands/custom.md'])
def test_unmanaged_both_preserves_disjoint_additions(sandbox, entry):
    root, _, _, _ = sandbox
    destination = (
        'AGENTS.md' if entry == 'CLAUDE.md' else entry.replace('.claude/', '.opencode/')
    )
    common = 'Shared neutral project policy.\n'
    put(root, entry, 'Legacy-only audit invariant.\n' + common)
    put(root, destination, common + 'Destination-only accessibility invariant.\n')
    result = invoke(root)
    assert result.exit_code == 0, result.output + str(result.exception)
    output = (root / destination).read_text()
    assert 'Legacy-only audit invariant.' in output
    assert 'Destination-only accessibility invariant.' in output
    assert output.count(common.strip()) == 1
    assert not (root / entry).exists()


def test_unmanaged_both_overlap_is_conflict_without_any_writes(sandbox):
    root, home, _, _ = sandbox
    put(root, '.claude/commands/custom.md', 'Policy\nMaximum retries: 3\nEnd\n')
    put(root, '.opencode/commands/custom.md', 'Policy\nMaximum retries: 7\nEnd\n')
    before, state = snapshot(root), snapshot(home)
    result = invoke(root)
    assert result.exit_code == 2, result.output + str(result.exception)
    assert snapshot(root) == before
    assert snapshot(home) == state


def test_successful_apply_then_update_is_idempotent_and_recovery_is_private(sandbox):
    root, home, _, _ = sandbox
    subprocess.run(
        ['git', 'init', '--quiet', str(root)], check=True, capture_output=True
    )
    first = invoke(root)
    assert first.exit_code == 0, first.output + str(first.exception)
    assert RULE in (root / 'AGENTS.md').read_text()
    before, state = snapshot(root), snapshot(home)
    second = invoke(root, 'update')
    assert second.exit_code == 0, second.output + str(second.exception)
    assert snapshot(root) == before
    assert snapshot(home) == state, 'completed replay must not churn recovery'
    store = home / '.local/state/dreamteam/migrations'
    assert store.is_dir(), 'protected originals and journal must exist outside project'
    for path in store.rglob('*'):
        assert not path.is_symlink()
        assert stat.S_IMODE(path.stat().st_mode) == (0o700 if path.is_dir() else 0o600)


@pytest.mark.parametrize(
    'event',
    [
        'recovery_prepared',
        'target_applied',
        'target_verified',
        'legacy_removed',
        'before_completion',
    ],
)
def test_controlled_io_fault_has_no_false_completion_and_retains_originals(
    sandbox, monkeypatch, event
):
    root, home, _, _ = sandbox
    store = import_module('dreamteam.migration_store')
    reached = []
    before = snapshot(root)

    def fail_at(actual, operation_id):
        if actual == event:
            reached.append(actual)
            raise OSError('injected synthetic storage failure')

    monkeypatch.setattr(store, 'checkpoint', fail_at)
    result = invoke(root)
    assert reached == [event], result.output + str(result.exception)
    assert result.exit_code == 1, result.output + str(result.exception)
    assert not (root / '.copier-answers.yml').exists()
    if snapshot(root) != before:
        assert 'recover' in result.output.lower(), result.output
    # Exact restoration via the public command is proof that scoped originals
    # survive; existence of an arbitrary nonempty recovery file is not proof.
    recovered = invoke(root, 'migration-recover', '--rollback')
    assert recovered.exit_code == 0, recovered.output + str(recovered.exception)
    original_files = {k: v for k, v in before.items() if v[0] != 'dir'}
    actual_files = {k: v for k, v in snapshot(root).items() if v[0] != 'dir'}
    assert actual_files == original_files


def test_failed_automatic_rollback_retains_publicly_restorable_bytes_and_modes(sandbox):
    root, _, _, _ = sandbox
    (root / 'CLAUDE.md').chmod(0o640)
    put(root, '.claude/commands/custom.md', 'Keep custom audit bytes.\n').chmod(0o750)
    original = {k: v for k, v in snapshot(root).items() if v[0] != 'dir'}
    unlink = Path.unlink
    reached = []

    def fail_forward_delete(path, *args, **kwargs):
        if path == root / 'CLAUDE.md' and not reached:
            reached.append('forward-delete')
            raise OSError('synthetic source deletion failure')
        if reached and path == root / 'AGENTS.md':
            reached.append('rollback-delete')
            raise OSError('synthetic automatic rollback failure')
        return unlink(path, *args, **kwargs)

    with patch.object(Path, 'unlink', fail_forward_delete):
        result = invoke(root)
    assert reached == ['forward-delete', 'rollback-delete'], result.output
    assert result.exit_code == 1, result.output + str(result.exception)
    assert 'migration-recover' in result.output
    assert not (root / '.copier-answers.yml').exists()
    assert (root / 'AGENTS.md').exists(), 'rollback really failed after mutation'
    recovery = invoke(root, 'migration-recover', '--rollback')
    assert recovery.exit_code == 0, recovery.output + str(recovery.exception)
    assert {k: v for k, v in snapshot(root).items() if v[0] != 'dir'} == original


@pytest.mark.parametrize('command', ['update', 'apply'])
def test_answers_symlink_is_blocked_before_external_read(sandbox, command):
    root, home, _, _ = sandbox
    external = root.parent / 'external-answers.yml'
    external.write_text('_commit: 1.7.0\nsecret: ' + SECRET + '\n')
    (root / '.copier-answers.yml').symlink_to(external)
    before, state, outside = snapshot(root), snapshot(home), external.read_bytes()
    read_bytes, read_text = Path.read_bytes, Path.read_text

    def guard_bytes(path, *args, **kwargs):
        assert path.resolve() != external, 'read external answers before validation'
        return read_bytes(path, *args, **kwargs)

    def guard_text(path, *args, **kwargs):
        assert path.resolve() != external, 'read external answers before validation'
        return read_text(path, *args, **kwargs)

    with (
        patch.object(Path, 'read_bytes', guard_bytes),
        patch.object(Path, 'read_text', guard_text),
    ):
        result = invoke(root, command, '--dry-run')
    assert result.exit_code == 1, result.output + str(result.exception)
    assert 'symlink' in result.output.lower()
    assert not isinstance(result.exception, AssertionError)
    assert SECRET not in result.output + result.stderr + str(result.exception)
    assert snapshot(root) == before
    assert snapshot(home) == state
    assert external.read_bytes() == outside


def test_edit_after_staging_is_revalidated_before_overwrite(sandbox, monkeypatch):
    root, _, _, _ = sandbox
    store = import_module('dreamteam.migration_store')
    change = 'New user edit after staging must not be overwritten.\n'
    reached = []

    def edit(event, operation_id):
        if event == 'recovery_prepared':
            reached.append(event)
            put(root, 'CLAUDE.md', change)

    monkeypatch.setattr(store, 'checkpoint', edit)
    result = invoke(root)
    assert reached, result.output + str(result.exception)
    assert result.exit_code == 1, result.output + str(result.exception)
    assert (root / 'CLAUDE.md').read_text() == change
    assert not (root / '.copier-answers.yml').exists()


@pytest.mark.parametrize(
    'failure', ['journal-first', 'target-first', 'target-second', 'delete-first']
)
def test_actual_filesystem_operation_failures_are_recoverable(
    sandbox, monkeypatch, failure
):
    root, home, _, _ = sandbox
    put(root, '.claude/commands/check.md', 'Independent preserved custom command.\n')
    original = {name: item for name, item in snapshot(root).items() if item[0] != 'dir'}
    replace, unlink = Path.replace, Path.unlink
    reached = []
    target_count = 0

    def fail_replace(path, destination, *args, **kwargs):
        nonlocal target_count
        if path.name.startswith('.dt-migrate-'):
            target_count += 1
            requested = 2 if failure == 'target-second' else 1
            if failure.startswith('target-') and target_count == requested:
                reached.append(failure)
                raise OSError('synthetic failed target replacement')
        if (
            failure == 'journal-first'
            and path.name.startswith('journal-')
            and not reached
        ):
            reached.append(failure)
            raise OSError('synthetic failed journal replacement')
        return replace(path, destination, *args, **kwargs)

    def fail_unlink(path, *args, **kwargs):
        if failure == 'delete-first' and path == root / 'CLAUDE.md' and not reached:
            reached.append(failure)
            raise OSError('synthetic failed source unlink')
        return unlink(path, *args, **kwargs)

    with (
        patch.object(Path, 'replace', fail_replace),
        patch.object(Path, 'unlink', fail_unlink),
    ):
        result = invoke(root)
    assert reached == [failure], result.output + str(result.exception)
    assert result.exit_code == 1, result.output + str(result.exception)
    assert not (root / '.copier-answers.yml').exists()
    if failure != 'journal-first':
        recovery = invoke(root, 'migration-recover', '--rollback')
        assert recovery.exit_code == 0, recovery.output + str(recovery.exception)
    actual = {name: item for name, item in snapshot(root).items() if item[0] != 'dir'}
    assert actual == original


@pytest.mark.parametrize('kind', ['directory-mode', 'journal-mode', 'symlink'])
def test_insecure_recovery_storage_blocks_before_project_mutation(sandbox, kind):
    root, home, _, _ = sandbox
    store = (
        home
        / '.local/state/dreamteam/migrations'
        / hashlib.sha256(os.fsencode(root.resolve())).hexdigest()
    )
    store.mkdir(parents=True, mode=0o700)
    if kind == 'directory-mode':
        store.chmod(0o755)
    elif kind == 'journal-mode':
        put(store, 'operation.json', '{}').chmod(0o644)
    else:
        outside = root.parent / 'external-journal'
        outside.write_text(SECRET)
        (store / 'operation.json').symlink_to(outside)
    before, state = snapshot(root), snapshot(home)
    result = invoke(root)
    assert result.exit_code == 1, result.output + str(result.exception)
    assert snapshot(root) == before
    assert snapshot(home) == state
    assert SECRET not in result.output + result.stderr + str(result.exception)


def test_recovery_creation_permission_failure_never_mutates_project(sandbox):
    root, home, _, _ = sandbox
    before = snapshot(root)
    original_mkdir = Path.mkdir

    def fail(path, *args, **kwargs):
        if path.is_relative_to(home / '.local/state'):
            raise PermissionError('synthetic unavailable private recovery')
        return original_mkdir(path, *args, **kwargs)

    with patch.object(Path, 'mkdir', fail):
        result = invoke(root)
    assert result.exit_code == 1, result.output + str(result.exception)
    assert snapshot(root) == before


@pytest.mark.parametrize('rollback', [False, True])
@pytest.mark.parametrize(
    'event',
    [
        'recovery_prepared',
        'target_applied',
        'target_verified',
        'legacy_removed',
        'before_completion',
        'answers_published',
    ],
)
def test_abrupt_process_loss_then_public_recovery_preserves_information(
    sandbox, event, rollback
):
    root, _, _, _ = sandbox
    put(root, '.claude/commands/custom.md', 'Keep independent custom procedure.\n')
    original = {name: item for name, item in snapshot(root).items() if item[0] != 'dir'}
    marker = root.parent / 'crash-reached'
    process = subprocess.run(
        [
            sys.executable,
            str(FIXTURES / 't171_crash_driver.py'),
            str(root),
            event,
            str(marker),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert marker.exists(), process.stdout + process.stderr
    assert process.returncode == -signal.SIGKILL, process.stdout + process.stderr
    assert (root / '.copier-answers.yml').exists() == (event == 'answers_published')
    recovered = invoke(root, 'migration-recover', *(['--rollback'] if rollback else []))
    assert recovered.exit_code == 0, recovered.output + str(recovered.exception)
    if rollback:
        actual = {
            name: item for name, item in snapshot(root).items() if item[0] != 'dir'
        }
        assert actual == original
        assert not (root / '.copier-answers.yml').exists()
        return
    assert RULE in (root / 'AGENTS.md').read_text()
    assert (
        'Keep independent custom procedure.'
        in (root / '.opencode/commands/custom.md').read_text()
    )
    assert not (root / 'CLAUDE.md').exists()
    assert (root / '.copier-answers.yml').exists()
    before = snapshot(root)
    again = invoke(root, 'migration-recover')
    assert again.exit_code == 0, again.output + str(again.exception)
    assert snapshot(root) == before


def test_recovery_blocks_concurrent_user_edit_without_destroying_it(sandbox):
    root, home, _, _ = sandbox
    marker = root.parent / 'crash-reached'
    process = subprocess.run(
        [
            sys.executable,
            str(FIXTURES / 't171_crash_driver.py'),
            str(root),
            'before_completion',
            str(marker),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert marker.exists(), process.stdout + process.stderr
    assert process.returncode == -signal.SIGKILL
    put(root, 'AGENTS.md', 'User change made after interruption.\n')
    before, state = snapshot(root), snapshot(home)
    for flags in ([], ['--rollback']):
        recovered = invoke(root, 'migration-recover', *flags)
        assert recovered.exit_code == 1, recovered.output + str(recovered.exception)
        assert snapshot(root) == before
        assert not (root / '.copier-answers.yml').exists()
    # Recovery originals must not be destroyed or rewritten by the rejected replay.
    assert snapshot(home) == state


def test_pending_recovery_also_requires_runtime_before_writes(sandbox):
    root, home, binary, _ = sandbox
    marker = root.parent / 'crash-reached'
    process = subprocess.run(
        [
            sys.executable,
            str(FIXTURES / 't171_crash_driver.py'),
            str(root),
            'before_completion',
            str(marker),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert marker.exists(), process.stdout + process.stderr
    assert process.returncode == -signal.SIGKILL
    binary.unlink()
    before, state = snapshot(root), snapshot(home)
    for flags in ([], ['--rollback']):
        result = invoke(root, 'migration-recover', *flags)
        assert result.exit_code == 1, result.output + str(result.exception)
        assert 'opencode' in result.output.lower()
        assert snapshot(root) == before
        assert snapshot(home) == state


def test_snapshot_fixture_records_bytes_modes_and_dangling_links_without_recursion(
    tmp_path,
):
    root = tmp_path / 'root'
    file = put(root, 'directory/file', 'fixture bytes')
    file.chmod(0o640)
    (root / 'cycle').symlink_to(root, target_is_directory=True)
    (root / 'dangling').symlink_to(tmp_path / 'missing')
    result = snapshot(root)
    assert result['directory/file'] == ('file', b'fixture bytes', 0o640)
    assert result['cycle'] == ('link', str(root))
    assert result['dangling'] == ('link', str(tmp_path / 'missing'))
    assert len(result) == 4
