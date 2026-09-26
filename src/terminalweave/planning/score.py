from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class ScenarioMetrics:
    vessel_delay_minutes: float
    truck_wait_minutes: float
    rehandles: int
    energy_kwh: float
    missed_connections: int
    safety_violations: int

@dataclass(frozen=True)
class ScoreWeights:
    vessel_delay: float = 1.0
    truck_wait: float = 0.5
    rehandle: float = 2.0
    energy: float = 0.01
    missed_connection: float = 50.0
    safety_violation: float = 10000.0

    def __post_init__(self):
        if min(self.vessel_delay, self.truck_wait, self.rehandle, self.energy, self.missed_connection, self.safety_violation) < 0:
            raise ValidationError('score weights cannot be negative')

class ScenarioScorer:

    def __init__(self, weights: ScoreWeights | None=None):
        self.weights = weights or ScoreWeights()

    def score(self, m: ScenarioMetrics) -> float:
        w = self.weights
        return m.vessel_delay_minutes * w.vessel_delay + m.truck_wait_minutes * w.truck_wait + m.rehandles * w.rehandle + m.energy_kwh * w.energy + m.missed_connections * w.missed_connection + m.safety_violations * w.safety_violation

    def compare(self, a: ScenarioMetrics, b: ScenarioMetrics) -> dict[str, object]:
        sa = self.score(a)
        sb = self.score(b)
        return {'a': sa, 'b': sb, 'delta': sb - sa, 'preferred': 'a' if sa < sb else 'b' if sb < sa else 'tie'}
