from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError, ConflictError

@dataclass(frozen=True)
class ContainerLeg:
    leg_id: str
    container_id: str
    mode: str
    origin: str
    destination: str
    departure: datetime
    arrival: datetime
    parent_leg_id: str | None = None

    def __post_init__(self):
        object.__setattr__(self, 'departure', ensure_utc(self.departure))
        object.__setattr__(self, 'arrival', ensure_utc(self.arrival))
        if self.arrival <= self.departure:
            raise ValidationError('arrival must follow departure')

class LineageGraph:

    def __init__(self):
        self.legs: dict[str, ContainerLeg] = {}

    def add(self, leg: ContainerLeg) -> None:
        if leg.leg_id in self.legs:
            raise ValidationError('duplicate leg')
        if leg.parent_leg_id:
            parent = self.legs.get(leg.parent_leg_id)
            if not parent:
                raise ValidationError('parent leg does not exist')
            if parent.container_id != leg.container_id:
                raise ConflictError('lineage cannot cross containers')
            if parent.destination != leg.origin:
                raise ConflictError('lineage location discontinuity')
            if parent.arrival > leg.departure:
                raise ConflictError('lineage time overlap')
        self.legs[leg.leg_id] = leg

    def chain(self, leg_id: str) -> list[ContainerLeg]:
        result = []
        current = self.legs[leg_id]
        seen = set()
        while current:
            if current.leg_id in seen:
                raise ConflictError('lineage cycle')
            seen.add(current.leg_id)
            result.append(current)
            current = self.legs.get(current.parent_leg_id) if current.parent_leg_id else None
        return list(reversed(result))

    def total_transit_seconds(self, leg_id: str) -> float:
        chain = self.chain(leg_id)
        return (chain[-1].arrival - chain[0].departure).total_seconds()
