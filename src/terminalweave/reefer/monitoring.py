from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError

class AlarmState(str, Enum):
    NORMAL = 'normal'
    PENDING = 'pending'
    ACTIVE = 'active'
    RECOVERING = 'recovering'

@dataclass(frozen=True)
class ReeferPolicy:
    low_c: float
    high_c: float
    trigger_after: timedelta
    clear_after: timedelta
    hysteresis_c: float = 0.5

    def __post_init__(self) -> None:
        if self.low_c >= self.high_c:
            raise ValidationError('low temperature must be below high temperature')
        if self.trigger_after.total_seconds() < 0 or self.clear_after.total_seconds() < 0 or self.hysteresis_c < 0:
            raise ValidationError('invalid reefer alarm policy')

@dataclass(frozen=True)
class ReeferReading:
    at: datetime
    temperature_c: float
    power_on: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, 'at', ensure_utc(self.at))
        if not -80 <= self.temperature_c <= 80:
            raise ValidationError('temperature outside supported range')

@dataclass
class ReeferAlarm:
    state: AlarmState = AlarmState.NORMAL
    state_since: datetime | None = None
    last_reading: ReeferReading | None = None
    excursions: int = 0

class ReeferMonitor:

    def __init__(self, policy: ReeferPolicy):
        self.policy = policy
        self.alarm = ReeferAlarm()

    def _outside(self, reading: ReeferReading) -> bool:
        return not reading.power_on or reading.temperature_c < self.policy.low_c or reading.temperature_c > self.policy.high_c

    def _inside_clear_band(self, reading: ReeferReading) -> bool:
        return reading.power_on and self.policy.low_c + self.policy.hysteresis_c <= reading.temperature_c <= self.policy.high_c - self.policy.hysteresis_c

    def ingest(self, reading: ReeferReading) -> AlarmState:
        alarm = self.alarm
        if alarm.last_reading and reading.at <= alarm.last_reading.at:
            raise ValidationError('readings must arrive in strictly increasing time order')
        outside = self._outside(reading)
        clear_band = self._inside_clear_band(reading)
        if alarm.state == AlarmState.NORMAL:
            if outside:
                alarm.state = AlarmState.PENDING
                alarm.state_since = reading.at
        elif alarm.state == AlarmState.PENDING:
            if not outside:
                alarm.state = AlarmState.NORMAL
                alarm.state_since = reading.at
            elif alarm.state_since and reading.at - alarm.state_since >= self.policy.trigger_after:
                alarm.state = AlarmState.ACTIVE
                alarm.state_since = reading.at
                alarm.excursions += 1
        elif alarm.state == AlarmState.ACTIVE:
            if clear_band:
                alarm.state = AlarmState.RECOVERING
                alarm.state_since = reading.at
        elif alarm.state == AlarmState.RECOVERING:
            if outside:
                alarm.state = AlarmState.ACTIVE
                alarm.state_since = reading.at
            elif not clear_band:
                alarm.state = AlarmState.RECOVERING
            elif alarm.state_since and reading.at - alarm.state_since >= self.policy.clear_after:
                alarm.state = AlarmState.NORMAL
                alarm.state_since = reading.at
        alarm.last_reading = reading
        return alarm.state

    def seconds_in_state(self, now: datetime) -> float:
        now = ensure_utc(now)
        if self.alarm.state_since is None:
            return 0.0
        return max(0.0, (now - self.alarm.state_since).total_seconds())
