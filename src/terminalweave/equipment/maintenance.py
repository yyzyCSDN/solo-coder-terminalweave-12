from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError, StateTransitionError

class WorkOrderState(str, Enum):
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    DONE = 'done'
    CANCELLED = 'cancelled'

@dataclass
class EquipmentMeter:
    equipment_id: str
    hours: float
    last_updated: datetime

    def __post_init__(self) -> None:
        self.last_updated = ensure_utc(self.last_updated)
        if self.hours < 0:
            raise ValidationError('meter hours cannot be negative')

    def update(self, hours: float, at: datetime) -> float:
        at = ensure_utc(at)
        if at <= self.last_updated:
            raise ValidationError('meter update must be newer')
        if hours < self.hours:
            raise ValidationError('usage meter cannot move backwards')
        delta = hours - self.hours
        self.hours = hours
        self.last_updated = at
        return delta

@dataclass(frozen=True)
class MaintenancePlan:
    plan_id: str
    interval_hours: float
    grace_hours: float = 0.0
    estimated_duration: timedelta = timedelta(hours=2)

    def __post_init__(self) -> None:
        if self.interval_hours <= 0 or self.grace_hours < 0 or self.estimated_duration.total_seconds() <= 0:
            raise ValidationError('invalid maintenance plan')

@dataclass
class WorkOrder:
    order_id: str
    equipment_id: str
    plan_id: str
    due_at_meter: float
    created_at: datetime
    state: WorkOrderState = WorkOrderState.OPEN
    started_at: datetime | None = None
    completed_at: datetime | None = None
    completed_meter: float | None = None

class MaintenanceManager:

    def __init__(self):
        self._plans: dict[str, MaintenancePlan] = {}
        self._meters: dict[str, EquipmentMeter] = {}
        self._last_service: dict[tuple[str, str], float] = {}
        self._orders: dict[str, WorkOrder] = {}

    def register_plan(self, plan: MaintenancePlan) -> None:
        self._plans[plan.plan_id] = plan

    def register_meter(self, meter: EquipmentMeter) -> None:
        self._meters[meter.equipment_id] = meter

    def due_hours(self, equipment_id: str, plan_id: str) -> float:
        plan = self._plans[plan_id]
        base = self._last_service.get((equipment_id, plan_id), 0.0)
        return base + plan.interval_hours

    def is_due(self, equipment_id: str, plan_id: str) -> bool:
        return self._meters[equipment_id].hours >= self.due_hours(equipment_id, plan_id)

    def is_overdue(self, equipment_id: str, plan_id: str) -> bool:
        plan = self._plans[plan_id]
        return self._meters[equipment_id].hours > self.due_hours(equipment_id, plan_id) + plan.grace_hours

    def open_due_orders(self, now: datetime) -> list[WorkOrder]:
        now = ensure_utc(now)
        created = []
        for equipment_id in sorted(self._meters):
            for plan_id in sorted(self._plans):
                if not self.is_due(equipment_id, plan_id):
                    continue
                existing = [o for o in self._orders.values() if o.equipment_id == equipment_id and o.plan_id == plan_id and (o.state in {WorkOrderState.OPEN, WorkOrderState.IN_PROGRESS})]
                if existing:
                    continue
                due = self.due_hours(equipment_id, plan_id)
                order = WorkOrder(f'WO-{equipment_id}-{plan_id}-{int(due)}', equipment_id, plan_id, due, now)
                self._orders[order.order_id] = order
                created.append(order)
        return created

    def start(self, order_id: str, at: datetime) -> WorkOrder:
        order = self._orders[order_id]
        at = ensure_utc(at)
        if order.state != WorkOrderState.OPEN:
            raise StateTransitionError('work order is not open')
        order.state = WorkOrderState.IN_PROGRESS
        order.started_at = at
        return order

    def complete(self, order_id: str, at: datetime) -> WorkOrder:
        order = self._orders[order_id]
        at = ensure_utc(at)
        if order.state != WorkOrderState.IN_PROGRESS:
            raise StateTransitionError('work order must be in progress')
        meter = self._meters[order.equipment_id]
        if order.started_at and at < order.started_at:
            raise ValidationError('completion cannot precede start')
        order.state = WorkOrderState.DONE
        order.completed_at = at
        order.completed_meter = meter.hours
        self._last_service[order.equipment_id, order.plan_id] = meter.hours
        return order
