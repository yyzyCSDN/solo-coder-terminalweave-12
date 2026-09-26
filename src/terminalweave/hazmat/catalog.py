from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class DangerousGood:
    un_number: str
    proper_shipping_name: str
    hazard_class: str
    packing_group: str | None
    marine_pollutant: bool = False
    flash_point_c: float | None = None

    def __post_init__(self):
        if not (self.un_number.startswith('UN') and self.un_number[2:].isdigit()):
            raise ValidationError('invalid UN number')
        if not self.proper_shipping_name.strip():
            raise ValidationError('shipping name required')
        if self.packing_group not in {None, 'I', 'II', 'III'}:
            raise ValidationError('invalid packing group')

class DangerousGoodsCatalog:

    def __init__(self):
        self._goods: dict[str, DangerousGood] = {}

    def add(self, good: DangerousGood) -> None:
        existing = self._goods.get(good.un_number)
        if existing and existing != good:
            raise ValidationError('UN number already has another definition')
        self._goods[good.un_number] = good

    def get(self, un_number: str) -> DangerousGood:
        try:
            return self._goods[un_number]
        except KeyError as exc:
            raise ValidationError('unknown UN number') from exc

    def by_class(self, hazard_class: str) -> tuple[DangerousGood, ...]:
        return tuple(sorted((g for g in self._goods.values() if g.hazard_class == hazard_class), key=lambda x: x.un_number))

    def marine_pollutants(self) -> tuple[DangerousGood, ...]:
        return tuple((g for g in self._goods.values() if g.marine_pollutant))
