"""Search execution engine, receipt binding, and provenance custody (WO-MATH-FORMAL-DISCOVERY-01A-R3)."""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import jsonschema

from msk_formal_discovery.backend.contract import (
    BackendFamily,
    ExecutionOrigin,
    LogicalAuthorityClass,
    ProblemDefinition,
    ReasoningBackend,
)
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
)
from msk_formal_discovery.trace.events import EventOrigin, ExecutionTraceEvent, TraceEventType
from msk_formal_discovery.trace.ir import ExecutionTrace

HEX_64_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass
class SearchExecutionReceipt:
    """Attested receipt from an executed search run (Section 2)."""
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
        ]:
            if not HEX_64_PATTERN.match(dig):
                raise ReceiptValidationError(f"INVALID_HEX_DIGEST: '{name}' value '{dig}' is not a 64-char lowercase hex SHA-256")

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
            receipt_digest=data.get("receipt_digest", ""),
        )


@dataclass
class SearchExecutionBundle:
    """Bundle containing executed search run, attested receipt, and generated traces."""
    search_run: SearchRun
    receipt: SearchExecutionReceipt
    traces: List[ExecutionTrace] = field(default_factory=list)

    @property
    def search_execution_receipt(self) -> SearchExecutionReceipt:
        return self.receipt


class SearchExecutor:
    """Governed search executor producing attested execution receipts (Section 3)."""

    def __init__(
        self,
        executor_id: str = "msk-search-executor-v0.1",
        executor_version: str = "0.1.0",
    ) -> None:
        self.executor_id = executor_id
        self.executor_version = executor_version
        self.executor_implementation_digest = hashlib.sha256(
            f"{self.executor_id}:{self.executor_version}:SearchExecutor:v0.1".encode("utf-8")
        ).hexdigest()

    def execute(
        self,
        policy: SearchPolicy,
        problem: ProblemDefinition,
        initial_state: SearchState,
        budget: Dict[str, Any],
        backend: Optional[ReasoningBackend] = None,
        candidate_id: Optional[str] = None,
        candidate_enabled: bool = False,
        random_seed: int = 0,
        corpus_context: Optional[Dict[str, Any]] = None,
        source_graph_context: Optional[Dict[str, Any]] = None,
        environment_identity: Optional[Dict[str, Any]] = None,
        backend_configuration: Optional[Dict[str, Any]] = None,
        action_generator: Optional[Any] = None,
    ) -> SearchExecutionBundle:
        """Execute search policy and generate verifiable execution receipt."""
        started_at = datetime.now(timezone.utc).isoformat()
        start_time = time.time()

        p_digest = (
            hashlib.sha256(problem.formal_syntax.encode("utf-8")).hexdigest()
            if getattr(problem, "formal_syntax", None)
            else hashlib.sha256(problem.problem_id.encode("utf-8")).hexdigest()
        )
        b_conf = backend_configuration or {}
        b_conf_dig = hashlib.sha256(json.dumps(b_conf, sort_keys=True).encode("utf-8")).hexdigest()
        p_conf_dig = hashlib.sha256(json.dumps(policy.config, sort_keys=True).encode("utf-8")).hexdigest()
        budget_dig = hashlib.sha256(json.dumps(budget, sort_keys=True).encode("utf-8")).hexdigest()
        corpus_dig = hashlib.sha256(json.dumps(corpus_context or {}, sort_keys=True).encode("utf-8")).hexdigest()
        graph_dig = hashlib.sha256(json.dumps(source_graph_context or {}, sort_keys=True).encode("utf-8")).hexdigest()
        env_dig = hashlib.sha256(json.dumps(environment_identity or {"host": "linux", "runtime": "cpython"}, sort_keys=True).encode("utf-8")).hexdigest()

        max_nodes = budget.get("max_nodes", 100)
        max_depth = budget.get("max_depth", 20)

        # Execute search algorithm loop
        frontier: List[SearchState] = [initial_state]
        nodes_expanded = 0
        nodes_evaluated = 1
        branch_count = 0
        max_depth_reached = initial_state.depth
        solved = False
        terminal_status = "EXHAUSTED"

        run_id = f"search-run-{problem.problem_id}-{int(start_time * 1000)}"

        # Track search traces
        traces: List[ExecutionTrace] = []

        while frontier and nodes_expanded < max_nodes:
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

            actions = policy.propose_actions(current)
            branch_count += len(actions)

            # Expand state with actions
            for act_idx, act in enumerate(actions):
                nodes_evaluated += 1
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
            traces.append(tr)

        wall_time = (time.time() - start_time) * 1000.0
        completed_at = datetime.now(timezone.utc).isoformat()

        trace_refs: List[str] = [t.trace_id for t in traces]
        trace_digests: List[str] = [
            hashlib.sha256(json.dumps(t.to_dict(), sort_keys=True).encode("utf-8")).hexdigest()
            for t in traces
        ]

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
            terminal_status="SUCCESS" if solved else terminal_status,
            wall_time_ms=wall_time,
            resulting_trace_refs=trace_refs,
            resulting_trace_digests=trace_digests,
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
            terminal_status="SUCCESS" if solved else terminal_status,
            resulting_trace_id=trace_refs[0] if trace_refs else None,
            execution_trace_refs=trace_refs,
            execution_trace_digests=trace_digests,
            replay_mode="EXECUTED_SEARCH_RUN",
            search_execution_receipt=receipt.to_dict(),
        )

        return SearchExecutionBundle(
            search_run=search_run,
            receipt=receipt,
            traces=traces,
        )
