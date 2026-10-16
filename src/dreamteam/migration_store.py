"""Private, file-scoped migration recovery with filesystem reconciliation."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import stat
import uuid
from pathlib import Path
from typing import Any

from dreamteam.migration import MigrationError, MigrationPlan, safe_path

PRIVATE_DIRECTORY_MODE = 0o700
PRIVATE_FILE_MODE = 0o600


def checkpoint(event: str, operation_id: str) -> None:
    """Observe durable boundaries; production is a no-op (fault-injection seam)."""


def _private(directory: Path) -> None:
    current = Path(directory.anchor)
    for component in directory.parts[1:]:
        current /= component
        if current.is_symlink():
            msg = 'Unsafe recovery directory: symlink.'
            raise MigrationError(msg)
        if not current.exists():
            current.mkdir(mode=PRIVATE_DIRECTORY_MODE)
        _safe_ancestor(current)
    info = directory.stat()
    if (
        not directory.is_dir()
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != PRIVATE_DIRECTORY_MODE
    ):
        msg = 'Recovery directory must be owner-only (0700).'
        raise MigrationError(msg)


def require_supported_platform() -> None:
    """Refuse recovery where its owner/mode and directory-fsync safety is absent."""
    if (
        os.name != 'posix'
        or not callable(getattr(os, 'getuid', None))
        or not hasattr(os, 'O_DIRECTORY')
    ):
        msg = (
            'Legacy migration and recovery require POSIX ownership, permissions '
            'and directory fsync; unsupported platform.'
        )
        raise MigrationError(msg)


def _recovery_location(root: Path) -> tuple[Path, Path]:
    """Calculate the configured location without reading or validating storage."""
    state = Path(
        os.environ.get('XDG_STATE_HOME') or str(Path.home() / '.local/state')
    ).expanduser()
    directory = (
        state / 'dreamteam/migrations' / hashlib.sha256(os.fsencode(root)).hexdigest()
    )
    return state, directory


def recovery_directory(root: Path) -> Path:
    """Return a private external store, never a path within the selected root."""
    require_supported_platform()
    state, directory = _recovery_location(root)
    if not state.is_absolute():
        msg = 'XDG_STATE_HOME must be absolute.'
        raise MigrationError(msg)
    _exists_without_links(directory)
    if state.exists():
        info = state.stat()
        if (
            state.is_symlink()
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o022
        ):
            message = 'Unsafe recovery state root ownership or permissions.'
            raise MigrationError(message)
    if directory.is_relative_to(root) or directory.resolve().is_relative_to(root):
        msg = 'Recovery storage must be outside the project.'
        raise MigrationError(msg)
    return directory


def _journal(root: Path) -> Path:
    return recovery_directory(root) / 'operation.json'


def has_pending(root: Path) -> bool:
    """Read pending status without creating storage or following a symlink."""
    _state, directory = _recovery_location(root)
    path = directory.absolute() / 'operation.json'
    if not _exists_without_links(path):
        return False
    # Only actual journal candidates require the secure-store/platform policy.
    path = _journal(root)
    data = _load(path, root)
    return data['state'] not in {'completed', 'rolled_back'}


def _exists_without_links(path: Path) -> bool:
    """Probe lexical components with lstat, never inspect a symlink target."""
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        try:
            info = current.lstat()
        except FileNotFoundError:
            # No journal means no migration policy applies to a native project,
            # even when the configured (unused) store would be unacceptable.
            return False
        if stat.S_ISLNK(info.st_mode):
            msg = 'Unsafe recovery path: symlink.'
            raise MigrationError(msg)
        if current != path and not stat.S_ISDIR(info.st_mode):
            return False
    return True


def _validate_store(path: Path) -> None:
    # Check the whole path even when the final file does not yet exist.
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        if current.is_symlink():
            msg = 'Unsafe recovery path: symlink.'
            raise MigrationError(msg)
        if current.exists() and current.is_dir():
            _safe_ancestor(current)
    if path.parent.exists():
        info = path.parent.stat()
        if (
            info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != PRIVATE_DIRECTORY_MODE
        ):
            msg = 'Unsafe recovery directory permissions.'
            raise MigrationError(msg)
    if path.exists():
        info = path.stat()
        if (
            not path.is_file()
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != PRIVATE_FILE_MODE
        ):
            msg = 'Unsafe recovery file permissions.'
            raise MigrationError(msg)


def _save(path: Path, data: dict[str, Any]) -> None:
    _validate_store(path)
    temporary = path.with_name('journal-' + uuid.uuid4().hex)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        temporary.unlink(missing_ok=True)


def _safe_ancestor(path: Path) -> None:
    """A private leaf is insufficient below an attacker-writable ancestor."""
    info = path.stat()
    mode = stat.S_IMODE(info.st_mode)
    writable_by_others = mode & 0o022
    trusted_sticky = bool(mode & stat.S_ISVTX) and info.st_uid == 0
    protected_parent = any(
        parent.stat().st_uid == os.getuid()
        and not stat.S_IMODE(parent.stat().st_mode) & 0o077
        for parent in path.parents
    )
    if (
        writable_by_others and not trusted_sticky and not protected_parent
    ) or info.st_uid not in {
        0,
        os.getuid(),
    }:
        message = 'Unsafe recovery ancestor ownership or permissions.'
        raise MigrationError(message)


def _pack(value: bytes | None) -> str | None:
    return base64.b64encode(value).decode('ascii') if value is not None else None


def _unpack(value: str | None) -> bytes | None:
    return base64.b64decode(value, validate=True) if value is not None else None


def _fingerprint(value: bytes | None) -> str | None:
    return hashlib.sha256(value).hexdigest() if value is not None else None


def _read(root: Path, rel: Path) -> bytes | None:
    path = safe_path(root, rel)
    return path.read_bytes() if path.exists() else None


def _load(path: Path, root: Path) -> dict[str, Any]:
    _validate_store(path)
    try:
        data = json.loads(path.read_text())
        _validate_data(data, root)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        msg = 'Invalid recovery journal; preserve it for inspection.'
        raise MigrationError(msg) from exc
    return data


def _validate_data(data: dict[str, Any], root: Path) -> None:
    if data['root'] != str(root) or data['schema'] != 1:
        raise ValueError
    if data['state'] not in {
        'staged',
        'applied',
        'verified',
        'completed',
        'rolled_back',
    }:
        raise ValueError
    if not isinstance(data['id'], str) or not isinstance(data['entries'], list):
        raise TypeError
    for entry in data['entries']:
        rel = Path(entry['path'])
        safe_path(root, rel)
        for key in ('before', 'after'):
            if _fingerprint(_unpack(entry[key])) != entry[key + '_hash']:
                raise ValueError
        if entry['kind'] not in {'write', 'delete', 'observe', 'answers'}:
            raise ValueError


def _check(root: Path, data: dict[str, Any], *, original_only: bool = False) -> None:
    for entry in data['entries']:
        rel = Path(entry['path'])
        current = (_read(root, rel), _mode(root, rel))
        allowed = [(_unpack(entry['before']), entry['before_mode'])]
        if not original_only:
            allowed.append((_unpack(entry['after']), entry['after_mode']))
        if current not in allowed:
            msg = f'Concurrent edit blocks recovery: {entry["path"]}'
            raise MigrationError(msg)


def _mode(root: Path, rel: Path) -> int | None:
    path = safe_path(root, rel)
    return stat.S_IMODE(path.stat().st_mode) if path.exists() else None


def _write(
    root: Path, rel: Path, content: bytes | None, mode: int | None = None
) -> None:
    path = safe_path(root, rel)
    if content is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive temporary in the same directory; replace is atomic per file,
    # not for the directory/transaction. Reconciliation handles interrupted ack.
    temporary = path.with_name('.dt-migrate-' + uuid.uuid4().hex)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(mode if mode is not None else 0o644)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _resume(root: Path, data: dict[str, Any], path: Path) -> None:
    _check(root, data)
    identifier = data['id']
    for entry in data['entries']:
        if entry['kind'] != 'write':
            continue
        _check(root, data)
        rel = Path(entry['path'])
        if _read(root, rel) != _unpack(entry['after']):
            _write(root, rel, _unpack(entry['after']), entry['after_mode'])
        checkpoint('target_applied', identifier)
        data['state'] = 'applied'
        _save(path, data)
    for entry in data['entries']:
        if entry['kind'] == 'write' and _read(root, Path(entry['path'])) != _unpack(
            entry['after']
        ):
            msg = 'Target verification failed; recovery preserved.'
            raise MigrationError(msg)
    data['state'] = 'verified'
    _save(path, data)
    checkpoint('target_verified', identifier)
    for entry in data['entries']:
        if entry['kind'] != 'delete':
            continue
        _check(root, data)
        _write(root, Path(entry['path']), None)
        checkpoint('legacy_removed', identifier)
        _save(path, data)
    checkpoint('before_completion', identifier)
    for entry in data['entries']:
        if entry['kind'] == 'answers':
            _check(root, data)
            _write(
                root, Path(entry['path']), _unpack(entry['after']), entry['after_mode']
            )
    _check(root, data)
    for entry in data['entries']:
        if _read(root, Path(entry['path'])) != _unpack(entry['after']):
            msg = 'Final migration verification failed.'
            raise MigrationError(msg)
    data['state'] = 'completed'
    _save(path, data)
    checkpoint('completed', identifier)


def execute_migration(root: Path, plan: MigrationPlan) -> None:
    """Stage exact scoped originals, apply, verify, remove sources, finalize."""
    path = _journal(root)
    if has_pending(root):
        msg = 'Interrupted migration: run dt migration-recover ROOT.'
        raise MigrationError(msg)
    entries = []
    for rel, original in sorted(plan.originals.items(), key=lambda item: str(item[0])):
        if _read(root, rel) != original:
            msg = f'Concurrent edit before migration: {rel}'
            raise MigrationError(msg)
        after = plan.writes.get(rel, original)
        original_mode = _mode(root, rel)
        after_mode: int | None = original_mode if original_mode is not None else 0o644
        kind = 'write' if rel in plan.writes else 'observe'
        if rel in plan.deletes:
            after, kind = None, 'delete'
            after_mode = None
        if rel == Path('.copier-answers.yml'):
            kind = 'answers'
        entries.append(
            {
                'path': str(rel),
                'before': _pack(original),
                'after': _pack(after),
                'before_hash': _fingerprint(original),
                'after_hash': _fingerprint(after),
                'kind': kind,
                'before_mode': original_mode,
                'after_mode': after_mode,
            }
        )
    data: dict[str, Any] = {
        'schema': 1,
        'root': str(root),
        'id': uuid.uuid4().hex,
        'state': 'staged',
        'entries': entries,
    }
    _private(path.parent)
    _save(path, data)
    checkpoint('recovery_prepared', data['id'])
    try:
        _resume(root, data, path)
    except OSError as exc:
        try:
            recover_migration(root, rollback=True)
        except OSError, MigrationError:
            msg = (
                'Migration interrupted; run dt migration-recover ROOT. '
                'Recovery preserved.'
            )
            raise MigrationError(msg) from exc
        msg = (
            'Migration I/O failed; scoped original files restored. '
            'Recovery retained; retry the original command.'
        )
        raise MigrationError(msg) from exc


def recover_migration(root: Path, *, rollback: bool = False) -> None:
    """Reconcile actual bytes before resume/rollback; never overwrite new edits."""
    path = _journal(root)
    _validate_store(path)
    if not path.exists():
        msg = 'No recovery journal for this root.'
        raise MigrationError(msg)
    data = _load(path, root)
    _check(root, data)
    if not rollback:
        if data['state'] == 'rolled_back':
            msg = 'Operation rolled back; retry the original migration command.'
            raise MigrationError(msg)
        if data['state'] != 'completed':
            _resume(root, data, path)
        return
    if data['state'] == 'completed':
        msg = 'Completed operation cannot be automatically rolled back.'
        raise MigrationError(msg)
    for entry in reversed(data['entries']):
        _check(root, data)
        rel = Path(entry['path'])
        original = _unpack(entry['before'])
        if (_read(root, rel), _mode(root, rel)) != (original, entry['before_mode']):
            _write(root, rel, original, entry['before_mode'])
    data['state'] = 'rolled_back'
    _save(path, data)
