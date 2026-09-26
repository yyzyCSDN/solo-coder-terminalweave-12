from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError, CapacityError

@dataclass(frozen=True)
class ResourcePool:
    resource_type: str
    capacity: int
    reserved: int = 0

    def __post_init__(self):
        if self.capacity < 0 or self.reserved < 0 or self.reserved > self.capacity:
            raise ValidationError('invalid resource pool')

    @property
    def available(self) -> int:
        return self.capacity - self.reserved

class ResourceLedger:

    def __init__(self, pools: list[ResourcePool]):
        self._capacity = {p.resource_type: p.capacity for p in pools}
        self._reservations: dict[str, dict[str, int]] = {}

    def used(self, resource_type: str) -> int:
        return sum((v.get(resource_type, 0) for v in self._reservations.values()))

    def available(self, resource_type: str) -> int:
        return self._capacity[resource_type] - self.used(resource_type)

    def reserve(self, owner: str, requirements: dict[str, int]) -> None:
        if owner in self._reservations:
            raise ValidationError('owner already reserved resources')
        for kind, count in requirements.items():
            if count < 0:
                raise ValidationError('resource count cannot be negative')
            if kind not in self._capacity:
                raise ValidationError(f'unknown resource type {kind}')
            if self.available(kind) < count:
                raise CapacityError(f'insufficient {kind}')
        self._reservations[owner] = dict(requirements)

    def release(self, owner: str) -> dict[str, int]:
        return self._reservations.pop(owner, {})

    def utilization(self, resource_type: str) -> float:
        capacity = self._capacity[resource_type]
        return self.used(resource_type) / capacity if capacity else 0.0
