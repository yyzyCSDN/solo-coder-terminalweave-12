from __future__ import annotations
from dataclasses import asdict, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from .clock import iso_z

def to_primitive(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return iso_z(value)
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {k: to_primitive(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): to_primitive(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_primitive(v) for v in value]
    return str(value)
