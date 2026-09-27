from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import (
    ValidationError,
    ConflictError,
    StateTransitionError,
    NotFoundError,
)
from .lane_control import LaneController
from .token import GateToken, GateTokenIssuer
from .truck_visit import (
    EvidenceKind,
    REQUIRED_EVIDENCE,
    TruckVisit,
    TruckVisitFlow,
    VisitState,
)
from .weighbridge import WeighbridgeBook, WeightTicket


class GateMessageKind(str, Enum):
    IDENTITY = 'identity'
    TOKEN = 'token'
    WEIGHT = 'weight'
    DEPARTURE = 'departure'


@dataclass(frozen=True)
class GateMessage:
    """One device/reader message for a single visit.

    Messages for the same visit may arrive in any order and may be
    redelivered by the messaging transport; ``message_id`` is the
    producer-assigned deduplication key.
    """
    message_id: str
    visit_id: str
    kind: GateMessageKind
    at: datetime
    truck_id: str | None = None
    container_id: str | None = None
    gross_kg: Decimal | None = None
    tare_kg: Decimal | None = None
    token: GateToken | None = None
    permission: str = 'gate.entry'

    def __post_init__(self) -> None:
        object.__setattr__(self, 'at', ensure_utc(self.at))
        if not self.message_id:
            raise ValidationError('message id required')


