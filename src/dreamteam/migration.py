"""Conservative, read-only conversion of active project-local legacy artifacts."""

from __future__ import annotations

import difflib
import itertools
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

FRONTMATTER_PARTS = 3
AGENT_PATH_PARTS = 3
SKILL_PATH_PARTS = 4


class MigrationError(RuntimeError):
    """A migration cannot safely proceed (messages never contain source bytes)."""


class MigrationConflictError(MigrationError):
    """Two useful inputs cannot be merged without a human decision."""


@dataclass
class MigrationPlan:
    """Explicit writes, verified source removals and their read fingerprints."""

    writes: dict[Path, bytes] = field(default_factory=dict)
    deletes: set[Path] = field(default_factory=set)
    originals: dict[Path, bytes | None] = field(default_factory=dict)


def safe_path(root: Path, rel: Path) -> Path:
    """Reject links and excluded namespaces before reading or writing."""
    if rel.is_absolute() or '..' in rel.parts or '.git' in rel.parts:
        msg = 'Unsafe migration path.'
        raise MigrationError(msg)
    if rel.parts[:2] == ('.claude', 'worktrees'):
        msg = 'Excluded migration path.'
        raise MigrationError(msg)
    current = root
    for part in rel.parts:
        current /= part
        if current.is_symlink():
            msg = f'Symlink blocks migration: {rel}'
            raise MigrationError(msg)
    if current.exists() and not current.is_file():
        msg = f'Expected a regular migration file: {rel}'
        raise MigrationError(msg)
    return current


def legacy_present(root: Path) -> bool:
    """Detect active legacy without descending into worktrees or links."""
    return bool(_inventory(root))


def _inventory(root: Path) -> list[Path]:
    result = []
    rules = root / 'CLAUDE.md'
    if rules.exists() or rules.is_symlink():
        safe_path(root, Path('CLAUDE.md'))
        result.append(Path('CLAUDE.md'))
    legacy = root / '.claude'
    if legacy.is_symlink():
        msg = 'Symlink blocks migration: .claude'
        raise MigrationError(msg)
    if not legacy.exists():
        return result
    if not legacy.is_dir():
        msg = 'Expected directory: .claude'
        raise MigrationError(msg)
    pending = [legacy]
    while pending:
        directory = pending.pop()
        for item in sorted(directory.iterdir()):
            rel = item.relative_to(root)
            if rel == Path('.claude/worktrees'):
                continue
            if item.is_symlink():
                msg = f'Symlink blocks migration: {rel}'
                raise MigrationError(msg)
            if item.is_dir():
                pending.append(item)
            elif item.is_file():
                result.append(rel)
            else:
                msg = f'Unsupported filesystem entry: {rel}'
                raise MigrationError(msg)
    return result


def _text(content: bytes, rel: Path) -> str:
    try:
        return content.decode('utf-8')
    except UnicodeError as exc:
        msg = f'Invalid UTF-8: {rel}'
        raise MigrationError(msg) from exc


def _neutral(text: str, rel: Path) -> None:
    # Deliberately narrow detection: historical mentions of Claude/Anthropic
    # alone are not active configuration. Unknown active CLI instructions block.
    pattern = (
        r'(?im)(?:@\.?\.?/?[^\s]*\.claude/|'
        r'\bclaude\s+(?:mcp|-|auth|code|/)|/design-login|'
        r'^\s*(?:[$>]\s*)?claude\s*$|\bclaude-code\b|'
        r'\.claude/|\bCLAUDE\.md\b)'
    )
    if re.search(pattern, text):
        msg = f'Unsupported active legacy instructions: {rel}'
        raise MigrationError(msg)


def _merge(base: str, ours: str, theirs: str, rel: Path) -> str:
    if ours in (base, theirs):
        return theirs
    if theirs == base:
        return ours
    if base and ours.startswith(base):
        extension = ours[len(base) :]
        return theirs if theirs.endswith(extension) else theirs + extension
    lines = base.splitlines(keepends=True)
    edits: list[tuple[int, int, list[str]]] = []
    for changed in (ours, theirs):
        other = changed.splitlines(keepends=True)
        for tag, start, end, a, b in difflib.SequenceMatcher(
            a=lines, b=other, autojunk=False
        ).get_opcodes():
            if tag != 'equal':
                edit = (start, end, other[a:b])
                if edit not in edits:
                    edits.append(edit)
    ordered = sorted(edits, key=lambda item: (item[0], item[1]))
    for left, right in itertools.pairwise(ordered):
        if right[0] < left[1] or right[0] == left[0]:
            # Independent appends at EOF are losslessly combined in source order.
            if left[0] == left[1] == right[0] == right[1] == len(lines):
                continue
            msg = f'Content conflict: {rel}'
            raise MigrationConflictError(msg)
    for start, end, replacement in reversed(ordered):
        lines[start:end] = replacement
    return ''.join(lines)


