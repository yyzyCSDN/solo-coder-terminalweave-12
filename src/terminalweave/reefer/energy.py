from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class MeterSample:
    container_id: str
    at: datetime
    cumulative_kwh: float

    def __post_init__(self):
        object.__setattr__(self, 'at', ensure_utc(self.at))
        if self.cumulative_kwh < 0:
            raise ValidationError('meter cannot be negative')

class ReeferEnergyBook:

    def __init__(self):
        self.samples: dict[str, list[MeterSample]] = {}

    def ingest(self, s: MeterSample) -> None:
        series = self.samples.setdefault(s.container_id, [])
        if series:
            last = series[-1]
            if s.at <= last.at:
                raise ValidationError('meter time must increase')
            if s.cumulative_kwh < last.cumulative_kwh:
                raise ValidationError('cumulative energy cannot decrease')
        series.append(s)

    def consumed_kwh(self, container_id: str) -> float:
        series = self.samples.get(container_id, [])
        return series[-1].cumulative_kwh - series[0].cumulative_kwh if len(series) >= 2 else 0.0

    def average_kw(self, container_id: str) -> float:
        series = self.samples.get(container_id, [])
        if len(series) < 2:
            return 0.0
        hours = (series[-1].at - series[0].at).total_seconds() / 3600
        return self.consumed_kwh(container_id) / hours if hours else 0.0

    def top_consumers(self, limit: int=10) -> list[tuple[str, float]]:
        if limit < 0:
            raise ValidationError('limit cannot be negative')
        values = [(cid, self.consumed_kwh(cid)) for cid in self.samples]
        return sorted(values, key=lambda x: (-x[1], x[0]))[:limit]
