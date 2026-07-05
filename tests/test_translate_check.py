"""Tests for scripts/translate_check.py (multilang source_hash CI guard)."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterable

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / 'scripts'
sys.path.insert(0, str(SCRIPTS_DIR))

import translate_check  # noqa: E402  (path injection above)

RU_BODY = '# Source\n\nHello.\n'
RU_HASH = hashlib.sha256(RU_BODY.encode('utf-8')).hexdigest()


def _make_template(tmp_path: Path, *, en_body: str | None = None) -> Path:
    """Build a minimal template tree with i18n/ru/<file> + optional i18n/en/<file>."""
    template_root = tmp_path / 'template'
    (template_root / 'i18n' / 'ru').mkdir(parents=True)
    (template_root / 'i18n' / 'ru' / 'CLAUDE.md').write_text(
        RU_BODY, encoding='utf-8',
    )
    if en_body is not None:
        (template_root / 'i18n' / 'en').mkdir(parents=True)
        (template_root / 'i18n' / 'en' / 'CLAUDE.md').write_text(
            en_body, encoding='utf-8',
        )
    return template_root


def _frontmatter(
    *,
    source_hash: str,
    translated_from: str = 'i18n/ru/CLAUDE.md',
) -> str:
    return (
        '---\n'
        f'translated_from: {translated_from}\n'
        f'source_hash: {source_hash}\n'
        'translation_engine: claude-opus-4-7\n'
        'translation_date: 2026-05-15\n'
        '---\n'
        '# Translated\n\nHello.\n'
    )


def _run(template_root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = translate_check.run(
        i18n_root=template_root / 'i18n',
        template_root=template_root,
    )
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_valid_frontmatter_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Matching source_hash → exit 0."""
    template_root = _make_template(
        tmp_path, en_body=_frontmatter(source_hash=RU_HASH),
    )
    code, out, err = _run(template_root, capsys)
    assert code == 0
    assert '1 ok' in out
    assert err == ''


def test_mismatched_hash_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Stale source_hash → exit 1 + FAIL line on stderr."""
    template_root = _make_template(
        tmp_path, en_body=_frontmatter(source_hash='deadbeef' * 8),
    )
    code, _out, err = _run(template_root, capsys)
    assert code == 1
    assert 'FAIL' in err
    assert 'i18n/en/CLAUDE.md' in err
    assert 'Hint:' in err


def test_missing_frontmatter_warns(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Translation file without frontmatter → warning + skip, exit 0."""
    template_root = _make_template(tmp_path, en_body='# Translated\n\nHi.\n')
    code, out, err = _run(template_root, capsys)
    assert code == 0
    assert 'WARN' in out
    assert '1 skipped' in out
    assert err == ''


def test_missing_source_file_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """`translated_from` pointing at a non-existent ru file → exit 1."""
    template_root = _make_template(
        tmp_path,
        en_body=_frontmatter(
            source_hash=RU_HASH,
            translated_from='i18n/ru/MISSING.md',
        ),
    )
    code, _out, err = _run(template_root, capsys)
    assert code == 1
    assert 'source not found' in err


def test_partial_frontmatter_warns(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Frontmatter present but lacks required keys → treated as no_frontmatter."""
    partial = (
        '---\n'
        'translation_engine: claude-opus-4-7\n'
        '---\n'
        '# Translated\n'
    )
    template_root = _make_template(tmp_path, en_body=partial)
    code, out, _err = _run(template_root, capsys)
    assert code == 0
    assert '1 skipped' in out


def test_parse_frontmatter_round_trip() -> None:
    """parse_frontmatter extracts the YAML block; absent → None."""
    fm = _frontmatter(source_hash=RU_HASH)
    parsed = translate_check.parse_frontmatter(fm)
    assert parsed is not None
    assert parsed['source_hash'] == RU_HASH
    assert parsed['translated_from'] == 'i18n/ru/CLAUDE.md'
    assert translate_check.parse_frontmatter('# no fm\n') is None


def test_iter_translation_files_skips_missing_dirs(tmp_path: Path) -> None:
    """If a language dir is missing it is silently skipped."""
    template_root = _make_template(
        tmp_path, en_body=_frontmatter(source_hash=RU_HASH),
    )
    files: Iterable[Path] = translate_check.iter_translation_files(
        template_root / 'i18n',
    )
    rels = [str(p.relative_to(template_root)) for p in files]
    assert rels == ['i18n/en/CLAUDE.md']


PARTIAL_RU_BODY = '<!-- description: X -->\nProse line.\n'
PARTIAL_RU_HASH = hashlib.sha256(PARTIAL_RU_BODY.encode('utf-8')).hexdigest()


def _make_partials(template_root: Path, *, en_hash: str) -> None:
    """Add partials/architect.body.{ru,en}.md under an existing template."""
    pdir = template_root / 'partials'
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / 'architect.body.ru.md').write_text(PARTIAL_RU_BODY, encoding='utf-8')
    (pdir / 'architect.body.en.md').write_text(
        '---\n'
        'translated_from: partials/architect.body.ru.md\n'
        f'source_hash: {en_hash}\n'
        '---\n'
        '<!-- description: X -->\nProse line.\n',
        encoding='utf-8',
    )


def test_partials_matching_hash_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """A partial translation with a matching source_hash is checked and ok."""
    template_root = _make_template(tmp_path)
    _make_partials(template_root, en_hash=PARTIAL_RU_HASH)
    code, out, err = _run(template_root, capsys)
    assert code == 0, out + err
    # 1 partial checked; the ru source is not flagged (no WARN).
    assert '1 ok' in out
    assert 'WARN' not in out
    assert err == ''


def test_partials_mismatch_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """A stale partial source_hash fails with the partials path on stderr."""
    template_root = _make_template(tmp_path)
    _make_partials(template_root, en_hash='deadbeef' * 8)
    code, _out, err = _run(template_root, capsys)
    assert code == 1
    assert 'partials/architect.body.en.md' in err


def test_iter_partial_files_excludes_ru(tmp_path: Path) -> None:
    """The ru source partial is never collected as a translation."""
    template_root = _make_template(tmp_path)
    _make_partials(template_root, en_hash=PARTIAL_RU_HASH)
    files = translate_check.iter_partial_files(template_root / 'partials')
    rels = [str(p.relative_to(template_root)) for p in files]
    assert rels == ['partials/architect.body.en.md']


def test_repo_state_passes(capsys: pytest.CaptureFixture[str]) -> None:
    """Live repo state must currently pass the guard (Phase 1 invariant)."""
    code = translate_check.run()
    captured = capsys.readouterr()
    assert code == 0, captured.out + captured.err
    assert '0 failed' in captured.out
