from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError, CapacityError

@dataclass(frozen=True)
class TruckArrival:
    truck_id: str
    arrived_at: datetime
    service_seconds: int
    priority: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, 'arrived_at', ensure_utc(self.arrived_at))
        if self.service_seconds <= 0:
            raise ValidationError('service time must be positive')

@dataclass(frozen=True)
class Lane:
    lane_id: str
    opens_at: datetime
    closes_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, 'opens_at', ensure_utc(self.opens_at))
        object.__setattr__(self, 'closes_at', ensure_utc(self.closes_at))
        if self.closes_at <= self.opens_at:
            raise ValidationError('lane close must follow open')

@dataclass(frozen=True)
class QueueService:
    truck_id: str
    lane_id: str
    start: datetime
    finish: datetime
    wait_seconds: float

class GateQueueSimulator:

    def __init__(self, lanes: list[Lane]):
        if not lanes:
            raise ValidationError('at least one lane is required')
        self.lanes = lanes

    def simulate(self, arrivals: list[TruckArrival]) -> list[QueueService]:
        available = {l.lane_id: l.opens_at for l in self.lanes}
        result = []
        for truck in sorted(arrivals, key=lambda t: (t.arrived_at, -t.priority, t.truck_id)):
            options = []
            for lane in self.lanes:
                start = max(truck.arrived_at, available[lane.lane_id], lane.opens_at)
                finish = start + timedelta(seconds=truck.service_seconds)
                if finish <= lane.closes_at:
                    options.append((finish, start, lane))
            if not options:
                raise CapacityError(f'no lane can serve {truck.truck_id}')
            finish, start, lane = min(options, key=lambda x: (x[0], x[2].lane_id))
            available[lane.lane_id] = finish
            result.append(QueueService(truck.truck_id, lane.lane_id, start, finish, (start - truck.arrived_at).total_seconds()))
        return result

    @staticmethod
    def percentile_wait(services: list[QueueService], percentile: float) -> float:
        if not 0 <= percentile <= 100:
            raise ValidationError('percentile must be 0..100')
        if not services:
            return 0.0
        values = sorted((s.wait_seconds for s in services))
        idx = (len(values) - 1) * percentile / 100
        lo = int(idx)
        hi = min(lo + 1, len(values) - 1)
        frac = idx - lo
        return values[lo] * (1 - frac) + values[hi] * frac
