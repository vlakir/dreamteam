"""
CI guard: verify multilang translation `source_hash` against ru source.

For every `src/dreamteam/template/i18n/{en,fr,de,zh}/*.md` (recursive)
that carries a YAML frontmatter, recompute the SHA-256 of the
referenced ru source file (`translated_from`) and compare it to
`source_hash` in the frontmatter:

- match            → ok
- mismatch         → fail (exit 1)
- no frontmatter   → skip + warning (community manual edit / bootstrap)
- missing source   → fail (broken `translated_from` pointer)

Usage:
    uv run python scripts/translate_check.py

Exits 0 on success, 1 on any hard error.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import NamedTuple

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_ROOT = REPO_ROOT / 'src' / 'dreamteam' / 'template'
I18N_ROOT = TEMPLATE_ROOT / 'i18n'
NON_RU_LANGUAGES = ('en', 'fr', 'de', 'zh')
FRONTMATTER_DELIM = '---'


class CheckResult(NamedTuple):
    """One file's verification outcome."""

    path: Path
    status: str  # 'ok', 'mismatch', 'no_frontmatter', 'missing_source'
    detail: str


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """Return the leading YAML frontmatter as a dict, or None if absent."""
    if not text.startswith(FRONTMATTER_DELIM + '\n'):
        return None
    end_marker = '\n' + FRONTMATTER_DELIM + '\n'
    end_idx = text.find(end_marker, len(FRONTMATTER_DELIM) + 1)
    if end_idx == -1:
        return None
    block = text[len(FRONTMATTER_DELIM) + 1 : end_idx]
    parsed = yaml.safe_load(block)
    if not isinstance(parsed, dict):
        return None
    return {str(k): str(v) for k, v in parsed.items()}


def check_file(translation_path: Path, template_root: Path) -> CheckResult:
    """Verify one translated file against its ru source hash."""
    text = translation_path.read_text(encoding='utf-8')
    frontmatter = parse_frontmatter(text)
    if frontmatter is None:
        return CheckResult(translation_path, 'no_frontmatter', '')
    source_rel = frontmatter.get('translated_from', '')
    recorded_hash = frontmatter.get('source_hash', '')
    if not source_rel or not recorded_hash:
        return CheckResult(
            translation_path,
            'no_frontmatter',
            'frontmatter present but missing translated_from / source_hash',
        )
    source_path = template_root / source_rel
    if not source_path.is_file():
        return CheckResult(
            translation_path,
            'missing_source',
            f'source not found: {source_rel}',
        )
    actual_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if actual_hash != recorded_hash:
        return CheckResult(
            translation_path,
            'mismatch',
            (
                f'source {source_rel} changed; recorded={recorded_hash[:12]}…, '
                f'actual={actual_hash[:12]}…'
            ),
        )
    return CheckResult(translation_path, 'ok', '')


def iter_translation_files(i18n_root: Path) -> list[Path]:
    """Collect all .md files under i18n/{non-ru-languages}/ (sorted)."""
    files: list[Path] = []
    for lang in NON_RU_LANGUAGES:
        lang_dir = i18n_root / lang
        if not lang_dir.is_dir():
            continue
        files.extend(sorted(lang_dir.rglob('*.md')))
    return files


def run(
    i18n_root: Path = I18N_ROOT,
    template_root: Path = TEMPLATE_ROOT,
) -> int:
    """Run the check across all translation files. Returns exit code."""
    files = iter_translation_files(i18n_root)
    failures: list[CheckResult] = []
    warnings: list[CheckResult] = []
    ok_count = 0
    for path in files:
        result = check_file(path, template_root)
        rel = path.relative_to(template_root)
        if result.status == 'ok':
            ok_count += 1
        elif result.status == 'no_frontmatter':
            warnings.append(result)
            sys.stdout.write(f'WARN  {rel}: no translation frontmatter; skipping\n')
        else:
            failures.append(result)
            sys.stderr.write(f'FAIL  {rel}: {result.detail}\n')
    summary = (
        f'translate_check: {ok_count} ok, {len(warnings)} skipped, '
        f'{len(failures)} failed'
    )
    if failures:
        sys.stderr.write(f'{summary}\n')
        sys.stderr.write(
            'Hint: regenerate translations via a Claude Code session — ask Claude '
            'to re-translate i18n/ru/ into i18n/{en,fr,de,zh}/ and refresh '
            'source_hash in each frontmatter.\n'
        )
        return 1
    sys.stdout.write(f'{summary}\n')
    return 0


if __name__ == '__main__':
    sys.exit(run())
