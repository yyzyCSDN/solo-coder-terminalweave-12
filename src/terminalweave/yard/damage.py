from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError, StateTransitionError

class DamageState(str, Enum):
    OPEN = 'open'
    SURVEYED = 'surveyed'
    RELEASED = 'released'
    REPAIR = 'repair'

@dataclass
class DamageCase:
    case_id: str
    container_id: str
    opened_at: datetime
    codes: set[str]
    state: DamageState = DamageState.OPEN
    notes: list[str] = None

    def __post_init__(self):
        self.opened_at = ensure_utc(self.opened_at)
        self.notes = list(self.notes or [])
        if not self.codes:
            raise ValidationError('at least one damage code required')

class DamageRegistry:

    def __init__(self):
        self.cases: dict[str, DamageCase] = {}

    def open(self, case: DamageCase) -> None:
        if case.case_id in self.cases:
            raise ValidationError('duplicate damage case')
        if any((c.container_id == case.container_id and c.state not in {DamageState.RELEASED} for c in self.cases.values())):
            raise StateTransitionError('container already has active damage case')
        self.cases[case.case_id] = case

    def survey(self, case_id: str, note: str) -> DamageCase:
        case = self.cases[case_id]
        if case.state != DamageState.OPEN:
            raise StateTransitionError('case is not open')
        case.state = DamageState.SURVEYED
        case.notes.append(note)
        return case

    def decide(self, case_id: str, repair: bool, note: str='') -> DamageCase:
        case = self.cases[case_id]
        if case.state != DamageState.SURVEYED:
            raise StateTransitionError('case must be surveyed')
        case.state = DamageState.REPAIR if repair else DamageState.RELEASED
        if note:
            case.notes.append(note)
        return case
