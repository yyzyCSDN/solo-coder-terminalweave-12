from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class PlacardObservation:
    container_id: str
    placards: frozenset[str]
    un_numbers: frozenset[str]

@dataclass(frozen=True)
class DeclaredHazmat:
    container_id: str
    classes: frozenset[str]
    un_numbers: frozenset[str]

@dataclass(frozen=True)
class PlacardFinding:
    container_id: str
    missing_classes: frozenset[str]
    extra_classes: frozenset[str]
    missing_un: frozenset[str]
    extra_un: frozenset[str]

    @property
    def clean(self) -> bool:
        return not (self.missing_classes or self.extra_classes or self.missing_un or self.extra_un)

class PlacardReconciler:

    def reconcile(self, declared: DeclaredHazmat, observed: PlacardObservation) -> PlacardFinding:
        if declared.container_id != observed.container_id:
            raise ValidationError('container ids differ')
        return PlacardFinding(declared.container_id, declared.classes - observed.placards, observed.placards - declared.classes, declared.un_numbers - observed.un_numbers, observed.un_numbers - declared.un_numbers)

    def severity(self, finding: PlacardFinding) -> str:
        if finding.missing_classes or finding.missing_un:
            return 'block'
        if finding.extra_classes or finding.extra_un:
            return 'review'
        return 'clear'
