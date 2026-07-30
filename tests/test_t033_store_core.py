"""T033 — storage skeleton and task model.

Covers `dreamteam.dt.paths` (`$DT_HOME` resolution, worktree `<slug>`, lazy
store creation, `DtHomeError`) and `dreamteam.dt.model` (task record parse /
serialize with unknown-field preservation). Path-resolution tests build real
git repositories (and a linked worktree) in `tmp_path`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from dreamteam.dt import (
    DtHomeError,
    Task,
    by_worktree_dir,
    dt_home,
    dump_task,
    ensure_store,
    load_task,
    parse_task,
    save_task,
    sessions_dir,
    store_dir,
    tasks_dir,
    worktree_slug,
    worktrees_dir,
)
from dreamteam.dt.model import _frontmatter, _split_frontmatter

if TYPE_CHECKING:
    from collections.abc import Iterator


def _git(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        ['git', *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _init_repo(path: Path) -> Path:
    """Init a git repo with one commit and return its resolved toplevel."""
    path.mkdir(parents=True, exist_ok=True)
    _git('init', '-q', cwd=path)
    _git('config', 'user.email', 'test@example.com', cwd=path)
    _git('config', 'user.name', 'Test', cwd=path)
    (path / 'README.md').write_text('x\n', encoding='utf-8')
    _git('add', '-A', cwd=path)
    _git('commit', '-q', '-m', 'init', cwd=path)
    return path


@pytest.fixture
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv('DT_HOME', raising=False)
    yield


# --------------------------------------------------------------------------- #
# paths: $DT_HOME resolution                                                   #
# --------------------------------------------------------------------------- #


@pytest.mark.usefixtures('_clean_env')
def test_dt_home_is_sibling_dot_dt(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / 'myproject')
    assert dt_home(cwd=repo) == repo.parent / 'myproject.dt'


def test_dt_home_env_override_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init_repo(tmp_path / 'myproject')
    custom = tmp_path / 'elsewhere' / 'state'
    monkeypatch.setenv('DT_HOME', str(custom))
    assert dt_home(cwd=repo) == custom


@pytest.mark.usefixtures('_clean_env')
def test_dt_home_identical_from_linked_worktree(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / 'myproject')
    linked = tmp_path / 'myproject-T034'
    _git('worktree', 'add', '-q', '-b', 'T034-x', str(linked), cwd=repo)
    assert dt_home(cwd=linked) == dt_home(cwd=repo) == repo.parent / 'myproject.dt'


@pytest.mark.usefixtures('_clean_env')
def test_dt_home_bare_repo_uses_common_dir(tmp_path: Path) -> None:
    bare = tmp_path / 'myproject.git'
    bare.mkdir()
    _git('init', '-q', '--bare', cwd=bare)
    assert dt_home(cwd=bare) == tmp_path / 'myproject.git.dt'


@pytest.mark.usefixtures('_clean_env')
def test_dt_home_outside_git_raises(tmp_path: Path) -> None:
    with pytest.raises(DtHomeError, match='DT_HOME'):
        dt_home(cwd=tmp_path)


@pytest.mark.usefixtures('_clean_env')
def test_dt_home_no_git_binary_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init_repo(tmp_path / 'myproject')
    monkeypatch.setattr('dreamteam.dt.paths.shutil.which', lambda _name: None)
    with pytest.raises(DtHomeError, match='git binary not found'):
        dt_home(cwd=repo)


@pytest.mark.usefixtures('_clean_env')
def test_dt_home_missing_cwd_raises_dthomeerror(tmp_path: Path) -> None:
    # subprocess.run on a non-existent cwd raises OSError before return-code
    # handling; it must surface as DtHomeError, not a raw traceback.
    with pytest.raises(DtHomeError, match='DT_HOME'):
        dt_home(cwd=tmp_path / 'does-not-exist')


# --------------------------------------------------------------------------- #
# paths: worktree slug                                                         #
# --------------------------------------------------------------------------- #


def test_worktree_slug_deterministic_and_8_hex(tmp_path: Path) -> None:
    slug = worktree_slug(tmp_path)
    assert slug == worktree_slug(tmp_path)
    assert len(slug) == 8
    assert all(c in '0123456789abcdef' for c in slug)


def test_worktree_slug_distinct_for_distinct_paths(tmp_path: Path) -> None:
    assert worktree_slug(tmp_path / 'a') != worktree_slug(tmp_path / 'b')


@pytest.mark.usefixtures('_clean_env')
def test_worktree_slug_defaults_to_current_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init_repo(tmp_path / 'myproject')
    monkeypatch.chdir(repo)
    assert worktree_slug() == worktree_slug(repo)


# --------------------------------------------------------------------------- #
# paths: store creation                                                        #
# --------------------------------------------------------------------------- #


@pytest.mark.usefixtures('_clean_env')
def test_ensure_store_creates_tree_and_prints_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _init_repo(tmp_path / 'myproject')
    home = ensure_store(cwd=repo)
    first = capsys.readouterr()
    assert home == dt_home(cwd=repo)
    for directory in (
        store_dir(cwd=repo),
        tasks_dir(cwd=repo),
        sessions_dir(cwd=repo),
        by_worktree_dir(cwd=repo),
        worktrees_dir(cwd=repo),
    ):
        assert directory.is_dir()
    assert str(home) in first.err
    assert first.err.count('created operational state directory') == 1

    ensure_store(cwd=repo)  # idempotent, silent
    second = capsys.readouterr()
    assert second.err == ''


@pytest.mark.usefixtures('_clean_env')
def test_ensure_store_recreates_missing_subdir_silently(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _init_repo(tmp_path / 'myproject')
    ensure_store(cwd=repo)
    capsys.readouterr()  # drop first-creation line
    tasks_dir(cwd=repo).rmdir()
    ensure_store(cwd=repo)
    out = capsys.readouterr()
    assert tasks_dir(cwd=repo).is_dir()
    assert out.err == ''  # root already existed → no second announcement


@pytest.mark.usefixtures('_clean_env')
def test_ensure_store_unwritable_parent_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init_repo(tmp_path / 'myproject')

    def _boom(*_args: object, **_kwargs: object) -> None:
        message = 'permission denied'
        raise OSError(message)

    monkeypatch.setattr(Path, 'mkdir', _boom)
    with pytest.raises(DtHomeError, match='DT_HOME'):
        ensure_store(cwd=repo)


# --------------------------------------------------------------------------- #
# model: parse / dump                                                          #
# --------------------------------------------------------------------------- #

_RECORD = """---
id: T001
title: Каркас хранилища
status: doing
deps: [T003, T005]
tags: [core, storage]
created: 2026-07-29
custom_field: 42
---
Body line one.

