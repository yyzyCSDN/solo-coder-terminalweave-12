from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError, CapacityError

@dataclass(frozen=True)
class ZoneHazmatLimit:
    zone_id: str
    class_code: str
    max_units: int
    max_net_kg: float

    def __post_init__(self):
        if self.max_units < 0 or self.max_net_kg < 0:
            raise ValidationError('hazmat limits cannot be negative')

@dataclass(frozen=True)
class HazmatPresence:
    container_id: str
    zone_id: str
    class_code: str
    net_kg: float

class HazmatCapacityLedger:

    def __init__(self, limits: list[ZoneHazmatLimit]):
        self.limits = {(x.zone_id, x.class_code): x for x in limits}
        self.items: dict[str, HazmatPresence] = {}

    def can_add(self, item: HazmatPresence) -> bool:
        limit = self.limits.get((item.zone_id, item.class_code))
        if not limit:
            return False
        existing = [x for x in self.items.values() if x.zone_id == item.zone_id and x.class_code == item.class_code]
        return len(existing) + 1 <= limit.max_units and sum((x.net_kg for x in existing)) + item.net_kg <= limit.max_net_kg

    def add(self, item: HazmatPresence) -> None:
        if item.container_id in self.items:
            raise ValidationError('container already present')
        if not self.can_add(item):
            raise CapacityError('hazmat zone limit exceeded')
        self.items[item.container_id] = item

    def remove(self, container_id: str) -> None:
        self.items.pop(container_id, None)