def _markdown(text: str, rel: Path) -> tuple[dict[str, object], str]:
    if not text.startswith('---\n'):
        return {}, text
    chunks = text.split('---\n', 2)
    if len(chunks) != FRONTMATTER_PARTS:
        msg = f'Invalid frontmatter: {rel}'
        raise MigrationError(msg)
    try:
        metadata = yaml.safe_load(chunks[1])
    except yaml.YAMLError as exc:
        msg = f'Invalid frontmatter: {rel}'
        raise MigrationError(msg) from exc
    if not isinstance(metadata, dict) or any(not isinstance(k, str) for k in metadata):
        msg = f'Invalid frontmatter: {rel}'
        raise MigrationError(msg)
    return metadata, chunks[2]


def _custom_markdown(text: str, rel: Path) -> str:
    metadata, body = _markdown(text, rel)
    expected = rel.parent.name if rel.name == 'SKILL.md' else rel.stem
    if (
        set(metadata) - {'name', 'description'}
        or any(not isinstance(value, str) for value in metadata.values())
        or ('name' in metadata and metadata['name'] != expected)
    ):
        msg = f'Unsupported custom metadata: {rel}'
        raise MigrationError(msg)
    _neutral(body, rel)
    if 'agents' in rel.parts:
        metadata.pop('name', None)
        metadata['mode'] = 'subagent'
    if not metadata:
        return body
    return '---\n' + yaml.safe_dump(metadata, sort_keys=False) + '---\n' + body


def _combine_neutral(left: str, right: str, rel: Path) -> str:
    """Merge only demonstrably shared structure and disjoint neutral additions."""
    if left == right:
        return left
    left_meta, left_body = _markdown(left, rel)
    right_meta, right_body = _markdown(right, rel)
    if left_meta != right_meta:
        message = f'BOTH metadata conflict: {rel}'
        raise MigrationConflictError(message)
    a = left_body.splitlines(keepends=True)
    b = right_body.splitlines(keepends=True)
    common = ''.join(
        ''.join(a[block.a : block.a + block.size])
        for block in difflib.SequenceMatcher(
            a=a, b=b, autojunk=False
        ).get_matching_blocks()
    )
    if not common.strip():
        message = f'BOTH has no verifiable shared basis: {rel}'
        raise MigrationConflictError(message)
    # Equal setting-like labels with different values are not disjoint additions.
    labels: dict[str, str] = {}
    for line in a + b:
        match = re.match(r'^\s*([\w .-]+)\s*[:=]\s*(.+)$', line)
        if match:
            label = match[1].strip()
            if label in labels and labels[label] != match[2]:
                message = f'BOTH content conflict: {rel}'
                raise MigrationConflictError(message)
            labels[label] = match[2]
    body = _merge(common, left_body, right_body, rel)
    if not left_meta:
        return body
    return '---\n' + yaml.safe_dump(left_meta, sort_keys=False) + '---\n' + body


def _architect(old: str, baseline: str, fresh: str, rel: Path) -> str:
    actual, body = _markdown(old, rel)
    original, base_body = _markdown(baseline, rel)
    new, new_body = _markdown(fresh, rel)
    if (
        set(actual) != set(original)
        or any(
            actual.get(key) != original.get(key) for key in ('name', 'tools', 'model')
        )
        or original.get('name') != 'architect'
        or original.get('tools') != 'Read, Glob, Grep'
    ):
        msg = f'Unsupported baseline agent controls: {rel}'
        raise MigrationError(msg)
    if not isinstance(actual.get('description'), str):
        msg = f'Invalid agent description: {rel}'
        raise MigrationError(msg)
    # Only inspect user-added/replaced lines, not verified old plumbing.
    delta = ''.join(
        line[2:]
        for line in difflib.ndiff(
            base_body.splitlines(keepends=True), body.splitlines(keepends=True)
        )
        if line.startswith('+ ')
    )
    _neutral(delta, rel)
    new['description'] = _merge(
        str(original['description']),
        str(actual['description']),
        str(new['description']),
        rel,
    )
    result = _merge(base_body, body, new_body, rel)
    return '---\n' + yaml.safe_dump(new, sort_keys=False) + '---\n' + result


