"""Core exception hierarchy for msk-formal-discovery."""

class FormalDiscoveryError(Exception):
    """Base exception for all formal discovery errors."""


class BackendExecutionError(FormalDiscoveryError):
    """Raised when a reasoning backend fails or misbehaves."""


class BackendUnavailableError(FormalDiscoveryError):
    """Raised when a requested reasoning backend executable is unavailable."""


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


class ReplayContractError(FormalDiscoveryError):
    """Raised when paired replay contract or execution invariants are violated."""


class RefactoringError(FormalDiscoveryError):
    """Raised when an automated refactoring proposal violates safety or mutates canonical source."""


class ReceiptValidationError(FormalDiscoveryError, ValueError):
    """Raised when an execution or replay receipt fails schema or consistency invariants."""


class CustodyGraphResolutionError(ReceiptValidationError):
    """Raised when end-to-end custody graph resolution fails or detects provenance divergence."""
