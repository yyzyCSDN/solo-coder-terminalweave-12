from __future__ import annotations
from dataclasses import dataclass
from statistics import mean
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class DemandPoint:
    period: int
    vessel_calls: float
    gate_moves: float
    rail_teu: float
    yard_teu: float

    def __post_init__(self):
        if self.period < 0 or min(self.vessel_calls, self.gate_moves, self.rail_teu, self.yard_teu) < 0:
            raise ValidationError('invalid demand point')

@dataclass(frozen=True)
class DemandForecast:
    period: int
    vessel_calls: float
    gate_moves: float
    rail_teu: float
    yard_teu: float

class MovingAverageForecaster:

    def __init__(self, window: int=4, growth_cap: float=0.35):
        if window < 1 or growth_cap < 0:
            raise ValidationError('invalid forecast settings')
        self.window = window
        self.growth_cap = growth_cap

    def _project(self, values: list[float]) -> float:
        if not values:
            return 0.0
        recent = values[-self.window:]
        baseline = mean(recent)
        if len(recent) < 2:
            return baseline
        first = max(recent[0], 1e-09)
        growth = (recent[-1] - recent[0]) / first / max(1, len(recent) - 1)
        growth = max(-self.growth_cap, min(self.growth_cap, growth))
        return max(0.0, baseline * (1 + growth))

    def forecast(self, history: list[DemandPoint], next_period: int) -> DemandForecast:
        if not history:
            raise ValidationError('history required')
        ordered = sorted(history, key=lambda x: x.period)
        if next_period <= ordered[-1].period:
            raise ValidationError('forecast period must be in the future')
        return DemandForecast(next_period, self._project([x.vessel_calls for x in ordered]), self._project([x.gate_moves for x in ordered]), self._project([x.rail_teu for x in ordered]), self._project([x.yard_teu for x in ordered]))

    def backtest_mae(self, history: list[DemandPoint], field: str) -> float:
        if field not in {'vessel_calls', 'gate_moves', 'rail_teu', 'yard_teu'}:
            raise ValidationError('unsupported field')
        ordered = sorted(history, key=lambda x: x.period)
        errors = []
        for i in range(self.window, len(ordered)):
            actual = getattr(ordered[i], field)
            prediction = self._project([getattr(x, field) for x in ordered[:i]])
            errors.append(abs(actual - prediction))
        return mean(errors) if errors else 0.0
