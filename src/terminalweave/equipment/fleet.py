from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from terminalweave.core.errors import ValidationError, StateTransitionError

class EquipmentState(str, Enum):
    AVAILABLE = 'available'
    WORKING = 'working'
    CHARGING = 'charging'
    MAINTENANCE = 'maintenance'
    OUT_OF_SERVICE = 'out_of_service'

@dataclass
class Equipment:
    equipment_id: str
    kind: str
    capacity_tonnes: float
    state: EquipmentState = EquipmentState.AVAILABLE
    location: str | None = None
    battery_percent: float | None = None

    def __post_init__(self):
        if self.capacity_tonnes <= 0:
            raise ValidationError('capacity must be positive')
        if self.battery_percent is not None and (not 0 <= self.battery_percent <= 100):
            raise ValidationError('battery percent must be 0..100')

class FleetRegistry:

    def __init__(self):
        self.items: dict[str, Equipment] = {}

    def add(self, item: Equipment) -> None:
        if item.equipment_id in self.items:
            raise ValidationError('duplicate equipment id')
        self.items[item.equipment_id] = item

    def transition(self, equipment_id: str, new_state: EquipmentState) -> Equipment:
        item = self.items[equipment_id]
        allowed = {EquipmentState.AVAILABLE: {EquipmentState.WORKING, EquipmentState.CHARGING, EquipmentState.MAINTENANCE, EquipmentState.OUT_OF_SERVICE}, EquipmentState.WORKING: {EquipmentState.AVAILABLE, EquipmentState.OUT_OF_SERVICE}, EquipmentState.CHARGING: {EquipmentState.AVAILABLE, EquipmentState.OUT_OF_SERVICE}, EquipmentState.MAINTENANCE: {EquipmentState.AVAILABLE, EquipmentState.OUT_OF_SERVICE}, EquipmentState.OUT_OF_SERVICE: {EquipmentState.MAINTENANCE, EquipmentState.AVAILABLE}}
        if new_state not in allowed[item.state]:
            raise StateTransitionError(f'cannot transition {item.state} -> {new_state}')
        item.state = new_state
        return item

    def update_location(self, equipment_id: str, location: str) -> None:
        if not location.strip():
            raise ValidationError('location required')
        self.items[equipment_id].location = location

    def available(self, kind: str | None=None) -> tuple[Equipment, ...]:
        values = [x for x in self.items.values() if x.state == EquipmentState.AVAILABLE and (kind is None or x.kind == kind)]
        return tuple(sorted(values, key=lambda x: x.equipment_id))

    def low_battery(self, threshold: float) -> tuple[Equipment, ...]:
        if not 0 <= threshold <= 100:
            raise ValidationError('threshold must be 0..100')
        return tuple((x for x in self.items.values() if x.battery_percent is not None and x.battery_percent < threshold))
