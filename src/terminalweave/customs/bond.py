from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError, ConflictError

@dataclass(frozen=True)
class BondMovement:
    movement_id: str
    container_id: str
    origin: str
    destination: str
    opened_at: datetime
    due_at: datetime
    closed_at: datetime | None = None

    def __post_init__(self):
        object.__setattr__(self, 'opened_at', ensure_utc(self.opened_at))
        object.__setattr__(self, 'due_at', ensure_utc(self.due_at))
        if self.due_at <= self.opened_at:
            raise ValidationError('bond due time must follow opening')

class BondLedger:

    def __init__(self):
        self.movements: dict[str, BondMovement] = {}

    def open(self, m: BondMovement) -> None:
        if m.movement_id in self.movements:
            raise ValidationError('duplicate bond movement')
        if any((x.container_id == m.container_id and x.closed_at is None for x in self.movements.values())):
            raise ConflictError('container already under active bond')
        self.movements[m.movement_id] = m

    def close(self, movement_id: str, at: datetime) -> BondMovement:
        at = ensure_utc(at)
        m = self.movements[movement_id]
        if m.closed_at is not None:
            raise ConflictError('bond already closed')
        if at < m.opened_at:
            raise ValidationError('close time precedes opening')
        closed = BondMovement(m.movement_id, m.container_id, m.origin, m.destination, m.opened_at, m.due_at, at)
        self.movements[movement_id] = closed
        return closed

    def overdue(self, now: datetime) -> tuple[BondMovement, ...]:
        now = ensure_utc(now)
        return tuple(sorted((m for m in self.movements.values() if m.closed_at is None and now > m.due_at), key=lambda x: x.due_at))
