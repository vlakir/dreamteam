"""OpenCode migration preserves custom rules and enforces the runtime contract."""

from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from unittest.mock import MagicMock, patch
import json
import os
import pytest
from typer.testing import CliRunner
from dreamteam.cli import app, _plan_merge, _apply_plan, _dry_run
from dreamteam.runtime import inspect_runtime, launch

runner = CliRunner()


@pytest.fixture
def legacy_runtime(tmp_path_factory, monkeypatch):
    """Explicit offline version executable for positive legacy CLI scenarios."""
    home = tmp_path_factory.mktemp('legacy-runtime-home')
    home.chmod(0o700)
    monkeypatch.setenv('HOME', str(home))
    for variable, relative in {
        'XDG_STATE_HOME': '.local/state',
        'XDG_CONFIG_HOME': '.config',
        'XDG_DATA_HOME': '.local/share',
        'XDG_CACHE_HOME': '.cache',
    }.items():
        monkeypatch.setenv(variable, str(home / relative))
    binary_dir = tmp_path_factory.mktemp('legacy-runtime-bin')
    binary = binary_dir / 'opencode'
    binary.write_text(
        '#!/bin/sh\n'
        '[ "$#" -eq 1 ] && [ "$1" = --version ] || exit 9\n'
        "printf '%s\\n' 1.19.0\n"
    )
    binary.chmod(0o700)
    monkeypatch.setenv('PATH', str(binary_dir) + os.pathsep + os.environ['PATH'])
    return binary


def test_rules_rename_merges_project_customization(tmp_path):
    target, base, new = [tmp_path / name for name in ('project', 'base', 'new')]
    for folder in (target, base, new):
        folder.mkdir()
    (base / 'CLAUDE.md').write_text('Old client rules\n\nProject policy\n')
    (target / 'CLAUDE.md').write_text(
        'Old client rules\n\nProject policy\nCustom project rule\n'
    )
    (new / 'AGENTS.md').write_text('OpenCode rules\n\nProject policy\n')
    empty = tmp_path / 'empty'
    empty.touch()
    before = (target / 'CLAUDE.md').read_bytes()
    writes, deletes, conflicts = _plan_merge(target, base, new, empty)
    assert conflicts == 0
    _apply_plan(target, writes, deletes)
    assert (
        target / 'AGENTS.md'
    ).read_text() == 'OpenCode rules\n\nProject policy\nCustom project rule\n'
    assert (target / 'CLAUDE.md').read_bytes() == before  # retained migration source


def test_changed_rules_raise_merge_conflict_without_losing_source(tmp_path):
    target, base, new = [tmp_path / name for name in ('project', 'base', 'new')]
    for folder in (target, base, new):
        folder.mkdir()
    (base / 'CLAUDE.md').write_text('original\n')
    (target / 'CLAUDE.md').write_text('custom\n')
    (new / 'AGENTS.md').write_text('replacement\n')
    empty = tmp_path / 'empty'
    empty.touch()
    writes, deletes, conflicts = _plan_merge(target, base, new, empty)
    assert conflicts > 0
    assert b'custom' in writes[Path('AGENTS.md')]
    assert Path('CLAUDE.md') not in deletes


def test_generated_config_is_provider_independent(tmp_path):
    result = runner.invoke(app, ['init', str(tmp_path / 'project'), '--defaults'])
    assert result.exit_code == 0, result.output
    project = tmp_path / 'project'
    config = json.loads((project / 'opencode.json').read_text())
    assert config['plugin'] == ['@hueyexe/opencode-ensemble@0.18.0']
    assert config['instructions'] == ['.opencode/team-roles.md']
    assert not {'model', 'provider', 'mcp'} & config.keys()
    assert not (project / '.claude').exists()
    assert not (project / 'CLAUDE.md').exists()
    assert '@.opencode/' not in (project / 'AGENTS.md').read_text()
    assert (
        json.loads((project / '.opencode/ensemble.json').read_text())['mergeOnCleanup']
        is False
    )


@patch('dreamteam.runtime.shutil.which', return_value=None)
def test_missing_runtime_is_actionable(_which):
    result = runner.invoke(app, ['doctor'])
    assert result.exit_code == 1
    assert '1.19.0' in result.output


