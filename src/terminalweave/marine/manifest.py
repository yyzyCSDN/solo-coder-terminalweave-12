from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError, ConflictError

@dataclass(frozen=True)
class VesselManifestContainer:
    container_id: str
    bay: int
    row: int
    tier: int
    weight_kg: float
    destination: str
    reefer: bool = False
    hazardous: bool = False

    def __post_init__(self):
        if self.bay < 1 or self.row < 0 or self.tier < 0 or (self.weight_kg <= 0):
            raise ValidationError('invalid stow position')

    @property
    def position(self):
        return (self.bay, self.row, self.tier)

class VesselManifest:

    def __init__(self, call_id: str):
        self.call_id = call_id
        self.items: dict[str, VesselManifestContainer] = {}
        self.positions: dict[tuple[int, int, int], str] = {}

    def add(self, item: VesselManifestContainer) -> None:
        if item.container_id in self.items:
            raise ConflictError('container already manifested')
        if item.position in self.positions:
            raise ConflictError('stow position already occupied')
        self.items[item.container_id] = item
        self.positions[item.position] = item.container_id

    def remove(self, container_id: str) -> VesselManifestContainer:
        item = self.items.pop(container_id)
        self.positions.pop(item.position, None)
        return item

    def by_destination(self, destination: str) -> tuple[VesselManifestContainer, ...]:
        return tuple(sorted((x for x in self.items.values() if x.destination == destination), key=lambda x: x.position))

    def total_weight_kg(self) -> float:
        return sum((x.weight_kg for x in self.items.values()))

    def reefer_count(self) -> int:
        return sum((x.reefer for x in self.items.values()))

    def hazardous_count(self) -> int:
        return sum((x.hazardous for x in self.items.values()))

    def bays(self) -> dict[int, list[VesselManifestContainer]]:
        out = {}
        for item in self.items.values():
            out.setdefault(item.bay, []).append(item)
        for values in out.values():
            values.sort(key=lambda x: (x.row, x.tier))
        return out
