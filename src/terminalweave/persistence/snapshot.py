from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from copy import deepcopy
from terminalweave.core.clock import ensure_utc, utc_now
from terminalweave.core.errors import ValidationError, ConflictError

@dataclass(frozen=True)
class Snapshot:
    stream_id: str
    sequence: int
    state: dict[str, object]
    created_at: datetime

    def __post_init__(self):
        object.__setattr__(self, 'created_at', ensure_utc(self.created_at))
        if self.sequence < 0:
            raise ValidationError('snapshot sequence cannot be negative')

class SnapshotStore:

    def __init__(self):
        self._items: dict[str, Snapshot] = {}

    def put(self, stream_id: str, sequence: int, state: dict[str, object], created_at: datetime | None=None) -> Snapshot:
        current = self._items.get(stream_id)
        if current and sequence < current.sequence:
            raise ConflictError('cannot replace snapshot with older sequence')
        snap = Snapshot(stream_id, sequence, deepcopy(state), created_at or utc_now())
        self._items[stream_id] = snap
        return snap

    def get(self, stream_id: str) -> Snapshot | None:
        snap = self._items.get(stream_id)
        if not snap:
            return None
        return Snapshot(snap.stream_id, snap.sequence, deepcopy(snap.state), snap.created_at)

    def delete_before(self, sequence: int) -> int:
        keys = [k for k, v in self._items.items() if v.sequence < sequence]
        for k in keys:
            del self._items[k]
        return len(keys)
