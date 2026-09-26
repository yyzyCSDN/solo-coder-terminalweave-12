from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError, CapacityError

@dataclass(frozen=True)
class PowerCircuit:
    circuit_id: str
    capacity_kw: float
    reserve_fraction: float = 0.1

    def __post_init__(self):
        if self.capacity_kw <= 0 or not 0 <= self.reserve_fraction < 1:
            raise ValidationError('invalid circuit')

    @property
    def usable_kw(self) -> float:
        return self.capacity_kw * (1 - self.reserve_fraction)

@dataclass(frozen=True)
class ReeferLoad:
    container_id: str
    demand_kw: float
    startup_multiplier: float = 1.0
    priority: int = 0

    def __post_init__(self):
        if self.demand_kw <= 0 or self.startup_multiplier < 1:
            raise ValidationError('invalid reefer load')

class ReeferPowerBoard:

    def __init__(self, circuits: list[PowerCircuit]):
        self.circuits = {c.circuit_id: c for c in circuits}
        self.loads: dict[str, dict[str, ReeferLoad]] = {c.circuit_id: {} for c in circuits}

    def used_kw(self, circuit_id: str, startup: bool=False) -> float:
        return sum((x.demand_kw * (x.startup_multiplier if startup else 1.0) for x in self.loads[circuit_id].values()))

    def connect(self, load: ReeferLoad) -> str:
        choices = []
        for cid, circuit in self.circuits.items():
            projected = self.used_kw(cid) + load.demand_kw * load.startup_multiplier
            if projected <= circuit.usable_kw:
                choices.append((circuit.usable_kw - projected, cid))
        if not choices:
            raise CapacityError('reefer power capacity unavailable')
        _, cid = min(choices)
        self.loads[cid][load.container_id] = load
        return cid

    def disconnect(self, container_id: str) -> bool:
        for mapping in self.loads.values():
            if container_id in mapping:
                del mapping[container_id]
                return True
        return False

    def rebalance(self) -> dict[str, str]:
        all_loads = [x for m in self.loads.values() for x in m.values()]
        all_loads.sort(key=lambda x: (-x.priority, -x.demand_kw, x.container_id))
        self.loads = {cid: {} for cid in self.circuits}
        return {load.container_id: self.connect(load) for load in all_loads}
