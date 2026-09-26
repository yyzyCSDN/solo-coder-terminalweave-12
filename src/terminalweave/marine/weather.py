from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from terminalweave.core.clock import ensure_utc
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class WeatherSample:
    at: datetime
    wind_kn: float
    gust_kn: float
    visibility_nm: float
    wave_m: float
    lightning: bool = False

    def __post_init__(self):
        object.__setattr__(self, 'at', ensure_utc(self.at))
        if min(self.wind_kn, self.gust_kn, self.visibility_nm, self.wave_m) < 0:
            raise ValidationError('weather values cannot be negative')

@dataclass(frozen=True)
class MarineWeatherLimits:
    max_wind_kn: float
    max_gust_kn: float
    min_visibility_nm: float
    max_wave_m: float
    prohibit_lightning: bool = True

    def __post_init__(self):
        if min(self.max_wind_kn, self.max_gust_kn, self.min_visibility_nm, self.max_wave_m) < 0:
            raise ValidationError('invalid weather limits')

class WeatherWindowChecker:

    def __init__(self, limits: MarineWeatherLimits):
        self.limits = limits

    def acceptable(self, s: WeatherSample) -> bool:
        return s.wind_kn <= self.limits.max_wind_kn and s.gust_kn <= self.limits.max_gust_kn and (s.visibility_nm >= self.limits.min_visibility_nm) and (s.wave_m <= self.limits.max_wave_m) and (not (self.limits.prohibit_lightning and s.lightning))

    def reasons(self, s: WeatherSample) -> list[str]:
        reasons = []
        if s.wind_kn > self.limits.max_wind_kn:
            reasons.append('sustained wind')
        if s.gust_kn > self.limits.max_gust_kn:
            reasons.append('wind gust')
        if s.visibility_nm < self.limits.min_visibility_nm:
            reasons.append('visibility')
        if s.wave_m > self.limits.max_wave_m:
            reasons.append('wave height')
        if self.limits.prohibit_lightning and s.lightning:
            reasons.append('lightning')
        return reasons

    def continuous_clearance(self, samples: list[WeatherSample], minimum_duration: timedelta) -> list[tuple[datetime, datetime]]:
        if minimum_duration.total_seconds() < 0:
            raise ValidationError('duration cannot be negative')
        items = sorted(samples, key=lambda x: x.at)
        result = []
        start = None
        for s in items:
            if self.acceptable(s) and start is None:
                start = s.at
            if not self.acceptable(s) and start is not None:
                if s.at - start >= minimum_duration:
                    result.append((start, s.at))
                start = None
        if start is not None and items[-1].at - start >= minimum_duration:
            result.append((start, items[-1].at))
        return result
