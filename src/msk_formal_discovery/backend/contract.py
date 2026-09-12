"""Reasoning backend contract, execution receipts, and authority derivation (WO-MATH-FORMAL-DISCOVERY-01A-R1)."""
from __future__ import annotations

import abc
import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import jsonschema

import re
from msk_formal_discovery.core.exceptions import AuthorityViolationError, ReceiptValidationError


class BackendFamily(str, Enum):
    """Reasoning backend class families."""
    SMT_SOLVER = "SMT_SOLVER"
    MODEL_CHECKER = "MODEL_CHECKER"
    PROOF_ASSISTANT = "PROOF_ASSISTANT"
    STRUCTURAL_PROOF_ASSISTANT = "STRUCTURAL_PROOF_ASSISTANT"
    INTERACTIVE_THEOREM_PROVER = "INTERACTIVE_THEOREM_PROVER"
    SYMBOLIC_ORACLE = "SYMBOLIC_ORACLE"
    EXECUTABLE_ORACLE = "EXECUTABLE_ORACLE"


class ExecutionOrigin(str, Enum):
    """Exact execution origin of backend evidence."""
    EXECUTED_NATIVE = "EXECUTED_NATIVE"
    EXECUTED_CONTAINERIZED = "EXECUTED_CONTAINERIZED"
    CERTIFIED_REPLAY = "CERTIFIED_REPLAY"
    SYNTHETIC_FIXTURE = "SYNTHETIC_FIXTURE"
    SIMULATED = "SIMULATED"


class LogicalAuthorityClass(str, Enum):
    """Logical authority levels that backends may produce."""
    SOLVER_SAT_OR_UNSAT = "SOLVER_SAT_OR_UNSAT"
    BOUNDED_EXHAUSTIVE_VERDICT = "BOUNDED_EXHAUSTIVE_VERDICT"
    DEDUCTIVE_PROOF_AUTHORITY = "DEDUCTIVE_PROOF_AUTHORITY"
    SYMBOLIC_IDENTITY = "SYMBOLIC_IDENTITY"
    EMPIRICAL_EXECUTION = "EMPIRICAL_EXECUTION"
    SYNTHETIC_FIXTURE_ONLY = "SYNTHETIC_FIXTURE_ONLY"
    NONE = "NONE"


FAMILY_TO_DEFAULT_AUTHORITY: Dict[BackendFamily, LogicalAuthorityClass] = {
    BackendFamily.SMT_SOLVER: LogicalAuthorityClass.SOLVER_SAT_OR_UNSAT,
    BackendFamily.MODEL_CHECKER: LogicalAuthorityClass.BOUNDED_EXHAUSTIVE_VERDICT,
    BackendFamily.PROOF_ASSISTANT: LogicalAuthorityClass.DEDUCTIVE_PROOF_AUTHORITY,
    BackendFamily.STRUCTURAL_PROOF_ASSISTANT: LogicalAuthorityClass.DEDUCTIVE_PROOF_AUTHORITY,
    BackendFamily.INTERACTIVE_THEOREM_PROVER: LogicalAuthorityClass.DEDUCTIVE_PROOF_AUTHORITY,
    BackendFamily.SYMBOLIC_ORACLE: LogicalAuthorityClass.SYMBOLIC_IDENTITY,
    BackendFamily.EXECUTABLE_ORACLE: LogicalAuthorityClass.EMPIRICAL_EXECUTION,
}


@dataclass
class BackendExecutionReceipt:
    """Attested receipt of a real or simulated backend invocation."""
    receipt_id: str
    backend_id: str
    backend_family: BackendFamily
    execution_origin: ExecutionOrigin
    executable_path: str
    executable_version: str
    executable_sha256: str
    command: List[str]
    input_digest: str
    started_at: str
    completed_at: str
    exit_code: Optional[int]
    timeout_status: bool
    stdout_digest: str
    stderr_digest: str
    terminal_classification: str
    logical_authority_class: LogicalAuthorityClass
    execution_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "miskatonic.backend-execution-receipt.v0.1",
            "receipt_id": self.receipt_id,
            "backend_id": self.backend_id,
            "backend_family": self.backend_family.value if isinstance(self.backend_family, BackendFamily) else str(self.backend_family),
            "execution_origin": self.execution_origin.value if isinstance(self.execution_origin, ExecutionOrigin) else str(self.execution_origin),
            "executable_path": self.executable_path,
            "executable_version": self.executable_version,
            "executable_sha256": self.executable_sha256,
            "command": self.command,
            "input_digest": self.input_digest,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "exit_code": self.exit_code,
            "timeout_status": self.timeout_status,
            "stdout_digest": self.stdout_digest,
            "stderr_digest": self.stderr_digest,
            "terminal_classification": self.terminal_classification,
            "logical_authority_class": self.logical_authority_class.value if isinstance(self.logical_authority_class, LogicalAuthorityClass) else str(self.logical_authority_class),
            "execution_metadata": self.execution_metadata,
        }

    def validate(self, schema_path: Optional[Path] = None) -> None:
        """Validate receipt against JSON schema and structural invariants."""
        if schema_path is None:
            default_path = Path(__file__).resolve().parents[3] / "schemas" / "backend-execution-receipt.v0.1.schema.json"
            if default_path.exists():
                schema_path = default_path
        if schema_path and schema_path.exists():
            try:
                schema_data = json.loads(schema_path.read_text(encoding="utf-8"))
                jsonschema.validate(self.to_dict(), schema_data)
            except jsonschema.ValidationError as err:
                raise ReceiptValidationError(f"RECEIPT_SCHEMA_VALIDATION_FAILED: {err.message}") from err

        # Field-level invariants
        if not self.receipt_id or not self.backend_id or not self.executable_path or not self.executable_version or not self.executable_sha256:
            raise ReceiptValidationError("RECEIPT_FIELD_MISSING: Core executable identity fields must not be empty")
        hex_64 = re.compile(r"^[a-f0-9]{64}$")
        if not hex_64.match(self.input_digest):
            raise ReceiptValidationError(f"RECEIPT_DIGEST_INVALID: input_digest '{self.input_digest}' is not 64-char hex")
        if not hex_64.match(self.stdout_digest):
            raise ReceiptValidationError(f"RECEIPT_DIGEST_INVALID: stdout_digest '{self.stdout_digest}' is not 64-char hex")
        if not hex_64.match(self.stderr_digest):
            raise ReceiptValidationError(f"RECEIPT_DIGEST_INVALID: stderr_digest '{self.stderr_digest}' is not 64-char hex")
        if not self.terminal_classification:
            raise ReceiptValidationError("RECEIPT_TERMINAL_MISSING: terminal_classification must not be empty")
        if self.exit_code is None and not self.timeout_status:
            raise ReceiptValidationError("RECEIPT_STATUS_INVALID: Non-timeout receipt must have an exit_code")

    def is_valid(self, schema_path: Optional[Path] = None) -> bool:
        """Return True if receipt passes all structural and schema validations."""
        try:
            self.validate(schema_path)
            return True
        except Exception:
            return False


