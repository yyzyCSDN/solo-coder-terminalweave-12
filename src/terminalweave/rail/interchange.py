from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError, ConflictError

@dataclass(frozen=True)
class InterchangeRecord:
    car_id: str
    from_railroad: str
    to_railroad: str
    at: datetime
    condition_code: str
    seal_ok: bool

    def __post_init__(self):
        object.__setattr__(self, 'at', ensure_utc(self.at))

class InterchangeLedger:

    def __init__(self):
        self.records: dict[str, list[InterchangeRecord]] = {}

    def record(self, r: InterchangeRecord) -> None:
        series = self.records.setdefault(r.car_id, [])
        if series:
            last = series[-1]
            if r.at <= last.at:
                raise ValidationError('interchange time must increase')
            if last.to_railroad != r.from_railroad:
                raise ConflictError('railroad custody chain is broken')
        series.append(r)

    def current_owner(self, car_id: str) -> str | None:
        series = self.records.get(car_id, [])
        return series[-1].to_railroad if series else None

    def seal_failures(self) -> tuple[InterchangeRecord, ...]:
        return tuple((r for series in self.records.values() for r in series if not r.seal_ok))
