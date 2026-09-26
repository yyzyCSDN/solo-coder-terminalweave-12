from __future__ import annotations
from dataclasses import dataclass
from datetime import timedelta
from terminalweave.core.errors import ValidationError, CapacityError
from terminalweave.core.intervals import TimeInterval

@dataclass(frozen=True)
class Pilot:
    pilot_id: str
    max_loa_m: float
    night_qualified: bool
    district: str
    max_shift: timedelta = timedelta(hours=8)

    def __post_init__(self) -> None:
        if self.max_loa_m <= 0 or self.max_shift.total_seconds() <= 0:
            raise ValidationError('invalid pilot profile')

@dataclass(frozen=True)
class PilotJob:
    job_id: str
    district: str
    vessel_loa_m: float
    interval: TimeInterval
    night: bool = False

@dataclass(frozen=True)
class PilotAssignment:
    pilot_id: str
    job_id: str
    interval: TimeInterval

class PilotRoster:

    def __init__(self, pilots: list[Pilot], rest_between_jobs: timedelta=timedelta(minutes=30)):
        if rest_between_jobs.total_seconds() < 0:
            raise ValidationError('rest cannot be negative')
        self.pilots = {p.pilot_id: p for p in pilots}
        self.rest = rest_between_jobs
        self.assignments: list[PilotAssignment] = []

    def eligible(self, pilot: Pilot, job: PilotJob) -> bool:
        if pilot.district != job.district or job.vessel_loa_m > pilot.max_loa_m:
            return False
        if job.night and (not pilot.night_qualified):
            return False
        if job.interval.duration > pilot.max_shift:
            return False
        for a in self.assignments:
            if a.pilot_id != pilot.pilot_id:
                continue
            expanded = TimeInterval(a.interval.start - self.rest, a.interval.end + self.rest)
            if expanded.overlaps(job.interval):
                return False
        return True

    def assign(self, job: PilotJob) -> PilotAssignment:
        candidates = [p for p in self.pilots.values() if self.eligible(p, job)]
        if not candidates:
            raise CapacityError('no qualified rested pilot is available')

        def workload(p: Pilot) -> float:
            return sum((a.interval.duration.total_seconds() for a in self.assignments if a.pilot_id == p.pilot_id))
        chosen = min(candidates, key=lambda p: (workload(p), p.pilot_id))
        assignment = PilotAssignment(chosen.pilot_id, job.job_id, job.interval)
        self.assignments.append(assignment)
        return assignment

    def release(self, job_id: str) -> bool:
        before = len(self.assignments)
        self.assignments = [a for a in self.assignments if a.job_id != job_id]
        return len(self.assignments) != before

    def duty_seconds(self, pilot_id: str, window: TimeInterval) -> float:
        total = 0.0
        for a in self.assignments:
            if a.pilot_id != pilot_id:
                continue
            overlap = a.interval.intersection(window)
            if overlap:
                total += overlap.duration.total_seconds()
        return total
