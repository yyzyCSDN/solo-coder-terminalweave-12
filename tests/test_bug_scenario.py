from datetime import datetime, timedelta, timezone

import pytest

from terminalweave.core.errors import ConflictError, StateTransitionError
from terminalweave.gate.truck_visit import TruckVisit, TruckVisitFlow, VisitState


UTC = timezone.utc
D = datetime(2026, 1, 1, tzinfo=UTC)


def test_replayed_gate_state_message_does_not_execute_transition_twice():
    flow = TruckVisitFlow()
    visit = TruckVisit("V1", "TRUCK1", None)
    flow.transition(visit, VisitState.ARRIVED, D)
    flow.transition(visit, VisitState.ARRIVED, D)
    assert visit.state == VisitState.ARRIVED
    assert visit.timestamps == {"arrived": D}


def test_out_of_order_evidence_merges_before_release():
    flow = TruckVisitFlow()
    visit = TruckVisit("V1", "TRUCK1", None)
    flow.transition(visit, VisitState.ARRIVED, D)
    flow.transition(visit, VisitState.INSIDE, D + timedelta(minutes=5))
    # weighing, identification and container messages arrive out of order
    flow.record_weight(visit, "W1")
    flow.confirm_identity(visit)
    flow.record_container(visit, "MSCU1234567")
    assert flow.evidence_complete(visit)
    flow.transition(visit, VisitState.RELEASED, D + timedelta(minutes=30))
    flow.transition(visit, VisitState.EXITED, D + timedelta(minutes=40))
    assert visit.state == VisitState.EXITED


def test_release_waits_for_complete_evidence():
    flow = TruckVisitFlow()
    visit = TruckVisit("V1", "TRUCK1", None)
    flow.transition(visit, VisitState.ARRIVED, D)
    flow.transition(visit, VisitState.INSIDE, D + timedelta(minutes=5))
    flow.confirm_identity(visit)
    flow.record_container(visit, "MSCU1234567")
    with pytest.raises(StateTransitionError):
        flow.transition(visit, VisitState.RELEASED, D + timedelta(minutes=30))
    assert visit.state == VisitState.INSIDE
    assert "released" not in visit.timestamps
    flow.record_weight(visit, "W1")
    flow.transition(visit, VisitState.RELEASED, D + timedelta(minutes=30))
    assert visit.state == VisitState.RELEASED


def test_duplicate_evidence_messages_do_not_execute_twice():
    flow = TruckVisitFlow()
    visit = TruckVisit("V1", "TRUCK1", None)
    flow.record_container(visit, "mscu1234567")
    flow.record_container(visit, "MSCU1234567")
    flow.record_weight(visit, "W1")
    flow.record_weight(visit, "W1")
    flow.confirm_identity(visit)
    flow.confirm_identity(visit)
    assert visit.container_id == "MSCU1234567"
    assert visit.weight_ticket_id == "W1"
    assert visit.identity_verified
    with pytest.raises(ConflictError):
        flow.record_container(visit, "TGHU7654321")
    with pytest.raises(ConflictError):
        flow.record_weight(visit, "W2")


def test_stale_message_for_passed_state_is_absorbed():
    flow = TruckVisitFlow()
    visit = TruckVisit("V1", "TRUCK1", None)
    flow.transition(visit, VisitState.ARRIVED, D)
    flow.transition(visit, VisitState.INSIDE, D + timedelta(minutes=5))
    flow.transition(visit, VisitState.ARRIVED, D)
    assert visit.state == VisitState.INSIDE
    assert visit.timestamps == {
        "arrived": D,
        "inside": D + timedelta(minutes=5),
    }


def test_state_cannot_skip_checks():
    flow = TruckVisitFlow()
    visit = TruckVisit("V1", "TRUCK1", None)
    with pytest.raises(StateTransitionError):
        flow.transition(visit, VisitState.INSIDE, D)
    assert visit.state == VisitState.EXPECTED


def test_rejected_visit_cannot_continue_flowing():
    flow = TruckVisitFlow()
    visit = TruckVisit("V1", "TRUCK1", None)
    flow.transition(visit, VisitState.ARRIVED, D)
    flow.transition(visit, VisitState.REJECTED, D + timedelta(minutes=5))
    flow.transition(visit, VisitState.REJECTED, D + timedelta(minutes=6))
    assert visit.state == VisitState.REJECTED
    assert visit.timestamps["rejected"] == D + timedelta(minutes=5)
    with pytest.raises(StateTransitionError):
        flow.transition(visit, VisitState.INSIDE, D + timedelta(minutes=10))
    with pytest.raises(StateTransitionError):
        flow.confirm_identity(visit)
    with pytest.raises(StateTransitionError):
        flow.record_container(visit, "MSCU1234567")
    with pytest.raises(StateTransitionError):
        flow.record_weight(visit, "W1")
    assert visit.state == VisitState.REJECTED
