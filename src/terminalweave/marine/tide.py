from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from bisect import bisect_right
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError, SafetyConstraintError
from terminalweave.core.intervals import TimeInterval, merge_intervals

@dataclass(frozen=True, order=True)
class TideSample:
    at: datetime
    height_m: float

    def __post_init__(self) -> None:
        object.__setattr__(self, 'at', ensure_utc(self.at))
        if not -8.0 <= self.height_m <= 15.0:
            raise ValidationError('tide height outside supported range')

@dataclass(frozen=True)
class UnderKeelRequirement:
    chart_depth_m: float
    vessel_draft_m: float
    minimum_clearance_m: float
    squat_allowance_m: float = 0.0
    wave_allowance_m: float = 0.0

    def __post_init__(self) -> None:
        if self.chart_depth_m <= 0 or self.vessel_draft_m <= 0:
            raise ValidationError('depth and draft must be positive')
        if min(self.minimum_clearance_m, self.squat_allowance_m, self.wave_allowance_m) < 0:
            raise ValidationError('allowances cannot be negative')

    @property
    def required_water_depth_m(self) -> float:
        return self.vessel_draft_m + self.minimum_clearance_m + self.squat_allowance_m + self.wave_allowance_m

class TideCurve:

    def __init__(self, samples: list[TideSample]):
        ordered = sorted(samples, key=lambda s: s.at)
        if len(ordered) < 2:
            raise ValidationError('at least two tide samples are required')
        if any((a.at == b.at for a, b in zip(ordered, ordered[1:]))):
            raise ValidationError('duplicate tide sample times are not allowed')
        self._samples = tuple(ordered)
        self._times = tuple((s.at for s in ordered))

    @property
    def start(self) -> datetime:
        return self._samples[0].at

    @property
    def end(self) -> datetime:
        return self._samples[-1].at

    def height_at(self, at: datetime) -> float:
        point = ensure_utc(at)
        if point < self.start or point > self.end:
            raise SafetyConstraintError('tide curve does not cover requested time')
        idx = bisect_right(self._times, point)
        if idx == 0:
            return self._samples[0].height_m
        if idx >= len(self._samples):
            return self._samples[-1].height_m
        left = self._samples[idx - 1]
        right = self._samples[idx]
        if point == left.at:
            return left.height_m
        span = (right.at - left.at).total_seconds()
        fraction = (point - left.at).total_seconds() / span
        return left.height_m + (right.height_m - left.height_m) * fraction

    def available_depth_m(self, at: datetime, chart_depth_m: float) -> float:
        if chart_depth_m <= 0:
            raise ValidationError('chart depth must be positive')
        return chart_depth_m + self.height_at(at)

    def clearance_m(self, at: datetime, requirement: UnderKeelRequirement) -> float:
        return self.available_depth_m(at, requirement.chart_depth_m) - requirement.vessel_draft_m - requirement.squat_allowance_m - requirement.wave_allowance_m

    def is_safe(self, at: datetime, requirement: UnderKeelRequirement) -> bool:
        return self.clearance_m(at, requirement) >= requirement.minimum_clearance_m

    def safe_windows(self, requirement: UnderKeelRequirement, start: datetime, end: datetime, step: timedelta=timedelta(minutes=5)) -> list[TimeInterval]:
        start = ensure_utc(start)
        end = ensure_utc(end)
        if end <= start:
            raise ValidationError('window end must be after start')
        if step.total_seconds() <= 0:
            raise ValidationError('step must be positive')
        if start < self.start or end > self.end:
            raise SafetyConstraintError('tide curve does not cover search window')
        safe_segments: list[TimeInterval] = []
        cursor = start
        open_start: datetime | None = None
        while cursor < end:
            safe = self.is_safe(cursor, requirement)
            if safe and open_start is None:
                open_start = cursor
            if not safe and open_start is not None:
                safe_segments.append(TimeInterval(open_start, cursor))
                open_start = None
            cursor = min(cursor + step, end)
        if open_start is not None:
            safe_segments.append(TimeInterval(open_start, end))
        return merge_intervals(safe_segments)

    def minimum_clearance(self, requirement: UnderKeelRequirement, interval: TimeInterval, step: timedelta=timedelta(minutes=2)) -> tuple[datetime, float]:
        if interval.start < self.start or interval.end > self.end:
            raise SafetyConstraintError('tide curve does not cover interval')
        point = interval.start
        best_at = point
        best = self.clearance_m(point, requirement)
        while point < interval.end:
            value = self.clearance_m(point, requirement)
            if value < best:
                best_at, best = (point, value)
            point = min(point + step, interval.end)
        value = self.clearance_m(interval.end, requirement)
        if value < best:
            best_at, best = (interval.end, value)
        return (best_at, best)