@pytest.mark.parametrize('version', ['1.18.0', '2.0.0', 'garbage'])
@patch('dreamteam.runtime.shutil.which', return_value='/bin/opencode')
def test_runtime_rejects_untested_versions(_which, version):
    with patch(
        'dreamteam.runtime.subprocess.run',
        return_value=CompletedProcess([], 0, version, ''),
    ):
        with pytest.raises(RuntimeError):
            inspect_runtime()


@patch('dreamteam.runtime.shutil.which', return_value='/bin/opencode')
def test_runtime_timeout_is_reported(_which):
    with patch(
        'dreamteam.runtime.subprocess.run', side_effect=TimeoutExpired('opencode', 15)
    ):
        with pytest.raises(RuntimeError, match='Cannot inspect'):
            inspect_runtime()


@patch('dreamteam.runtime.shutil.which', return_value='/bin/opencode')
def test_doctor_reports_only_runtime_not_live_capabilities(_which):
    with patch(
        'dreamteam.runtime.subprocess.run',
        return_value=CompletedProcess([], 0, '1.19.0\n', ''),
    ):
        result = runner.invoke(app, ['doctor'])
        assert result.exit_code == 0
        assert 'not tested' in result.output


@patch('dreamteam.runtime.inspect_ensemble', return_value=['team_create'])
def test_launch_passes_project_and_session_as_arguments(_ensemble, tmp_path):
    (tmp_path / 'opencode.json').write_text('{}')
    with patch(
        'dreamteam.runtime.inspect_runtime', return_value=('/bin/opencode', '1.19.0')
    ):
        with patch(
            'dreamteam.runtime.subprocess.run', return_value=CompletedProcess([], 7)
        ) as execute:
            assert launch(tmp_path, session='ses_test') == 7
            assert execute.call_args.args[0] == [
                '/bin/opencode',
                'attach',
                'http://127.0.0.1:4096',
                '--dir',
                str(tmp_path),
                '--session',
                'ses_test',
            ]


def test_launch_validates_remote_project_instead_of_client_filesystem(tmp_path):
    remote = tmp_path / 'exists-only-on-server'
    assert not remote.exists()
    with (
        patch(
            'dreamteam.runtime.inspect_runtime',
            return_value=('/bin/opencode', '1.19.0'),
        ),
        patch('dreamteam.runtime.inspect_ensemble') as inspect,
        patch(
            'dreamteam.runtime.subprocess.run', return_value=CompletedProcess([], 0)
        ) as execute,
    ):
        assert launch(remote, server='http://127.0.0.1:4096') == 0
        inspect.assert_called_once_with('http://127.0.0.1:4096', remote)
        assert execute.call_args.args[0][-1] == str(remote)
    with (
        patch(
            'dreamteam.runtime.inspect_runtime',
            return_value=('/bin/opencode', '1.19.0'),
        ),
        patch(
            'dreamteam.runtime.inspect_ensemble',
            side_effect=RuntimeError('Ensemble missing'),
        ),
        patch('dreamteam.runtime.subprocess.run') as execute,
    ):
        with pytest.raises(RuntimeError, match='Ensemble missing'):
            launch(remote)
        execute.assert_not_called()


def test_legacy_migration_refuses_destructive_fallback(tmp_path, monkeypatch, legacy_runtime):
    from dreamteam import cli
    import yaml

    (tmp_path / 'CLAUDE.md').write_text('Unique project policy\n')
    (tmp_path / '.copier-answers.yml').write_text(
        yaml.safe_dump({'_commit': 'missing-tag', 'language': 'en'})
    )
    monkeypatch.setattr(cli, '_has_git', lambda: False)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    result = runner.invoke(app, ['update', str(tmp_path)])
    assert result.exit_code == 1
    assert 'No files changed' in result.output
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


@pytest.mark.integration
def test_released_170_project_migrates_with_custom_rules(tmp_path, legacy_runtime):
    import shutil
    from dreamteam.cli import _bundle_path, _clone_bundle, _copier_render_at

    target = tmp_path / 'project'
    clone = tmp_path / 'bundle'
    _clone_bundle(_bundle_path(), clone)
    _copier_render_at(target, {'language': 'ru'}, clone=clone, ref='1.7.0')
    # The original CLI wrote metadata separately after template rendering.
    import yaml

    (target / '.copier-answers.yml').write_text(
        yaml.safe_dump({'_commit': '1.7.0', 'language': 'ru'})
    )
    old = target / 'CLAUDE.md'
    old.write_text(old.read_text() + '\nProject-specific invariant: T170_KEEP_THIS.\n')
    import subprocess

    subprocess.run(['git', 'init', '--quiet', str(target)], check=True)
    result = runner.invoke(app, ['update', str(target)])
    assert result.exit_code == 0, result.output
    assert (target / 'AGENTS.md').read_text().count(
        'Project-specific invariant: T170_KEEP_THIS.'
    ) == 1
    assert not old.exists(), 'T171 removes the verified migration source'
    assert (target / '.opencode/agents/architect.md').is_file()
    assert json.loads((target / 'opencode.json').read_text())['plugin']


