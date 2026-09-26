from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from terminalweave.core.money import Money
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class DiscountRule:
    code: str
    threshold: Money
    percent: Decimal
    cap: Money | None = None

    def __post_init__(self):
        if not 0 <= self.percent <= 1:
            raise ValidationError('discount percent must be 0..1')
        if self.cap and self.cap.currency != self.threshold.currency:
            raise ValidationError('discount currency mismatch')

    def apply(self, subtotal: Money) -> Money:
        if subtotal.currency != self.threshold.currency:
            raise ValidationError('currency mismatch')
        if subtotal.amount < self.threshold.amount:
            return Money.zero(subtotal.currency)
        amount = subtotal.scale(self.percent)
        if self.cap and amount.amount > self.cap.amount:
            return self.cap
        return amount

class DiscountBook:

    def __init__(self, rules: list[DiscountRule]):
        self.rules = {r.code: r for r in rules}

    def best(self, subtotal: Money, eligible_codes: set[str]) -> tuple[str | None, Money]:
        options = [(code, self.rules[code].apply(subtotal)) for code in eligible_codes if code in self.rules]
        if not options:
            return (None, Money.zero(subtotal.currency))
        return max(options, key=lambda x: (x[1].amount, x[0]))