def plan_migration(
    target: Path, rendered: Path, *, base: Path | None = None
) -> MigrationPlan:
    """Build a complete read-only plan; unsupported inputs abort before staging."""
    plan = MigrationPlan()
    sources = _inventory(target)
    # Validate the full required path set before attempting any content merge.
    for rel in sources:
        safe_path(target, rel)
        destination = (
            Path('AGENTS.md')
            if rel == Path('CLAUDE.md')
            else Path('.opencode', *rel.parts[1:])
        )
        safe_path(target, destination)
    for item in rendered.rglob('*'):
        if item.is_file():
            safe_path(target, item.relative_to(rendered))
    for rel in sources:
        raw = safe_path(target, rel).read_bytes()
        text = _text(raw, rel)
        plan.originals[rel] = raw
        if rel.name in {'settings.json', 'settings.local.json'} and rel.parent == Path(
            '.claude'
        ):
            try:
                settings = json.loads(text)
            except ValueError as exc:
                msg = f'Invalid legacy settings: {rel}'
                raise MigrationError(msg) from exc
            if settings != {}:
                msg = f'Unsupported legacy settings: {rel}'
                raise MigrationError(msg)
            plan.deletes.add(rel)
            continue
        destination = (
            Path('AGENTS.md')
            if rel == Path('CLAUDE.md')
            else Path('.opencode', *rel.parts[1:])
        )
        old_base = base / rel if base is not None else None
        new_file = rendered / destination
        baseline = (
            _text(old_base.read_bytes(), rel)
            if old_base is not None and old_base.is_file()
            else None
        )
        fresh = _text(new_file.read_bytes(), destination) if new_file.is_file() else ''
        if rel in {Path('CLAUDE.md'), Path('.claude/team-roles.md')}:
            if baseline is not None:
                delta = ''.join(
                    line[2:]
                    for line in difflib.ndiff(
                        baseline.splitlines(keepends=True),
                        text.splitlines(keepends=True),
                    )
                    if line.startswith('+ ')
                )
                _neutral(delta, rel)
                shared = set(baseline.splitlines()) & set(text.splitlines())
                if text != baseline and not any(line.strip() for line in shared):
                    # A wholly rewritten neutral rule document is user-owned
                    # content, not a conflicting edit of known template plumbing.
                    _neutral(text, rel)
                    converted = fresh + '\n\n' + text
                else:
                    converted = _merge(baseline, text, fresh, rel)
            else:
                _neutral(text, rel)
                converted = fresh + ('\n\n' if fresh else '') + text
        elif rel == Path('.claude/agents/architect.md') and baseline is not None:
            converted = _architect(text, baseline, fresh, rel)
        elif (
            len(rel.parts) == AGENT_PATH_PARTS
            and rel.parts[1] in {'agents', 'commands'}
            and rel.suffix == '.md'
        ) or (
            len(rel.parts) == SKILL_PATH_PARTS
            and rel.parts[1] == 'skills'
            and rel.name == 'SKILL.md'
        ):
            converted = _custom_markdown(text, rel)
        else:
            msg = f'Unsupported legacy artifact: {rel}'
            raise MigrationError(msg)
        existing = safe_path(target, destination)
        previous = existing.read_bytes() if existing.exists() else None
        plan.originals[destination] = previous
        if previous is not None:
            current = _text(previous, destination)
            if baseline is None:
                if rel in {Path('CLAUDE.md'), Path('.claude/team-roles.md')}:
                    combined = _combine_neutral(text, current, destination)
                    converted = fresh + ('\n\n' if fresh else '') + combined
                else:
                    converted = _combine_neutral(converted, current, destination)
            else:
                converted = _merge(fresh, converted, current, destination)
        plan.writes[destination] = converted.encode()
        plan.deletes.add(rel)
    # New standard roles/config are delivered, but unrelated application files
    # retain their established update/apply policy and are not overwritten here.
    for item in rendered.rglob('*'):
        if not item.is_file():
            continue
        rel = item.relative_to(rendered)
        if rel in plan.writes:
            continue
        destination = safe_path(target, rel)
        previous = destination.read_bytes() if destination.exists() else None
        if previous is not None and rel == Path('opencode.json'):
            try:
                config = json.loads(previous)
            except ValueError as exc:
                message = 'Invalid OpenCode configuration.'
                raise MigrationError(message) from exc
            if not isinstance(config, dict):
                message = 'Invalid OpenCode configuration object.'
                raise MigrationError(message)
            standard = json.loads(item.read_bytes())
            for key in ('plugin', 'instructions'):
                old = config.get(key, [])
                if not isinstance(old, list) or any(
                    not isinstance(v, str) for v in old
                ):
                    message = 'Unsupported OpenCode instruction/plugin configuration.'
                    raise MigrationError(message)
                if key == 'instructions':
                    aliases = {
                        'CLAUDE.md': 'AGENTS.md',
                        '.claude/team-roles.md': '.opencode/team-roles.md',
                    }
                    old = [aliases.get(value, value) for value in old]
                    _neutral('\n'.join(old), rel)
                config[key] = list(dict.fromkeys(old + standard[key]))
            plan.writes[rel] = (json.dumps(config, indent=2) + '\n').encode()
        plan.originals[rel] = previous
        if previous is None:
            plan.writes[rel] = item.read_bytes()
        elif (
            base is not None and (base / rel).is_file() and rel != Path('opencode.json')
        ):
            old = (base / rel).read_bytes()
            new = item.read_bytes()
            if old != new:
                if previous == old:
                    plan.writes[rel] = new
                else:
                    plan.writes[rel] = _merge(
                        _text(old, rel), _text(previous, rel), _text(new, rel), rel
                    ).encode()
    return plan
