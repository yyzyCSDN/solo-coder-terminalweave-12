from __future__ import annotations
from datetime import datetime, timezone
from .errors import ValidationError
UTC = timezone.utc

def utc_now() -> datetime:
    return datetime.now(tz=UTC)

def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError('datetime must be timezone-aware')
    return value.astimezone(UTC)

def iso_z(value: datetime) -> str:
    return ensure_utc(value).isoformat().replace('+00:00', 'Z')

def parse_iso_z(text: str) -> datetime:
    cleaned = text.strip().replace('Z', '+00:00')
    try:
        return ensure_utc(datetime.fromisoformat(cleaned))
    except ValueError as exc:
        raise ValidationError(f'invalid ISO datetime: {text}') from exc
