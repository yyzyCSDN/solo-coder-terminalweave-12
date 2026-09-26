from __future__ import annotations
from dataclasses import dataclass
from terminalweave.planning.score import ScenarioMetrics, ScenarioScorer
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class WhatIfChange:
    field: str
    delta: float

class WhatIfEngine:
    allowed = {'vessel_delay_minutes', 'truck_wait_minutes', 'rehandles', 'energy_kwh', 'missed_connections', 'safety_violations'}

    def apply(self, base: ScenarioMetrics, changes: list[WhatIfChange]) -> ScenarioMetrics:
        values = base.__dict__.copy()
        for c in changes:
            if c.field not in self.allowed:
                raise ValidationError(f'unsupported metric {c.field}')
            values[c.field] = values[c.field] + c.delta
            if values[c.field] < 0:
                raise ValidationError('what-if metric cannot become negative')
            if c.field in {'rehandles', 'missed_connections', 'safety_violations'}:
                values[c.field] = int(round(values[c.field]))
        return ScenarioMetrics(**values)

    def evaluate(self, base: ScenarioMetrics, changes: list[WhatIfChange], scorer: ScenarioScorer | None=None) -> dict[str, object]:
        scorer = scorer or ScenarioScorer()
        candidate = self.apply(base, changes)
        return {'base_score': scorer.score(base), 'candidate_score': scorer.score(candidate), 'metrics': candidate}
