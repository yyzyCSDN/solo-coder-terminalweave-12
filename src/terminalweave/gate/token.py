from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
import hmac, secrets
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class GateToken:
    token_id: str
    visit_id: str
    issued_at: datetime
    expires_at: datetime
    signature: str

class GateTokenIssuer:

    def __init__(self, secret: bytes):
        if len(secret) < 16:
            raise ValidationError('secret must be at least 16 bytes')
        self.secret = secret

    def _sign(self, token_id: str, visit_id: str, issued: datetime, expires: datetime) -> str:
        message = f'{token_id}|{visit_id}|{issued.isoformat()}|{expires.isoformat()}'.encode()
        return hmac.new(self.secret, message, sha256).hexdigest()

    def issue(self, visit_id: str, at: datetime, ttl: timedelta=timedelta(hours=2)) -> GateToken:
        at = ensure_utc(at)
        if ttl.total_seconds() <= 0:
            raise ValidationError('TTL must be positive')
        token_id = secrets.token_hex(12)
        expires = at + ttl
        signature = self._sign(token_id, visit_id, at, expires)
        return GateToken(token_id, visit_id, at, expires, signature)

    def verify(self, token: GateToken, at: datetime) -> bool:
        at = ensure_utc(at)
        if at < token.issued_at or at >= token.expires_at:
            return False
        expected = self._sign(token.token_id, token.visit_id, token.issued_at, token.expires_at)
        return hmac.compare_digest(expected, token.signature)
