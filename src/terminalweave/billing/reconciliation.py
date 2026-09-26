from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from terminalweave.core.money import Money
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class PaymentRecord:
    payment_id: str
    reference: str
    amount: Money

@dataclass(frozen=True)
class Receivable:
    invoice_id: str
    reference: str
    amount: Money

class PaymentReconciler:

    def match(self, payments: list[PaymentRecord], receivables: list[Receivable], tolerance: Decimal=Decimal('0.01')) -> dict[str, str]:
        result = {}
        used = set()
        for payment in payments:
            candidates = []
            for rec in receivables:
                if rec.invoice_id in used or rec.amount.currency != payment.amount.currency:
                    continue
                delta = abs(rec.amount.amount - payment.amount.amount)
                if delta <= tolerance:
                    candidates.append((0 if rec.reference == payment.reference else 1, delta, rec.invoice_id, rec))
            if candidates:
                _, _, _, rec = min(candidates)
                result[payment.payment_id] = rec.invoice_id
                used.add(rec.invoice_id)
        return result

    def unmatched_value(self, receivables: list[Receivable], matched: dict[str, str]) -> Money:
        if not receivables:
            return Money.zero()
        currency = receivables[0].amount.currency
        matched_ids = set(matched.values())
        total = Money.zero(currency)
        for r in receivables:
            if r.amount.currency != currency:
                raise ValidationError('mixed currencies')
            if r.invoice_id not in matched_ids:
                total = total + r.amount
        return total
