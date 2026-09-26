from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from copy import deepcopy
from terminalweave.core.clock import ensure_utc, utc_now
from terminalweave.core.errors import ValidationError, StateTransitionError

@dataclass
class TerminalScenario:
    scenario_id: str
    name: str
    created_at: datetime = field(default_factory=utc_now)
    base_revision: int = 0
    status: str = 'draft'
    assumptions: dict[str, object] = field(default_factory=dict)
    decisions: list[dict[str, object]] = field(default_factory=list)

    def __post_init__(self):
        self.created_at = ensure_utc(self.created_at)
        if not self.scenario_id.strip() or not self.name.strip():
            raise ValidationError('scenario id and name required')

    def set_assumption(self, key: str, value: object) -> None:
        if self.status != 'draft':
            raise StateTransitionError('only draft scenarios are editable')
        if not key.strip():
            raise ValidationError('assumption key required')
        self.assumptions[key] = value

    def record_decision(self, kind: str, payload: dict[str, object]) -> None:
        if self.status != 'draft':
            raise StateTransitionError('only draft scenarios are editable')
        if not kind.strip():
            raise ValidationError('decision kind required')
        self.decisions.append({'kind': kind, 'payload': deepcopy(payload)})

    def freeze(self) -> None:
        if self.status != 'draft':
            raise StateTransitionError('scenario is not draft')
        self.status = 'frozen'

    def clone(self, new_id: str, new_name: str) -> 'TerminalScenario':
        clone = TerminalScenario(new_id, new_name, utc_now(), self.base_revision, 'draft', deepcopy(self.assumptions), deepcopy(self.decisions))
        return clone

    def fingerprint_input(self) -> tuple:
        assumptions = tuple(sorted(((k, repr(v)) for k, v in self.assumptions.items())))
        decisions = tuple(((d['kind'], repr(sorted(d['payload'].items()))) for d in self.decisions))
        return (self.base_revision, assumptions, decisions)
