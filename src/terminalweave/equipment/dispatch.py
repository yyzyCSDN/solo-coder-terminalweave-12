from __future__ import annotations
from dataclasses import dataclass
from math import hypot
from terminalweave.core.errors import ValidationError, CapacityError

@dataclass(frozen=True)
class Position:
    x: float
    y: float

@dataclass(frozen=True)
class DispatchUnit:
    equipment_id: str
    kind: str
    capacity_tonnes: float
    position: Position
    available: bool = True

@dataclass(frozen=True)
class DispatchJob:
    job_id: str
    required_kind: str
    load_tonnes: float
    pickup: Position
    dropoff: Position
    priority: int = 0

@dataclass(frozen=True)
class DispatchDecision:
    equipment_id: str
    job_id: str
    deadhead_distance: float
    loaded_distance: float
    score: float

class EquipmentDispatcher:

    def __init__(self, units: list[DispatchUnit]):
        self.units = {u.equipment_id: u for u in units}
        self.busy: set[str] = set()

    def dispatch(self, job: DispatchJob) -> DispatchDecision:
        if job.load_tonnes <= 0:
            raise ValidationError('load must be positive')
        candidates = []
        for unit in self.units.values():
            if not unit.available or unit.equipment_id in self.busy or unit.kind != job.required_kind or (unit.capacity_tonnes < job.load_tonnes):
                continue
            dead = hypot(unit.position.x - job.pickup.x, unit.position.y - job.pickup.y)
            loaded = hypot(job.dropoff.x - job.pickup.x, job.dropoff.y - job.pickup.y)
            score = dead + loaded * 0.15 - job.priority * 0.1
            candidates.append((score, dead, unit.equipment_id, unit))
        if not candidates:
            raise CapacityError('no compatible equipment available')
        score, dead, _, unit = min(candidates)
        self.busy.add(unit.equipment_id)
        return DispatchDecision(unit.equipment_id, job.job_id, dead, hypot(job.dropoff.x - job.pickup.x, job.dropoff.y - job.pickup.y), score)

    def release(self, equipment_id: str, new_position: Position) -> None:
        unit = self.units[equipment_id]
        self.units[equipment_id] = DispatchUnit(unit.equipment_id, unit.kind, unit.capacity_tonnes, new_position, unit.available)
        self.busy.discard(equipment_id)
