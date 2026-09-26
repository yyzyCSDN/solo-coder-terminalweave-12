from datetime import datetime,timedelta,timezone
from terminalweave.persistence.event_store import InMemoryEventStore
from terminalweave.persistence.repository import VersionedRepository
from terminalweave.reporting.audit import AuditTrail
from terminalweave.gate.queues import Lane,TruckArrival,GateQueueSimulator
from terminalweave.gate.ocr import OcrCandidate,ContainerOcrResolver
from terminalweave.reefer.power import PowerCircuit,ReeferLoad,ReeferPowerBoard
from terminalweave.equipment.charging import Charger,ChargeRequest,ChargePlanner
from terminalweave.planning.optimizer import PlannedJob,SmallBatchOptimizer
from terminalweave.api.service import TerminalService

UTC=timezone.utc
D=datetime(2026,1,1,tzinfo=UTC)

def test_event_store_optimistic_sequence():
    s=InMemoryEventStore();e=s.append("x",0,"created",{"a":1},D)
    assert e.sequence==1 and s.current_sequence("x")==1

def test_repository_versions():
    r=VersionedRepository();v=r.put("x",{"a":1},0);assert v==1
    assert r.get("x")== (1,{"a":1})

def test_audit_chain_verifies():
    a=AuditTrail();a.append("u","create","x",{"v":1},D);a.append("u","edit","x",{"v":2},D+timedelta(seconds=1))
    assert a.verify()

def test_gate_queue_assigns_lane():
    sim=GateQueueSimulator([Lane("L",D,D+timedelta(hours=2))])
    rows=sim.simulate([TruckArrival("T",D,60)])
    assert rows[0].lane_id=="L" and rows[0].wait_seconds==0

def test_ocr_accepts_valid_high_confidence():
    result=ContainerOcrResolver().resolve([OcrCandidate("ABCD1234567",0.99)])
    assert result.value=="ABCD1234567" and not result.manual_review

def test_reefer_power_connection():
    board=ReeferPowerBoard([PowerCircuit("A",20,0.1)])
    assert board.connect(ReeferLoad("C",5,1.5))=="A"

def test_charge_planner_meets_deadline():
    req=ChargeRequest("E",100,20,80,D,D+timedelta(hours=4))
    charger,finish=ChargePlanner().choose([Charger("C",50,1.0)],req)
    assert charger.charger_id=="C" and finish<=req.required_by

def test_small_optimizer_returns_all_jobs():
    jobs=[PlannedJob("A",20,1,50,"x"),PlannedJob("B",10,0,15,"x")]
    out=SmallBatchOptimizer().optimize(jobs)
    assert {x.job_id for x in out}=={"A","B"}

def test_service_health_and_tide():
    svc=TerminalService();assert svc.health()["status"]=="ok"
    r=svc.tide_clearance({"samples":[{"at":"2026-01-01T00:00:00Z","height_m":0},{"at":"2026-01-01T02:00:00Z","height_m":2}],"chart_depth_m":10,"draft_m":9,"minimum_clearance_m":1,"at":"2026-01-01T01:00:00Z"})
    assert r["safe"]
