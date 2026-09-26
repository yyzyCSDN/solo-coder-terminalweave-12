from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.money import Money
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class HandlingTariff:
    operation: str
    container_size: int
    base: Money
    hazardous_surcharge: Money | None = None
    reefer_surcharge: Money | None = None

    def __post_init__(self):
        if self.container_size not in {20, 40, 45}:
            raise ValidationError('unsupported size')
        for extra in (self.hazardous_surcharge, self.reefer_surcharge):
            if extra and extra.currency != self.base.currency:
                raise ValidationError('surcharge currency mismatch')

    def price(self, hazardous: bool=False, reefer: bool=False) -> Money:
        total = self.base
        if hazardous and self.hazardous_surcharge:
            total = total + self.hazardous_surcharge
        if reefer and self.reefer_surcharge:
            total = total + self.reefer_surcharge
        return total

class TariffBook:

    def __init__(self, tariffs: list[HandlingTariff]):
        self._map = {(t.operation, t.container_size): t for t in tariffs}
        if len(self._map) != len(tariffs):
            raise ValidationError('duplicate handling tariff')

    def quote(self, operation: str, size: int, count: int=1, **flags) -> Money:
        if count < 0:
            raise ValidationError('count cannot be negative')
        tariff = self._map[operation, size]
        return tariff.price(**flags).scale(count)
