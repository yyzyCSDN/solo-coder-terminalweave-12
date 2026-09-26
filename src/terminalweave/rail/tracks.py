from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError, CapacityError

@dataclass(frozen=True)
class YardTrack:
    track_id: str
    usable_length_m: float
    electrified: bool = False
    service_track: bool = False

    def __post_init__(self):
        if self.usable_length_m <= 0:
            raise ValidationError('track length must be positive')

@dataclass(frozen=True)
class TrainMovement:
    train_id: str
    length_m: float
    needs_electric: bool = False
    needs_service: bool = False

class TrackAllocator:

    def __init__(self, tracks: list[YardTrack]):
        self.tracks = {t.track_id: t for t in tracks}
        self.occupied: dict[str, str] = {}

    def allocate(self, m: TrainMovement) -> str:
        candidates = []
        for t in self.tracks.values():
            if t.track_id in self.occupied or t.usable_length_m < m.length_m:
                continue
            if m.needs_electric and (not t.electrified):
                continue
            if m.needs_service and (not t.service_track):
                continue
            candidates.append((t.usable_length_m - m.length_m, t.track_id))
        if not candidates:
            raise CapacityError('no compatible yard track')
        _, track = min(candidates)
        self.occupied[track] = m.train_id
        return track

    def release(self, track_id: str) -> str | None:
        return self.occupied.pop(track_id, None)
