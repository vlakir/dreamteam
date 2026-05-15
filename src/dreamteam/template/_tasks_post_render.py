#!/usr/bin/env python3
"""Post-render task for dreamteam template (invoked via copier `_tasks`).

Moves narrative files from `i18n/<language>/` to the project root,
strips translation frontmatter (for non-ru languages), removes the
`i18n/` directory, and deletes itself. Runs in the rendered project's
working directory (set by copier).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

FRONTMATTER_DELIM = '---'


def _strip_frontmatter(text: str) -> str:
    """Drop a leading YAML frontmatter block (`---` … `---`) if present.

    Non-ru language files carry a frontmatter with `source_hash` for
    CI guard verification (`scripts/translate_check.py`). Derived
    users do not need that metadata — strip it on materialization.
    """
    if not text.startswith(FRONTMATTER_DELIM + '\n'):
        return text
    end_marker = '\n' + FRONTMATTER_DELIM + '\n'
    idx = text.find(end_marker, len(FRONTMATTER_DELIM) + 1)
    if idx == -1:
        return text
    rest = text[idx + len(end_marker):]
    return rest.lstrip('\n')


def _materialize(lang_dir: Path, project_root: Path) -> None:
    for src in lang_dir.rglob('*'):
        if not src.is_file():
            continue
        rel = src.relative_to(lang_dir)
        dst = project_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix == '.md':
            stripped = _strip_frontmatter(src.read_text(encoding='utf-8'))
            dst.write_text(stripped, encoding='utf-8')
        else:
            shutil.copy2(src, dst)


def main(language: str) -> int:
    project_root = Path.cwd()
    i18n_dir = project_root / 'i18n'
    if not i18n_dir.is_dir():
        return 0
    lang_dir = i18n_dir / language
    if not lang_dir.is_dir():
        sys.stderr.write(
            f'_tasks_post_render: i18n/{language}/ not found; '
            f'available: {sorted(p.name for p in i18n_dir.iterdir())}\n'
        )
        return 1
    _materialize(lang_dir, project_root)
    shutil.rmtree(i18n_dir)
    Path(__file__).unlink(missing_ok=True)
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.stderr.write('usage: _tasks_post_render.py <language>\n')
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
