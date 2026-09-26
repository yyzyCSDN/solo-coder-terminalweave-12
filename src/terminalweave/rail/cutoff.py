from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class TrainCutoff:
    train_id: str
    departure: datetime
    documentation_before: timedelta
    physical_before: timedelta

    def __post_init__(self):
        object.__setattr__(self, 'departure', ensure_utc(self.departure))
        if self.documentation_before.total_seconds() < 0 or self.physical_before.total_seconds() < 0:
            raise ValidationError('cutoffs cannot be negative')

    @property
    def documentation_deadline(self) -> datetime:
        return self.departure - self.documentation_before

    @property
    def physical_deadline(self) -> datetime:
        return self.departure - self.physical_before

@dataclass(frozen=True)
class ContainerReadiness:
    container_id: str
    documentation_ready_at: datetime
    yard_ready_at: datetime

    def __post_init__(self):
        object.__setattr__(self, 'documentation_ready_at', ensure_utc(self.documentation_ready_at))
        object.__setattr__(self, 'yard_ready_at', ensure_utc(self.yard_ready_at))

class CutoffChecker:

    def evaluate(self, cutoff: TrainCutoff, readiness: ContainerReadiness) -> dict[str, object]:
        doc_ok = readiness.documentation_ready_at <= cutoff.documentation_deadline
        physical_ok = readiness.yard_ready_at <= cutoff.physical_deadline
        return {'container_id': readiness.container_id, 'documentation_ok': doc_ok, 'physical_ok': physical_ok, 'eligible': doc_ok and physical_ok, 'document_slack_seconds': (cutoff.documentation_deadline - readiness.documentation_ready_at).total_seconds(), 'physical_slack_seconds': (cutoff.physical_deadline - readiness.yard_ready_at).total_seconds()}

    def rank_risk(self, cutoff: TrainCutoff, items: list[ContainerReadiness]) -> list[dict[str, object]]:
        rows = [self.evaluate(cutoff, x) for x in items]
        return sorted(rows, key=lambda r: (r['eligible'], min(r['document_slack_seconds'], r['physical_slack_seconds']), r['container_id']))
