from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable
from .clock import ensure_utc
from .errors import ValidationError

@dataclass(frozen=True, order=True)
class TimeInterval:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        start = ensure_utc(self.start)
        end = ensure_utc(self.end)
        if end <= start:
            raise ValidationError('interval end must be after start')
        object.__setattr__(self, 'start', start)
        object.__setattr__(self, 'end', end)

    @property
    def duration(self) -> timedelta:
        return self.end - self.start

    def overlaps(self, other: 'TimeInterval') -> bool:
        return self.start < other.end and other.start < self.end

    def touches(self, other: 'TimeInterval') -> bool:
        return self.end == other.start or other.end == self.start

    def contains(self, point: datetime) -> bool:
        p = ensure_utc(point)
        return self.start <= p < self.end

    def intersection(self, other: 'TimeInterval') -> 'TimeInterval | None':
        start = max(self.start, other.start)
        end = min(self.end, other.end)
        return TimeInterval(start, end) if start < end else None

def merge_intervals(values: Iterable[TimeInterval]) -> list[TimeInterval]:
    items = sorted(values, key=lambda x: (x.start, x.end))
    if not items:
        return []
    merged = [items[0]]
    for current in items[1:]:
        last = merged[-1]
        if last.overlaps(current) or last.touches(current):
            merged[-1] = TimeInterval(last.start, max(last.end, current.end))
        else:
            merged.append(current)
    return merged
