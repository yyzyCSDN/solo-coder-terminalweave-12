from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError, SafetyConstraintError

@dataclass(frozen=True)
class ChannelLeg:
    leg_id: str
    length_nm: float
    width_m: float
    chart_depth_m: float
    speed_limit_kn: float
    one_way: bool = False

    def __post_init__(self) -> None:
        if min(self.length_nm, self.width_m, self.chart_depth_m, self.speed_limit_kn) <= 0:
            raise ValidationError('channel leg values must be positive')

@dataclass(frozen=True)
class TransitRequirement:
    draft_m: float
    beam_m: float
    requested_speed_kn: float
    minimum_depth_margin_m: float
    beam_clearance_factor: float = 1.5

@dataclass(frozen=True)
class TransitLegResult:
    leg_id: str
    speed_kn: float
    hours: float
    width_margin_m: float
    depth_margin_m: float

class ChannelRoute:

    def __init__(self, legs: list[ChannelLeg]):
        if not legs:
            raise ValidationError('route needs at least one leg')
        if len({l.leg_id for l in legs}) != len(legs):
            raise ValidationError('duplicate channel leg')
        self.legs = tuple(legs)

    def evaluate(self, requirement: TransitRequirement, tide_by_leg: dict[str, float] | None=None) -> list[TransitLegResult]:
        tide_by_leg = tide_by_leg or {}
        results = []
        for leg in self.legs:
            depth = leg.chart_depth_m + tide_by_leg.get(leg.leg_id, 0.0)
            depth_margin = depth - requirement.draft_m
            width_margin = leg.width_m - requirement.beam_m * requirement.beam_clearance_factor
            if depth_margin < requirement.minimum_depth_margin_m:
                raise SafetyConstraintError(f'insufficient depth on {leg.leg_id}')
            if width_margin < 0:
                raise SafetyConstraintError(f'insufficient width on {leg.leg_id}')
            speed = min(requirement.requested_speed_kn, leg.speed_limit_kn)
            if speed <= 0:
                raise ValidationError('transit speed must be positive')
            results.append(TransitLegResult(leg.leg_id, speed, leg.length_nm / speed, width_margin, depth_margin))
        return results

    def total_hours(self, requirement: TransitRequirement, tide_by_leg: dict[str, float] | None=None) -> float:
        return sum((x.hours for x in self.evaluate(requirement, tide_by_leg)))

    def has_one_way_leg(self) -> bool:
        return any((l.one_way for l in self.legs))
