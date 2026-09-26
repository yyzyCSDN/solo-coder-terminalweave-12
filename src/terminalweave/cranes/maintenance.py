from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class CraneInspection:
    crane_id: str
    performed_at: datetime
    valid_for: timedelta
    defects: tuple[str, ...] = ()
    restricted: bool = False

    def __post_init__(self):
        object.__setattr__(self, 'performed_at', ensure_utc(self.performed_at))
        if self.valid_for.total_seconds() <= 0:
            raise ValidationError('inspection validity must be positive')

    @property
    def expires_at(self):
        return self.performed_at + self.valid_for

class CraneReadiness:

    def __init__(self):
        self.inspections: dict[str, CraneInspection] = {}
        self.locks: set[str] = set()

    def record(self, inspection: CraneInspection) -> None:
        prior = self.inspections.get(inspection.crane_id)
        if prior and inspection.performed_at <= prior.performed_at:
            raise ValidationError('inspection must be newer')
        self.inspections[inspection.crane_id] = inspection

    def lock(self, crane_id: str) -> None:
        self.locks.add(crane_id)

    def unlock(self, crane_id: str) -> None:
        self.locks.discard(crane_id)

    def ready(self, crane_id: str, at: datetime) -> bool:
        at = ensure_utc(at)
        inspection = self.inspections.get(crane_id)
        return bool(inspection and crane_id not in self.locks and (not inspection.restricted) and (not inspection.defects) and (at < inspection.expires_at))

    def status(self, crane_id: str, at: datetime) -> list[str]:
        at = ensure_utc(at)
        issues = []
        inspection = self.inspections.get(crane_id)
        if crane_id in self.locks:
            issues.append('locked')
        if not inspection:
            return issues + ['no inspection']
        if inspection.defects:
            issues.extend((f'defect:{x}' for x in inspection.defects))
        if inspection.restricted:
            issues.append('restricted')
        if at >= inspection.expires_at:
            issues.append('inspection expired')
        return issues
