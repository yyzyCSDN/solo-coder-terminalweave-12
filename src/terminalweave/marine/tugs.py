from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError, CapacityError

@dataclass(frozen=True)
class Tug:
    tug_id: str
    bollard_pull_t: float
    azimuthing: bool
    firefighting: bool = False

    def __post_init__(self):
        if self.bollard_pull_t <= 0:
            raise ValidationError('bollard pull must be positive')

@dataclass(frozen=True)
class TugRequirement:
    minimum_total_pull_t: float
    minimum_count: int
    require_azimuthing: int = 0
    require_firefighting: bool = False

class TugAllocator:

    def __init__(self, tugs: list[Tug]):
        self.tugs = {t.tug_id: t for t in tugs}
        self.busy: set[str] = set()

    def allocate(self, req: TugRequirement) -> tuple[Tug, ...]:
        candidates = [t for t in self.tugs.values() if t.tug_id not in self.busy]
        candidates.sort(key=lambda t: (not t.firefighting if req.require_firefighting else False, not t.azimuthing, -t.bollard_pull_t, t.tug_id))
        chosen = []
        pull = 0.0
        for tug in candidates:
            chosen.append(tug)
            pull += tug.bollard_pull_t
            if len(chosen) >= req.minimum_count and pull >= req.minimum_total_pull_t and (sum((t.azimuthing for t in chosen)) >= req.require_azimuthing) and (not req.require_firefighting or any((t.firefighting for t in chosen))):
                break
        if len(chosen) < req.minimum_count or pull < req.minimum_total_pull_t or sum((t.azimuthing for t in chosen)) < req.require_azimuthing or (req.require_firefighting and (not any((t.firefighting for t in chosen)))):
            raise CapacityError('tug requirement cannot be met')
        self.busy.update((t.tug_id for t in chosen))
        return tuple(chosen)

    def release(self, *tug_ids: str) -> None:
        for x in tug_ids:
            self.busy.discard(x)
