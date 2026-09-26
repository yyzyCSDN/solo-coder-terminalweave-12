from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError, ConflictError

@dataclass(frozen=True)
class StackItem:
    container_id: str
    priority: int
    departure_order: int

@dataclass(frozen=True)
class ReshuffleMove:
    container_id: str
    from_stack: str
    to_stack: str
    reason: str

class ReshufflePlanner:

    def __init__(self, stacks: dict[str, list[StackItem]], max_height: int):
        if max_height < 1:
            raise ValidationError('max height must be positive')
        self.stacks = {k: list(v) for k, v in stacks.items()}
        self.max_height = max_height
        if any((len(v) > max_height for v in self.stacks.values())):
            raise ValidationError('initial stack exceeds max height')
        ids = [i.container_id for values in self.stacks.values() for i in values]
        if len(ids) != len(set(ids)):
            raise ValidationError('duplicate container in stacks')

    def blockers(self, container_id: str) -> list[StackItem]:
        for items in self.stacks.values():
            for idx, item in enumerate(items):
                if item.container_id == container_id:
                    return items[idx + 1:]
        raise ValidationError('container not found')

    def _best_destination(self, source: str, item: StackItem) -> str:
        candidates = []
        for name, items in self.stacks.items():
            if name == source or len(items) >= self.max_height:
                continue
            if items:
                top = items[-1]
                inversion = 1 if top.departure_order < item.departure_order else 0
                gap = abs(top.departure_order - item.departure_order)
            else:
                inversion = 0
                gap = 0
            candidates.append((inversion, gap, len(items), name))
        if not candidates:
            raise ConflictError('no temporary stack capacity')
        return min(candidates)[3]

    def expose(self, container_id: str) -> list[ReshuffleMove]:
        source = None
        index = None
        for name, items in self.stacks.items():
            for i, item in enumerate(items):
                if item.container_id == container_id:
                    source = name
                    index = i
                    break
            if source:
                break
        if source is None or index is None:
            raise ValidationError('container not found')
        moves = []
        while len(self.stacks[source]) - 1 > index:
            item = self.stacks[source].pop()
            target = self._best_destination(source, item)
            self.stacks[target].append(item)
            moves.append(ReshuffleMove(item.container_id, source, target, 'unblock target'))
        return moves

    def disorder_score(self) -> int:
        score = 0
        for items in self.stacks.values():
            for lower, upper in zip(items, items[1:]):
                if upper.departure_order > lower.departure_order:
                    score += 1
        return score
