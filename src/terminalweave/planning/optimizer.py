from __future__ import annotations
from dataclasses import dataclass
from itertools import permutations
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class PlannedJob:
    job_id: str
    duration_minutes: int
    priority: int
    due_minute: int
    resource_group: str

    def __post_init__(self):
        if self.duration_minutes <= 0 or self.due_minute < 0:
            raise ValidationError('invalid planned job')

@dataclass(frozen=True)
class PlannedPlacement:
    job_id: str
    start_minute: int
    finish_minute: int
    tardiness_minutes: int

class SmallBatchOptimizer:

    def __init__(self, max_exact_jobs: int=8):
        if max_exact_jobs < 1:
            raise ValidationError('max_exact_jobs must be positive')
        self.max_exact_jobs = max_exact_jobs

    def _evaluate(self, order: list[PlannedJob], start_minute: int) -> tuple[int, list[PlannedPlacement]]:
        cursor = start_minute
        score = 0
        placements = []
        for job in order:
            finish = cursor + job.duration_minutes
            tard = max(0, finish - job.due_minute)
            score += tard * (1 + max(0, job.priority))
            placements.append(PlannedPlacement(job.job_id, cursor, finish, tard))
            cursor = finish
        return (score, placements)

    def optimize(self, jobs: list[PlannedJob], start_minute: int=0) -> list[PlannedPlacement]:
        if start_minute < 0:
            raise ValidationError('start_minute cannot be negative')
        if len(jobs) > self.max_exact_jobs:
            ordered = sorted(jobs, key=lambda j: (j.due_minute, -j.priority, j.duration_minutes, j.job_id))
            return self._evaluate(ordered, start_minute)[1]
        best = None
        for order in permutations(jobs):
            score, placements = self._evaluate(list(order), start_minute)
            key = (score, tuple((p.job_id for p in placements)))
            if best is None or key < best[0]:
                best = (key, placements)
        return best[1] if best else []

    def optimize_by_group(self, jobs: list[PlannedJob], start_minute: int=0) -> dict[str, list[PlannedPlacement]]:
        grouped = {}
        for j in jobs:
            grouped.setdefault(j.resource_group, []).append(j)
        return {g: self.optimize(items, start_minute) for g, items in grouped.items()}