def test_doctor_detects_silently_missing_ensemble(tmp_path):
    from io import BytesIO
    from dreamteam.runtime import inspect_ensemble

    response = BytesIO(b'["read", "bash"]')
    response.status = 200
    connection = MagicMock()
    connection.getresponse.return_value = response
    with patch('dreamteam.runtime.HTTPConnection', return_value=connection):
        with pytest.raises(RuntimeError, match='Ensemble tools are missing'):
            inspect_ensemble('http://localhost:4096', tmp_path)


def test_doctor_accepts_registered_team_tools(tmp_path):
    from io import BytesIO
    from dreamteam.runtime import inspect_ensemble

    tools = ['team_create', 'team_spawn', 'team_message', 'team_tasks_list']
    response = BytesIO(json.dumps(tools).encode())
    response.status = 200
    connection = MagicMock()
    connection.getresponse.return_value = response
    with patch('dreamteam.runtime.HTTPConnection', return_value=connection):
        assert inspect_ensemble('http://localhost:4096', tmp_path) == sorted(tools)
    connection.close.assert_called_once()


def test_legacy_architect_alias_does_not_become_invalid_opencode_model():
    from dreamteam.cli import _user_answers

    assert _user_answers({'architect_model': 'opus'})['architect_model'] == 'inherit'
    assert (
        _user_answers({'architect_model': 'example/coder'})['architect_model']
        == 'example/coder'
    )


def test_new_project_rejects_claude_model_alias(tmp_path):
    result = runner.invoke(
        app, ['init', str(tmp_path), '--defaults', '--data', 'architect_model=opus']
    )
    assert result.exit_code != 0
    assert 'provider/model-id' in result.output


@pytest.mark.parametrize('language', ['en', 'ru', 'fr', 'de', 'zh'])
def test_standard_team_has_nine_provider_independent_roles(tmp_path, language):
    import yaml

    project = tmp_path / language
    result = runner.invoke(
        app, ['init', str(project), '--defaults', '--data', f'language={language}']
    )
    assert result.exit_code == 0, result.output
    config = json.loads((project / 'opencode.json').read_text())
    assert config['default_agent'] == 'tech-lead'
    roles = {
        p.stem: yaml.safe_load(p.read_text().split('---', 2)[1])
        for p in (project / '.opencode/agents').glob('*.md')
    }
    assert set(roles) == {
        'tech-lead',
        'architect',
        'designer',
        'frontend',
        'mobile',
        'backend',
        'tester',
        'reviewer',
        'devops',
    }
    for name, role in roles.items():
        assert 'model' not in role
        assert role['mode'] == ('primary' if name == 'tech-lead' else 'subagent')
    for name in ('architect', 'reviewer'):
        assert roles[name]['permission']['*'] == 'deny'
        assert roles[name]['permission']['team_message'] == 'allow'


def test_server_binds_locally_and_uses_project_directory(tmp_path):
    from dreamteam.runtime import serve

    (tmp_path / 'opencode.json').write_text('{}')
    with patch(
        'dreamteam.runtime.inspect_runtime', return_value=('/bin/opencode', '1.19.0')
    ):
        with patch(
            'dreamteam.runtime.subprocess.run', return_value=CompletedProcess([], 0)
        ) as execute:
            assert serve(tmp_path, port=4098) == 0
            assert execute.call_args.args[0] == [
                '/bin/opencode',
                'serve',
                '--hostname',
                '127.0.0.1',
                '--port',
                '4098',
            ]
            assert execute.call_args.kwargs['cwd'] == tmp_path


