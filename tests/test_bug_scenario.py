from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from terminalweave.core.errors import (
    ConflictError,
    StateTransitionError,
    ValidationError,
)
from terminalweave.gate.clearance import GateClearance, GateMessage, GateMessageKind
from terminalweave.gate.lane_control import LaneController, LaneMode
from terminalweave.gate.token import GateTokenIssuer
from terminalweave.gate.truck_visit import (
    EvidenceKind,
    TruckVisit,
    TruckVisitFlow,
    VisitState,
)
from terminalweave.gate.weighbridge import WeighbridgeBook


UTC = timezone.utc
D = datetime(2026, 1, 1, tzinfo=UTC)
SECRET = b"0123456789abcdef"


def _clearance():
    lanes = LaneController(["L1"])
    lanes.set_mode("L1", LaneMode.ENTRY)
    return GateClearance(
        lanes,
        token_issuer=GateTokenIssuer(SECRET),
        weighbridge=WeighbridgeBook(),
    )


def _arrive(gate, visit_id="V1", truck_id="TRUCK1", at=D):
    visit = TruckVisit(visit_id, truck_id, None)
    return gate.arrive(visit, at, lane_id="L1")


def _identity(msg_id, visit_id="V1", at=D, truck_id="TRUCK1", container="MSCU1234567"):
    return GateMessage(msg_id, visit_id, GateMessageKind.IDENTITY, at,
                       truck_id=truck_id, container_id=container)


def _weight(msg_id, visit_id="V1", at=D, gross=30000, tare=12000,
            container="MSCU1234567"):
    return GateMessage(msg_id, visit_id, GateMessageKind.WEIGHT, at,
                       container_id=container, gross_kg=Decimal(gross),
                       tare_kg=Decimal(tare))


def _token_message(msg_id, visit_id="V1", at=D, ttl=timedelta(hours=2)):
    token = GateTokenIssuer(SECRET).issue(visit_id, at, ttl=ttl)
    return GateMessage(msg_id, visit_id, GateMessageKind.TOKEN, at, token=token), token


def _departure(msg_id, visit_id="V1", at=D + timedelta(minutes=10)):
    return GateMessage(msg_id, visit_id, GateMessageKind.DEPARTURE, at)


def test_replayed_gate_state_message_does_not_execute_transition_twice():
    flow = TruckVisitFlow()
    visit = TruckVisit("V1", "TRUCK1", None)
    flow.transition(visit, VisitState.ARRIVED, D)
    flow.transition(visit, VisitState.ARRIVED, D)
    assert visit.state == VisitState.ARRIVED
    assert visit.timestamps == {"arrived": D}


def test_partial_evidence_cannot_advance_to_inside():
    flow = TruckVisitFlow()
    visit = TruckVisit("V1", "TRUCK1", None)
    flow.transition(visit, VisitState.ARRIVED, D)
    flow.record_identity(visit, "TRUCK1", D)
    with pytest.raises(StateTransitionError):
        flow.transition(visit, VisitState.INSIDE, D)
    assert visit.state == VisitState.ARRIVED


def test_out_of_order_identity_weight_container_still_clears_visit():
    gate = _clearance()
    _arrive(gate)
    gate.handle(_weight("m-weight", at=D + timedelta(seconds=2)))
    # Identity (with container number) arrives last: the visit merges and
    # only then advances.
    visit = gate.handle(_identity("m-id", at=D + timedelta(seconds=3)))
    assert visit.state == VisitState.INSIDE
    assert visit.evidence_complete()
    assert gate.lanes.states["L1"].occupied is True


def test_duplicate_message_id_is_applied_at_most_once():
    gate = _clearance()
    _arrive(gate)
    gate.handle(_weight("m-weight"))
    gate.handle(_weight("m-weight"))
    visit = gate.get("V1")
    assert visit.processed_messages == {"m-weight"}
    assert list(visit.evidence_at) == ["container", "weight"]


def test_conflicting_evidence_is_rejected_instead_of_overwritten():
    gate = _clearance()
    _arrive(gate)
    gate.handle(_weight("m-weight", container="MSCU1234567"))
    with pytest.raises(ConflictError):
        gate.handle(_weight("m-weight-2", container="OTHER9876543"))


