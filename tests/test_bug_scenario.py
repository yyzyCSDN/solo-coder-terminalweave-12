from datetime import datetime, timezone

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
