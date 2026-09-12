"""Reasoning backend contract and authority boundaries (WO-MATH-FORMAL-DISCOVERY-01A)."""
from __future__ import annotations

import abc
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from msk_formal_discovery.core.exceptions import AuthorityViolationError
from msk_formal_discovery.trace.ir import ExecutionTrace


class BackendFamily(str, Enum):
    """Reasoning backend class families."""
    SMT_SOLVER = "SMT_SOLVER"
    MODEL_CHECKER = "MODEL_CHECKER"
    PROOF_ASSISTANT = "PROOF_ASSISTANT"
    SYMBOLIC_ORACLE = "SYMBOLIC_ORACLE"
    EXECUTABLE_ORACLE = "EXECUTABLE_ORACLE"


class LogicalAuthorityClass(str, Enum):
    """Logical authority levels that backends may produce."""
    SOLVER_SAT_OR_UNSAT = "SOLVER_SAT_OR_UNSAT"
    BOUNDED_EXHAUSTIVE_VERDICT = "BOUNDED_EXHAUSTIVE_VERDICT"
    DEDUCTIVE_PROOF_AUTHORITY = "DEDUCTIVE_PROOF_AUTHORITY"
    SYMBOLIC_IDENTITY = "SYMBOLIC_IDENTITY"
    EMPIRICAL_EXECUTION = "EMPIRICAL_EXECUTION"


# Enforce standard authority mapping per backend family
FAMILY_TO_DEFAULT_AUTHORITY: Dict[BackendFamily, LogicalAuthorityClass] = {
    BackendFamily.SMT_SOLVER: LogicalAuthorityClass.SOLVER_SAT_OR_UNSAT,
    BackendFamily.MODEL_CHECKER: LogicalAuthorityClass.BOUNDED_EXHAUSTIVE_VERDICT,
    BackendFamily.PROOF_ASSISTANT: LogicalAuthorityClass.DEDUCTIVE_PROOF_AUTHORITY,
    BackendFamily.SYMBOLIC_ORACLE: LogicalAuthorityClass.SYMBOLIC_IDENTITY,
    BackendFamily.EXECUTABLE_ORACLE: LogicalAuthorityClass.EMPIRICAL_EXECUTION,
}


@dataclass
class ProblemDefinition:
    """Formal problem definition passed to a reasoning backend."""
    problem_id: str
    formal_syntax: str  # SMT-LIB2, Lean4, Rocq, etc.
    context: Dict[str, Any]
    goals: List[str]
    assumptions: List[str]
    timeout_seconds: float = 30.0


class ReasoningBackend(abc.ABC):
    """Provider-neutral reasoning backend interface."""

    def __init__(
        self,
        backend_id: str,
        backend_family: BackendFamily,
        backend_version: str,
        logical_authority_class: Optional[LogicalAuthorityClass] = None,
    ) -> None:
        self.backend_id = backend_id
        self.backend_family = backend_family
        self.backend_version = backend_version
        self.logical_authority_class = (
            logical_authority_class or FAMILY_TO_DEFAULT_AUTHORITY[backend_family]
        )
        self._validate_authority_class()

    def _validate_authority_class(self) -> None:
        """Enforce authority boundaries: backends cannot claim higher authority than their family supports."""
        if self.backend_family == BackendFamily.SMT_SOLVER:
            if self.logical_authority_class == LogicalAuthorityClass.DEDUCTIVE_PROOF_AUTHORITY:
                raise AuthorityViolationError(
                    "SOLVER_SAT_RESULT_CANNOT_CLAIM_PROOF_AUTHORITY: SMT solver cannot assert deductive proof authority without verified certificate"
                )
        if self.backend_family == BackendFamily.MODEL_CHECKER:
            if self.logical_authority_class == LogicalAuthorityClass.DEDUCTIVE_PROOF_AUTHORITY:
                raise AuthorityViolationError(
                    "MODEL_CHECKER_MISLABELED_AS_PROOF_ASSISTANT: Model checker results cannot be labeled as deductive proof assistant results"
                )

    @abc.abstractmethod
    def solve(self, problem: ProblemDefinition) -> ExecutionTrace:
        """Attempt to solve the formal problem and return a governed ExecutionTrace."""

    @abc.abstractmethod
    def supported_operations(self) -> List[str]:
        """List operations supported by this backend adapter."""

    def to_descriptor(self) -> Dict[str, Any]:
        """Emit descriptor conforming to reasoning-backend schema."""
        return {
            "schema_version": "miskatonic.reasoning-backend.v0.1",
            "backend_id": self.backend_id,
            "backend_family": self.backend_family.value,
            "backend_version": self.backend_version,
            "logical_authority_class": self.logical_authority_class.value,
            "status": "ACTIVE_ADAPTER",
            "supported_operations": self.supported_operations(),
            "configuration": {},
            "adapter_identity": {
                "adapter_class": self.__class__.__name__,
                "implementation_ref": f"{self.__class__.__module__}.{self.__class__.__name__}",
                "is_reference_adapter": True,
            },
        }
