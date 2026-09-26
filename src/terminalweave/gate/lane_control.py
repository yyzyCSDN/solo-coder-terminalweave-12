from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from terminalweave.core.errors import ValidationError, StateTransitionError

class LaneMode(str, Enum):
    CLOSED = 'closed'
    ENTRY = 'entry'
    EXIT = 'exit'
    FLEX = 'flex'

@dataclass
class GateLaneState:
    lane_id: str
    mode: LaneMode = LaneMode.CLOSED
    occupied: bool = False
    direction_lock: str | None = None

class LaneController:

    def __init__(self, lanes: list[str]):
        if len(lanes) != len(set(lanes)):
            raise ValidationError('duplicate lane')
        self.states = {x: GateLaneState(x) for x in lanes}

    def set_mode(self, lane_id: str, mode: LaneMode) -> GateLaneState:
        state = self.states[lane_id]
        if state.occupied and mode == LaneMode.CLOSED:
            raise StateTransitionError('occupied lane cannot be closed')
        if state.direction_lock and mode.value not in {state.direction_lock, LaneMode.FLEX.value}:
            raise StateTransitionError('lane direction is locked')
        state.mode = mode
        return state

    def enter(self, lane_id: str, direction: str) -> GateLaneState:
        state = self.states[lane_id]
        if state.occupied:
            raise StateTransitionError('lane already occupied')
        if direction not in {'entry', 'exit'}:
            raise ValidationError('invalid direction')
        if state.mode == LaneMode.CLOSED:
            raise StateTransitionError('lane is closed')
        if state.mode not in {LaneMode.FLEX, LaneMode(direction)}:
            raise StateTransitionError('lane direction does not match movement')
        state.occupied = True
        state.direction_lock = direction
        return state

    def leave(self, lane_id: str) -> GateLaneState:
        state = self.states[lane_id]
        if not state.occupied:
            raise StateTransitionError('lane is empty')
        state.occupied = False
        state.direction_lock = None
        return state

    def open_count(self, direction: str) -> int:
        return sum((s.mode in {LaneMode.FLEX, LaneMode(direction)} for s in self.states.values()))
