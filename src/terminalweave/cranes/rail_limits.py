from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError, ConflictError

@dataclass(frozen=True)
class RailSegment:
    start_m: float
    end_m: float
    max_wheel_load_t: float
    closed: bool = False

    def __post_init__(self):
        if self.end_m <= self.start_m or self.max_wheel_load_t <= 0:
            raise ValidationError('invalid rail segment')

@dataclass(frozen=True)
class CranePosition:
    crane_id: str
    center_m: float
    wheel_load_t: float
    footprint_m: float

class CraneRailAuthority:

    def __init__(self, segments: list[RailSegment]):
        self.segments = sorted(segments, key=lambda s: s.start_m)

    def validate(self, pos: CranePosition) -> None:
        left = pos.center_m - pos.footprint_m / 2
        right = pos.center_m + pos.footprint_m / 2
        covered = [s for s in self.segments if s.start_m < right and left < s.end_m]
        if not covered:
            raise ConflictError('crane is outside configured rail')
        if any((s.closed for s in covered)):
            raise ConflictError('crane footprint intersects closed rail')
        if any((pos.wheel_load_t > s.max_wheel_load_t for s in covered)):
            raise ConflictError('wheel load exceeds rail limit')

    def permitted_range(self, wheel_load_t: float, footprint_m: float, step_m: float=1.0) -> list[float]:
        if step_m <= 0:
            raise ValidationError('step must be positive')
        if not self.segments:
            return []
        start = min((s.start_m for s in self.segments)) + footprint_m / 2
        end = max((s.end_m for s in self.segments)) - footprint_m / 2
        out = []
        x = start
        while x <= end:
            try:
                self.validate(CranePosition('probe', x, wheel_load_t, footprint_m))
                out.append(round(x, 6))
            except ConflictError:
                pass
            x += step_m
        return out
