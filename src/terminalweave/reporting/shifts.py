from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class ShiftActivity:
    operator_id: str
    start: datetime
    end: datetime
    activity: str
    moves: int = 0

    def __post_init__(self):
        object.__setattr__(self, 'start', ensure_utc(self.start))
        object.__setattr__(self, 'end', ensure_utc(self.end))
        if self.end <= self.start or self.moves < 0:
            raise ValidationError('invalid shift activity')

class ShiftReport:

    def summarize(self, activities: list[ShiftActivity]) -> dict[str, dict[str, float]]:
        out = {}
        for a in activities:
            row = out.setdefault(a.operator_id, {'hours': 0.0, 'productive_hours': 0.0, 'moves': 0.0})
            hours = (a.end - a.start).total_seconds() / 3600
            row['hours'] += hours
            row['moves'] += a.moves
            if a.activity in {'crane', 'yard_move', 'gate_service', 'rail_service'}:
                row['productive_hours'] += hours
        for row in out.values():
            row['moves_per_productive_hour'] = row['moves'] / row['productive_hours'] if row['productive_hours'] else 0.0
        return out

    def excessive_shifts(self, activities: list[ShiftActivity], limit: timedelta=timedelta(hours=12)) -> list[str]:
        summary = self.summarize(activities)
        limit_hours = limit.total_seconds() / 3600
        return sorted((operator for operator, row in summary.items() if row['hours'] > limit_hours))