def test_dryrun_never_copies_or_traverses_user_environment(tmp_path):
    target = tmp_path / 'project'
    target.mkdir()
    (target / '.copier-answers.yml').write_text('_commit: 1.7.0\nproject_name: demo\n')
    env = target / '.venv'
    env.mkdir()
    (env / 'cycle').symlink_to(env, target_is_directory=True)
    (target / 'AGENTS.md').write_text('custom rules\n')
    before = (target / 'AGENTS.md').read_bytes()
    with (
        patch('dreamteam.cli._has_git', return_value=True),
        patch('dreamteam.cli._bundle_has_tag', return_value=True),
        patch(
            'dreamteam.cli._compute_update_plan',
            return_value=({Path('AGENTS.md'): b'updated rules\n'}, set(), 0),
        ),
        patch(
            'dreamteam.cli.shutil.copytree',
            side_effect=AssertionError('must not copy project'),
        ),
    ):
        assert _dry_run(target, {'project_name': 'demo'}) == 0
    assert (target / 'AGENTS.md').read_bytes() == before
    assert (env / 'cycle').is_symlink()


@pytest.mark.parametrize('nested', [False, True])
def test_apply_plan_refuses_symlink_before_any_write(tmp_path, nested):
    project = tmp_path / 'project'
    project.mkdir()
    external = tmp_path / 'outside'
    external.mkdir()
    (external / 'AGENTS.md').write_text('do not overwrite\n')
    relative = Path('.opencode/AGENTS.md') if nested else Path('AGENTS.md')
    if nested:
        (project / '.opencode').symlink_to(external, target_is_directory=True)
    else:
        (project / 'AGENTS.md').symlink_to(external / 'AGENTS.md')
    with pytest.raises(RuntimeError, match='symlink'):
        _apply_plan(
            project,
            {Path('first.txt'): b'no partial write', relative: b'unsafe'},
            set(),
        )
    assert not (project / 'first.txt').exists()
    assert (external / 'AGENTS.md').read_text() == 'do not overwrite\n'


@pytest.mark.parametrize(
    ('relative', 'parent_link'),
    [(Path('AGENTS.md'), False), (Path('.opencode/agents/reviewer.md'), True)],
)
def test_update_dry_run_rejects_symlinked_managed_paths_without_leaking(
    tmp_path, relative, parent_link
):
    project = tmp_path / 'project'
    external = tmp_path / 'outside'
    project.mkdir()
    external.mkdir()
    sentinel = 'EXTERNAL_SENTINEL_MUST_NOT_BE_READ_OR_PRINTED'
    (project / '.copier-answers.yml').write_text('_commit: 1.7.0\nproject_name: demo\n')
    if parent_link:
        nested = external / '.opencode' / 'agents'
        nested.mkdir(parents=True)
        (nested / 'reviewer.md').write_text(sentinel, encoding='utf-8')
        (project / '.opencode').symlink_to(
            external / '.opencode', target_is_directory=True
        )
    else:
        (external / 'AGENTS.md').write_text(sentinel, encoding='utf-8')
        (project / 'AGENTS.md').symlink_to(external / 'AGENTS.md')
    external_before = {
        p.relative_to(external): p.read_bytes()
        for p in external.rglob('*')
        if p.is_file()
    }
    original_read_bytes = Path.read_bytes
    original_read_text = Path.read_text

    def guard_external_read(path, *args, **kwargs):
        if path.resolve() in {p.resolve() for p in external.rglob('*') if p.is_file()}:
            raise AssertionError('attempted to read external symlink destination')
        return original_read_bytes(path)

    def guard_external_text(path, *args, **kwargs):
        if path.resolve() in {p.resolve() for p in external.rglob('*') if p.is_file()}:
            raise AssertionError('attempted to read external symlink destination')
        return original_read_text(path, *args, **kwargs)

    before = {
        p.name: (p.is_symlink(), os.readlink(p) if p.is_symlink() else p.read_bytes())
        for p in project.iterdir()
    }

    with (
        patch('dreamteam.cli._has_git', return_value=True),
        patch('dreamteam.cli._bundle_has_tag', return_value=True),
        patch.object(Path, 'read_bytes', guard_external_read),
        patch.object(Path, 'read_text', guard_external_text),
    ):
        result = runner.invoke(app, ['update', str(project), '--dry-run'])

    assert result.exit_code == 1, result.output
    assert 'Template path is a symlink' in str(result.exception)
    assert sentinel not in result.output
    assert sentinel not in result.stderr
    assert not list(project.glob('first.txt'))
    after = {
        p.name: (p.is_symlink(), os.readlink(p) if p.is_symlink() else p.read_bytes())
        for p in project.iterdir()
    }
    assert after == before
    assert {
        p.relative_to(external): p.read_bytes()
        for p in external.rglob('*')
        if p.is_file()
    } == external_before


