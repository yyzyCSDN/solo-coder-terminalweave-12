from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class HazmatDeclaration:
    container_id: str
    un_number: str
    proper_name: str
    hazard_class: str
    packing_group: str | None
    emergency_contact: str
    signed: bool

class DeclarationValidator:

    def validate(self, d: HazmatDeclaration) -> list[str]:
        errors = []
        if not d.container_id.strip():
            errors.append('container id missing')
        if not (d.un_number.startswith('UN') and d.un_number[2:].isdigit()):
            errors.append('UN number invalid')
        if not d.proper_name.strip():
            errors.append('proper shipping name missing')
        if not d.hazard_class.strip():
            errors.append('hazard class missing')
        if d.packing_group not in {None, 'I', 'II', 'III'}:
            errors.append('packing group invalid')
        digits = ''.join((ch for ch in d.emergency_contact if ch.isdigit()))
        if len(digits) < 7:
            errors.append('emergency contact invalid')
        if not d.signed:
            errors.append('declaration unsigned')
        return errors

    def accepted(self, d: HazmatDeclaration) -> bool:
        return not self.validate(d)
