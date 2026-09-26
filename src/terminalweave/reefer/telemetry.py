from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class TelemetryPoint:
    container_id: str
    at: datetime
    temperature_c: float
    return_air_c: float
    setpoint_c: float
    compressor_on: bool

    def __post_init__(self):
        object.__setattr__(self, 'at', ensure_utc(self.at))

class TelemetryBuffer:

    def __init__(self, retention: timedelta=timedelta(days=7)):
        if retention.total_seconds() <= 0:
            raise ValidationError('retention must be positive')
        self.retention = retention
        self.points: dict[str, list[TelemetryPoint]] = {}

    def ingest(self, point: TelemetryPoint) -> None:
        series = self.points.setdefault(point.container_id, [])
        if series and point.at <= series[-1].at:
            raise ValidationError('telemetry time must increase')
        series.append(point)
        cutoff = point.at - self.retention
        while series and series[0].at < cutoff:
            series.pop(0)

    def latest(self, container_id: str) -> TelemetryPoint | None:
        series = self.points.get(container_id, [])
        return series[-1] if series else None

    def mean_offset(self, container_id: str, window: timedelta) -> float:
        series = self.points.get(container_id, [])
        if not series:
            return 0.0
        cutoff = series[-1].at - window
        values = [p.temperature_c - p.setpoint_c for p in series if p.at >= cutoff]
        return sum(values) / len(values) if values else 0.0

    def compressor_duty(self, container_id: str, window: timedelta) -> float:
        series = self.points.get(container_id, [])
        if len(series) < 2:
            return 0.0
        cutoff = series[-1].at - window
        active = total = 0.0
        for a, b in zip(series, series[1:]):
            if b.at < cutoff:
                continue
            seconds = (b.at - max(a.at, cutoff)).total_seconds()
            total += max(seconds, 0)
            active += max(seconds, 0) if a.compressor_on else 0
        return active / total if total else 0.0
