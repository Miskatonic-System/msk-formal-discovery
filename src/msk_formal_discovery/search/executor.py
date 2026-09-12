"""Search execution engine, receipt binding, and provenance custody (WO-MATH-FORMAL-DISCOVERY-01A-R4)."""
from __future__ import annotations

import hashlib
import hmac
import inspect
import json
from pathlib import Path
import re
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional, Sequence, Tuple

import jsonschema

from msk_formal_discovery.backend.contract import (
    BackendFamily,
    ExecutionOrigin,
    LogicalAuthorityClass,
    ProblemDefinition,
    ReasoningBackend,
)
from msk_formal_discovery.abstraction.candidate import compute_candidate_artifact_digest
from msk_formal_discovery.core.exceptions import (
    AuthorityViolationError,
    ReceiptValidationError,
    ReplayContractError,
)
from msk_formal_discovery.search.policy import (
    SearchAction,
    SearchPolicy,
    SearchPolicyKind,
    SearchRun,
    SearchState,
    is_successful_terminal,
)
from msk_formal_discovery.trace.events import EventOrigin, ExecutionTraceEvent, TraceEventType
from msk_formal_discovery.trace.ir import ExecutionTrace

HEX_64_PATTERN = re.compile(r"^[0-9a-f]{64}$")
CANONICAL_DISABLED_APPLICATION_DIGEST: str = "0" * 64


def get_executor_implementation_digest() -> str:
    """Return SHA-256 digest of search/executor.py source bytes (Section 6)."""
    target = Path(__file__).resolve()
    return hashlib.sha256(target.read_bytes()).hexdigest()


def _make_json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_make_json_safe(x) for x in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif hasattr(obj, "canonical_repr"):
        return obj.canonical_repr()
    return str(obj)


