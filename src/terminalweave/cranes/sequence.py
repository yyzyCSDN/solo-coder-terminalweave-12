from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError, ConflictError

@dataclass(frozen=True)
class HatchTask:
    task_id: str
    hatch: int
    bay: int
    moves: int
    phase: str
    predecessor_ids: frozenset[str] = frozenset()

    def __post_init__(self):
        if self.hatch < 1 or self.bay < 1 or self.moves < 1:
            raise ValidationError('invalid hatch task')

class HatchSequence:

    def __init__(self, tasks: list[HatchTask]):
        self.tasks = {t.task_id: t for t in tasks}
        if len(self.tasks) != len(tasks):
            raise ValidationError('duplicate hatch task')
        ids = set(self.tasks)
        if any((t.predecessor_ids - ids for t in tasks)):
            raise ValidationError('unknown task predecessor')

    def topological(self) -> list[HatchTask]:
        remaining = set(self.tasks)
        done = set()
        out = []
        while remaining:
            ready = [self.tasks[x] for x in remaining if self.tasks[x].predecessor_ids <= done]
            if not ready:
                raise ConflictError('hatch sequence contains cycle')
            ready.sort(key=lambda t: (0 if t.phase == 'discharge' else 1, t.hatch, t.bay, t.task_id))
            for task in ready:
                out.append(task)
                done.add(task.task_id)
                remaining.remove(task.task_id)
        return out

    def total_moves(self) -> int:
        return sum((t.moves for t in self.tasks.values()))

    def hatch_moves(self) -> dict[int, int]:
        out = {}
        for t in self.tasks.values():
            out[t.hatch] = out.get(t.hatch, 0) + t.moves
        return out
