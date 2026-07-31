"""
Branch-slug generation from a (possibly Cyrillic) task title.

``dt task start`` derives a branch name ``T<NNN>-<slug>`` from the task title.
The slug is transliterated ru→lat and normalized to ASCII so the branch reads
cleanly everywhere git names surface (git refs, tmux window names, CI, URLs).
Pure and dependency-free — see ``specs/T039-task-start/spec.md`` §A4.

The transliteration is a pragmatic approximation, not a strict GOST/BGN
standard: it only needs to yield a human-readable name. Uniqueness is
guaranteed by the ``T<NNN>`` prefix, so slug collisions are harmless.
"""

from __future__ import annotations

import re

# ru→lat transliteration for lowercase Cyrillic. Applied after case-folding, so
# only lowercase keys are needed. Soft/hard signs map to empty; `ё`→`e`.
_TRANSLIT = {
    'а': 'a',
    'б': 'b',
    'в': 'v',
    'г': 'g',
    'д': 'd',
    'е': 'e',
    'ё': 'e',
    'ж': 'zh',
    'з': 'z',
    'и': 'i',
    'й': 'i',
    'к': 'k',
    'л': 'l',
    'м': 'm',
    'н': 'n',
    'о': 'o',
    'п': 'p',
    'р': 'r',
    'с': 's',
    'т': 't',
    'у': 'u',
    'ф': 'f',
    'х': 'h',
    'ц': 'c',
    'ч': 'ch',
    'ш': 'sh',
    'щ': 'shch',
    'ъ': '',
    'ы': 'y',
    'ь': '',
    'э': 'e',
    'ю': 'yu',
    'я': 'ya',
}

# Longest slug kept: enough words to stay readable without letting a branch name
# (and therefore a worktree directory) grow unbounded. Truncation is whole-word.
_MAX_SLUG_LEN = 40
_NON_SLUG_RE = re.compile(r'[^a-z0-9]+')


def transliterate(text: str) -> str:
    """Case-fold ``text`` and map Cyrillic letters to their latin equivalents."""
    return ''.join(_TRANSLIT.get(char, char) for char in text.casefold())


def slugify(title: str) -> str:
    """
    Build an ASCII branch slug from a task title.

    Transliterates ru→lat, lowercases, collapses every run of non-``[a-z0-9]``
    into a single ``-``, strips leading/trailing ``-`` and truncates to whole
    words within :data:`_MAX_SLUG_LEN`. Returns ``''`` when nothing survives
    (a title with no transliterable characters) — the caller drops the suffix.
    """
    ascii_text = _NON_SLUG_RE.sub('-', transliterate(title)).strip('-')
    if len(ascii_text) <= _MAX_SLUG_LEN:
        return ascii_text
    truncated = ascii_text[:_MAX_SLUG_LEN]
    # Prefer a whole-word cut; fall back to the hard cut if the first word alone
    # already exceeds the limit (no `-` before the boundary).
    if '-' in truncated:
        truncated = truncated.rsplit('-', 1)[0]
    return truncated.strip('-')


def branch_name(task_id: str, title: str) -> str:
    """
    Compose the task branch name ``T<NNN>-<slug>``.

    Falls back to the bare ``task_id`` when the title yields an empty slug, so
    the branch is always a valid, non-empty ref.
    """
    slug = slugify(title)
    return f'{task_id}-{slug}' if slug else task_id