def test_legacy_claude_symlink_is_rejected_before_read_or_fallback(tmp_path):
    project = tmp_path / 'project'
    external = tmp_path / 'outside'
    project.mkdir()
    external.mkdir()
    sentinel = 'LEGACY_EXTERNAL_SENTINEL_MUST_NOT_LEAK'
    source = external / 'rules.md'
    source.write_text(sentinel, encoding='utf-8')
    (project / '.copier-answers.yml').write_text('_commit: 1.7.0\nproject_name: demo\n')
    (project / 'CLAUDE.md').symlink_to(source)
    external_before = source.read_bytes()
    original_read_bytes = Path.read_bytes
    original_read_text = Path.read_text

    def guard_external_read(path, *args, **kwargs):
        if path.resolve() == source.resolve():
            raise AssertionError('attempted to read external symlink destination')
        return original_read_bytes(path)

    def guard_external_text(path, *args, **kwargs):
        if path.resolve() == source.resolve():
            raise AssertionError('attempted to read external symlink destination')
        return original_read_text(path, *args, **kwargs)

    before = {
        p.name: (p.is_symlink(), os.readlink(p) if p.is_symlink() else p.read_bytes())
        for p in project.iterdir()
    }

    with (
        patch(
            'dreamteam.cli.inspect_runtime',
            return_value=('/bin/opencode', '1.19.0'),
        ),
        patch('dreamteam.cli._has_git', return_value=True),
        patch('dreamteam.cli._bundle_has_tag', return_value=True),
        patch.object(Path, 'read_bytes', guard_external_read),
        patch.object(Path, 'read_text', guard_external_text),
    ):
        result = runner.invoke(app, ['update', str(project), '--dry-run'])

    assert result.exit_code == 1, result.output
    assert isinstance(result.exception, SystemExit)
    assert 'symlink' in result.output.lower()
    assert not isinstance(result.exception, AssertionError)
    assert sentinel not in result.output
    assert sentinel not in result.stderr
    assert original_read_bytes(source) == external_before
    after = {
        p.name: (p.is_symlink(), os.readlink(p) if p.is_symlink() else p.read_bytes())
        for p in project.iterdir()
    }
    assert after == before


def test_update_dry_run_fallback_refuses_symlink_without_reading_sentinel(tmp_path):
    project = tmp_path / 'project'
    external = tmp_path / 'outside'
    project.mkdir()
    external.mkdir()
    sentinel = 'FALLBACK_EXTERNAL_SENTINEL_MUST_NOT_LEAK'
    destination = external / 'rules.md'
    destination.write_text(sentinel, encoding='utf-8')
    (project / '.copier-answers.yml').write_text(
        '_commit: unavailable-tag\nproject_name: demo\n'
    )
    (project / 'AGENTS.md').symlink_to(destination)
    external_before = destination.read_bytes()
    original_read_bytes = Path.read_bytes
    original_read_text = Path.read_text

    def guard_external_read(path, *args, **kwargs):
        if path.resolve() == destination.resolve():
            raise AssertionError('attempted to read external symlink destination')
        return original_read_bytes(path)

    def guard_external_text(path, *args, **kwargs):
        if path.resolve() == destination.resolve():
            raise AssertionError('attempted to read external symlink destination')
        return original_read_text(path, *args, **kwargs)

    before = {
        p.name: (p.is_symlink(), os.readlink(p) if p.is_symlink() else p.read_bytes())
        for p in project.iterdir()
    }

    def render_preview(**kwargs):
        destination = Path(kwargs['dst_path'])
        destination.mkdir(parents=True, exist_ok=True)
        (destination / 'AGENTS.md').write_text('preview rules\n', encoding='utf-8')

    with (
        patch('dreamteam.cli._has_git', return_value=True),
        patch('dreamteam.cli._bundle_has_tag', return_value=False),
        patch.object(Path, 'read_bytes', guard_external_read),
        patch.object(Path, 'read_text', guard_external_text),
        patch('dreamteam.cli.run_copy', side_effect=render_preview),
    ):
        result = runner.invoke(app, ['update', str(project), '--dry-run'])

    assert result.exit_code == 1, result.output
    assert 'Template path is a symlink' in str(result.exception)
    assert sentinel not in result.output
    assert sentinel not in result.stderr
    assert original_read_bytes(destination) == external_before
    after = {
        p.name: (p.is_symlink(), os.readlink(p) if p.is_symlink() else p.read_bytes())
        for p in project.iterdir()
    }
    assert after == before


