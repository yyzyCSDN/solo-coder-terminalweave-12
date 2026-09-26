from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from .errors import ValidationError
_CENT = Decimal('0.01')

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = 'USD'

    def __post_init__(self) -> None:
        cur = self.currency.strip().upper()
        if len(cur) != 3 or not cur.isalpha():
            raise ValidationError('currency must be a 3-letter code')
        amt = Decimal(self.amount).quantize(_CENT, rounding=ROUND_HALF_UP)
        object.__setattr__(self, 'currency', cur)
        object.__setattr__(self, 'amount', amt)

    def _check(self, other: 'Money') -> None:
        if self.currency != other.currency:
            raise ValidationError('currency mismatch')

    def __add__(self, other: 'Money') -> 'Money':
        self._check(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: 'Money') -> 'Money':
        self._check(other)
        return Money(self.amount - other.amount, self.currency)

    def scale(self, factor: Decimal | int | float | str) -> 'Money':
        return Money(self.amount * Decimal(str(factor)), self.currency)

    @classmethod
    def zero(cls, currency: str='USD') -> 'Money':
        return cls(Decimal('0'), currency)
