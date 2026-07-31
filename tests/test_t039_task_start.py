"""T039 — composite `dt task start`.

Two layers, mirroring T036: the pure, git-free helpers (`dreamteam.dt.slug`,
`dreamteam.dt.starts`, `dreamteam.dt.tmux`) tested in isolation, and the Typer
`dt task start` command driven against a *real* temporary git repository — that
end-to-end path exercises the git helpers added to `dreamteam.dt.paths`
(`local_branch_exists`, `add_worktree`).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dreamteam.cli import app
from dreamteam.dt.model import Task, save_task
from dreamteam.dt.paths import (
    DtHomeError,
    add_worktree,
    by_worktree_dir,
    ensure_store,
    local_branch_exists,
    store_dir,
    worktree_slug,
    worktrees_dir,
)
from dreamteam.dt.slug import branch_name, slugify, transliterate
from dreamteam.dt.starts import (
    context_line,
    extract_handover,
    plan_start,
    write_binding,
)
from dreamteam.dt.tmux import rename_window


# --------------------------------------------------------------------------- #
# slug — transliteration and branch naming (pure)                             #
# --------------------------------------------------------------------------- #


def test_transliterate_covers_tricky_letters() -> None:
    assert transliterate('Щёлочь жизнь') == 'shcheloch zhizn'


def test_slugify_cyrillic_title() -> None:
    assert slugify('Композитный старт задачи') == 'kompozitnyi-start-zadachi'


def test_slugify_mixed_and_punctuation_collapse() -> None:
    assert slugify('Fix: cursor (fullscreen) — v2!') == 'fix-cursor-fullscreen-v2'


def test_slugify_empty_when_no_transliterable_chars() -> None:
    assert slugify('!!! ??? 世界') == ''


def test_slugify_truncates_on_word_boundary() -> None:
    slug = slugify('one two three four five six seven eight nine ten eleven')
    assert len(slug) <= 40
    # whole-word cut: never ends mid-word / with a stray hyphen
    assert not slug.endswith('-')
    assert all(word in slug.split('-') for word in ('one', 'two'))


def test_slugify_hard_cut_single_long_word() -> None:
    slug = slugify('a' * 50)
    assert len(slug) == 40
    assert slug == 'a' * 40


def test_branch_name_with_and_without_slug() -> None:
    assert branch_name('T039', 'Композитный старт') == 'T039-kompozitnyi-start'
    assert branch_name('T039', '世界') == 'T039'


# --------------------------------------------------------------------------- #
# plan_start — decision table (pure)                                           #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ('worktree_exists', 'branch_exists', 'create_worktree', 'create_branch'),
    [
        (False, False, True, True),  # nothing there → create both
        (False, True, True, False),  # branch exists, no worktree → attach
        (True, False, False, False),  # worktree already there → reuse
        (True, True, False, False),  # both there → reuse
    ],
)
def test_plan_start_decision_table(
    *,
    worktree_exists: bool,
    branch_exists: bool,
    create_worktree: bool,
    create_branch: bool,
) -> None:
    plan = plan_start(
        'T039-x',
        Path('/wt/T039-x'),
        worktree_exists=worktree_exists,
        branch_exists=branch_exists,
    )
    assert plan.branch == 'T039-x'
    assert plan.path == Path('/wt/T039-x')
    assert plan.create_worktree is create_worktree
    assert plan.create_branch is create_branch


# --------------------------------------------------------------------------- #
# context_line and extract_handover (pure)                                     #
# --------------------------------------------------------------------------- #


def test_context_line_format() -> None:
    task = Task(id='T039', title='Старт задачи', status='doing')
    assert context_line(task) == 'T039 [doing] Старт задачи'


def test_extract_handover_stops_at_next_section() -> None:
    body = (
        'Контекст.\n\n'
        '## Handover\n'
        '- Сделано: каркас\n'
        '- Следующий шаг: тесты\n\n'
        '## Notes\n'
        'не попадать сюда\n'
    )
    assert extract_handover(body) == '- Сделано: каркас\n- Следующий шаг: тесты'


def test_extract_handover_stops_at_top_level_heading() -> None:
    body = '## Handover\nодна строка\n# Заголовок\nдальше\n'
    assert extract_handover(body) == 'одна строка'


def test_extract_handover_absent_is_empty() -> None:
    assert extract_handover('просто тело без секции\n') == ''


def test_extract_handover_keeps_indented_hash_lines() -> None:
    # An *indented* `#`-line is section content, not a real markdown heading,
    # so it must not terminate extraction (qodo #2).
    body = '## Handover\n- шаг\n    # это пример, не заголовок\n- ещё шаг\n'
    assert extract_handover(body) == '- шаг\n    # это пример, не заголовок\n- ещё шаг'


# --------------------------------------------------------------------------- #
# write_binding (fs)                                                           #
# --------------------------------------------------------------------------- #


def test_write_binding_creates_files(tmp_path: Path) -> None:
    write_binding(tmp_path, 'abc12345', 'T039', 'T039 [doing] X')
    d = tmp_path / 'abc12345'
    assert (d / 'current-task').read_text(encoding='utf-8') == 'T039\n'
    assert (d / 'context.line').read_text(encoding='utf-8') == 'T039 [doing] X\n'


# --------------------------------------------------------------------------- #
# tmux — best-effort, never raises                                            #
# --------------------------------------------------------------------------- #


def test_rename_window_noop_outside_tmux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('TMUX', raising=False)
    assert rename_window('T039') is False


def test_rename_window_noop_without_tmux_binary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('TMUX', '/tmp/tmux-1000/default,123,0')
    monkeypatch.setattr('dreamteam.dt.tmux.shutil.which', lambda _: None)
    assert rename_window('T039') is False


def test_rename_window_survives_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_timeout(cmd: list[str], **_kwargs: object) -> object:
        raise subprocess.TimeoutExpired(cmd, 3.0)

    monkeypatch.setenv('TMUX', '/tmp/tmux-1000/default,123,0')
    monkeypatch.setattr('dreamteam.dt.tmux.shutil.which', lambda _: '/usr/bin/tmux')
    monkeypatch.setattr('dreamteam.dt.tmux.subprocess.run', _raise_timeout)
    assert rename_window('T039') is False


def test_rename_window_runs_in_tmux(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    class _Result:
        returncode = 0

    def _fake_run(cmd: list[str], **_kwargs: object) -> _Result:
        calls.append(cmd)
        return _Result()

    monkeypatch.setenv('TMUX', '/tmp/tmux-1000/default,123,0')
    monkeypatch.setenv('TMUX_PANE', '%7')
    monkeypatch.setattr('dreamteam.dt.tmux.shutil.which', lambda _: '/usr/bin/tmux')
    monkeypatch.setattr('dreamteam.dt.tmux.subprocess.run', _fake_run)
    assert rename_window('T039') is True
    assert calls == [['/usr/bin/tmux', 'rename-window', '-t', '%7', 'T039']]


# --------------------------------------------------------------------------- #
# CLI layer — real temporary git repository                                    #
# --------------------------------------------------------------------------- #


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ['git', *args], cwd=repo, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A real git repo (one commit on `main`), made the process CWD."""
    root = tmp_path / 'proj'
    root.mkdir()
    _git(root, 'init', '-b', 'main')
    _git(root, 'config', 'user.email', 'test@example.com')
    _git(root, 'config', 'user.name', 'Test')
    (root / 'README.md').write_text('hello\n', encoding='utf-8')
    _git(root, 'add', '.')
    _git(root, 'commit', '-m', 'init')
    monkeypatch.delenv('DT_HOME', raising=False)
    # tmux rename must be a no-op in tests regardless of the host environment.
    monkeypatch.delenv('TMUX', raising=False)
    monkeypatch.chdir(root)
    # Pre-create the store so the one-shot "created …" stderr line does not land
    # in the CliRunner's merged output and trip assertions.
    ensure_store()
    return root


