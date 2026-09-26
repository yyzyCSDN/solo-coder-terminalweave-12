from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class EquipmentIncident:
    incident_id: str
    equipment_id: str
    at: datetime
    severity: int
    category: str
    lost_time_minutes: int = 0

    def __post_init__(self):
        object.__setattr__(self, 'at', ensure_utc(self.at))
        if not 1 <= self.severity <= 5 or self.lost_time_minutes < 0:
            raise ValidationError('invalid incident')

class IncidentBook:

    def __init__(self):
        self.items: dict[str, EquipmentIncident] = {}

    def add(self, i: EquipmentIncident) -> None:
        if i.incident_id in self.items:
            raise ValidationError('duplicate incident')
        self.items[i.incident_id] = i

    def frequency(self, equipment_id: str) -> int:
        return sum((i.equipment_id == equipment_id for i in self.items.values()))

    def lost_time(self, equipment_id: str | None=None) -> int:
        return sum((i.lost_time_minutes for i in self.items.values() if equipment_id is None or i.equipment_id == equipment_id))

    def severe(self, threshold: int=4) -> tuple[EquipmentIncident, ...]:
        return tuple(sorted((i for i in self.items.values() if i.severity >= threshold), key=lambda x: (-x.severity, x.at)))
