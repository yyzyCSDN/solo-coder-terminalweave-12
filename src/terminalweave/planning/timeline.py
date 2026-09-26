from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from terminalweave.core.errors import ValidationError, ConflictError
from terminalweave.core.intervals import TimeInterval

@dataclass(frozen=True)
class TimelineItem:
    item_id: str
    kind: str
    interval: TimeInterval
    resource: str | None = None
    predecessors: frozenset[str] = frozenset()

class Timeline:

    def __init__(self, items: list[TimelineItem] | None=None):
        self.items = {x.item_id: x for x in items or []}

    def add(self, item: TimelineItem) -> None:
        if item.item_id in self.items:
            raise ValidationError('duplicate timeline item')
        unknown = item.predecessors - set(self.items)
        if unknown:
            raise ValidationError(f'unknown predecessors: {sorted(unknown)}')
        for pred_id in item.predecessors:
            if self.items[pred_id].interval.end > item.interval.start:
                raise ConflictError('predecessor finishes after item starts')
        self.items[item.item_id] = item

    def resource_conflicts(self) -> list[tuple[str, str]]:
        values = list(self.items.values())
        out = []
        for i, a in enumerate(values):
            if not a.resource:
                continue
            for b in values[i + 1:]:
                if a.resource == b.resource and a.interval.overlaps(b.interval):
                    out.append((a.item_id, b.item_id))
        return out

    def critical_end(self) -> datetime | None:
        return max((x.interval.end for x in self.items.values()), default=None)

    def shift(self, item_id: str, delta: timedelta) -> TimelineItem:
        item = self.items[item_id]
        moved = TimelineItem(item.item_id, item.kind, TimeInterval(item.interval.start + delta, item.interval.end + delta), item.resource, item.predecessors)
        return moved
