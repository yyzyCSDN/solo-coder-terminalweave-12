from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class RiskInput:
    origin_country: str
    commodity_code: str
    shipper_score: float
    weight_deviation_pct: float
    seal_mismatch: bool
    prior_exams: int

@dataclass(frozen=True)
class RiskResult:
    score: float
    band: str
    reasons: tuple[str, ...]

class CustomsRiskEngine:

    def __init__(self, high_risk_origins: set[str] | None=None):
        self.high_risk_origins = set(high_risk_origins or set())

    def evaluate(self, x: RiskInput) -> RiskResult:
        if not 0 <= x.shipper_score <= 1 or x.prior_exams < 0:
            raise ValidationError('invalid risk input')
        score = 0.0
        reasons = []
        if x.origin_country in self.high_risk_origins:
            score += 25
            reasons.append('origin')
        if x.shipper_score < 0.4:
            score += (0.4 - x.shipper_score) * 50
            reasons.append('shipper history')
        if abs(x.weight_deviation_pct) > 5:
            score += min(abs(x.weight_deviation_pct), 30)
            reasons.append('weight variance')
        if x.seal_mismatch:
            score += 35
            reasons.append('seal mismatch')
        if x.prior_exams:
            score += min(x.prior_exams * 3, 15)
            reasons.append('prior examinations')
        score = min(100.0, score)
        band = 'high' if score >= 60 else 'medium' if score >= 30 else 'low'
        return RiskResult(round(score, 2), band, tuple(reasons))