def _new_task(title: str = 'Композитный старт задачи') -> str:
    """Create a task via the CLI and return its ID."""
    result = CliRunner().invoke(app, ['task', 'new', title, '--json'])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)['id']


def test_start_creates_branch_and_worktree(repo: Path) -> None:
    task_id = _new_task()
    result = CliRunner().invoke(app, ['task', 'start', task_id, '--json'])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload['status'] == 'doing'
    assert payload['branch'] == f'{task_id}-kompozitnyi-start-zadachi'
    assert payload['worktree_created'] is True
    assert payload['branch_created'] is True
    assert payload['tmux_renamed'] is False
    # worktree really exists on that branch
    branches = _git(repo, 'worktree', 'list', '--porcelain')
    assert f'branch refs/heads/{payload["branch"]}' in branches
    # record updated on disk
    record = (store_dir() / 'tasks' / f'{task_id}.md').read_text(encoding='utf-8')
    assert 'status: doing' in record
    assert f'branch: {payload["branch"]}' in record


def test_start_binds_new_worktree_slug(repo: Path) -> None:
    task_id = _new_task()
    result = CliRunner().invoke(app, ['task', 'start', task_id, '--json'])
    worktree = Path(json.loads(result.output)['worktree'])
    slug = worktree_slug(worktree)
    binding = by_worktree_dir() / slug
    assert (binding / 'current-task').read_text(encoding='utf-8') == f'{task_id}\n'
    assert task_id in (binding / 'context.line').read_text(encoding='utf-8')


