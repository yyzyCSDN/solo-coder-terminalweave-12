from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError, ConflictError

@dataclass(frozen=True)
class InventoryEvent:
    sequence: int
    container_id: str
    event_type: str
    at: datetime
    location: str | None
    reference: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, 'at', ensure_utc(self.at))
        if self.sequence < 1:
            raise ValidationError('sequence must be positive')

@dataclass(frozen=True)
class InventoryState:
    container_id: str
    location: str | None
    present: bool
    last_sequence: int
    last_event_at: datetime

class InventoryLedger:

    def __init__(self):
        self._events: dict[str, list[InventoryEvent]] = {}

    def append(self, event: InventoryEvent) -> InventoryState:
        events = self._events.setdefault(event.container_id, [])
        expected = events[-1].sequence + 1 if events else 1
        if event.sequence != expected:
            raise ConflictError(f'expected sequence {expected}')
        if events and event.at < events[-1].at:
            raise ValidationError('event time cannot move backwards')
        state = self._project(events)
        if event.event_type == 'gate_in' and state and state.present:
            raise ConflictError('container already present')
        if event.event_type in {'gate_out', 'loaded'} and (not state or not state.present):
            raise ConflictError('container not present')
        if event.event_type == 'move' and (not state or not state.present or (not event.location)):
            raise ConflictError('move requires a present container and destination')
        events.append(event)
        return self._project(events)

    def _project(self, events: list[InventoryEvent]) -> InventoryState | None:
        if not events:
            return None
        present = False
        location = None
        for e in events:
            if e.event_type in {'gate_in', 'discharged'}:
                present = True
                location = e.location
            elif e.event_type == 'move':
                location = e.location
            elif e.event_type in {'gate_out', 'loaded'}:
                present = False
                location = None
        last = events[-1]
        return InventoryState(last.container_id, location, present, last.sequence, last.at)

    def state(self, container_id: str) -> InventoryState | None:
        return self._project(self._events.get(container_id, []))

    def history(self, container_id: str) -> tuple[InventoryEvent, ...]:
        return tuple(self._events.get(container_id, []))

    def present_at(self, location_prefix: str) -> tuple[InventoryState, ...]:
        states = []
        for cid in self._events:
            state = self.state(cid)
            if state and state.present and state.location and state.location.startswith(location_prefix):
                states.append(state)
        return tuple(sorted(states, key=lambda s: s.container_id))
