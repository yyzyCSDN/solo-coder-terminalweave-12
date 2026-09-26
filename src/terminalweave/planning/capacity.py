from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class CapacityDemand:
    name: str
    berth_hours: float
    crane_hours: float
    yard_teu: float
    gate_moves: int
    rail_teu: float

    def __post_init__(self):
        if min(self.berth_hours, self.crane_hours, self.yard_teu, self.gate_moves, self.rail_teu) < 0:
            raise ValidationError('capacity demand cannot be negative')

@dataclass(frozen=True)
class CapacitySupply:
    berth_hours: float
    crane_hours: float
    yard_teu: float
    gate_moves: int
    rail_teu: float

class CapacityPlanner:

    def aggregate(self, demands: list[CapacityDemand]) -> dict[str, float]:
        return {'berth_hours': sum((x.berth_hours for x in demands)), 'crane_hours': sum((x.crane_hours for x in demands)), 'yard_teu': sum((x.yard_teu for x in demands)), 'gate_moves': sum((x.gate_moves for x in demands)), 'rail_teu': sum((x.rail_teu for x in demands))}

    def headroom(self, supply: CapacitySupply, demands: list[CapacityDemand]) -> dict[str, float]:
        used = self.aggregate(demands)
        return {'berth_hours': supply.berth_hours - used['berth_hours'], 'crane_hours': supply.crane_hours - used['crane_hours'], 'yard_teu': supply.yard_teu - used['yard_teu'], 'gate_moves': supply.gate_moves - used['gate_moves'], 'rail_teu': supply.rail_teu - used['rail_teu']}

    def bottlenecks(self, supply: CapacitySupply, demands: list[CapacityDemand]) -> list[str]:
        return [k for k, v in self.headroom(supply, demands).items() if v < 0]
