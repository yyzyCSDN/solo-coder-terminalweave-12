from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError, CapacityError

@dataclass(frozen=True)
class Charger:
    charger_id: str
    power_kw: float
    efficiency: float = 0.92

    def __post_init__(self):
        if self.power_kw <= 0 or not 0 < self.efficiency <= 1:
            raise ValidationError('invalid charger')

@dataclass(frozen=True)
class ChargeRequest:
    equipment_id: str
    battery_kwh: float
    current_pct: float
    target_pct: float
    available_from: datetime
    required_by: datetime

    def __post_init__(self):
        object.__setattr__(self, 'available_from', ensure_utc(self.available_from))
        object.__setattr__(self, 'required_by', ensure_utc(self.required_by))
        if self.battery_kwh <= 0 or not 0 <= self.current_pct < self.target_pct <= 100 or self.required_by <= self.available_from:
            raise ValidationError('invalid charge request')

class ChargePlanner:

    def required_hours(self, charger: Charger, req: ChargeRequest) -> float:
        return req.battery_kwh * ((req.target_pct - req.current_pct) / 100) / (charger.power_kw * charger.efficiency)

    def choose(self, chargers: list[Charger], req: ChargeRequest) -> tuple[Charger, datetime]:
        candidates = []
        for c in chargers:
            finish = req.available_from + timedelta(hours=self.required_hours(c, req))
            if finish <= req.required_by:
                candidates.append((finish, c.charger_id, c))
        if not candidates:
            raise CapacityError('no charger can meet required-by time')
        finish, _, charger = min(candidates)
        return (charger, finish)