def compute_initial_state_digest(state: SearchState) -> str:
    """Deterministic SHA-256 digest of initial search state (Section 14)."""
    payload = {
        "state_id": state.state_id,
        "goal": state.goal,
        "depth": state.depth,
        "parent_id": state.parent_id,
        "path_cost": float(state.path_cost),
        "heuristic_value": float(state.heuristic_value),
        "context": _make_json_safe(getattr(state, "context", {})),
        "is_terminal": state.is_terminal,
        "is_solved": state.is_solved,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def get_policy_implementation_digest(policy: SearchPolicy) -> str:
    """Deterministic SHA-256 digest of policy implementation (Section 16)."""
    try:
        code = inspect.getsource(policy.__class__)
    except Exception:
        code = f"{policy.__class__.__module__}.{policy.__class__.__name__}"
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def compute_candidate_application_digest(
    status: str,
    candidate_id: Optional[str] = None,
    candidate_artifact_digest: Optional[str] = None,
) -> str:
    """Compute candidate application digest (WO-MATH-FORMAL-DISCOVERY-01A-R4-R1 Section 12).

    For DISABLED: returns CANONICAL_DISABLED_APPLICATION_DIGEST ("0" * 64).
    For REQUESTED_NOT_APPLIED: binds requested candidate ID, candidate artifact digest, and status.

    EXPLICIT ATTRIBUTION INVARIANT:
    REQUEST_DIGEST != APPLICATION_PROOF
    This establishes WHAT was requested, not that the candidate was applied.
    """
    if status == "DISABLED":
        return CANONICAL_DISABLED_APPLICATION_DIGEST

    cid = candidate_id or "default_candidate"
    art_dig = candidate_artifact_digest or ("0" * 64)
    payload = {
        "status": status,
        "candidate_id": cid,
        "candidate_artifact_digest": art_dig,
        "attribution_statement": "REQUEST_DIGEST != APPLICATION_PROOF",
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SearchExecutionWitness:
    """Opaque runtime witness establishing live SearchExecutor provenance (Section 4).

    TRUST & INTEGRITY NOTE (WO-MATH-FORMAL-DISCOVERY-01A-R4-R1 Section 16):
    SearchExecutionWitness is a process-local provenance / anti-construction mechanism.
    It is NOT a cryptographic security boundary against arbitrary code executing inside
    the same Python interpreter.
    FREEZE: PROCESS_LOCAL_PROVENANCE_WITNESS != HOSTILE_CODE_ISOLATION.
    """
    receipt_digest: str
    run_id: str
    executor_id: str
    implementation_digest: str
    witness_token: str


@dataclass
class SearchExecutionReceipt:
    """Attested receipt from an executed search run (Section 2 & 7)."""
    executor_id: str
    executor_version: str
    executor_implementation_digest: str
    run_id: str
    problem_id: str
    problem_digest: str
    backend_id: str
    backend_configuration_digest: str
    search_policy: str
    search_policy_configuration_digest: str
    search_budget_digest: str
    random_seed: int
    corpus_context_digest: str
    source_graph_context_digest: str
    environment_identity_digest: str
    candidate_id: Optional[str]
    candidate_enabled: bool
    started_at: str
    completed_at: str
    nodes_expanded: int
    nodes_evaluated: int
    branch_count: int
    terminal_status: str
    wall_time_ms: float
    resulting_trace_refs: List[str] = field(default_factory=list)
    resulting_trace_digests: List[str] = field(default_factory=list)
    initial_state_digest: str = "0" * 64
    transition_model_id: str = "default_discrete_transition_model"
    transition_model_digest: str = "0" * 64
    search_policy_implementation_digest: str = "0" * 64
    candidate_application_status: str = "DISABLED"
    candidate_application_digest: str = "0" * 64
    candidate_application_receipt_refs: List[str] = field(default_factory=list)
    candidate_application_receipt_digests: List[str] = field(default_factory=list)
    receipt_digest: str = ""

    def __post_init__(self) -> None:
        if not self.receipt_digest:
            self.receipt_digest = self.compute_digest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "miskatonic.search-execution-receipt.v0.1",
            "executor_id": self.executor_id,
            "executor_version": self.executor_version,
            "executor_implementation_digest": self.executor_implementation_digest,
            "run_id": self.run_id,
            "problem_id": self.problem_id,
            "problem_digest": self.problem_digest,
            "backend_id": self.backend_id,
            "backend_configuration_digest": self.backend_configuration_digest,
            "search_policy": self.search_policy,
            "search_policy_configuration_digest": self.search_policy_configuration_digest,
            "search_budget_digest": self.search_budget_digest,
            "random_seed": self.random_seed,
            "corpus_context_digest": self.corpus_context_digest,
            "source_graph_context_digest": self.source_graph_context_digest,
            "environment_identity_digest": self.environment_identity_digest,
            "candidate_id": self.candidate_id,
            "candidate_enabled": self.candidate_enabled,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "nodes_expanded": self.nodes_expanded,
            "nodes_evaluated": self.nodes_evaluated,
            "branch_count": self.branch_count,
            "terminal_status": self.terminal_status,
            "wall_time_ms": self.wall_time_ms,
            "resulting_trace_refs": list(self.resulting_trace_refs),
            "resulting_trace_digests": list(self.resulting_trace_digests),
            "initial_state_digest": self.initial_state_digest,
            "transition_model_id": self.transition_model_id,
            "transition_model_digest": self.transition_model_digest,
            "search_policy_implementation_digest": self.search_policy_implementation_digest,
            "candidate_application_status": self.candidate_application_status,
            "candidate_application_digest": self.candidate_application_digest,
            "candidate_application_receipt_refs": list(self.candidate_application_receipt_refs),
            "candidate_application_receipt_digests": list(self.candidate_application_receipt_digests),
            "receipt_digest": self.receipt_digest,
        }

    def compute_digest(self) -> str:
        d = self.to_dict()
        d.pop("receipt_digest", None)
        serialized = json.dumps(d, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def validate(self, schema_path: Optional[Path] = None) -> None:
        if schema_path is None:
            default_path = Path(__file__).resolve().parents[3] / "schemas" / "search-execution-receipt.v0.1.schema.json"
            if default_path.exists():
                schema_path = default_path
        if schema_path and schema_path.exists():
            schema_data = json.loads(schema_path.read_text(encoding="utf-8"))
            try:
                jsonschema.validate(self.to_dict(), schema_data)
            except jsonschema.ValidationError as e:
                raise ReceiptValidationError(f"SEARCH_EXECUTION_RECEIPT_SCHEMA_ERROR: {e.message}") from e

        # Invariant: length of trace refs and digests must match
        if len(self.resulting_trace_refs) != len(self.resulting_trace_digests):
            raise ReceiptValidationError(
                f"TRACE_REF_DIGEST_COUNT_MISMATCH: {len(self.resulting_trace_refs)} refs != {len(self.resulting_trace_digests)} digests"
            )

        # Invariant: recomputed digest must match
        expected_digest = self.compute_digest()
        if self.receipt_digest != expected_digest:
            raise ReceiptValidationError(
                f"RECEIPT_DIGEST_MISMATCH: receipt_digest '{self.receipt_digest}' != computed '{expected_digest}'"
            )

        # Hex digest checks
        for name, dig in [
            ("executor_implementation_digest", self.executor_implementation_digest),
            ("problem_digest", self.problem_digest),
            ("backend_configuration_digest", self.backend_configuration_digest),
            ("search_policy_configuration_digest", self.search_policy_configuration_digest),
            ("search_budget_digest", self.search_budget_digest),
            ("corpus_context_digest", self.corpus_context_digest),
            ("source_graph_context_digest", self.source_graph_context_digest),
            ("environment_identity_digest", self.environment_identity_digest),
            ("initial_state_digest", self.initial_state_digest),
            ("transition_model_digest", self.transition_model_digest),
            ("search_policy_implementation_digest", self.search_policy_implementation_digest),
            ("candidate_application_digest", self.candidate_application_digest),
            ("receipt_digest", self.receipt_digest),
        ]:
            if not HEX_64_PATTERN.match(dig):
                raise ReceiptValidationError(f"INVALID_HEX_DIGEST: '{name}' value '{dig}' is not a 64-char lowercase hex SHA-256")

        for d in self.resulting_trace_digests:
            if not HEX_64_PATTERN.match(d):
                raise ReceiptValidationError(f"INVALID_HEX_DIGEST: trace digest '{d}' is not a 64-char lowercase hex SHA-256")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SearchExecutionReceipt:
        return cls(
            executor_id=data["executor_id"],
            executor_version=data["executor_version"],
            executor_implementation_digest=data["executor_implementation_digest"],
            run_id=data["run_id"],
            problem_id=data["problem_id"],
            problem_digest=data["problem_digest"],
            backend_id=data["backend_id"],
            backend_configuration_digest=data["backend_configuration_digest"],
            search_policy=data["search_policy"],
            search_policy_configuration_digest=data["search_policy_configuration_digest"],
            search_budget_digest=data["search_budget_digest"],
            random_seed=data["random_seed"],
            corpus_context_digest=data["corpus_context_digest"],
            source_graph_context_digest=data["source_graph_context_digest"],
            environment_identity_digest=data["environment_identity_digest"],
            candidate_id=data.get("candidate_id"),
            candidate_enabled=data["candidate_enabled"],
            started_at=data["started_at"],
            completed_at=data["completed_at"],
            nodes_expanded=data["nodes_expanded"],
            nodes_evaluated=data["nodes_evaluated"],
            branch_count=data["branch_count"],
            terminal_status=data["terminal_status"],
            wall_time_ms=data["wall_time_ms"],
            resulting_trace_refs=list(data.get("resulting_trace_refs", [])),
            resulting_trace_digests=list(data.get("resulting_trace_digests", [])),
            initial_state_digest=data.get("initial_state_digest", "0" * 64),
            transition_model_id=data.get("transition_model_id", "default_discrete_transition_model"),
            transition_model_digest=data.get("transition_model_digest", "0" * 64),
            search_policy_implementation_digest=data.get("search_policy_implementation_digest", "0" * 64),
            candidate_application_status=data.get("candidate_application_status", "DISABLED"),
            candidate_application_digest=data.get("candidate_application_digest", "0" * 64),
            candidate_application_receipt_refs=list(data.get("candidate_application_receipt_refs", [])),
            candidate_application_receipt_digests=list(data.get("candidate_application_receipt_digests", [])),
            receipt_digest=data.get("receipt_digest", ""),
        )


@dataclass
class SearchExecutionBundle:
    """Bundle containing executed search run, attested receipt, traces, and opaque witness (Section 4 & 7)."""
    search_run: SearchRun
    receipt: SearchExecutionReceipt
    traces: List[ExecutionTrace] = field(default_factory=list)
    runtime_witness: Optional[SearchExecutionWitness] = None
    candidate_application_receipts: List[Any] = field(default_factory=list)

    @property
    def search_execution_receipt(self) -> SearchExecutionReceipt:
        return self.receipt

    def validate(self, schema_path: Optional[Path] = None) -> None:
        """Validate receipt against schema, SearchRun, traces, and runtime witness (Section 7)."""
        self.receipt.validate(schema_path=schema_path)

        # Cross-checks with SearchRun
        sr = self.search_run
        if self.receipt.run_id != sr.run_id:
            raise ReceiptValidationError(
                f"BUNDLE_RUN_ID_MISMATCH: receipt '{self.receipt.run_id}' != SearchRun '{sr.run_id}'"
            )
        if self.receipt.problem_id != sr.problem_id:
            raise ReceiptValidationError(
                f"BUNDLE_PROBLEM_ID_MISMATCH: receipt '{self.receipt.problem_id}' != SearchRun '{sr.problem_id}'"
            )
        if self.receipt.problem_digest != sr.problem_digest:
            raise ReceiptValidationError(
                f"BUNDLE_PROBLEM_DIGEST_MISMATCH: receipt '{self.receipt.problem_digest}' != SearchRun '{sr.problem_digest}'"
            )
        sr_policy_str = sr.search_policy.value if hasattr(sr.search_policy, "value") else str(sr.search_policy)
        if self.receipt.search_policy != sr_policy_str:
            raise ReceiptValidationError(
                f"BUNDLE_POLICY_MISMATCH: receipt '{self.receipt.search_policy}' != SearchRun '{sr_policy_str}'"
            )
        if self.receipt.terminal_status != sr.terminal_status:
            raise ReceiptValidationError(
                f"BUNDLE_TERMINAL_STATUS_MISMATCH: receipt '{self.receipt.terminal_status}' != SearchRun '{sr.terminal_status}'"
            )
        if self.receipt.nodes_expanded != sr.nodes_expanded:
            raise ReceiptValidationError(
                f"BUNDLE_NODES_EXPANDED_MISMATCH: receipt {self.receipt.nodes_expanded} != SearchRun {sr.nodes_expanded}"
            )
        if self.receipt.nodes_evaluated != sr.nodes_evaluated:
            raise ReceiptValidationError(
                f"BUNDLE_NODES_EVALUATED_MISMATCH: receipt {self.receipt.nodes_evaluated} != SearchRun {sr.nodes_evaluated}"
            )
        if self.receipt.resulting_trace_refs != sr.execution_trace_refs:
            raise ReceiptValidationError(
                f"BUNDLE_TRACE_REFS_MISMATCH: receipt {self.receipt.resulting_trace_refs} != SearchRun {sr.execution_trace_refs}"
            )
        if self.receipt.resulting_trace_digests != sr.execution_trace_digests:
            raise ReceiptValidationError(
                f"BUNDLE_TRACE_DIGESTS_MISMATCH: receipt {self.receipt.resulting_trace_digests} != SearchRun {sr.execution_trace_digests}"
            )

        # Cross-check implementation digest
        expected_impl_digest = get_executor_implementation_digest()
        if self.receipt.executor_implementation_digest != expected_impl_digest:
            raise ReceiptValidationError(
                f"EXECUTOR_IMPLEMENTATION_DIGEST_MISMATCH: receipt '{self.receipt.executor_implementation_digest}' != current '{expected_impl_digest}'"
            )

        # Cross-check runtime witness
        if not SearchExecutor.verify_bundle_witness(self):
            raise ReceiptValidationError(
                "INVALID_EXECUTION_WITNESS: SearchExecutionBundle lacks a valid SearchExecutor runtime witness"
            )


class SearchExecutor:
    """Governed search executor producing attested execution receipts and runtime witnesses.

    APPLICATION BOUNDARY & FUTURE 01B CONTRACT (WO-MATH-FORMAL-DISCOVERY-01A-R4-R1 Section 4 & 14):
    In 01A, candidate_enabled=True yields candidate_application_status="REQUESTED_NOT_APPLIED".
    No 01A SearchExecutor invocation may emit "APPLIED".

    01B will implement CandidateApplicator and CandidateApplicationReceipt, binding:
    - candidate artifact digest
    - applicator implementation digest
    - input search state digest
    - output / transformed search state or action surface digest
    - application semantics and application result
    - exact experimental unit
    Only such evidence may establish "APPLIED".
    """

    _SECRET: ClassVar[str] = secrets.token_hex(32)

    def __init__(
        self,
        executor_id: str = "msk-search-executor-v0.1",
        executor_version: str = "0.1.0",
    ) -> None:
        self.executor_id = executor_id
        self.executor_version = executor_version
        self.executor_implementation_digest = get_executor_implementation_digest()

    @classmethod
    def verify_bundle_witness(cls, bundle: SearchExecutionBundle) -> bool:
        """Verify the opaque runtime witness attached to a bundle."""
        if not bundle.runtime_witness:
            return False
        witness = bundle.runtime_witness
        if not isinstance(witness, SearchExecutionWitness):
            return False

        expected_token = hmac.new(
            cls._SECRET.encode("utf-8"),
            f"{witness.receipt_digest}:{witness.run_id}:{witness.executor_id}:{witness.implementation_digest}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return (
            hmac.compare_digest(witness.witness_token, expected_token)
            and witness.receipt_digest == bundle.receipt.receipt_digest
            and witness.run_id == bundle.receipt.run_id
            and witness.executor_id == bundle.receipt.executor_id
            and witness.implementation_digest == bundle.receipt.executor_implementation_digest
        )

    def execute(
        self,
        policy: SearchPolicy,
        problem: ProblemDefinition,
        initial_state: SearchState,
        budget: Dict[str, Any],
        backend: Optional[ReasoningBackend] = None,
        candidate_id: Optional[str] = None,
        candidate_enabled: bool = False,
        candidate_application_status: Optional[str] = None,
        candidate: Optional[Any] = None,
        random_seed: int = 0,
        corpus_context: Optional[Dict[str, Any]] = None,
        source_graph_context: Optional[Dict[str, Any]] = None,
        environment_identity: Optional[Dict[str, Any]] = None,
        backend_configuration: Optional[Dict[str, Any]] = None,
        transition_model_id: str = "default_discrete_transition_model",
        action_generator: Optional[Any] = None,
        traces: Optional[List[ExecutionTrace]] = None,
        environment: Optional[Any] = None,
    ) -> SearchExecutionBundle:
        """Execute search policy and generate verifiable execution receipt with runtime witness."""
        started_at = datetime.now(timezone.utc).isoformat()
        start_time = time.time()

        p_digest = (
            getattr(problem, "problem_digest", None)
            or (
                hashlib.sha256(problem.formal_syntax.encode("utf-8")).hexdigest()
                if getattr(problem, "formal_syntax", None)
                else hashlib.sha256(problem.problem_id.encode("utf-8")).hexdigest()
            )
        )
        b_conf = backend_configuration or {}
        b_conf_dig = hashlib.sha256(json.dumps(b_conf, sort_keys=True).encode("utf-8")).hexdigest()
        p_conf_dig = hashlib.sha256(json.dumps(policy.config, sort_keys=True).encode("utf-8")).hexdigest()
        budget_dig = hashlib.sha256(json.dumps(budget, sort_keys=True).encode("utf-8")).hexdigest()
        corpus_dig = hashlib.sha256(json.dumps(corpus_context or {}, sort_keys=True).encode("utf-8")).hexdigest()
        graph_dig = hashlib.sha256(json.dumps(source_graph_context or {}, sort_keys=True).encode("utf-8")).hexdigest()
        env_dig = hashlib.sha256(json.dumps(environment_identity or {"host": "linux", "runtime": "cpython"}, sort_keys=True).encode("utf-8")).hexdigest()

        # Section 14, 15, 16 bindings
        initial_state_dig = compute_initial_state_digest(initial_state)
        if action_generator is not None:
            act_gen_bytes = getattr(action_generator, "__name__", str(action_generator)).encode("utf-8")
            act_gen_dig = hashlib.sha256(act_gen_bytes).hexdigest()
            trans_model_digest = hashlib.sha256(f"{transition_model_id}:{act_gen_dig}".encode("utf-8")).hexdigest()
        else:
            trans_model_digest = hashlib.sha256(f"{transition_model_id}:v0.1".encode("utf-8")).hexdigest()
        policy_impl_dig = get_policy_implementation_digest(policy)

        # Section 2, 10: Caller cannot set APPLIED
        if candidate_application_status == "APPLIED":
            raise AuthorityViolationError(
                "CALLER_CANNOT_SET_APPLIED: SearchExecutor in 01A cannot produce APPLIED status. APPLIED is reserved for 01B CandidateApplicator."
            )

        # Section 3, 12, 13: Derive application state and candidate application digest
        if not candidate_enabled:
            cand_status = "DISABLED"
            cand_app_dig = CANONICAL_DISABLED_APPLICATION_DIGEST
        else:
            cand_status = "REQUESTED_NOT_APPLIED"
            cand_art_dig = None
            if candidate is not None:
                cand_art_dig = compute_candidate_artifact_digest(candidate)
            elif candidate_id is not None:
                cand_art_dig = compute_candidate_artifact_digest({"candidate_id": candidate_id})
            cand_app_dig = compute_candidate_application_digest(
                status=cand_status,
                candidate_id=candidate_id or (getattr(candidate, "candidate_id", None) if candidate else None),
                candidate_artifact_digest=cand_art_dig,
            )

        max_nodes = budget.get("max_nodes", 100)
        max_depth = budget.get("max_depth", 20)

        # Execute search algorithm loop
        frontier: List[SearchState] = [initial_state]
        nodes_expanded = 0
        nodes_evaluated = 1
        branch_count = 0
        max_depth_reached = initial_state.depth
        solved = initial_state.is_solved
        terminal_status = "SUCCESS" if solved else "EXHAUSTED"

        run_id = f"search-run-{problem.problem_id}-{int(start_time * 1000)}"

        # Track search traces
        search_traces: List[ExecutionTrace] = list(traces) if traces else []
        candidate_application_receipts: List[Any] = []

        while frontier and nodes_expanded < max_nodes and not solved:
            current = policy.select_next(frontier)
            if not current:
                break
            frontier.remove(current)
            nodes_expanded += 1
            if current.depth > max_depth_reached:
                max_depth_reached = current.depth

            if current.is_solved:
                solved = True
                terminal_status = "SUCCESS"
                break

            if current.depth >= max_depth:
                terminal_status = "BUDGET_REACHED"
                continue

            # Governed environment action enumeration & candidate applicator (WO-MATH-FORMAL-DISCOVERY-01B Section 20)
            if environment is not None:
                primitive_actions = environment.actions(current)
                if candidate_enabled and candidate is not None:
                    from msk_formal_discovery.application.applicator import CandidateApplicator
                    app_res = CandidateApplicator.apply(
                        candidate=candidate,
                        state=current,
                        primitive_actions=primitive_actions,
                        environment=environment,
                        problem_digest=p_digest,
                        experimental_unit_id=problem.problem_id,
                    )
                    candidate_application_receipts.append(app_res.receipt)
                    if app_res.status == "APPLIED":
                        actions = app_res.transformed_actions
                    else:
                        actions = primitive_actions
                else:
                    actions = primitive_actions
            elif action_generator is not None:
                actions = action_generator(current)
            else:
                actions = policy.propose_actions(current)
            branch_count += len(actions)

            # Expand state with actions
            for act_idx, act in enumerate(actions):
                nodes_evaluated += 1
                if environment is not None:
                    new_state, _ = environment.transition(current, act)
                else:
                    new_state = SearchState(
                        state_id=f"{current.state_id}-s{act_idx}",
                        goal=f"subgoal-{act.operation}",
                        depth=current.depth + 1,
                        parent_id=current.state_id,
                        path_cost=current.path_cost + act.estimated_cost,
                        heuristic_value=act.prior_probability,
                        is_solved=(act.operation in ("qed", "solve", "exact")),
                    )
                frontier.append(new_state)

        if nodes_expanded >= max_nodes and not solved:
            terminal_status = "BUDGET_REACHED"

        # Execute backend if provided
        backend_id = backend.backend_id if backend else "internal_search_engine"
        if backend:
            tr = backend.solve(problem)
            search_traces.append(tr)

        wall_time = (time.time() - start_time) * 1000.0
        completed_at = datetime.now(timezone.utc).isoformat()

        trace_refs: List[str] = [t.trace_id for t in search_traces]
        trace_digests: List[str] = [
            t.digest() for t in search_traces
        ]

        final_terminal = "SUCCESS" if solved else terminal_status

        # Section 20 & 21: Derive search-level candidate_application_status and receipts
        applied_receipts = [r for r in candidate_application_receipts if getattr(r, "application_status", "") == "APPLIED"]
        if applied_receipts:
            cand_status = "APPLIED"
            cand_app_refs = [r.application_id for r in applied_receipts]
            cand_app_receipt_digests = [r.receipt_digest for r in applied_receipts]
            cand_app_dig = hashlib.sha256(":".join(sorted(cand_app_receipt_digests)).encode("utf-8")).hexdigest()
        elif candidate_enabled:
            cand_status = "REQUESTED_NOT_APPLIED"
            cand_app_refs = [r.application_id for r in candidate_application_receipts]
            cand_app_receipt_digests = [r.receipt_digest for r in candidate_application_receipts]
            cand_art_dig = None
            if candidate is not None:
                cand_art_dig = compute_candidate_artifact_digest(candidate)
            elif candidate_id is not None:
                cand_art_dig = compute_candidate_artifact_digest({"candidate_id": candidate_id})
            cand_app_dig = compute_candidate_application_digest(
                status=cand_status,
                candidate_id=candidate_id or (getattr(candidate, "candidate_id", None) if candidate else None),
                candidate_artifact_digest=cand_art_dig,
            )
        else:
            cand_status = "DISABLED"
            cand_app_refs = []
            cand_app_receipt_digests = []
            cand_app_dig = CANONICAL_DISABLED_APPLICATION_DIGEST

        receipt = SearchExecutionReceipt(
            executor_id=self.executor_id,
            executor_version=self.executor_version,
            executor_implementation_digest=self.executor_implementation_digest,
            run_id=run_id,
            problem_id=problem.problem_id,
            problem_digest=p_digest,
            backend_id=backend_id,
            backend_configuration_digest=b_conf_dig,
            search_policy=policy.policy_kind.value,
            search_policy_configuration_digest=p_conf_dig,
            search_budget_digest=budget_dig,
            random_seed=random_seed,
            corpus_context_digest=corpus_dig,
            source_graph_context_digest=graph_dig,
            environment_identity_digest=env_dig,
            candidate_id=candidate_id,
            candidate_enabled=candidate_enabled,
            started_at=started_at,
            completed_at=completed_at,
            nodes_expanded=nodes_expanded,
            nodes_evaluated=nodes_evaluated,
            branch_count=branch_count,
            terminal_status=final_terminal,
            wall_time_ms=wall_time,
            resulting_trace_refs=trace_refs,
            resulting_trace_digests=trace_digests,
            initial_state_digest=initial_state_dig,
            transition_model_id=transition_model_id,
            transition_model_digest=trans_model_digest,
            search_policy_implementation_digest=policy_impl_dig,
            candidate_application_status=cand_status,
            candidate_application_digest=cand_app_dig,
            candidate_application_receipt_refs=cand_app_refs,
            candidate_application_receipt_digests=cand_app_receipt_digests,
        )
        receipt.validate()

        search_run = SearchRun(
            run_id=run_id,
            problem_id=problem.problem_id,
            search_policy=policy.policy_kind,
            policy_configuration=policy.config,
            problem_digest=p_digest,
            nodes_expanded=nodes_expanded,
            nodes_evaluated=nodes_evaluated,
            max_depth_reached=max_depth_reached,
            branching_factor_effective=float(branch_count) / max(1, nodes_expanded),
            total_wall_time_ms=wall_time,
            terminal_status=final_terminal,
            resulting_trace_id=trace_refs[0] if trace_refs else None,
            execution_trace_refs=trace_refs,
            execution_trace_digests=trace_digests,
            replay_mode="EXECUTED_SEARCH_RUN",
            search_execution_receipt=receipt.to_dict(),
        )

        # Mint opaque runtime witness
        witness_token = hmac.new(
            self._SECRET.encode("utf-8"),
            f"{receipt.receipt_digest}:{receipt.run_id}:{self.executor_id}:{self.executor_implementation_digest}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        witness = SearchExecutionWitness(
            receipt_digest=receipt.receipt_digest,
            run_id=receipt.run_id,
            executor_id=self.executor_id,
            implementation_digest=self.executor_implementation_digest,
            witness_token=witness_token,
        )

        return SearchExecutionBundle(
            search_run=search_run,
            receipt=receipt,
            traces=search_traces,
            runtime_witness=witness,
            candidate_application_receipts=candidate_application_receipts,
        )