def derive_authority(
    backend_family: BackendFamily,
    execution_origin: ExecutionOrigin,
    receipt: Optional[BackendExecutionReceipt],
    terminal_classification: str,
) -> LogicalAuthorityClass:
    """Derive logical authority class strictly from execution origin, receipt, and status (sole authority path)."""
    # Simulation or Synthetic Fixture NEVER grants proof or solver authority
    if execution_origin in (ExecutionOrigin.SYNTHETIC_FIXTURE, ExecutionOrigin.SIMULATED):
        return LogicalAuthorityClass.NONE

    if receipt is None:
        return LogicalAuthorityClass.NONE

    # Automatically validate receipt: must be valid
    if not receipt.is_valid():
        return LogicalAuthorityClass.NONE

    # Execution failure or timeout yields NONE authority
    if receipt.exit_code != 0 or receipt.timeout_status:
        return LogicalAuthorityClass.NONE

    # Exact agreement between arguments and receipt
    if receipt.backend_family != backend_family:
        return LogicalAuthorityClass.NONE
    if receipt.execution_origin != execution_origin:
        return LogicalAuthorityClass.NONE
    if receipt.terminal_classification != terminal_classification:
        return LogicalAuthorityClass.NONE

    # Proof assistants
    if backend_family in (
        BackendFamily.PROOF_ASSISTANT,
        BackendFamily.STRUCTURAL_PROOF_ASSISTANT,
        BackendFamily.INTERACTIVE_THEOREM_PROVER,
    ):
        if (
            terminal_classification == "PROVEN"
            and execution_origin in (ExecutionOrigin.EXECUTED_NATIVE, ExecutionOrigin.EXECUTED_CONTAINERIZED)
        ):
            return LogicalAuthorityClass.DEDUCTIVE_PROOF_AUTHORITY
        return LogicalAuthorityClass.NONE

    # SMT Solvers
    if backend_family == BackendFamily.SMT_SOLVER:
        if (
            terminal_classification in ("SAT", "UNSAT", "UNSAT_REFUTED", "REFUTED_SAT")
            and execution_origin in (ExecutionOrigin.EXECUTED_NATIVE, ExecutionOrigin.EXECUTED_CONTAINERIZED)
        ):
            return LogicalAuthorityClass.SOLVER_SAT_OR_UNSAT
        return LogicalAuthorityClass.NONE

    # Model Checkers
    if backend_family == BackendFamily.MODEL_CHECKER:
        if (
            terminal_classification in ("VERIFIED", "REFUTED", "BOUNDED_EXHAUSTIVE")
            and execution_origin in (ExecutionOrigin.EXECUTED_NATIVE, ExecutionOrigin.EXECUTED_CONTAINERIZED)
        ):
            return LogicalAuthorityClass.BOUNDED_EXHAUSTIVE_VERDICT
        return LogicalAuthorityClass.NONE

    # Symbolic Oracles
    if backend_family == BackendFamily.SYMBOLIC_ORACLE:
        if execution_origin in (ExecutionOrigin.EXECUTED_NATIVE, ExecutionOrigin.EXECUTED_CONTAINERIZED):
            return LogicalAuthorityClass.SYMBOLIC_IDENTITY
        return LogicalAuthorityClass.NONE

    # Executable Oracles
    if backend_family == BackendFamily.EXECUTABLE_ORACLE:
        if execution_origin in (ExecutionOrigin.EXECUTED_NATIVE, ExecutionOrigin.EXECUTED_CONTAINERIZED):
            return LogicalAuthorityClass.EMPIRICAL_EXECUTION
        return LogicalAuthorityClass.NONE

    return LogicalAuthorityClass.NONE


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
    def solve(self, problem: ProblemDefinition) -> Any:
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
