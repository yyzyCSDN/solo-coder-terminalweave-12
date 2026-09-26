from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.intervals import TimeInterval

@dataclass(frozen=True)
class ResourceUse:
    owner: str
    resource: str
    interval: TimeInterval
    quantity: int = 1

@dataclass(frozen=True)
class ResourceConflict:
    resource: str
    interval: TimeInterval
    owners: tuple[str, ...]
    excess: int

class ConflictDetector:

    def detect(self, uses: list[ResourceUse], capacities: dict[str, int]) -> list[ResourceConflict]:
        out = []
        for resource, capacity in capacities.items():
            relevant = [u for u in uses if u.resource == resource]
            points = sorted({p for u in relevant for p in (u.interval.start, u.interval.end)})
            for a, b in zip(points, points[1:]):
                if a >= b:
                    continue
                active = [u for u in relevant if u.interval.start < b and a < u.interval.end]
                total = sum((u.quantity for u in active))
                if total > capacity:
                    out.append(ResourceConflict(resource, TimeInterval(a, b), tuple(sorted((u.owner for u in active))), total - capacity))
        return out
