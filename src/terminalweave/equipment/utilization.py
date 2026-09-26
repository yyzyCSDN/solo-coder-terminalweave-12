from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class ActivitySpan:
    equipment_id: str
    start: datetime
    end: datetime
    activity: str
    productive: bool

    def __post_init__(self):
        object.__setattr__(self, 'start', ensure_utc(self.start))
        object.__setattr__(self, 'end', ensure_utc(self.end))
        if self.end <= self.start:
            raise ValidationError('activity span is empty')

class UtilizationAnalyzer:

    def summarize(self, spans: list[ActivitySpan], equipment_id: str) -> dict[str, float]:
        rows = [s for s in spans if s.equipment_id == equipment_id]
        total = sum(((s.end - s.start).total_seconds() for s in rows))
        productive = sum(((s.end - s.start).total_seconds() for s in rows if s.productive))
        idle = sum(((s.end - s.start).total_seconds() for s in rows if s.activity == 'idle'))
        maintenance = sum(((s.end - s.start).total_seconds() for s in rows if s.activity == 'maintenance'))
        return {'total_hours': total / 3600, 'productive_hours': productive / 3600, 'idle_hours': idle / 3600, 'maintenance_hours': maintenance / 3600, 'productive_ratio': productive / total if total else 0.0}

    def overlaps(self, spans: list[ActivitySpan], equipment_id: str) -> list[tuple[str, str]]:
        rows = sorted((s for s in spans if s.equipment_id == equipment_id), key=lambda s: s.start)
        out = []
        for i, a in enumerate(rows):
            for b in rows[i + 1:]:
                if b.start >= a.end:
                    break
                if a.start < b.end and b.start < a.end:
                    out.append((a.activity, b.activity))
        return out
