from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from terminalweave.core.errors import ValidationError

class VesselType(str, Enum):
    FEEDER = 'feeder'
    PANAMAX = 'panamax'
    POST_PANAMAX = 'post_panamax'
    ULCS = 'ulcs'

@dataclass(frozen=True)
class VesselProfile:
    imo: str
    name: str
    vessel_type: VesselType
    loa_m: float
    beam_m: float
    summer_draft_m: float
    air_draft_m: float
    teu_capacity: int
    bow_thruster: bool = True
    stern_thruster: bool = False

    def __post_init__(self) -> None:
        if not (self.imo.isdigit() and len(self.imo) == 7):
            raise ValidationError('IMO number must contain seven digits')
        if min(self.loa_m, self.beam_m, self.summer_draft_m, self.air_draft_m) <= 0:
            raise ValidationError('vessel dimensions must be positive')
        if self.teu_capacity <= 0:
            raise ValidationError('TEU capacity must be positive')

    @property
    def aspect_ratio(self) -> float:
        return self.loa_m / self.beam_m

    def draft_margin(self, actual_draft_m: float) -> float:
        if actual_draft_m <= 0 or actual_draft_m > self.summer_draft_m + 0.5:
            raise ValidationError('actual draft is implausible')
        return self.summer_draft_m - actual_draft_m

class VesselRegistry:

    def __init__(self):
        self._profiles: dict[str, VesselProfile] = {}

    def register(self, profile: VesselProfile) -> None:
        prior = self._profiles.get(profile.imo)
        if prior and prior != profile:
            raise ValidationError('IMO number already registered with different profile')
        self._profiles[profile.imo] = profile

    def get(self, imo: str) -> VesselProfile:
        try:
            return self._profiles[imo]
        except KeyError as exc:
            raise ValidationError('unknown vessel') from exc

    def by_type(self, vessel_type: VesselType) -> tuple[VesselProfile, ...]:
        return tuple(sorted((v for v in self._profiles.values() if v.vessel_type == vessel_type), key=lambda v: v.name))

    def compatible_with_bridge(self, max_air_draft_m: float) -> tuple[VesselProfile, ...]:
        if max_air_draft_m <= 0:
            raise ValidationError('bridge clearance must be positive')
        return tuple((v for v in self._profiles.values() if v.air_draft_m <= max_air_draft_m))

    def fleet_teu(self) -> int:
        return sum((v.teu_capacity for v in self._profiles.values()))
