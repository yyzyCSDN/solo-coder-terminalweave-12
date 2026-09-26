from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from terminalweave.core.clock import ensure_utc, iso_z
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class AuditRecord:
    sequence: int
    actor: str
    action: str
    subject: str
    at: datetime
    details: dict[str, object]
    previous_hash: str
    hash: str

class AuditTrail:

    def __init__(self):
        self.records: list[AuditRecord] = []

    def _digest(self, sequence: int, actor: str, action: str, subject: str, at: datetime, details: dict[str, object], previous_hash: str) -> str:
        payload = json.dumps({'sequence': sequence, 'actor': actor, 'action': action, 'subject': subject, 'at': iso_z(at), 'details': details, 'previous_hash': previous_hash}, sort_keys=True, separators=(',', ':'), default=str)
        return sha256(payload.encode()).hexdigest()

    def append(self, actor: str, action: str, subject: str, details: dict[str, object], at: datetime) -> AuditRecord:
        at = ensure_utc(at)
        if not actor or not action or (not subject):
            raise ValidationError('actor, action and subject required')
        sequence = len(self.records) + 1
        previous = self.records[-1].hash if self.records else '0' * 64
        digest = self._digest(sequence, actor, action, subject, at, details, previous)
        record = AuditRecord(sequence, actor, action, subject, at, dict(details), previous, digest)
        self.records.append(record)
        return record

    def verify(self) -> bool:
        previous = '0' * 64
        for expected, record in enumerate(self.records, start=1):
            if record.sequence != expected or record.previous_hash != previous:
                return False
            if self._digest(record.sequence, record.actor, record.action, record.subject, record.at, record.details, record.previous_hash) != record.hash:
                return False
            previous = record.hash
        return True
