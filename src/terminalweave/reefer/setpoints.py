from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError, ConflictError

@dataclass(frozen=True)
class ReeferBooking:
    container_id: str
    commodity: str
    booked_setpoint_c: float
    ventilation_pct: int
    humidity_pct: int | None = None

    def __post_init__(self):
        if not -40 <= self.booked_setpoint_c <= 30:
            raise ValidationError('setpoint outside supported range')
        if not 0 <= self.ventilation_pct <= 100:
            raise ValidationError('ventilation must be 0..100')
        if self.humidity_pct is not None and (not 0 <= self.humidity_pct <= 100):
            raise ValidationError('humidity must be 0..100')

@dataclass(frozen=True)
class ControllerSettings:
    container_id: str
    setpoint_c: float
    ventilation_pct: int
    humidity_pct: int | None = None

class SetpointReconciler:

    def compare(self, booking: ReeferBooking, settings: ControllerSettings, tolerance_c: float=0.2) -> list[str]:
        if booking.container_id != settings.container_id:
            raise ConflictError('container id mismatch')
        issues = []
        if abs(booking.booked_setpoint_c - settings.setpoint_c) > tolerance_c:
            issues.append('temperature setpoint')
        if booking.ventilation_pct != settings.ventilation_pct:
            issues.append('ventilation')
        if booking.humidity_pct is not None and booking.humidity_pct != settings.humidity_pct:
            issues.append('humidity')
        return issues
