from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError, StateTransitionError, ConflictError

class VisitState(str, Enum):
    EXPECTED = 'expected'
    ARRIVED = 'arrived'
    INSIDE = 'inside'
    RELEASED = 'released'
    EXITED = 'exited'
    REJECTED = 'rejected'

@dataclass
class TruckVisit:
    visit_id: str
    truck_id: str
    appointment_id: str | None
    state: VisitState = VisitState.EXPECTED
    timestamps: dict[str, datetime] = field(default_factory=dict)
    exceptions: list[str] = field(default_factory=list)
    identity_verified: bool = False
    container_id: str | None = None
    weight_ticket_id: str | None = None

class TruckVisitFlow:
    sequence = [VisitState.EXPECTED, VisitState.ARRIVED, VisitState.INSIDE, VisitState.RELEASED, VisitState.EXITED]

    def transition(self, visit: TruckVisit, target: VisitState, at: datetime) -> TruckVisit:
        at = ensure_utc(at)
        if target == VisitState.REJECTED:
            if visit.state in {VisitState.RELEASED, VisitState.EXITED}:
                raise StateTransitionError('released visit cannot be rejected')
            if visit.state == VisitState.REJECTED:
                return visit
            visit.state = target
            visit.timestamps[target.value] = at
            return visit
        if visit.state == VisitState.REJECTED:
            raise StateTransitionError('rejected visit cannot continue')
        current = self.sequence.index(visit.state)
        if target in self.sequence and self.sequence.index(target) <= current:
            # duplicate or late-arriving message: already merged, do not execute again
            return visit
        expected = self.sequence[current + 1] if current + 1 < len(self.sequence) else None
        if target != expected:
            raise StateTransitionError(f'expected transition to {expected}')
        if target == VisitState.RELEASED:
            missing = self.missing_evidence(visit)
            if missing:
                raise StateTransitionError(f'release requires complete evidence, missing: {", ".join(missing)}')
        if visit.timestamps and at < max(visit.timestamps.values()):
            raise ValidationError('visit time cannot move backwards')
        visit.state = target
        visit.timestamps[target.value] = at
        return visit

    def missing_evidence(self, visit: TruckVisit) -> list[str]:
        missing = []
        if not visit.identity_verified:
            missing.append('identity')
        if not visit.container_id:
            missing.append('container')
        if not visit.weight_ticket_id:
            missing.append('weight')
        return missing

    def evidence_complete(self, visit: TruckVisit) -> bool:
        return not self.missing_evidence(visit)

    def _ensure_collecting(self, visit: TruckVisit) -> None:
        if visit.state == VisitState.REJECTED:
            raise StateTransitionError('rejected visit cannot continue')
        if visit.state in {VisitState.RELEASED, VisitState.EXITED}:
            raise StateTransitionError('visit is already released')

    def confirm_identity(self, visit: TruckVisit) -> TruckVisit:
        if visit.state == VisitState.REJECTED:
            raise StateTransitionError('rejected visit cannot continue')
        visit.identity_verified = True
        return visit

    def record_container(self, visit: TruckVisit, container_id: str) -> TruckVisit:
        container_id = container_id.strip().upper()
        if not container_id:
            raise ValidationError('container id required')
        if visit.container_id is not None:
            if visit.container_id == container_id:
                return visit
            raise ConflictError('conflicting container id for visit')
        self._ensure_collecting(visit)
        visit.container_id = container_id
        return visit

    def record_weight(self, visit: TruckVisit, ticket_id: str) -> TruckVisit:
        ticket_id = ticket_id.strip()
        if not ticket_id:
            raise ValidationError('weight ticket id required')
        if visit.weight_ticket_id is not None:
            if visit.weight_ticket_id == ticket_id:
                return visit
            raise ConflictError('conflicting weight ticket for visit')
        self._ensure_collecting(visit)
        visit.weight_ticket_id = ticket_id
        return visit

    def turn_time_minutes(self, visit: TruckVisit) -> float | None:
        arrived = visit.timestamps.get('arrived')
        exited = visit.timestamps.get('exited')
        return (exited - arrived).total_seconds() / 60 if arrived and exited else None

    def add_exception(self, visit: TruckVisit, code: str) -> None:
        if not code.strip():
            raise ValidationError('exception code required')
        if code not in visit.exceptions:
            visit.exceptions.append(code)