class GateClearance:
    """Merge out-of-order gate messages into visit state transitions.

    Invariants enforced here:

    * every producer message is applied at most once (idempotent replay);
    * identity, container and weight evidence must all be merged before a
      visit may move from ``ARRIVED`` to ``INSIDE``;
    * a failed or invalid token rejects the visit, and a rejected visit can
      never move forward;
    * lane occupancy is always released, including failed retries.
    """

    def __init__(
        self,
        lanes: LaneController,
        *,
        token_issuer: GateTokenIssuer | None = None,
        weighbridge: WeighbridgeBook | None = None,
        flow: TruckVisitFlow | None = None,
    ):
        self.lanes = lanes
        self.token_issuer = token_issuer
        self.weighbridge = weighbridge
        self.flow = flow or TruckVisitFlow()
        self.visits: dict[str, TruckVisit] = {}
        self._occupied_lane: dict[str, str] = {}
        self._departure_pending: dict[str, GateMessage] = {}

    def get(self, visit_id: str) -> TruckVisit:
        visit = self.visits.get(visit_id)
        if visit is None:
            raise NotFoundError(f'unknown visit {visit_id}')
        return visit

    def arrive(
        self,
        visit: TruckVisit,
        at: datetime,
        *,
        lane_id: str | None = None,
    ) -> TruckVisit:
        """Register a physical arrival and occupy its lane."""
        at = ensure_utc(at)
        existing = self.visits.get(visit.visit_id)
        if existing is not None:
            visit = existing
        else:
            self.visits[visit.visit_id] = visit

        if visit.state == VisitState.ARRIVED:
            # Replayed arrival: keep the original lane reservation.
            return visit

        # Only the EXPECTED -> ARRIVED transition is valid here; a failure
        # must not touch a lane reserved by an earlier successful attempt.
        self.flow.transition(visit, VisitState.ARRIVED, at)
        if lane_id is not None and visit.visit_id not in self._occupied_lane:
            self.lanes.enter(lane_id, 'entry')
            self._occupied_lane[visit.visit_id] = lane_id
        return visit

    def handle(self, message: GateMessage) -> TruckVisit:
        visit = self.get(message.visit_id)
        if visit.has_message(message.message_id):
            # Transport redelivery: the transition already happened.
            return visit
        if visit.state == VisitState.REJECTED:
            # An already rejected access cannot continue to flow.
            raise StateTransitionError('rejected visit cannot continue')

        if message.kind == GateMessageKind.IDENTITY:
            self._apply_identity(visit, message)
        elif message.kind == GateMessageKind.WEIGHT:
            self._apply_weight(visit, message)
        elif message.kind == GateMessageKind.TOKEN:
            self._apply_token(visit, message)
        elif message.kind == GateMessageKind.DEPARTURE:
            self._apply_departure(visit, message)
        else:  # pragma: no cover - enum is exhaustive
            raise ValidationError(f'unknown message kind {message.kind}')

        self._advance(visit)
        # Only acknowledge a message after it merged cleanly, so a failed
        # delivery can be retried instead of being treated as a duplicate.
        visit.mark_message(message.message_id)
        return visit

    def _apply_identity(self, visit: TruckVisit, message: GateMessage) -> None:
        if message.truck_id is None:
            raise ValidationError('identity message requires truck id')
        self.flow.record_identity(visit, message.truck_id, message.at)
        if message.container_id is not None:
            self.flow.record_container(visit, message.container_id, message.at)

    def _apply_weight(self, visit: TruckVisit, message: GateMessage) -> None:
        if message.gross_kg is None:
            raise ValidationError('weight message requires gross weight')
        ticket = WeightTicket(
            ticket_id=message.message_id,
            truck_id=message.truck_id or visit.truck_id,
            gross_kg=Decimal(str(message.gross_kg)),
            tare_kg=Decimal(str(message.tare_kg or 0)),
            container_id=message.container_id,
        )
        if message.container_id is not None:
            self.flow.record_container(visit, message.container_id, message.at)
        self.flow.record_weight(visit, ticket.net_kg, message.at)

    def _apply_token(self, visit: TruckVisit, message: GateMessage) -> None:
        token = message.token
        if token is None:
            raise ValidationError('token message requires a gate token')
        if token.visit_id != visit.visit_id:
            self._reject(visit, message.at, 'token.visit_mismatch')
            raise StateTransitionError('token belongs to another visit')
        if self.token_issuer is None or not self.token_issuer.verify(token, message.at):
            # Fail closed: an unverifiable token rejects the visit and frees
            # the lane instead of leaving the truck occupying it.
            self._reject(visit, message.at, 'token.invalid')
            raise StateTransitionError('invalid gate token')
        self.flow.add_evidence(visit, EvidenceKind.TOKEN, token.token_id, message.at)

    def _apply_departure(self, visit: TruckVisit, message: GateMessage) -> None:
        if visit.state in {VisitState.ARRIVED}:
            # Departure raced ahead of entry clearance: remember it and let
            # the evidence messages pump the visit forward later.
            self._departure_pending[visit.visit_id] = message
            return
        self._depart(visit, message.at)

    def _depart(self, visit: TruckVisit, at: datetime) -> None:
        try:
            if visit.state == VisitState.INSIDE:
                self.flow.transition(visit, VisitState.RELEASED, at)
            if visit.state == VisitState.RELEASED:
                self.flow.transition(visit, VisitState.EXITED, at)
        except Exception:
            # Retrying a failed departure must not leave the lane occupied.
            self._release_lane(visit.visit_id)
            raise
        self._release_lane(visit.visit_id)

    def _advance(self, visit: TruckVisit) -> None:
        """Move a cleared visit through any buffered progression."""
        if visit.state == VisitState.ARRIVED and visit.evidence_complete():
            last = max(visit.evidence_at[k.value] for k in REQUIRED_EVIDENCE)
            self.flow.transition(visit, VisitState.INSIDE, last)
        pending = self._departure_pending.get(visit.visit_id)
        if pending is None or visit.state != VisitState.INSIDE:
            return
        # A departure that was buffered before clearance cannot carry a
        # timestamp earlier than the entry it follows; pin it to clearance.
        at = max(pending.at, visit.timestamps[VisitState.INSIDE.value])
        self._depart(visit, at)
        # Pop and acknowledge only once the departure actually completed,
        # so a failed retry remains retriable.
        self._departure_pending.pop(visit.visit_id, None)
        visit.mark_message(pending.message_id)

    def _reject(self, visit: TruckVisit, at: datetime, reason: str) -> None:
        self._departure_pending.pop(visit.visit_id, None)
        self.flow.reject(visit, at, reason)
        self._release_lane(visit.visit_id)

    def _release_lane(self, visit_id: str) -> None:
        lane_id = self._occupied_lane.pop(visit_id, None)
        if lane_id is None:
            return
        state = self.lanes.states[lane_id]
        if state.occupied:
            self.lanes.leave(lane_id)

    def release(self, visit_id: str, at: datetime) -> TruckVisit:
        """Explicit exit-side release after the truck is cleared inside."""
        visit = self.get(visit_id)
        self._depart(visit, ensure_utc(at))
        return visit

    def missing_evidence(self, visit_id: str) -> list[str]:
        visit = self.get(visit_id)
        return sorted(k.value for k in REQUIRED_EVIDENCE if k.value not in visit.evidence)
