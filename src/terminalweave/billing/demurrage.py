from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError
from terminalweave.core.money import Money

@dataclass(frozen=True)
class TariffBand:
    from_day: int
    to_day: int | None
    daily_rate: Money

    def __post_init__(self) -> None:
        if self.from_day < 1 or (self.to_day is not None and self.to_day < self.from_day):
            raise ValidationError('invalid tariff band')

class BusinessCalendar:

    def __init__(self, holidays: set[date] | None=None, weekends_free: bool=True):
        self.holidays = set(holidays or set())
        self.weekends_free = weekends_free

    def is_chargeable(self, day: date) -> bool:
        if day in self.holidays:
            return False
        if self.weekends_free and day.weekday() >= 5:
            return False
        return True

    def chargeable_days(self, start: date, end_inclusive: date) -> list[date]:
        if end_inclusive < start:
            return []
        result = []
        cursor = start
        while cursor <= end_inclusive:
            if self.is_chargeable(cursor):
                result.append(cursor)
            cursor += timedelta(days=1)
        return result

@dataclass(frozen=True)
class DemurrageTariff:
    free_chargeable_days: int
    bands: tuple[TariffBand, ...]

    def __post_init__(self) -> None:
        if self.free_chargeable_days < 0 or not self.bands:
            raise ValidationError('invalid demurrage tariff')
        ordered = sorted(self.bands, key=lambda b: b.from_day)
        if ordered[0].from_day != 1:
            raise ValidationError('tariff bands must start at day 1')
        previous_end = 0
        for band in ordered:
            if band.from_day != previous_end + 1:
                raise ValidationError('tariff bands must be contiguous')
            previous_end = band.to_day if band.to_day is not None else previous_end
            if band.to_day is None and band is not ordered[-1]:
                raise ValidationError('open-ended band must be last')

    def rate_for_charge_day(self, charge_day: int) -> Money:
        for band in self.bands:
            if charge_day >= band.from_day and (band.to_day is None or charge_day <= band.to_day):
                return band.daily_rate
        raise ValidationError('no tariff band for charge day')

@dataclass(frozen=True)
class DemurrageLine:
    day: date
    charge_day_number: int
    amount: Money

class DemurrageCalculator:

    def __init__(self, calendar: BusinessCalendar, tariff: DemurrageTariff):
        self.calendar = calendar
        self.tariff = tariff

    def calculate(self, discharge_at: datetime, gate_out_at: datetime) -> list[DemurrageLine]:
        discharge_at = ensure_utc(discharge_at)
        gate_out_at = ensure_utc(gate_out_at)
        if gate_out_at < discharge_at:
            raise ValidationError('gate-out cannot precede discharge')
        days = self.calendar.chargeable_days(discharge_at.date(), gate_out_at.date())
        billable = days[self.tariff.free_chargeable_days:]
        lines = []
        for index, day in enumerate(billable, start=1):
            lines.append(DemurrageLine(day, index, self.tariff.rate_for_charge_day(index)))
        return lines

    def total(self, discharge_at: datetime, gate_out_at: datetime) -> Money:
        lines = self.calculate(discharge_at, gate_out_at)
        if not lines:
            currency = self.tariff.bands[0].daily_rate.currency
            return Money.zero(currency)
        total = Money.zero(lines[0].amount.currency)
        for line in lines:
            total = total + line.amount
        return total
