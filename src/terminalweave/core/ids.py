from __future__ import annotations
import re
from dataclasses import dataclass
from uuid import uuid4
from .errors import ValidationError
_ALLOWED = re.compile('^[A-Z0-9][A-Z0-9._-]{1,63}$')

@dataclass(frozen=True, order=True)
class EntityId:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()
        if not _ALLOWED.match(normalized):
            raise ValidationError(f'invalid entity id: {self.value!r}')
        object.__setattr__(self, 'value', normalized)

    def __str__(self) -> str:
        return self.value

def new_id(prefix: str) -> EntityId:
    p = prefix.strip().upper()
    if not re.fullmatch('[A-Z][A-Z0-9]{1,7}', p):
        raise ValidationError('prefix must be 2-8 uppercase alphanumeric characters')
    return EntityId(f'{p}-{uuid4().hex[:16].upper()}')
