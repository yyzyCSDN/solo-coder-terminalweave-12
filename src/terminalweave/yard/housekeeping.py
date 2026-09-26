from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class YardBox:
    container_id: str
    block: str
    stack: str
    tier: int
    departure_rank: int
    destination: str

@dataclass(frozen=True)
class HousekeepingSuggestion:
    container_id: str
    from_stack: str
    target_destination_group: str
    benefit: float

class HousekeepingAdvisor:

    def suggestions(self, boxes: list[YardBox], max_moves: int=10) -> list[HousekeepingSuggestion]:
        if max_moves < 0:
            raise ValidationError('max_moves cannot be negative')
        by_stack = {}
        for b in boxes:
            by_stack.setdefault((b.block, b.stack), []).append(b)
        out = []
        for (block, stack), items in by_stack.items():
            items = sorted(items, key=lambda x: x.tier)
            for lower, upper in zip(items, items[1:]):
                if upper.departure_rank > lower.departure_rank:
                    benefit = float(upper.departure_rank - lower.departure_rank)
                    same = sum((1 for x in items if x.destination == upper.destination))
                    out.append(HousekeepingSuggestion(upper.container_id, f'{block}/{stack}', upper.destination, benefit + same * 0.25))
        return sorted(out, key=lambda x: (-x.benefit, x.container_id))[:max_moves]
