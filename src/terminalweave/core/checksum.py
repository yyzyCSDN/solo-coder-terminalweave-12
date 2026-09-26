from __future__ import annotations
from hashlib import sha256
import json
from terminalweave.core.errors import ValidationError

class PayloadChecksum:

    @staticmethod
    def canonical_bytes(payload: dict[str, object]) -> bytes:
        if not isinstance(payload, dict):
            raise ValidationError('payload must be a mapping')
        return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False, default=str).encode('utf-8')

    @classmethod
    def digest(cls, payload: dict[str, object]) -> str:
        return sha256(cls.canonical_bytes(payload)).hexdigest()

    @classmethod
    def verify(cls, payload: dict[str, object], expected: str) -> bool:
        if len(expected) != 64:
            return False
        return cls.digest(payload) == expected.lower()

CHECKSUM_ALGORITHM = "sha256"
CHECKSUM_HEX_LENGTH = 64
