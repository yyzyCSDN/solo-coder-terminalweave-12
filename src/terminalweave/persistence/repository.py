from __future__ import annotations
from copy import deepcopy
from threading import RLock
from terminalweave.core.errors import ConflictError

class VersionedRepository:

    def __init__(self):
        self._data: dict[str, tuple[int, dict[str, object]]] = {}
        self._lock = RLock()

    def get(self, key: str) -> tuple[int, dict[str, object]] | None:
        with self._lock:
            item = self._data.get(key)
            return (item[0], deepcopy(item[1])) if item else None

    def put(self, key: str, value: dict[str, object], expected_version: int | None) -> int:
        with self._lock:
            current = self._data.get(key)
            version = current[0] if current else 0
            if expected_version is not None and expected_version != version:
                raise ConflictError(f'expected version {expected_version}, actual {version}')
            next_version = version + 1
            self._data[key] = (next_version, deepcopy(value))
            return next_version

    def delete(self, key: str, expected_version: int | None=None) -> bool:
        with self._lock:
            current = self._data.get(key)
            if not current:
                return False
            if expected_version is not None and current[0] != expected_version:
                raise ConflictError('version changed')
            del self._data[key]
            return True

    def keys(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._data))