## Handover
- Сделано: X
"""


def test_parse_typed_fields() -> None:
    task = parse_task(_RECORD)
    assert task.id == 'T001'
    assert task.status == 'doing'
    assert task.deps == ['T003', 'T005']
    assert task.created is not None
    assert task.created.isoformat() == '2026-07-29'
    assert '## Handover' in task.body


def test_parse_preserves_unknown_fields() -> None:
    task = parse_task(_RECORD)
    assert task.model_extra == {'custom_field': 42}
    assert parse_task(dump_task(task)).model_extra == {'custom_field': 42}


def test_dump_is_idempotent() -> None:
    once = dump_task(parse_task(_RECORD))
    twice = dump_task(parse_task(once))
    assert once == twice


def test_dump_canonical_order_known_before_extra() -> None:
    text = dump_task(parse_task(_RECORD))
    assert text.index('\nid:') < text.index('\nstatus:') < text.index('\ncustom_field:')


def test_dump_omits_none_scalars_keeps_empty_lists() -> None:
    text = dump_task(Task(id='T009', title='x', created=None))
    assert 'parent:' not in text
    assert 'updated:' not in text
    assert 'deps: []' in text
    assert 'tags: []' in text


def test_invalid_status_rejected() -> None:
    with pytest.raises(ValidationError):
        parse_task('---\nid: T1\ntitle: x\nstatus: bogus\n---\n')


def test_missing_required_field_rejected() -> None:
    with pytest.raises(ValidationError):
        parse_task('---\ntitle: no id\n---\n')


def test_split_frontmatter_empty_body() -> None:
    fm, body = _split_frontmatter('---\nid: T1\ntitle: x\n---\n')
    assert 'id: T1' in fm
    assert body == ''


def test_split_frontmatter_no_leading_fence_is_all_body() -> None:
    fm, body = _split_frontmatter('no frontmatter here\n')
    assert fm == ''
    assert body == 'no frontmatter here\n'


def test_missing_closing_fence_raises() -> None:
    with pytest.raises(ValueError, match='closing'):
        parse_task('---\nid: T1\ntitle: x\n')


def test_non_mapping_frontmatter_raises() -> None:
    with pytest.raises(TypeError, match='mapping'):
        parse_task('---\n- a\n- b\n---\nbody\n')


def test_frontmatter_helper_drops_body_key() -> None:
    assert 'body' not in _frontmatter(parse_task(_RECORD))


def test_frontmatter_body_key_does_not_collide() -> None:
    task = parse_task('---\nid: T1\ntitle: x\nbody: reserved\n---\nreal body\n')
    assert task.body == 'real body\n'
    assert task.model_extra == {}  # frontmatter `body` dropped, not kept as extra


def test_body_without_trailing_newline_normalized() -> None:
    text = dump_task(Task(id='T1', title='x', body='no newline'))
    assert text.endswith('no newline\n')


def test_load_and_save_round_trip(tmp_path: Path) -> None:
    path = tmp_path / 'T001.md'
    save_task(path, parse_task(_RECORD))
    reloaded = load_task(path)
    assert reloaded.id == 'T001'
    assert reloaded.model_extra == {'custom_field': 42}
    assert path.read_text(encoding='utf-8') == dump_task(reloaded)
