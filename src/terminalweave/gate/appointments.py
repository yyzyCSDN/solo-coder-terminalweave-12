from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError, CapacityError, StateTransitionError

class AppointmentState(str, Enum):
    BOOKED = 'booked'
    CHECKED_IN = 'checked_in'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    NO_SHOW = 'no_show'

@dataclass(frozen=True)
class GateSlotPolicy:
    slot_minutes: int
    general_capacity: int
    reefer_capacity: int
    hazardous_capacity: int

    def __post_init__(self) -> None:
        if self.slot_minutes <= 0 or min(self.general_capacity, self.reefer_capacity, self.hazardous_capacity) < 0:
            raise ValidationError('invalid gate slot policy')

@dataclass
class Appointment:
    appointment_id: str
    truck_id: str
    slot_start: datetime
    reefer: bool = False
    hazardous: bool = False
    state: AppointmentState = AppointmentState.BOOKED
    checked_in_at: datetime | None = None
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        self.slot_start = ensure_utc(self.slot_start)

class GateBook:

    def __init__(self, policy: GateSlotPolicy):
        self.policy = policy
        self._items: dict[str, Appointment] = {}

    def _normalize_slot(self, at: datetime) -> datetime:
        at = ensure_utc(at)
        minute = at.minute // self.policy.slot_minutes * self.policy.slot_minutes
        return at.replace(minute=minute, second=0, microsecond=0)

    def _active_in_slot(self, slot: datetime) -> list[Appointment]:
        return [a for a in self._items.values() if a.slot_start == slot and a.state not in {AppointmentState.CANCELLED, AppointmentState.NO_SHOW}]

    def capacity_remaining(self, at: datetime, *, reefer: bool=False, hazardous: bool=False) -> int:
        slot = self._normalize_slot(at)
        active = self._active_in_slot(slot)
        remaining = self.policy.general_capacity - len(active)
        if reefer:
            remaining = min(remaining, self.policy.reefer_capacity - sum((a.reefer for a in active)))
        if hazardous:
            remaining = min(remaining, self.policy.hazardous_capacity - sum((a.hazardous for a in active)))
        return max(0, remaining)

    def book(self, appointment_id: str, truck_id: str, at: datetime, *, reefer: bool=False, hazardous: bool=False) -> Appointment:
        if appointment_id in self._items:
            raise ValidationError('appointment id already exists')
        slot = self._normalize_slot(at)
        if self.capacity_remaining(slot, reefer=reefer, hazardous=hazardous) <= 0:
            raise CapacityError('gate slot capacity exhausted')
        item = Appointment(appointment_id, truck_id, slot, reefer, hazardous)
        self._items[appointment_id] = item
        return item

    def cancel(self, appointment_id: str) -> Appointment:
        item = self._items[appointment_id]
        if item.state != AppointmentState.BOOKED:
            raise StateTransitionError('only booked appointments can be cancelled')
        item.state = AppointmentState.CANCELLED
        return item

    def check_in(self, appointment_id: str, at: datetime, grace: timedelta=timedelta(minutes=45)) -> Appointment:
        item = self._items[appointment_id]
        at = ensure_utc(at)
        if item.state != AppointmentState.BOOKED:
            raise StateTransitionError('appointment is not bookable for check-in')
        slot_end = item.slot_start + timedelta(minutes=self.policy.slot_minutes)
        if at < item.slot_start - grace or at > slot_end + grace:
            raise StateTransitionError('truck is outside check-in grace period')
        item.state = AppointmentState.CHECKED_IN
        item.checked_in_at = at
        return item

    def complete(self, appointment_id: str, at: datetime) -> Appointment:
        item = self._items[appointment_id]
        at = ensure_utc(at)
        if item.state != AppointmentState.CHECKED_IN:
            raise StateTransitionError('appointment must be checked in first')
        if item.checked_in_at and at < item.checked_in_at:
            raise ValidationError('completion cannot precede check-in')
        item.state = AppointmentState.COMPLETED
        item.completed_at = at
        return item

    def mark_no_shows(self, now: datetime, grace: timedelta=timedelta(minutes=45)) -> list[str]:
        now = ensure_utc(now)
        changed = []
        for item in self._items.values():
            slot_end = item.slot_start + timedelta(minutes=self.policy.slot_minutes)
            if item.state == AppointmentState.BOOKED and now > slot_end + grace:
                item.state = AppointmentState.NO_SHOW
                changed.append(item.appointment_id)
        return changed
