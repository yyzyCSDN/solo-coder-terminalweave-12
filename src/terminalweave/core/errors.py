class TerminalWeaveError(Exception):
    """Base domain error."""

class ValidationError(TerminalWeaveError):
    pass

class ConflictError(TerminalWeaveError):
    pass

class CapacityError(TerminalWeaveError):
    pass

class StateTransitionError(TerminalWeaveError):
    pass

class NotFoundError(TerminalWeaveError):
    pass

class SafetyConstraintError(TerminalWeaveError):
    pass
