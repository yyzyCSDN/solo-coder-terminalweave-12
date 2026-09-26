from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class ThroughputEvent:
    at: datetime
    kind: str
    teu: int
    direction: str

    def __post_init__(self):
        object.__setattr__(self, 'at', ensure_utc(self.at))
        if self.teu <= 0:
            raise ValidationError('TEU must be positive')

class ThroughputSeries:

    def __init__(self, events: list[ThroughputEvent]):
        self.events = sorted(events, key=lambda x: x.at)

    def between(self, start: datetime, end: datetime) -> list[ThroughputEvent]:
        start = ensure_utc(start)
        end = ensure_utc(end)
        if end < start:
            raise ValidationError('invalid range')
        return [e for e in self.events if start <= e.at < end]

    def total_teu(self, start: datetime, end: datetime, direction: str | None=None) -> int:
        return sum((e.teu for e in self.between(start, end) if direction is None or e.direction == direction))

    def rolling(self, end: datetime, window: timedelta) -> dict[str, int]:
        end = ensure_utc(end)
        start = end - window
        out = {}
        for e in self.between(start, end):
            out[e.kind] = out.get(e.kind, 0) + e.teu
        return out
