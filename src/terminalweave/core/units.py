from __future__ import annotations
from dataclasses import dataclass
from .errors import ValidationError

@dataclass(frozen=True)
class LengthM:
    value: float

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValidationError('length cannot be negative')

    @classmethod
    def from_feet(cls, feet: float) -> 'LengthM':
        return cls(feet * 0.3048)

@dataclass(frozen=True)
class MassKg:
    value: float

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValidationError('mass cannot be negative')

    @classmethod
    def from_tonnes(cls, tonnes: float) -> 'MassKg':
        return cls(tonnes * 1000.0)

@dataclass(frozen=True)
class TemperatureC:
    value: float

    def __post_init__(self) -> None:
        if not -100.0 <= self.value <= 100.0:
            raise ValidationError('temperature outside supported range')
