from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError, SafetyConstraintError

@dataclass(frozen=True)
class MooringLine:
    line_id: str
    breaking_load_t: float
    pretension_t: float
    angle_deg: float
    condition_factor: float = 1.0

    def __post_init__(self):
        if self.breaking_load_t <= 0 or self.pretension_t < 0:
            raise ValidationError('invalid mooring line')
        if not 0 < self.condition_factor <= 1:
            raise ValidationError('condition factor must be 0..1')
        if not -180 <= self.angle_deg <= 180:
            raise ValidationError('angle outside range')

    @property
    def effective_breaking_load_t(self):
        return self.breaking_load_t * self.condition_factor

@dataclass(frozen=True)
class MooringRequirement:
    minimum_lines: int
    maximum_utilization: float
    minimum_total_effective_load_t: float

    def __post_init__(self):
        if self.minimum_lines < 1 or not 0 < self.maximum_utilization < 1 or self.minimum_total_effective_load_t <= 0:
            raise ValidationError('invalid mooring requirement')

class MooringChecker:

    def evaluate(self, lines: list[MooringLine], requirement: MooringRequirement) -> dict[str, object]:
        if len(lines) < requirement.minimum_lines:
            raise SafetyConstraintError('insufficient mooring lines')
        total = sum((x.effective_breaking_load_t for x in lines))
        if total < requirement.minimum_total_effective_load_t:
            raise SafetyConstraintError('insufficient effective mooring strength')
        overload = [x.line_id for x in lines if x.effective_breaking_load_t and x.pretension_t / x.effective_breaking_load_t > requirement.maximum_utilization]
        if overload:
            raise SafetyConstraintError('mooring line utilization exceeded: ' + ','.join(sorted(overload)))
        average = sum((x.pretension_t for x in lines)) / len(lines)
        spread = max((x.pretension_t for x in lines)) - min((x.pretension_t for x in lines))
        return {'lines': len(lines), 'total_effective_breaking_load_t': total, 'average_pretension_t': average, 'pretension_spread_t': spread}

    def weakest(self, lines: list[MooringLine]) -> MooringLine | None:
        return min(lines, key=lambda x: (x.effective_breaking_load_t, x.line_id)) if lines else None
