from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError, StateTransitionError

class ExceptionState(str, Enum):
    OPEN = 'open'
    ASSIGNED = 'assigned'
    RESOLVED = 'resolved'
    REJECTED = 'rejected'

@dataclass
class GateException:
    exception_id: str
    truck_id: str
    code: str
    opened_at: datetime
    state: ExceptionState = ExceptionState.OPEN
    assignee: str | None = None
    resolution: str | None = None

    def __post_init__(self):
        self.opened_at = ensure_utc(self.opened_at)

class GateExceptionDesk:

    def __init__(self):
        self.items: dict[str, GateException] = {}

    def open(self, item: GateException) -> None:
        if item.exception_id in self.items:
            raise ValidationError('duplicate exception')
        self.items[item.exception_id] = item

    def assign(self, exception_id: str, operator: str) -> GateException:
        item = self.items[exception_id]
        if item.state != ExceptionState.OPEN:
            raise StateTransitionError('exception is not open')
        item.state = ExceptionState.ASSIGNED
        item.assignee = operator
        return item

    def resolve(self, exception_id: str, resolution: str, accepted: bool) -> GateException:
        item = self.items[exception_id]
        if item.state != ExceptionState.ASSIGNED:
            raise StateTransitionError('exception is not assigned')
        if not resolution.strip():
            raise ValidationError('resolution required')
        item.state = ExceptionState.RESOLVED if accepted else ExceptionState.REJECTED
        item.resolution = resolution
        return item

    def open_for_truck(self, truck_id: str) -> tuple[GateException, ...]:
        return tuple((x for x in self.items.values() if x.truck_id == truck_id and x.state in {ExceptionState.OPEN, ExceptionState.ASSIGNED}))
