from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError, StateTransitionError

class CallState(str, Enum):
    PLANNED = 'planned'
    ARRIVED = 'arrived'
    ALL_FAST = 'all_fast'
    WORKING = 'working'
    COMPLETED = 'completed'
    SAILED = 'sailed'
    CANCELLED = 'cancelled'

@dataclass
class CallOperation:
    call_id: str
    eta: datetime
    etd: datetime
    state: CallState = CallState.PLANNED
    actuals: dict[str, datetime] = field(default_factory=dict)

    def __post_init__(self):
        self.eta = ensure_utc(self.eta)
        self.etd = ensure_utc(self.etd)
        if self.etd <= self.eta:
            raise ValidationError('ETD must follow ETA')

class CallLifecycle:
    order = [CallState.PLANNED, CallState.ARRIVED, CallState.ALL_FAST, CallState.WORKING, CallState.COMPLETED, CallState.SAILED]

    def transition(self, call: CallOperation, state: CallState, at: datetime) -> CallOperation:
        at = ensure_utc(at)
        if state == CallState.CANCELLED:
            if call.state in {CallState.COMPLETED, CallState.SAILED}:
                raise StateTransitionError('completed call cannot be cancelled')
            call.state = state
            call.actuals[state.value] = at
            return call
        if call.state == CallState.CANCELLED:
            raise StateTransitionError('cancelled call cannot transition')
        current = self.order.index(call.state)
        target = self.order.index(state)
        if target != current + 1:
            raise StateTransitionError('call transition must be sequential')
        if call.actuals and at < max(call.actuals.values()):
            raise ValidationError('actual time cannot move backwards')
        call.state = state
        call.actuals[state.value] = at
        return call

    def delay_minutes(self, call: CallOperation) -> float:
        arrived = call.actuals.get('arrived')
        return max(0.0, (arrived - call.eta).total_seconds() / 60) if arrived else 0.0
