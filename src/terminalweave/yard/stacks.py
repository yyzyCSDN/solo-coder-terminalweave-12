from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError, CapacityError, ConflictError

@dataclass(frozen=True)
class StackRule:
    max_tier: int
    max_total_weight_kg: float
    allow_overweight_above: bool = False

    def __post_init__(self):
        if self.max_tier < 1 or self.max_total_weight_kg <= 0:
            raise ValidationError('invalid stack rule')

@dataclass(frozen=True)
class StackContainer:
    container_id: str
    weight_kg: float
    oversize: bool = False

class PhysicalStack:

    def __init__(self, stack_id: str, rule: StackRule):
        self.stack_id = stack_id
        self.rule = rule
        self.items: list[StackContainer] = []

    def can_push(self, item: StackContainer) -> bool:
        if len(self.items) >= self.rule.max_tier:
            return False
        if sum((x.weight_kg for x in self.items)) + item.weight_kg > self.rule.max_total_weight_kg:
            return False
        if item.oversize and self.items:
            return False
        if self.items and self.items[-1].oversize:
            return False
        if not self.rule.allow_overweight_above and self.items and (item.weight_kg > self.items[-1].weight_kg):
            return False
        return True

    def push(self, item: StackContainer) -> None:
        if not self.can_push(item):
            raise CapacityError('stack rule rejects container')
        self.items.append(item)

    def pop(self) -> StackContainer:
        if not self.items:
            raise ConflictError('stack is empty')
        return self.items.pop()

    def find(self, container_id: str) -> int | None:
        for tier, item in enumerate(self.items, start=1):
            if item.container_id == container_id:
                return tier
        return None

    def blocked_count(self, container_id: str) -> int:
        tier = self.find(container_id)
        if tier is None:
            raise ValidationError('container not in stack')
        return len(self.items) - tier
