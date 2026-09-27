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

class EvidenceKind(str, Enum):
    IDENTITY = 'identity'
    CONTAINER = 'container'
    WEIGHT = 'weight'
    TOKEN = 'token'

# A visit may not enter the terminal until all of this evidence has been
# merged: who the truck is, which container it carries, and its weight.
REQUIRED_EVIDENCE = frozenset({EvidenceKind.IDENTITY, EvidenceKind.CONTAINER, EvidenceKind.WEIGHT})

@dataclass
class TruckVisit:
    visit_id: str
    truck_id: str
    appointment_id: str | None
    state: VisitState = VisitState.EXPECTED
    timestamps: dict[str, datetime] = field(default_factory=dict)
    exceptions: list[str] = field(default_factory=list)
    evidence: dict[str, object] = field(default_factory=dict)
    evidence_at: dict[str, datetime] = field(default_factory=dict)
    processed_messages: set[str] = field(default_factory=set)

    def has_message(self, message_id: str | None) -> bool:
        return message_id is not None and message_id in self.processed_messages

    def mark_message(self, message_id: str | None) -> bool:
        """Remember a processed message id. Returns False on a replay."""
        if message_id is None:
            return True
        if message_id in self.processed_messages:
            return False
        self.processed_messages.add(message_id)
        return True

    def evidence_complete(self) -> bool:
        return REQUIRED_EVIDENCE.issubset(self.evidence)

class TruckVisitFlow:
    sequence = [VisitState.EXPECTED, VisitState.ARRIVED, VisitState.INSIDE, VisitState.RELEASED, VisitState.EXITED]

    def transition(self, visit: TruckVisit, target: VisitState, at: datetime) -> TruckVisit:
        at = ensure_utc(at)
        if target == VisitState.REJECTED:
            if visit.state in {VisitState.RELEASED, VisitState.EXITED}:
                raise StateTransitionError('released visit cannot be rejected')
            if visit.state == VisitState.REJECTED:
                # Replaying a rejection must not stamp it a second time.
                return visit
            visit.state = target
            visit.timestamps[target.value] = at
            return visit
        if visit.state == VisitState.REJECTED:
            raise StateTransitionError('rejected visit cannot continue')
        # Idempotent replay: the same state message arriving again must not
        # execute any transition side effect, nor overwrite its timestamp.
        if visit.state == target:
            recorded = visit.timestamps.get(target.value)
            if recorded is not None and recorded != at:
                raise ConflictError(f'{target.value} already recorded at {recorded.isoformat()}')
            return visit
        current = self.sequence.index(visit.state)
        expected = self.sequence[current + 1] if current + 1 < len(self.sequence) else None
        if target != expected:
            raise StateTransitionError(f'expected transition to {expected}')
        if visit.timestamps and at < max(visit.timestamps.values()):
            raise ValidationError('visit time cannot move backwards')
        if target == VisitState.INSIDE and not visit.evidence_complete():
            missing = sorted(k.value for k in REQUIRED_EVIDENCE if k.value not in visit.evidence)
            raise StateTransitionError(
                f'cannot enter without complete evidence; missing: {", ".join(missing)}'
            )
        visit.state = target
        visit.timestamps[target.value] = at
        return visit

    def add_evidence(
        self,
        visit: TruckVisit,
        kind: EvidenceKind,
        value: object,
        at: datetime,
    ) -> bool:
        """Merge one piece of evidence, ignoring exact duplicates.

        Returns True when new evidence was stored, False when the same
        evidence was delivered again. Conflicting values for an already
        recorded kind raise instead of silently replacing the evidence.
        """
        at = ensure_utc(at)
        key = kind.value
        if key in visit.evidence:
            if visit.evidence[key] != value:
                raise ConflictError(f'conflicting {key} evidence')
            return False
        previous = max(visit.evidence_at.values(), default=None)
        if previous is not None and at < previous:
            raise ValidationError('evidence time cannot move backwards')
        visit.evidence[key] = value
        visit.evidence_at[key] = at
        return True

    def record_identity(self, visit: TruckVisit, truck_id: str, at: datetime) -> bool:
        if visit.truck_id != truck_id:
            raise ConflictError('identity evidence does not match visit truck')
        return self.add_evidence(visit, EvidenceKind.IDENTITY, truck_id, at)

    def record_container(self, visit: TruckVisit, container_id: str, at: datetime) -> bool:
        if not isinstance(container_id, str) or not container_id.strip():
            raise ValidationError('container id required')
        return self.add_evidence(visit, EvidenceKind.CONTAINER, container_id.strip(), at)

    def record_weight(self, visit: TruckVisit, net_kg: object, at: datetime) -> bool:
        from decimal import Decimal
        net_kg = Decimal(str(net_kg))
        if net_kg <= 0:
            raise ValidationError('weight evidence must be positive')
        return self.add_evidence(visit, EvidenceKind.WEIGHT, str(net_kg), at)

    def can_enter(self, visit: TruckVisit) -> bool:
        return visit.state == VisitState.ARRIVED and visit.evidence_complete()

    def reject(self, visit: TruckVisit, at: datetime, reason: str | None = None) -> TruckVisit:
        self.transition(visit, VisitState.REJECTED, at)
        if reason and reason not in visit.exceptions:
            visit.exceptions.append(reason)
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
