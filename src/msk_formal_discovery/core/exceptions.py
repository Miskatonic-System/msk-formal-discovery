"""Core exception hierarchy for msk-formal-discovery."""

class FormalDiscoveryError(Exception):
    """Base exception for all formal discovery errors."""


class BackendExecutionError(FormalDiscoveryError):
    """Raised when a reasoning backend fails or misbehaves."""


class TraceValidationError(FormalDiscoveryError):
    """Raised when an execution trace IR invariant is violated."""


class AntiUnificationError(FormalDiscoveryError):
    """Raised when structural anti-unification fails or produces invalid generalization."""


class AuthorityViolationError(FormalDiscoveryError):
    """Raised when an authority boundary firewall is breached."""


class SearchPolicyError(FormalDiscoveryError):
    """Raised when a search policy operation fails."""


class HeldOutDataLeakageError(FormalDiscoveryError):
    """Raised when training/discovery traces leak into held-out qualification set."""


class RefactoringError(FormalDiscoveryError):
    """Raised when an automated refactoring proposal violates safety or mutates canonical source."""
