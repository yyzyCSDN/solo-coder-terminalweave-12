from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError, CapacityError

@dataclass(frozen=True)
class YardZone:
    zone_id: str
    capacity_teu: int
    allowed_sizes: frozenset[int]
    reefer: bool = False
    hazardous: bool = False
    import_export: str = 'mixed'

    def __post_init__(self) -> None:
        if self.capacity_teu <= 0 or not self.allowed_sizes:
            raise ValidationError('invalid yard zone')
        if not self.allowed_sizes <= {20, 40, 45}:
            raise ValidationError('unsupported container size')

@dataclass(frozen=True)
class ZoneDemand:
    size_ft: int
    count: int
    reefer: bool = False
    hazardous: bool = False
    flow: str = 'mixed'

    def teu(self) -> int:
        return self.count * (1 if self.size_ft == 20 else 2)

class ZoneCapacityBook:

    def __init__(self, zones: list[YardZone]):
        self.zones = {z.zone_id: z for z in zones}
        self.used = {z.zone_id: 0 for z in zones}

    def compatible(self, zone: YardZone, demand: ZoneDemand) -> bool:
        if demand.size_ft not in zone.allowed_sizes:
            return False
        if demand.reefer and (not zone.reefer):
            return False
        if demand.hazardous and (not zone.hazardous):
            return False
        if zone.import_export != 'mixed' and demand.flow not in {'mixed', zone.import_export}:
            return False
        return self.used[zone.zone_id] + demand.teu() <= zone.capacity_teu

    def reserve(self, demand: ZoneDemand) -> str:
        candidates = [z for z in self.zones.values() if self.compatible(z, demand)]
        if not candidates:
            raise CapacityError('no yard zone can satisfy demand')
        chosen = min(candidates, key=lambda z: (z.capacity_teu - self.used[z.zone_id] - demand.teu(), z.zone_id))
        self.used[chosen.zone_id] += demand.teu()
        return chosen.zone_id

    def release(self, zone_id: str, teu: int) -> None:
        if teu < 0 or teu > self.used[zone_id]:
            raise ValidationError('invalid release amount')
        self.used[zone_id] -= teu

    def utilization(self, zone_id: str) -> float:
        zone = self.zones[zone_id]
        return self.used[zone_id] / zone.capacity_teu
