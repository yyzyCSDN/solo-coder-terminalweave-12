from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from terminalweave.core.errors import ValidationError, CapacityError, ConflictError

class ContainerSize(str, Enum):
    FT20 = '20'
    FT40 = '40'

@dataclass(frozen=True)
class YardSlot:
    block: str
    bay: int
    row: int
    tier: int
    max_weight_kg: float
    reefer_plug: bool = False
    reserved: bool = False

    def __post_init__(self) -> None:
        if self.bay < 1 or self.row < 1 or self.tier < 1 or (self.max_weight_kg <= 0):
            raise ValidationError('invalid yard slot')

    @property
    def key(self) -> tuple[str, int, int, int]:
        return (self.block, self.bay, self.row, self.tier)

@dataclass(frozen=True)
class YardContainer:
    container_id: str
    size: ContainerSize
    gross_weight_kg: float
    destination: str
    reefer: bool = False
    hazardous: bool = False
    discharge_sequence: int = 0

    def __post_init__(self) -> None:
        if self.gross_weight_kg <= 0:
            raise ValidationError('gross weight must be positive')

class YardInventory:

    def __init__(self, slots: list[YardSlot], max_stack_weight_kg: float=120000.0):
        if not slots:
            raise ValidationError('at least one slot is required')
        if max_stack_weight_kg <= 0:
            raise ValidationError('max stack weight must be positive')
        if len({s.key for s in slots}) != len(slots):
            raise ValidationError('duplicate yard slot')
        self.slots = {s.key: s for s in slots}
        self.max_stack_weight_kg = max_stack_weight_kg
        self.contents: dict[tuple[str, int, int, int], YardContainer] = {}

    def _stack_keys(self, slot: YardSlot) -> list[tuple[str, int, int, int]]:
        return sorted([k for k in self.slots if k[:3] == slot.key[:3]], key=lambda k: k[3])

    def _weight_below_or_at(self, slot: YardSlot, candidate_weight: float) -> float:
        total = candidate_weight
        for key, container in self.contents.items():
            if key[:3] == slot.key[:3] and key[3] <= slot.tier:
                total += container.gross_weight_kg
        return total

    def can_place(self, container: YardContainer, slot: YardSlot) -> bool:
        if slot.key in self.contents or slot.reserved:
            return False
        if container.gross_weight_kg > slot.max_weight_kg:
            return False
        if container.reefer and (not slot.reefer_plug):
            return False
        if slot.tier > 1:
            below = (slot.block, slot.bay, slot.row, slot.tier - 1)
            if below not in self.contents:
                return False
        if self._weight_below_or_at(slot, container.gross_weight_kg) > self.max_stack_weight_kg:
            return False
        return True

    def place(self, container: YardContainer, slot_key: tuple[str, int, int, int]) -> None:
        if container.container_id in {c.container_id for c in self.contents.values()}:
            raise ConflictError('container already in yard')
        slot = self.slots.get(slot_key)
        if slot is None:
            raise ValidationError('unknown yard slot')
        if not self.can_place(container, slot):
            raise CapacityError('container cannot be placed in requested slot')
        self.contents[slot.key] = container

    def remove(self, container_id: str) -> YardContainer:
        key = next((k for k, c in self.contents.items() if c.container_id == container_id), None)
        if key is None:
            raise ValidationError('container not found')
        block, bay, row, tier = key
        above = [k for k in self.contents if k[:3] == (block, bay, row) and k[3] > tier]
        if above:
            raise ConflictError('container is blocked by higher tiers')
        return self.contents.pop(key)

    def recommend_slot(self, container: YardContainer) -> YardSlot:
        candidates = [s for s in self.slots.values() if self.can_place(container, s)]
        if not candidates:
            raise CapacityError('no compatible yard slot')

        def score(slot: YardSlot) -> tuple[int, int, int, str, int, int]:
            same_destination = sum((1 for k, c in self.contents.items() if k[:3] == slot.key[:3] and c.destination == container.destination))
            hazardous_penalty = 1 if container.hazardous and any((c.hazardous for k, c in self.contents.items() if k[:3] == slot.key[:3])) else 0
            return (-same_destination, hazardous_penalty, slot.tier, slot.block, slot.bay, slot.row)
        return min(candidates, key=score)

    def move(self, container_id: str, to_key: tuple[str, int, int, int]) -> None:
        original_key = next((k for k, c in self.contents.items() if c.container_id == container_id), None)
        if original_key is None:
            raise ValidationError('container not found')
        container = self.contents[original_key]
        if original_key == to_key:
            return
        block, bay, row, tier = original_key
        if any((k[:3] == (block, bay, row) and k[3] > tier for k in self.contents)):
            raise ConflictError('container is blocked')
        del self.contents[original_key]
        try:
            self.place(container, to_key)
        except Exception:
            self.contents[original_key] = container
            raise

    def occupancy_ratio(self) -> float:
        return len(self.contents) / len(self.slots)
