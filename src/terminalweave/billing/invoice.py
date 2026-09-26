from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from terminalweave.core.money import Money
from terminalweave.core.errors import ValidationError, StateTransitionError

@dataclass(frozen=True)
class InvoiceLine:
    code: str
    description: str
    quantity: Decimal
    unit_price: Money

    def __post_init__(self):
        if self.quantity < 0:
            raise ValidationError('quantity cannot be negative')

    @property
    def amount(self) -> Money:
        return self.unit_price.scale(self.quantity)

@dataclass
class Invoice:
    invoice_id: str
    customer_id: str
    currency: str = 'USD'
    lines: list[InvoiceLine] = field(default_factory=list)
    finalized: bool = False

    def add(self, line: InvoiceLine) -> None:
        if self.finalized:
            raise StateTransitionError('invoice finalized')
        if line.unit_price.currency != self.currency:
            raise ValidationError('invoice currency mismatch')
        self.lines.append(line)

    def subtotal(self) -> Money:
        total = Money.zero(self.currency)
        for line in self.lines:
            total = total + line.amount
        return total

    def total(self, tax_rate: Decimal=Decimal('0')) -> Money:
        if tax_rate < 0:
            raise ValidationError('tax rate cannot be negative')
        subtotal = self.subtotal()
        return subtotal + subtotal.scale(tax_rate)

    def finalize(self) -> None:
        if not self.lines:
            raise StateTransitionError('empty invoice cannot be finalized')
        self.finalized = True
