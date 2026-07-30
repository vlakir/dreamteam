"""
Task record model and unknown-field-preserving (de)serialization.

A task record is a file ``$DT_STORE/tasks/T<NNN>.md`` of the form::

    ---
    <yaml frontmatter>
    ---
    <markdown body>

The frontmatter is modelled with pydantic (typed known fields + ``extra`` for
forward-compatible unknown fields); the body is free markdown (context,
acceptance criteria, ``## Handover``). ``parse_task``/``dump_task`` round-trip
without losing unknown fields — see ``specs/T033-store-core/spec.md`` §3.
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from pathlib import Path

TaskStatus = Literal['todo', 'doing', 'review', 'done', 'dropped']

_FRONTMATTER_FENCE = '---'
_BOM = '﻿'
# Canonical frontmatter key order (known fields), followed by any extra keys
# in their original relative order — keeps serialized records deterministic.
_KNOWN_ORDER = (
    'id',
    'title',
    'status',
    'deps',
    'parent',
    'spec',
    'branch',
    'pr',
    'tags',
    'created',
    'updated',
)
# List fields are always written, even when empty; other None scalars are dropped.
_ALWAYS_WRITTEN = ('deps', 'tags')


class Task(BaseModel):
    """
    A task record's frontmatter plus its markdown body.

    Unknown frontmatter keys are retained (``extra='allow'``) and written back
    on serialization, so records authored by a newer format version survive a
    read/modify/write cycle by older code intact.
    """

    model_config = ConfigDict(extra='allow')

    id: str
    title: str
    status: TaskStatus = 'todo'
    deps: list[str] = Field(default_factory=list)
    parent: str | None = None
    spec: str | None = None
    branch: str | None = None
    pr: int | None = None
    tags: list[str] = Field(default_factory=list)
    created: datetime.date | None = None
    updated: datetime.date | None = None
    # The markdown body is not part of the frontmatter; excluded from dumps and
    # re-attached after the closing fence by `dump_task`.
    body: str = Field(default='', exclude=True)


def _frontmatter(task: Task) -> dict[str, Any]:
    """
    Ordered frontmatter dict: known fields (canonical order) then extra.

    ``None`` optional scalars are dropped (minimal frontmatter); list fields
    (``deps``/``tags``) are always written, empty or not.
    """
    dumped = task.model_dump(exclude={'body'}, mode='python')
    # `dumped` always contains every known field plus any extras, so every key
    # below is present by construction.
    extra_keys = [k for k in dumped if k not in _KNOWN_ORDER]
    ordered: dict[str, Any] = {}
    for key in (*_KNOWN_ORDER, *extra_keys):
        value = dumped[key]
        if value is None and key not in _ALWAYS_WRITTEN:
            continue
        ordered[key] = value
    return ordered


def _split_frontmatter(text: str) -> tuple[str, str]:
    r"""
    Split ``---\\nYAML\\n---\\nbody`` into ``(frontmatter, body)``.

    A record without a leading fence has empty frontmatter and is treated as
    all-body; a missing closing fence is a malformed record.
    """
    normalized = text.lstrip(_BOM)
    lines = normalized.split('\n')
    if lines[0].strip() != _FRONTMATTER_FENCE:
        return '', normalized
    for index in range(1, len(lines)):
        if lines[index].strip() == _FRONTMATTER_FENCE:
            return '\n'.join(lines[1:index]), '\n'.join(lines[index + 1 :])
    message = 'task record frontmatter is missing its closing `---` fence'
    raise ValueError(message)


def parse_task(text: str) -> Task:
    """Parse a task record (frontmatter + body) into a :class:`Task`."""
    frontmatter, body = _split_frontmatter(text)
    data = yaml.safe_load(frontmatter) or {}
    if not isinstance(data, dict):
        message = 'task record frontmatter must be a YAML mapping'
        raise TypeError(message)
    # `body` is reserved for the markdown after the fence; drop any frontmatter
    # key of the same name so it never collides with the constructor kwarg.
    data.pop('body', None)
    return Task(**data, body=body)


def dump_task(task: Task) -> str:
    r"""Serialize a :class:`Task` back to ``---\\nfrontmatter\\n---\\nbody``."""
    frontmatter = yaml.safe_dump(
        _frontmatter(task),
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
    )
    document = f'{_FRONTMATTER_FENCE}\n{frontmatter}{_FRONTMATTER_FENCE}\n'
    body = task.body
    if body:
        document += body if body.endswith('\n') else f'{body}\n'
    return document


def load_task(path: Path) -> Task:
    """Read and parse a task record from ``path``."""
    return parse_task(path.read_text(encoding='utf-8'))


def save_task(path: Path, task: Task) -> None:
    """Serialize ``task`` and write it to ``path`` (UTF-8)."""
    path.write_text(dump_task(task), encoding='utf-8')
