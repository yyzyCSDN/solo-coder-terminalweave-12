from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class OperationalException:
    exception_id: str
    domain: str
    severity: int
    opened_at: datetime
    owner: str | None
    closed_at: datetime | None = None

    def __post_init__(self):
        object.__setattr__(self, 'opened_at', ensure_utc(self.opened_at))
        if self.closed_at is not None:
            object.__setattr__(self, 'closed_at', ensure_utc(self.closed_at))
        if not 1 <= self.severity <= 5:
            raise ValidationError('severity must be 1..5')

class ExceptionReporter:

    def backlog(self, items: list[OperationalException]) -> dict[str, object]:
        open_items = [x for x in items if x.closed_at is None]
        by_domain = {}
        by_severity = {}
        for x in open_items:
            by_domain[x.domain] = by_domain.get(x.domain, 0) + 1
            by_severity[x.severity] = by_severity.get(x.severity, 0) + 1
        return {'open': len(open_items), 'by_domain': dict(sorted(by_domain.items())), 'by_severity': dict(sorted(by_severity.items()))}

    def mean_resolution_hours(self, items: list[OperationalException]) -> float:
        values = [(x.closed_at - x.opened_at).total_seconds() / 3600 for x in items if x.closed_at is not None]
        return sum(values) / len(values) if values else 0.0
