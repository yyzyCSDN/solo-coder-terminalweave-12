from __future__ import annotations
from dataclasses import dataclass
from statistics import median
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class MoveObservation:
    crane_id: str
    cycle_seconds: float
    hatch: str
    twin_lift: bool = False
    delay_code: str | None = None

    def __post_init__(self) -> None:
        if self.cycle_seconds <= 0:
            raise ValidationError('cycle time must be positive')

@dataclass(frozen=True)
class ProductivitySummary:
    crane_id: str
    moves: int
    productive_moves: int
    median_cycle_seconds: float
    gross_moves_per_hour: float
    productive_moves_per_hour: float
    twin_lift_ratio: float

class ProductivityAnalyzer:

    def summarize(self, observations: list[MoveObservation]) -> list[ProductivitySummary]:
        grouped: dict[str, list[MoveObservation]] = {}
        for obs in observations:
            grouped.setdefault(obs.crane_id, []).append(obs)
        result = []
        for crane_id, items in sorted(grouped.items()):
            seconds = sum((i.cycle_seconds for i in items))
            productive = [i for i in items if not i.delay_code]
            productive_seconds = sum((i.cycle_seconds for i in productive))
            result.append(ProductivitySummary(crane_id, len(items), len(productive), median((i.cycle_seconds for i in items)), len(items) * 3600 / seconds if seconds else 0.0, len(productive) * 3600 / productive_seconds if productive_seconds else 0.0, sum((i.twin_lift for i in items)) / len(items)))
        return result

    def delay_breakdown(self, observations: list[MoveObservation]) -> dict[str, float]:
        totals: dict[str, float] = {}
        for obs in observations:
            if obs.delay_code:
                totals[obs.delay_code] = totals.get(obs.delay_code, 0.0) + obs.cycle_seconds
        total = sum(totals.values())
        return {k: v / total for k, v in sorted(totals.items())} if total else {}

    def outliers(self, observations: list[MoveObservation], factor: float=2.5) -> list[MoveObservation]:
        if factor <= 0:
            raise ValidationError('factor must be positive')
        if not observations:
            return []
        baseline = median((i.cycle_seconds for i in observations))
        return [i for i in observations if i.cycle_seconds > baseline * factor]
