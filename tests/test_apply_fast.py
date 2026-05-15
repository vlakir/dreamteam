"""
Fast unit tests for `dt apply` helpers and CLI validation.

These exercise the apply code without running copier:
- Pure helpers (`_files_equal`, `_classify_apply_files`,
  `_execute_apply_decisions`, `_print_apply_summary`,
  `_print_file_diff`, `_prompt_conflict_choice`,
  `_resolve_conflict`) operate on synthetic preview/target trees.
- CLI validation paths (`apply` command) fail before rendering,
  so they stay fast even though they use CliRunner.

Coverage target: every branch in lines 636-919 of `cli.py`.
The slow integration tests live in `tests/test_t018_phase2.py`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

from typer.testing import CliRunner

from dreamteam.cli import (
    CONFLICT_CHOICES,
    EXIT_ERROR,
    _classify_apply_files,
    _execute_apply_decisions,
    _files_equal,
    _print_apply_summary,
    _print_file_diff,
    _prompt_conflict_choice,
    _resolve_conflict,
    app,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

runner = CliRunner()


def _make_tree(root: Path, files: dict[str, str | bytes]) -> None:
    """Materialise a list of relative paths → contents under `root`."""
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding='utf-8')


def _rels(decisions: Iterable[tuple[Path, str]]) -> dict[str, str]:
    """Flatten (Path, action) tuples to a {rel-str: action} map."""
    return {str(rel): action for rel, action in decisions}


# ---------------- pure helpers ----------------


def test_files_equal_text_match(tmp_path: Path) -> None:
    a = tmp_path / 'a'
    b = tmp_path / 'b'
    a.write_text('hello\n', encoding='utf-8')
    b.write_text('hello\n', encoding='utf-8')
    assert _files_equal(a, b) is True


def test_files_equal_text_mismatch(tmp_path: Path) -> None:
    a = tmp_path / 'a'
    b = tmp_path / 'b'
    a.write_text('hello\n', encoding='utf-8')
    b.write_text('world\n', encoding='utf-8')
    assert _files_equal(a, b) is False


def test_files_equal_binary_match(tmp_path: Path) -> None:
    a = tmp_path / 'a.bin'
    b = tmp_path / 'b.bin'
    a.write_bytes(b'\xff\xfe\x00\x01')
    b.write_bytes(b'\xff\xfe\x00\x01')
    assert _files_equal(a, b) is True


def test_files_equal_binary_mismatch(tmp_path: Path) -> None:
    a = tmp_path / 'a.bin'
    b = tmp_path / 'b.bin'
    a.write_bytes(b'\xff\xfe\x00\x01')
    b.write_bytes(b'\xff\xfe\x00\x02')
    assert _files_equal(a, b) is False


def test_classify_create_unchanged_and_conflict_dry(tmp_path: Path) -> None:
    target = tmp_path / 'tgt'
    preview = tmp_path / 'prv'
    target.mkdir()
    preview.mkdir()
    _make_tree(
        preview,
        {
            'NEW.md': 'new content\n',
            'SAME.md': 'identical\n',
            'DIFF.md': 'template version\n',
        },
    )
    _make_tree(
        target,
        {
            'SAME.md': 'identical\n',
            'DIFF.md': 'user version\n',
        },
    )

    decisions = _classify_apply_files(target, preview, None, dry_run=True)
    assert _rels(decisions) == {
        'NEW.md': 'create',
        'SAME.md': 'unchanged',
        'DIFF.md': 'conflict-dry',
    }


def test_classify_with_on_conflict_flag(tmp_path: Path) -> None:
    target = tmp_path / 'tgt'
    preview = tmp_path / 'prv'
    target.mkdir()
    preview.mkdir()
    _make_tree(preview, {'a.txt': 'TEMPLATE\n'})
    _make_tree(target, {'a.txt': 'USER\n'})

    keep = _classify_apply_files(target, preview, 'keep', dry_run=False)
    assert _rels(keep) == {'a.txt': 'keep'}

    overwrite = _classify_apply_files(target, preview, 'overwrite', dry_run=False)
    assert _rels(overwrite) == {'a.txt': 'overwrite'}

    save_new = _classify_apply_files(target, preview, 'save-as-new', dry_run=False)
    assert _rels(save_new) == {'a.txt': 'save-as-new'}


def test_execute_create_overwrite_save_keep_unchanged(tmp_path: Path) -> None:
    target = tmp_path / 'tgt'
    preview = tmp_path / 'prv'
    target.mkdir()
    preview.mkdir()
    _make_tree(
        preview,
        {
            'NEW.md': 'fresh\n',
            'OW.md': 'template\n',
            'SAVE.md': 'template\n',
            'KEEP.md': 'template\n',
            'SAME.md': 'identical\n',
            'nested/deep.md': 'deep\n',
        },
    )
    _make_tree(
        target,
        {
            'OW.md': 'user\n',
            'SAVE.md': 'user\n',
            'KEEP.md': 'user\n',
            'SAME.md': 'identical\n',
        },
    )

    decisions = [
        (Path('NEW.md'), 'create'),
        (Path('OW.md'), 'overwrite'),
        (Path('SAVE.md'), 'save-as-new'),
        (Path('KEEP.md'), 'keep'),
        (Path('SAME.md'), 'unchanged'),
        (Path('nested/deep.md'), 'create'),
    ]
    summary = _execute_apply_decisions(target, preview, decisions, dry_run=False)
    assert summary['create'] == 2
    assert summary['overwrite'] == 1
    assert summary['save-as-new'] == 1
    assert summary['keep'] == 1
    assert summary['unchanged'] == 1

    assert (target / 'NEW.md').read_text(encoding='utf-8') == 'fresh\n'
    assert (target / 'OW.md').read_text(encoding='utf-8') == 'template\n'
    assert (target / 'KEEP.md').read_text(encoding='utf-8') == 'user\n'
    assert (target / 'SAVE.md').read_text(encoding='utf-8') == 'user\n'
    assert (target / 'SAVE.md.dt-new').read_text(encoding='utf-8') == 'template\n'
    assert (target / 'nested' / 'deep.md').read_text(encoding='utf-8') == 'deep\n'


def test_execute_dry_run_skips_writes(tmp_path: Path) -> None:
    target = tmp_path / 'tgt'
    preview = tmp_path / 'prv'
    target.mkdir()
    preview.mkdir()
    _make_tree(preview, {'NEW.md': 'fresh\n', 'OW.md': 'template\n'})
    _make_tree(target, {'OW.md': 'user\n'})

    decisions = [
        (Path('NEW.md'), 'create'),
        (Path('OW.md'), 'conflict-dry'),
    ]
    summary = _execute_apply_decisions(target, preview, decisions, dry_run=True)
    assert summary['create'] == 1
    assert summary['conflict-dry'] == 1
    assert not (target / 'NEW.md').exists()
    assert (target / 'OW.md').read_text(encoding='utf-8') == 'user\n'


def test_print_apply_summary_dry_run_format(capsys: object) -> None:
    summary = {
        'create': 3,
        'unchanged': 1,
        'keep': 0,
        'overwrite': 0,
        'save-as-new': 0,
        'conflict-dry': 2,
    }
    _print_apply_summary(summary, dry_run=True)
    captured = capsys.readouterr().out  # type: ignore[attr-defined]
    assert 'dreamteam apply --dry-run' in captured
    assert '3 created' in captured
    assert '2 would conflict' in captured


def test_print_apply_summary_live_format(capsys: object) -> None:
    summary = {
        'create': 5,
        'unchanged': 2,
        'keep': 1,
        'overwrite': 1,
        'save-as-new': 1,
        'conflict-dry': 0,
    }
    _print_apply_summary(summary, dry_run=False)
    captured = capsys.readouterr().out  # type: ignore[attr-defined]
    assert 'dreamteam apply:' in captured
    assert 'would conflict' not in captured
    assert '1 kept' in captured
    assert '1 overwritten' in captured
    assert '1 saved as .dt-new' in captured


def test_print_file_diff_text(tmp_path: Path, capsys: object) -> None:
    a = tmp_path / 'a.txt'
    b = tmp_path / 'b.txt'
    a.write_text('line1\nline2\n', encoding='utf-8')
    b.write_text('line1\nLINE2\n', encoding='utf-8')
    _print_file_diff(a, b, Path('a.txt'))
    captured = capsys.readouterr().out  # type: ignore[attr-defined]
    assert '-line2' in captured
    assert '+LINE2' in captured


def test_print_file_diff_binary(tmp_path: Path, capsys: object) -> None:
    a = tmp_path / 'a.bin'
    b = tmp_path / 'b.bin'
    a.write_bytes(b'\xff\xfe\x00\x01')
    b.write_bytes(b'\xff\xfe\x00\x02')
    _print_file_diff(a, b, Path('a.bin'))
    captured = capsys.readouterr().out  # type: ignore[attr-defined]
    assert 'Binary files' in captured


def test_prompt_conflict_choice_keep(tmp_path: Path) -> None:
    a = tmp_path / 'a.txt'
    b = tmp_path / 'b.txt'
    a.write_text('user\n', encoding='utf-8')
    b.write_text('template\n', encoding='utf-8')
    with patch('typer.prompt', return_value='k'):
        assert _prompt_conflict_choice(Path('a.txt'), a, b) == 'keep'


def test_prompt_conflict_choice_default_enter(tmp_path: Path) -> None:
    a = tmp_path / 'a.txt'
    b = tmp_path / 'b.txt'
    a.write_text('user\n', encoding='utf-8')
    b.write_text('template\n', encoding='utf-8')
    with patch('typer.prompt', return_value=''):
        assert _prompt_conflict_choice(Path('a.txt'), a, b) == 'keep'


def test_prompt_conflict_choice_overwrite(tmp_path: Path) -> None:
    a = tmp_path / 'a.txt'
    b = tmp_path / 'b.txt'
    a.write_text('user\n', encoding='utf-8')
    b.write_text('template\n', encoding='utf-8')
    with patch('typer.prompt', return_value='o'):
        assert _prompt_conflict_choice(Path('a.txt'), a, b) == 'overwrite'


def test_prompt_conflict_choice_save_as_new(tmp_path: Path) -> None:
    a = tmp_path / 'a.txt'
    b = tmp_path / 'b.txt'
    a.write_text('user\n', encoding='utf-8')
    b.write_text('template\n', encoding='utf-8')
    with patch('typer.prompt', return_value='s'):
        assert _prompt_conflict_choice(Path('a.txt'), a, b) == 'save-as-new'


def test_prompt_conflict_choice_diff_then_keep(
    tmp_path: Path, capsys: object,
) -> None:
    a = tmp_path / 'a.txt'
    b = tmp_path / 'b.txt'
    a.write_text('one\n', encoding='utf-8')
    b.write_text('two\n', encoding='utf-8')
    # First answer 'd' triggers diff + loop; second answer 'keep' terminates.
    with patch('typer.prompt', side_effect=['d', 'keep']):
        assert _prompt_conflict_choice(Path('a.txt'), a, b) == 'keep'
    captured = capsys.readouterr().out  # type: ignore[attr-defined]
    assert '-one' in captured
    assert '+two' in captured


def test_prompt_conflict_choice_unknown_then_overwrite(
    tmp_path: Path, capsys: object,
) -> None:
    a = tmp_path / 'a.txt'
    b = tmp_path / 'b.txt'
    a.write_text('user\n', encoding='utf-8')
    b.write_text('template\n', encoding='utf-8')
    with patch('typer.prompt', side_effect=['x', 'overwrite']):
        assert _prompt_conflict_choice(Path('a.txt'), a, b) == 'overwrite'
    captured = capsys.readouterr().out  # type: ignore[attr-defined]
    assert 'unknown choice' in captured


def test_resolve_conflict_flag_short_circuits(tmp_path: Path) -> None:
    a = tmp_path / 'a.txt'
    b = tmp_path / 'b.txt'
    a.write_text('user\n', encoding='utf-8')
    b.write_text('template\n', encoding='utf-8')
    # Flag wins over prompt; prompt must not even be called.
    with patch('typer.prompt') as mocked:
        assert _resolve_conflict(Path('a.txt'), a, b, 'overwrite') == 'overwrite'
        assert mocked.call_count == 0


def test_resolve_conflict_no_flag_delegates_to_prompt(tmp_path: Path) -> None:
    a = tmp_path / 'a.txt'
    b = tmp_path / 'b.txt'
    a.write_text('user\n', encoding='utf-8')
    b.write_text('template\n', encoding='utf-8')
    with patch('typer.prompt', return_value='s'):
        assert _resolve_conflict(Path('a.txt'), a, b, None) == 'save-as-new'


def test_conflict_choices_constant() -> None:
    assert CONFLICT_CHOICES == ('keep', 'overwrite', 'save-as-new')


# ---------------- CLI validation paths (no rendering) ----------------


def test_apply_target_is_file_errors(tmp_path: Path) -> None:
    target = tmp_path / 'a-file'
    target.write_text('not a dir', encoding='utf-8')
    result = runner.invoke(
        app,
        ['apply', str(target), '--defaults', '--on-conflict', 'keep'],
    )
    assert result.exit_code == EXIT_ERROR
    combined = result.output + (result.stderr or '')
    assert 'not a directory' in combined


def test_apply_invalid_on_conflict_value(tmp_path: Path) -> None:
    target = tmp_path / 'bad'
    result = runner.invoke(
        app,
        ['apply', str(target), '--defaults', '--on-conflict', 'nuke'],
    )
    assert result.exit_code == EXIT_ERROR
    combined = result.output + (result.stderr or '')
    assert '--on-conflict must be one of' in combined


def test_apply_already_dreamteam_errors_before_render(tmp_path: Path) -> None:
    target = tmp_path / 'existing'
    target.mkdir()
    (target / '.copier-answers.yml').write_text(
        '_commit: 1.5.0\nlanguage: en\npackage_manager: uv\n',
        encoding='utf-8',
    )
    result = runner.invoke(
        app,
        ['apply', str(target), '--defaults', '--on-conflict', 'keep'],
    )
    assert result.exit_code == EXIT_ERROR
    combined = result.output + (result.stderr or '')
    assert 'dt update' in combined


def test_apply_non_tty_without_on_conflict_errors(tmp_path: Path) -> None:
    target = tmp_path / 'tty-less'
    # CliRunner.invoke() emulates non-TTY stdin by default — exactly the
    # path we want to assert on.
    with patch('sys.stdin.isatty', return_value=False):
        result = runner.invoke(app, ['apply', str(target), '--defaults'])
    assert result.exit_code == EXIT_ERROR
    combined = result.output + (result.stderr or '')
    assert 'stdin is not a TTY' in combined
