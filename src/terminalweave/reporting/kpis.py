from __future__ import annotations
from dataclasses import dataclass
from statistics import mean, median
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class VesselPerformance:
    call_id: str
    berth_delay_minutes: float
    berth_hours: float
    moves: int

@dataclass(frozen=True)
class GatePerformance:
    truck_id: str
    wait_minutes: float
    turn_minutes: float

class KpiBook:

    def vessel(self, rows: list[VesselPerformance]) -> dict[str, float]:
        if not rows:
            return {'calls': 0.0, 'avg_delay_minutes': 0.0, 'gross_moves_per_hour': 0.0}
        hours = sum((r.berth_hours for r in rows))
        moves = sum((r.moves for r in rows))
        return {'calls': float(len(rows)), 'avg_delay_minutes': mean((r.berth_delay_minutes for r in rows)), 'median_delay_minutes': median((r.berth_delay_minutes for r in rows)), 'gross_moves_per_hour': moves / hours if hours else 0.0}

    def gate(self, rows: list[GatePerformance]) -> dict[str, float]:
        if not rows:
            return {'trucks': 0.0, 'avg_wait_minutes': 0.0, 'avg_turn_minutes': 0.0}
        return {'trucks': float(len(rows)), 'avg_wait_minutes': mean((r.wait_minutes for r in rows)), 'median_wait_minutes': median((r.wait_minutes for r in rows)), 'avg_turn_minutes': mean((r.turn_minutes for r in rows))}

    def percentile(self, values: list[float], p: float) -> float:
        if not 0 <= p <= 100:
            raise ValidationError('percentile must be 0..100')
        if not values:
            return 0.0
        data = sorted(values)
        pos = (len(data) - 1) * p / 100
        lo = int(pos)
        hi = min(lo + 1, len(data) - 1)
        frac = pos - lo
        return data[lo] * (1 - frac) + data[hi] * frac