@pytest.mark.parametrize(
    'unsafe_kind', ['canonical-leaf', 'canonical-parent', 'legacy-alias']
)
def test_plan_merge_preflights_real_render_paths_before_reading_project(
    tmp_path, unsafe_kind
):
    project = tmp_path / 'project'
    base = tmp_path / 'base'
    new = tmp_path / 'new'
    external = tmp_path / 'external'
    empty = tmp_path / 'empty'
    for folder in (project, base, new, external):
        folder.mkdir()
    empty.touch()
    sentinel = 'PLAN_EXTERNAL_SENTINEL'

    if unsafe_kind == 'legacy-alias':
        (base / 'CLAUDE.md').write_text('base rules\n', encoding='utf-8')
        (new / 'AGENTS.md').write_text('new rules\n', encoding='utf-8')
        (external / 'rules.md').write_text(sentinel, encoding='utf-8')
        (project / 'CLAUDE.md').symlink_to(external / 'rules.md')
    elif unsafe_kind == 'canonical-parent':
        rel = Path('.opencode/agents/reviewer.md')
        (new / rel).parent.mkdir(parents=True)
        (new / rel).write_text('new only\n', encoding='utf-8')
        outside = external / 'agents'
        outside.mkdir()
        (outside / 'reviewer.md').write_text(sentinel, encoding='utf-8')
        (project / '.opencode').symlink_to(external, target_is_directory=True)
    else:
        rel = Path('AGENTS.md')
        (new / rel).write_text('new only\n', encoding='utf-8')
        (external / 'AGENTS.md').write_text(sentinel, encoding='utf-8')
        (project / rel).symlink_to(external / 'AGENTS.md')

    before = {
        p.name: (p.is_symlink(), os.readlink(p) if p.is_symlink() else p.read_bytes())
        for p in project.iterdir()
    }
    external_before = {
        p.relative_to(external): p.read_bytes()
        for p in external.rglob('*')
        if p.is_file()
    }
    with patch(
        'dreamteam.cli._merge_file', side_effect=AssertionError('must not read/merge')
    ) as merge:
        with pytest.raises(RuntimeError, match='symlink'):
            _plan_merge(project, base, new, empty)
    merge.assert_not_called()
    assert {
        p.relative_to(external): p.read_bytes()
        for p in external.rglob('*')
        if p.is_file()
    } == external_before
    after = {
        p.name: (p.is_symlink(), os.readlink(p) if p.is_symlink() else p.read_bytes())
        for p in project.iterdir()
    }
    assert after == before


def _snapshot_tree(root):
    """Capture project entries without following symlinks."""
    snapshot = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if path.is_symlink():
            snapshot[relative] = ('symlink', os.readlink(path))
        elif path.is_file():
            snapshot[relative] = ('file', path.read_bytes(), path.stat().st_mode)
        elif path.is_dir():
            snapshot[relative] = ('directory',)
    return snapshot


@pytest.mark.parametrize('link_kind', ['leaf', 'parent'])
def test_force_update_refuses_managed_symlinks_before_any_write(tmp_path, link_kind):
    project = tmp_path / 'project'
    external = tmp_path / 'private-external'
    external.mkdir()
    sentinel = 'UTF8_PRIVATE_EXTERNAL_SENTINEL_DO_NOT_READ_OR_WRITE'
    (external / 'AGENTS.md').write_text(sentinel, encoding='utf-8')
    initialized = runner.invoke(app, ['init', str(project), '--defaults'])
    assert initialized.exit_code == 0, initialized.output

    if link_kind == 'leaf':
        (project / 'AGENTS.md').unlink()
        (project / 'AGENTS.md').symlink_to(external / 'AGENTS.md')
    else:
        external_agents = external / '.opencode' / 'agents'
        external_agents.mkdir(parents=True)
        (external_agents / 'reviewer.md').write_text(sentinel, encoding='utf-8')
        (project / '.opencode').rename(project / '.opencode.original')
        (project / '.opencode').symlink_to(
            external / '.opencode', target_is_directory=True
        )

    before_project = _snapshot_tree(project)
    before_external = _snapshot_tree(external)
    result = runner.invoke(app, ['update', str(project), '--force'])

    assert result.exit_code != 0, result.output
    assert 'Template path is a symlink' in (result.output + str(result.exception))
    assert sentinel not in result.output
    assert sentinel not in result.stderr
    assert _snapshot_tree(project) == before_project
    assert _snapshot_tree(external) == before_external


