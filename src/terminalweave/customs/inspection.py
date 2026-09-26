from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError, CapacityError, StateTransitionError

class InspectionState(str, Enum):
    REQUESTED = 'requested'
    SCHEDULED = 'scheduled'
    STARTED = 'started'
    CLEARED = 'cleared'
    REFERRED = 'referred'

@dataclass
class Inspection:
    inspection_id: str
    container_id: str
    requested_at: datetime
    state: InspectionState = InspectionState.REQUESTED
    bay_id: str | None = None
    scheduled_at: datetime | None = None

    def __post_init__(self):
        self.requested_at = ensure_utc(self.requested_at)

@dataclass(frozen=True)
class InspectionBay:
    bay_id: str
    daily_capacity: int
    supports_xray: bool = True

    def __post_init__(self):
        if self.daily_capacity <= 0:
            raise ValidationError('capacity must be positive')

class InspectionScheduler:

    def __init__(self, bays: list[InspectionBay]):
        self.bays = {b.bay_id: b for b in bays}
        self.items: dict[str, Inspection] = {}

    def request(self, item: Inspection) -> None:
        if item.inspection_id in self.items:
            raise ValidationError('duplicate inspection')
        self.items[item.inspection_id] = item

    def schedule(self, inspection_id: str, at: datetime, requires_xray: bool=False) -> Inspection:
        at = ensure_utc(at)
        item = self.items[inspection_id]
        if item.state != InspectionState.REQUESTED:
            raise StateTransitionError('inspection not requestable')
        choices = []
        for bay in self.bays.values():
            if requires_xray and (not bay.supports_xray):
                continue
            count = sum((1 for x in self.items.values() if x.bay_id == bay.bay_id and x.scheduled_at and (x.scheduled_at.date() == at.date())))
            if count < bay.daily_capacity:
                choices.append((count, bay.bay_id, bay))
        if not choices:
            raise CapacityError('inspection capacity exhausted')
        _, _, bay = min(choices)
        item.bay_id = bay.bay_id
        item.scheduled_at = at
        item.state = InspectionState.SCHEDULED
        return item

    def start(self, inspection_id: str) -> Inspection:
        item = self.items[inspection_id]
        if item.state != InspectionState.SCHEDULED:
            raise StateTransitionError('inspection is not scheduled')
        item.state = InspectionState.STARTED
        return item

    def finish(self, inspection_id: str, cleared: bool) -> Inspection:
        item = self.items[inspection_id]
        if item.state != InspectionState.STARTED:
            raise StateTransitionError('inspection has not started')
        item.state = InspectionState.CLEARED if cleared else InspectionState.REFERRED
        return item
