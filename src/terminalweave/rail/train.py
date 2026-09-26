from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError, CapacityError

@dataclass(frozen=True)
class RailCar:
    car_id: str
    tare_kg: float
    gross_limit_kg: float
    length_m: float

    def __post_init__(self):
        if min(self.tare_kg, self.gross_limit_kg, self.length_m) <= 0 or self.tare_kg >= self.gross_limit_kg:
            raise ValidationError('invalid rail car')

    @property
    def payload_limit_kg(self) -> float:
        return self.gross_limit_kg - self.tare_kg

@dataclass
class TrainConsist:
    train_id: str
    max_length_m: float
    max_gross_kg: float
    cars: list[RailCar]

    def __post_init__(self):
        if self.max_length_m <= 0 or self.max_gross_kg <= 0:
            raise ValidationError('invalid train limits')
        if len({c.car_id for c in self.cars}) != len(self.cars):
            raise ValidationError('duplicate rail car')
        self.validate()

    def length_m(self) -> float:
        return sum((c.length_m for c in self.cars))

    def tare_kg(self) -> float:
        return sum((c.tare_kg for c in self.cars))

    def validate(self) -> None:
        if self.length_m() > self.max_length_m:
            raise CapacityError('train length exceeded')
        if self.tare_kg() > self.max_gross_kg:
            raise CapacityError('train tare exceeds gross limit')

    def payload_capacity_kg(self) -> float:
        return min(sum((c.payload_limit_kg for c in self.cars)), self.max_gross_kg - self.tare_kg())

    def append(self, car: RailCar) -> None:
        self.cars.append(car)
        try:
            self.validate()
        except Exception:
            self.cars.pop()
            raise
