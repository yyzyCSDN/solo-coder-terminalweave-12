from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from terminalweave.core.money import Money
from terminalweave.core.errors import ValidationError, CapacityError

@dataclass
class CreditAccount:
    customer_id: str
    limit: Money
    outstanding: Money
    suspended: bool = False

    def __post_init__(self):
        if self.limit.currency != self.outstanding.currency or self.limit.amount < 0 or self.outstanding.amount < 0:
            raise ValidationError('invalid credit account')

    @property
    def available(self):
        return Money(max(Decimal('0'), self.limit.amount - self.outstanding.amount), self.limit.currency)

class CreditController:

    def authorize(self, account: CreditAccount, charge: Money) -> None:
        if account.suspended:
            raise CapacityError('customer credit is suspended')
        if charge.currency != account.limit.currency:
            raise ValidationError('currency mismatch')
        if charge.amount > account.available.amount:
            raise CapacityError('credit limit exceeded')
        account.outstanding = account.outstanding + charge

    def payment(self, account: CreditAccount, payment: Money) -> None:
        if payment.currency != account.limit.currency or payment.amount < 0:
            raise ValidationError('invalid payment')
        amount = max(Decimal('0'), account.outstanding.amount - payment.amount)
        account.outstanding = Money(amount, account.limit.currency)
