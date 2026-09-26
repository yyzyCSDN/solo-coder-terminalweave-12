from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError, SafetyConstraintError

@dataclass(frozen=True)
class LiftPlan:
    container_id: str
    gross_weight_t: float
    outreach_m: float
    wind_kn: float
    twin_lift: bool = False

@dataclass(frozen=True)
class CraneEnvelope:
    max_weight_t: float
    max_outreach_m: float
    max_wind_kn: float
    twin_lift_max_weight_t: float

    def __post_init__(self):
        if min(self.max_weight_t, self.max_outreach_m, self.max_wind_kn, self.twin_lift_max_weight_t) <= 0:
            raise ValidationError('invalid crane envelope')

class LiftSafetyChecker:

    def __init__(self, envelope: CraneEnvelope):
        self.envelope = envelope

    def validate(self, plan: LiftPlan) -> None:
        if plan.gross_weight_t <= 0 or plan.outreach_m < 0 or plan.wind_kn < 0:
            raise ValidationError('invalid lift plan')
        limit = self.envelope.twin_lift_max_weight_t if plan.twin_lift else self.envelope.max_weight_t
        if plan.gross_weight_t > limit:
            raise SafetyConstraintError('lift exceeds weight envelope')
        if plan.outreach_m > self.envelope.max_outreach_m:
            raise SafetyConstraintError('lift exceeds outreach envelope')
        if plan.wind_kn > self.envelope.max_wind_kn:
            raise SafetyConstraintError('wind exceeds crane operating limit')

    def margin(self, plan: LiftPlan) -> dict[str, float]:
        limit = self.envelope.twin_lift_max_weight_t if plan.twin_lift else self.envelope.max_weight_t
        return {'weight_t': limit - plan.gross_weight_t, 'outreach_m': self.envelope.max_outreach_m - plan.outreach_m, 'wind_kn': self.envelope.max_wind_kn - plan.wind_kn}
