from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from terminalweave.core.errors import ValidationError, ConflictError

@dataclass(frozen=True)
class WeightTicket:
    ticket_id: str
    truck_id: str
    gross_kg: Decimal
    tare_kg: Decimal
    container_id: str | None = None

    def __post_init__(self):
        if self.gross_kg <= 0 or self.tare_kg < 0 or self.gross_kg <= self.tare_kg:
            raise ValidationError('invalid weighbridge ticket')

    @property
    def net_kg(self):
        return self.gross_kg - self.tare_kg

class WeighbridgeBook:

    def __init__(self):
        self.tickets: dict[str, WeightTicket] = {}

    def add(self, ticket: WeightTicket) -> None:
        if ticket.ticket_id in self.tickets:
            raise ConflictError('duplicate weight ticket')
        self.tickets[ticket.ticket_id] = ticket

    def verify_container(self, ticket_id: str, declared_kg: Decimal, tolerance_kg: Decimal) -> dict[str, object]:
        if tolerance_kg < 0:
            raise ValidationError('tolerance cannot be negative')
        ticket = self.tickets[ticket_id]
        delta = ticket.net_kg - declared_kg
        return {'ticket_id': ticket_id, 'net_kg': str(ticket.net_kg), 'declared_kg': str(declared_kg), 'delta_kg': str(delta), 'within_tolerance': abs(delta) <= tolerance_kg}
