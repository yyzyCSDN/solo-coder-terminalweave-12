from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError, SafetyConstraintError

@dataclass(frozen=True)
class HazmatClass:
    code: str
    name: str
    default_separation_m: float

    def __post_init__(self) -> None:
        if not self.code.strip() or self.default_separation_m < 0:
            raise ValidationError('invalid hazardous class')

@dataclass(frozen=True)
class HazmatUnit:
    container_id: str
    class_code: str
    block: str
    x_m: float
    y_m: float

class CompatibilityMatrix:

    def __init__(self):
        self._rules: dict[frozenset[str], float | None] = {}

    def set_compatible(self, a: str, b: str, minimum_separation_m: float=0.0) -> None:
        if minimum_separation_m < 0:
            raise ValidationError('separation cannot be negative')
        self._rules[frozenset((a, b))] = float(minimum_separation_m)

    def set_incompatible(self, a: str, b: str) -> None:
        self._rules[frozenset((a, b))] = None

    def requirement(self, a: str, b: str) -> float | None:
        if a == b:
            return 0.0
        key = frozenset((a, b))
        if key not in self._rules:
            raise SafetyConstraintError(f'no compatibility rule for {a}/{b}')
        return self._rules[key]

class SegregationChecker:

    def __init__(self, matrix: CompatibilityMatrix):
        self.matrix = matrix

    @staticmethod
    def distance(a: HazmatUnit, b: HazmatUnit) -> float:
        return ((a.x_m - b.x_m) ** 2 + (a.y_m - b.y_m) ** 2) ** 0.5

    def check_pair(self, a: HazmatUnit, b: HazmatUnit) -> tuple[bool, str]:
        requirement = self.matrix.requirement(a.class_code, b.class_code)
        if requirement is None:
            return (False, 'classes are prohibited from co-location')
        actual = self.distance(a, b)
        if actual + 1e-09 < requirement:
            return (False, f'requires {requirement:.1f}m separation, observed {actual:.1f}m')
        return (True, 'compatible')

    def validate_layout(self, units: list[HazmatUnit]) -> list[str]:
        violations = []
        for i, a in enumerate(units):
            for b in units[i + 1:]:
                ok, reason = self.check_pair(a, b)
                if not ok:
                    violations.append(f'{a.container_id}/{b.container_id}: {reason}')
        return violations

    def candidate_is_safe(self, candidate: HazmatUnit, existing: list[HazmatUnit]) -> bool:
        return all((self.check_pair(candidate, other)[0] for other in existing))
