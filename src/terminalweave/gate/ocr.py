from __future__ import annotations
from dataclasses import dataclass
import re
from terminalweave.core.errors import ValidationError
_CONTAINER = re.compile('^[A-Z]{4}[0-9]{7}$')

@dataclass(frozen=True)
class OcrCandidate:
    text: str
    confidence: float

@dataclass(frozen=True)
class OcrDecision:
    value: str | None
    confidence: float
    manual_review: bool
    reason: str

class ContainerOcrResolver:

    def resolve(self, candidates: list[OcrCandidate], minimum_confidence: float=0.92, ambiguity_margin: float=0.03) -> OcrDecision:
        if not 0 <= minimum_confidence <= 1 or ambiguity_margin < 0:
            raise ValidationError('invalid OCR thresholds')
        normalized = []
        for c in candidates:
            text = ''.join((ch for ch in c.text.upper() if ch.isalnum()))
            if _CONTAINER.match(text):
                normalized.append((c.confidence, text))
        if not normalized:
            return OcrDecision(None, 0.0, True, 'no syntactically valid candidate')
        normalized.sort(reverse=True)
        best_conf, best = normalized[0]
        if best_conf < minimum_confidence:
            return OcrDecision(best, best_conf, True, 'confidence below threshold')
        if len(normalized) > 1 and normalized[1][1] != best and (best_conf - normalized[1][0] < ambiguity_margin):
            return OcrDecision(best, best_conf, True, 'ambiguous alternatives')
        return OcrDecision(best, best_conf, False, 'accepted')
