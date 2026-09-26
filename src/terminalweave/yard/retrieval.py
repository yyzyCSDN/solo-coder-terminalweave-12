from __future__ import annotations
from dataclasses import dataclass
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class RetrievalCandidate:
    container_id: str
    stack_id: str
    blockers: int
    travel_m: float
    due_rank: int
    reefer: bool = False

class RetrievalRanker:

    def __init__(self, blocker_weight: float=5.0, travel_weight: float=0.02, due_weight: float=1.0):
        if min(blocker_weight, travel_weight, due_weight) < 0:
            raise ValidationError('weights cannot be negative')
        self.blocker_weight = blocker_weight
        self.travel_weight = travel_weight
        self.due_weight = due_weight

    def score(self, c: RetrievalCandidate) -> float:
        if c.blockers < 0 or c.travel_m < 0 or c.due_rank < 0:
            raise ValidationError('invalid retrieval candidate')
        reefer_bonus = -2.0 if c.reefer else 0.0
        return c.blockers * self.blocker_weight + c.travel_m * self.travel_weight + c.due_rank * self.due_weight + reefer_bonus

    def rank(self, candidates: list[RetrievalCandidate]) -> list[RetrievalCandidate]:
        return sorted(candidates, key=lambda c: (self.score(c), c.container_id))