def test_start_is_idempotent(repo: Path) -> None:
    task_id = _new_task()
    first = CliRunner().invoke(app, ['task', 'start', task_id, '--json'])
    assert json.loads(first.output)['worktree_created'] is True
    second = CliRunner().invoke(app, ['task', 'start', task_id, '--json'])
    payload = json.loads(second.output)
    assert payload['worktree_created'] is False
    assert payload['branch_created'] is False
    # exactly one managed worktree, no duplicate
    managed = [
        line
        for line in _git(repo, 'worktree', 'list').splitlines()
        if '.dt/worktrees/' in line
    ]
    assert len(managed) == 1


def test_start_attaches_to_existing_branch(repo: Path) -> None:
    task_id = _new_task()
    branch = f'{task_id}-kompozitnyi-start-zadachi'
    # branch exists but has no worktree yet
    _git(repo, 'branch', branch)
    assert local_branch_exists(branch) is True
    result = CliRunner().invoke(app, ['task', 'start', task_id, '--json'])
    payload = json.loads(result.output)
    assert payload['worktree_created'] is True
    assert payload['branch_created'] is False


def test_start_reuses_recorded_branch(repo: Path) -> None:
    """A branch already in the record is reused, not regenerated from the title."""
    ensure_store()
    task_id = 'T099'
    save_task(
        store_dir() / 'tasks' / f'{task_id}.md',
        Task(id=task_id, title='другой заголовок', branch='T099-custom-branch'),
    )
    result = CliRunner().invoke(app, ['task', 'start', task_id, '--json'])
    assert json.loads(result.output)['branch'] == 'T099-custom-branch'


def test_start_json_includes_spec_and_handover(repo: Path) -> None:
    ensure_store()
    task_id = 'T050'
    task = Task(id=task_id, title='Задача', spec='specs/T050-x/spec.md')
    task.body = '## Handover\n- Сделано: старт\n'
    save_task(store_dir() / 'tasks' / f'{task_id}.md', task)
    result = CliRunner().invoke(app, ['task', 'start', task_id, '--json'])
    payload = json.loads(result.output)
    assert payload['spec'] == 'specs/T050-x/spec.md'
    assert payload['handover'] == '- Сделано: старт'


def test_add_worktree_surfaces_real_git_error(repo: Path) -> None:
    # A missing base ref must surface git's real cause, not a generic
    # "not inside a git repository" (qodo #1).
    with pytest.raises(DtHomeError) as exc:
        add_worktree(
            worktrees_dir() / 'T404-x',
            'T404-x',
            create_branch=True,
            base='no-such-base-ref',
        )
    message = str(exc.value)
    assert 'not inside a git repository' not in message
    assert 'no-such-base-ref' in message or 'invalid reference' in message


def test_start_unknown_task_errors(repo: Path) -> None:
    result = CliRunner().invoke(app, ['task', 'start', 'T404'])
    assert result.exit_code == 1
    assert 'not found' in result.output


def test_start_human_output(repo: Path) -> None:
    task_id = _new_task()
    result = CliRunner().invoke(app, ['task', 'start', task_id])
    assert result.exit_code == 0
    assert f'{task_id} → doing' in result.output
    assert 'worktree created' in result.output
