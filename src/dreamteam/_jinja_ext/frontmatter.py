"""
Jinja filters for assembling the Architect subagent file (T026).

The Architect subagent (`.claude/agents/architect.md`) needs a
*functional* YAML frontmatter (`name`/`description`/`tools`/`model`)
that must reach the derived project intact. Its prose body, however, is
translatable and lives in `partials/architect.body.<language>.md`.
Translation partials carry a `source_hash` frontmatter (CI guard); the
ru source carries none. These filters let the template's assembler
splice the two streams: strip the translation frontmatter off the
included body, lift the `description` out of its leading HTML comment,
and emit a single valid subagent header.

Filters registered on the environment:

- ``strip_frontmatter``     drop a leading ``---`` … ``---`` block
  (no-op when absent, e.g. the ru source).
- ``md_comment_value``      read ``value`` from a leading
  ``<!-- key: value -->`` comment — the methodology-language
  ``description``, guarded by the same ``source_hash`` as the body.
- ``strip_leading_comment`` drop that leading HTML comment line.
- ``yaml_str``              JSON-encode a string (``ensure_ascii=False``)
  into a valid, readable double-quoted YAML scalar — safe for colons
  and non-ASCII (Cyrillic / CJK) description text.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from jinja2.ext import Extension

if TYPE_CHECKING:
    from jinja2 import Environment

# Leading YAML frontmatter block. `\A` anchors to the string start (never
# a `---` inside the body); `count=1` limits the substitution to it.
_LEADING_FM = re.compile(r'\A---\r?\n.*?\r?\n---\r?\n', re.DOTALL)

# A leading `<!-- ... -->` HTML comment line, plus its trailing newline.
_LEADING_COMMENT = re.compile(r'\A[ \t]*<!--.*?-->[ \t]*\r?\n?', re.DOTALL)


def strip_frontmatter(text: str) -> str:
    """Drop a leading ``---`` … ``---`` frontmatter block, if present."""
    return _LEADING_FM.sub('', text, count=1)


def md_comment_value(text: str, key: str) -> str:
    """Return ``value`` from a leading ``<!-- key: value -->`` comment."""
    pattern = r'\A\s*<!--\s*' + re.escape(key) + r'\s*:\s*(.*?)\s*-->'
    match = re.match(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ''


def strip_leading_comment(text: str) -> str:
    """Drop a leading ``<!-- ... -->`` comment line and blank lines after."""
    return _LEADING_COMMENT.sub('', text, count=1).lstrip('\n')


def yaml_str(value: str) -> str:
    """Encode a string as a double-quoted YAML scalar (unicode preserved)."""
    return json.dumps(value, ensure_ascii=False)


class FrontmatterExtension(Extension):
    """Register the Architect-assembly filters on the Jinja environment."""

    def __init__(self, environment: Environment) -> None:
        super().__init__(environment)
        environment.filters['strip_frontmatter'] = strip_frontmatter
        environment.filters['md_comment_value'] = md_comment_value
        environment.filters['strip_leading_comment'] = strip_leading_comment
        environment.filters['yaml_str'] = yaml_str
