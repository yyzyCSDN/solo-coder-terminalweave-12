from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class EmissionFactor:
    activity: str
    kg_co2e_per_unit: Decimal
    unit: str

    def __post_init__(self):
        if self.kg_co2e_per_unit < 0:
            raise ValidationError('emission factor cannot be negative')

@dataclass(frozen=True)
class ActivityQuantity:
    activity: str
    quantity: Decimal
    unit: str
    scope: str

    def __post_init__(self):
        if self.quantity < 0:
            raise ValidationError('activity quantity cannot be negative')

@dataclass(frozen=True)
class EmissionLine:
    activity: str
    scope: str
    quantity: Decimal
    unit: str
    kg_co2e: Decimal

class CarbonLedger:

    def __init__(self, factors: list[EmissionFactor]):
        self.factors = {f.activity: f for f in factors}
        if len(self.factors) != len(factors):
            raise ValidationError('duplicate emission factor')

    def calculate(self, activities: list[ActivityQuantity]) -> list[EmissionLine]:
        lines = []
        for activity in activities:
            factor = self.factors.get(activity.activity)
            if not factor:
                raise ValidationError(f'missing emission factor for {activity.activity}')
            if factor.unit != activity.unit:
                raise ValidationError('emission factor unit mismatch')
            lines.append(EmissionLine(activity.activity, activity.scope, activity.quantity, activity.unit, activity.quantity * factor.kg_co2e_per_unit))
        return lines

    def total(self, activities: list[ActivityQuantity]) -> Decimal:
        return sum((line.kg_co2e for line in self.calculate(activities)), Decimal('0'))

    def by_scope(self, activities: list[ActivityQuantity]) -> dict[str, Decimal]:
        result = {}
        for line in self.calculate(activities):
            result[line.scope] = result.get(line.scope, Decimal('0')) + line.kg_co2e
        return dict(sorted(result.items()))

    def intensity(self, activities: list[ActivityQuantity], throughput_teu: Decimal) -> Decimal:
        if throughput_teu <= 0:
            raise ValidationError('throughput TEU must be positive')
        return self.total(activities) / throughput_teu