def test_departure_before_clearance_is_buffered_and_completes_later():
    gate = _clearance()
    _arrive(gate)
    gate.handle(_departure("m-dep", at=D + timedelta(minutes=5)))
    assert gate.get("V1").state == VisitState.ARRIVED

    gate.handle(_weight("m-weight", at=D + timedelta(seconds=2)))
    visit = gate.handle(_identity("m-id", at=D + timedelta(seconds=3)))
    # Once evidence is complete the buffered departure pumps it through.
    assert visit.state == VisitState.EXITED
    assert gate.lanes.states["L1"].occupied is False


def test_replayed_departure_does_not_double_release_lane():
    gate = _clearance()
    _arrive(gate)
    gate.handle(_weight("m-weight"))
    gate.handle(_identity("m-id"))
    gate.handle(_departure("m-dep"))
    assert gate.get("V1").state == VisitState.EXITED
    gate.handle(_departure("m-dep"))  # redelivery
    assert gate.get("V1").state == VisitState.EXITED
    assert gate.lanes.states["L1"].occupied is False


def test_invalid_token_rejects_visit_and_releases_lane():
    gate = _clearance()
    _arrive(gate)
    bad_token = GateTokenIssuer(b"x" * 16).issue("V1", D)  # wrong signature
    msg = GateMessage("m-token", "V1", GateMessageKind.TOKEN, D, token=bad_token)
    with pytest.raises(StateTransitionError):
        gate.handle(msg)
    visit = gate.get("V1")
    assert visit.state == VisitState.REJECTED
    assert "token.invalid" in visit.exceptions
    assert gate.lanes.states["L1"].occupied is False


def test_rejected_visit_rejects_later_evidence_messages():
    gate = _clearance()
    _arrive(gate)
    bad_token = GateTokenIssuer(b"x" * 16).issue("V1", D)
    with pytest.raises(StateTransitionError):
        gate.handle(GateMessage("m-bad", "V1", GateMessageKind.TOKEN, D, token=bad_token))
    with pytest.raises(StateTransitionError):
        gate.handle(_identity("m-id"))
    with pytest.raises(StateTransitionError):
        gate.handle(_departure("m-dep"))
    assert gate.get("V1").state == VisitState.REJECTED


def test_failed_departure_retry_does_not_leave_lane_occupied():
    gate = _clearance()
    _arrive(gate)
    gate.handle(_weight("m-weight"))
    gate.handle(_identity("m-id"))
    assert gate.lanes.states["L1"].occupied is True
    with pytest.raises(ValidationError):
        # A departure timestamp before entry fails validation.
        gate.release("V1", D - timedelta(hours=1))
    assert gate.lanes.states["L1"].occupied is False
    # Retrying with a valid timestamp still completes the visit.
    gate.release("V1", D + timedelta(minutes=10))
    assert gate.get("V1").state == VisitState.EXITED


def test_replayed_rejection_is_idempotent():
    flow = TruckVisitFlow()
    visit = TruckVisit("V1", "TRUCK1", None)
    flow.transition(visit, VisitState.ARRIVED, D)
    flow.transition(visit, VisitState.REJECTED, D + timedelta(minutes=1))
    flow.transition(visit, VisitState.REJECTED, D + timedelta(minutes=1))
    assert visit.state == VisitState.REJECTED
    assert visit.timestamps == {
        "arrived": D,
        "rejected": D + timedelta(minutes=1),
    }


def test_evidence_merged_before_departure_prevents_skip():
    # Departure, token, weight, identity in scrambled order: the gate must
    # never release the truck without the full evidence set.
    gate = _clearance()
    _arrive(gate)
    token_msg, _ = _token_message("m-token", at=D + timedelta(seconds=1))
    gate.handle(token_msg)
    gate.handle(_departure("m-dep", at=D + timedelta(seconds=4)))
    gate.handle(_weight("m-weight", at=D + timedelta(seconds=2)))
    visit = gate.get("V1")
    assert visit.state == VisitState.ARRIVED
    visit = gate.handle(_identity("m-id", at=D + timedelta(seconds=3)))
    assert visit.state == VisitState.EXITED