def test_force_update_refuses_answers_symlink_before_reading_it(tmp_path):
    project = tmp_path / 'project'
    external = tmp_path / 'private-external'
    external.mkdir()
    sentinel = '_commit: 1.7.0\nproject_name: UTF8_PRIVATE_ANSWERS_SENTINEL\n'
    answers_source = external / 'answers.yml'
    answers_source.write_text(sentinel, encoding='utf-8')
    initialized = runner.invoke(app, ['init', str(project), '--defaults'])
    assert initialized.exit_code == 0, initialized.output
    (project / '.copier-answers.yml').unlink()
    (project / '.copier-answers.yml').symlink_to(answers_source)

    before_project = _snapshot_tree(project)
    before_external = _snapshot_tree(external)

    original_read_bytes = Path.read_bytes
    original_read_text = Path.read_text

    def guard_answers_bytes(path, *args, **kwargs):
        if path.resolve() == answers_source.resolve():
            raise AssertionError('attempted to read external answers symlink target')
        return original_read_bytes(path, *args, **kwargs)

    def guard_answers_text(path, *args, **kwargs):
        if path.resolve() == answers_source.resolve():
            raise AssertionError('attempted to read external answers symlink target')
        return original_read_text(path, *args, **kwargs)

    with (
        patch.object(Path, 'read_bytes', guard_answers_bytes),
        patch.object(Path, 'read_text', guard_answers_text),
    ):
        result = runner.invoke(app, ['update', str(project), '--force'])

    assert result.exit_code != 0, result.output
    assert 'Template path is a symlink' in (result.output + str(result.exception))
    assert not isinstance(result.exception, AssertionError)
    marker = 'UTF8_PRIVATE_ANSWERS_SENTINEL'
    assert marker not in result.output
    assert marker not in result.stderr
    assert _snapshot_tree(project) == before_project
    assert _snapshot_tree(external) == before_external


def test_force_update_overwrites_managed_files_preserves_modes_and_unmanaged(
    tmp_path,
):
    project = tmp_path / 'project'
    initialized = runner.invoke(app, ['init', str(project), '--defaults'])
    assert initialized.exit_code == 0, initialized.output
    script = project / 'hooks' / 'pre-push'
    assert script.is_file()
    script.chmod(script.stat().st_mode | 0o111)
    unmanaged = project / 'my-private-note.txt'
    unmanaged.write_text('keep this user file\n', encoding='utf-8')
    (project / 'AGENTS.md').write_text('old local content\n', encoding='utf-8')

    result = runner.invoke(app, ['update', str(project), '--force'])

    assert result.exit_code == 0, result.output
    assert (project / 'AGENTS.md').read_text(encoding='utf-8') != 'old local content\n'
    assert script.stat().st_mode & 0o111
    assert unmanaged.read_text(encoding='utf-8') == 'keep this user file\n'


def test_rule_append_survives_replacement_of_final_template_section(tmp_path):
    target,base,new=[tmp_path/name for name in ('target','base','new')]
    for path in (target,base,new):path.mkdir()
    old='Project rules\n\nOld team roles\n'
    (base/'CLAUDE.md').write_text(old)
    (target/'CLAUDE.md').write_text(old+'\nCustom project invariant\n')
    (new/'AGENTS.md').write_text('Project rules\n\nNine native team roles\n')
    empty=tmp_path/'empty';empty.touch()
    writes,deletes,conflicts=_plan_merge(target,base,new,empty)
    assert conflicts==0
    assert writes[Path('AGENTS.md')]==b'Project rules\n\nNine native team roles\n\nCustom project invariant\n'
    assert (target/'CLAUDE.md').read_text()==old+'\nCustom project invariant\n'
