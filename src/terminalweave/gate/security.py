from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class Credential:
    credential_id: str
    holder: str
    valid_from: datetime
    valid_until: datetime
    permissions: frozenset[str]
    revoked: bool = False

    def __post_init__(self):
        object.__setattr__(self, 'valid_from', ensure_utc(self.valid_from))
        object.__setattr__(self, 'valid_until', ensure_utc(self.valid_until))
        if self.valid_until <= self.valid_from:
            raise ValidationError('credential validity is empty')

class AccessController:

    def __init__(self, credentials: list[Credential]):
        self.credentials = {c.credential_id: c for c in credentials}
        self.failed: dict[str, list[datetime]] = {}

    def authorize(self, credential_id: str, permission: str, at: datetime) -> bool:
        at = ensure_utc(at)
        c = self.credentials.get(credential_id)
        ok = bool(c and (not c.revoked) and (c.valid_from <= at < c.valid_until) and (permission in c.permissions))
        if not ok:
            self.failed.setdefault(credential_id, []).append(at)
        return ok

    def recent_failures(self, credential_id: str, now: datetime, window: timedelta=timedelta(hours=1)) -> int:
        now = ensure_utc(now)
        cutoff = now - window
        values = [x for x in self.failed.get(credential_id, []) if x >= cutoff]
        self.failed[credential_id] = values
        return len(values)
