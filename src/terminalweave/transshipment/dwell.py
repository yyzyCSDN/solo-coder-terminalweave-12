from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class DwellRecord:
    container_id: str
    discharged_at: datetime
    loaded_at: datetime | None
    destination: str

    def __post_init__(self):
        object.__setattr__(self, 'discharged_at', ensure_utc(self.discharged_at))
        if self.loaded_at is not None:
            object.__setattr__(self, 'loaded_at', ensure_utc(self.loaded_at))
            if self.loaded_at < self.discharged_at:
                raise ValidationError('load time precedes discharge')

class DwellAnalyzer:

    def duration(self, r: DwellRecord, now: datetime) -> timedelta:
        now = ensure_utc(now)
        end = r.loaded_at or now
        if end < r.discharged_at:
            raise ValidationError('analysis time precedes discharge')
        return end - r.discharged_at

    def overdue(self, records: list[DwellRecord], now: datetime, limit: timedelta) -> list[DwellRecord]:
        if limit.total_seconds() < 0:
            raise ValidationError('limit cannot be negative')
        return sorted((r for r in records if self.duration(r, now) > limit), key=lambda r: (-self.duration(r, now).total_seconds(), r.container_id))

    def average_hours(self, records: list[DwellRecord], now: datetime) -> float:
        return sum((self.duration(r, now).total_seconds() for r in records)) / 3600 / len(records) if records else 0.0
