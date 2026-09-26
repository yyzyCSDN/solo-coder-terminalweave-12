from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class FuelReading:
    equipment_id: str
    at: datetime
    liters: float
    engine_hours: float

    def __post_init__(self):
        object.__setattr__(self, 'at', ensure_utc(self.at))
        if self.liters < 0 or self.engine_hours < 0:
            raise ValidationError('fuel and hours cannot be negative')

class FuelEfficiencyTracker:

    def __init__(self):
        self.readings: dict[str, list[FuelReading]] = {}

    def ingest(self, r: FuelReading) -> None:
        series = self.readings.setdefault(r.equipment_id, [])
        if series and (r.at <= series[-1].at or r.engine_hours < series[-1].engine_hours):
            raise ValidationError('reading order invalid')
        series.append(r)

    def liters_per_hour(self, equipment_id: str) -> float | None:
        s = self.readings.get(equipment_id, [])
        if len(s) < 2:
            return None
        consumed = s[0].liters - s[-1].liters
        hours = s[-1].engine_hours - s[0].engine_hours
        if hours <= 0 or consumed < 0:
            return None
        return consumed / hours

    def suspected_refuel(self, equipment_id: str) -> list[tuple[datetime, float]]:
        s = self.readings.get(equipment_id, [])
        out = []
        for a, b in zip(s, s[1:]):
            if b.liters > a.liters:
                out.append((b.at, b.liters - a.liters))
        return out
