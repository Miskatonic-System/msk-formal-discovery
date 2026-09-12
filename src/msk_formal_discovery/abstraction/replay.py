"""Held-out replay engine, paired replay contracts, and empirical search measurement (WO-MATH-FORMAL-DISCOVERY-01A-R2)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Union

import jsonschema

from msk_formal_discovery.abstraction.anti_unification import (
    AdmissibilityReceipt,
    AdmissibilityStatus,
)
from msk_formal_discovery.abstraction.candidate import AbstractionCandidate, CandidateStatus
from msk_formal_discovery.abstraction.value_metrics import AbstractionValueReport
from msk_formal_discovery.core.exceptions import (
    HeldOutDataLeakageError,
    ReceiptValidationError,
    ReplayContractError,
)
from msk_formal_discovery.search.executor import SearchExecutionBundle, SearchExecutionReceipt
from msk_formal_discovery.search.policy import SearchRun
from msk_formal_discovery.trace.ir import ExecutionTrace

HEX_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SCHEMAS_DIR = Path(__file__).resolve().parents[3] / "schemas"
REPLAY_RECEIPT_SCHEMA_PATH = SCHEMAS_DIR / "replay-run-receipt.v0.1.schema.json"
SEARCH_EXECUTION_RECEIPT_SCHEMA_PATH = SCHEMAS_DIR / "search-execution-receipt.v0.1.schema.json"
ADMISSIBILITY_RECEIPT_SCHEMA_PATH = SCHEMAS_DIR / "admissibility-receipt.v0.1.schema.json"


@dataclass
class ReplayRunReceipt:
    """Observed run receipt from executing an arm of a paired replay (Sections 16 & 17)."""
    receipt_id: str = ""
    arm: str = "BASELINE"  # "BASELINE" or "ABSTRACTED"
    problem_id: str = ""
    run_id: Optional[str] = None
    problem_digest: str = ""
    experimental_unit_id: str = ""
    paired_contract_digest: str = ""
    backend_id: str = "default_backend"
    search_policy_kind: str = "DEFAULT"
    search_policy_configuration_digest: str = "0" * 64
    search_budget_digest: str = "0" * 64
    random_seed: int = 0
    corpus_context_digest: str = "0" * 64
    candidate_id: str = ""
    candidate_enabled: bool = False
    started_at: str = ""
    completed_at: str = ""
    nodes_expanded: int = 0
    nodes_evaluated: int = 0
    branch_count: int = 0
    solved: bool = False
    wall_time_ms: float = 0.0
    backend_calls: int = 1
    replay_mode: str = "EXECUTED_HELD_OUT_REPLAY"
    search_run_ref: str = "unbound_search_run"
    search_run_digest: str = "0" * 64
    execution_trace_refs: List[str] = field(default_factory=list)
    execution_trace_digests: List[str] = field(default_factory=list)
    evidence_origin: str = "SYNTHETIC_FIXTURE"
    authority: str = "NONE"
    bound_search_run: Optional[SearchRun] = None
    search_execution_receipt: Optional[Dict[str, Any]] = None
    execution_receipts: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.receipt_id and self.run_id:
            self.receipt_id = self.run_id
        if not self.run_id and self.receipt_id:
            self.run_id = self.receipt_id
        now_iso = datetime.now(timezone.utc).isoformat()
        if not self.started_at:
            self.started_at = now_iso
        if not self.completed_at:
            self.completed_at = now_iso
        if not self.problem_digest and self.problem_id:
            self.problem_digest = hashlib.sha256(self.problem_id.encode("utf-8")).hexdigest()
        if not self.experimental_unit_id:
            self.experimental_unit_id = self.problem_digest

        # Validate hex digest patterns on digests
        for name, d in [
            ("problem_digest", self.problem_digest),
            ("paired_contract_digest", self.paired_contract_digest),
            ("search_policy_configuration_digest", self.search_policy_configuration_digest),
            ("search_budget_digest", self.search_budget_digest),
            ("corpus_context_digest", self.corpus_context_digest),
            ("search_run_digest", self.search_run_digest),
        ]:
            if d and not HEX_DIGEST_PATTERN.match(d):
                raise ValueError(f"Invalid {name}: {d}. Must be 64-char lowercase hex.")

        for d in self.execution_trace_digests:
            if not HEX_DIGEST_PATTERN.match(d):
                raise ValueError(f"Invalid execution_trace_digest: {d}. Must be 64-char lowercase hex.")

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "schema_version": "miskatonic.replay-run-receipt.v0.1",
            "receipt_id": self.receipt_id,
            "replay_mode": self.replay_mode,
            "arm": self.arm,
            "paired_contract_digest": self.paired_contract_digest,
            "experimental_unit_id": self.experimental_unit_id,
            "problem_id": self.problem_id,
            "problem_digest": self.problem_digest,
            "backend_id": self.backend_id,
            "search_policy_kind": self.search_policy_kind,
            "search_policy_configuration_digest": self.search_policy_configuration_digest,
            "search_budget_digest": self.search_budget_digest,
            "random_seed": self.random_seed,
            "corpus_context_digest": self.corpus_context_digest,
            "candidate_id": self.candidate_id,
            "candidate_enabled": self.candidate_enabled,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "nodes_expanded": self.nodes_expanded,
            "nodes_evaluated": self.nodes_evaluated,
            "branch_count": self.branch_count,
            "solved": self.solved,
            "wall_time_ms": self.wall_time_ms,
            "backend_calls": self.backend_calls,
            "search_run_ref": self.search_run_ref,
            "search_run_digest": self.search_run_digest,
            "execution_trace_refs": self.execution_trace_refs,
            "execution_trace_digests": self.execution_trace_digests,
            "evidence_origin": self.evidence_origin,
            "authority": self.authority,
        }
        if self.search_execution_receipt is not None:
            data["search_execution_receipt"] = self.search_execution_receipt
        return data

    def validate(self, schema_path: Optional[Path] = None) -> None:
        if schema_path is None:
            if REPLAY_RECEIPT_SCHEMA_PATH.exists():
                schema_path = REPLAY_RECEIPT_SCHEMA_PATH
        if schema_path and schema_path.exists():
            schema_data = json.loads(schema_path.read_text(encoding="utf-8"))
            try:
                jsonschema.validate(self.to_dict(), schema_data)
            except jsonschema.ValidationError as e:
                raise ReceiptValidationError(f"SCHEMA_VALIDATION_FAILED: {e.message}") from e

        if not self.receipt_id or not self.paired_contract_digest:
            raise ReceiptValidationError("RECEIPT_FIELD_MISSING: receipt_id and paired_contract_digest must not be empty")

        # Section 4 & 5: EXECUTED_SEARCH_RUN requires valid SearchExecutionReceipt
        if self.evidence_origin == "EXECUTED_SEARCH_RUN":
            if not self.search_execution_receipt:
                raise ReceiptValidationError(
                    "MISSING_SEARCH_EXECUTION_RECEIPT: evidence_origin EXECUTED_SEARCH_RUN requires valid search_execution_receipt"
                )
            if SEARCH_EXECUTION_RECEIPT_SCHEMA_PATH.exists():
                s_schema = json.loads(SEARCH_EXECUTION_RECEIPT_SCHEMA_PATH.read_text(encoding="utf-8"))
                jsonschema.validate(self.search_execution_receipt, s_schema)

            s_rcpt = SearchExecutionReceipt.from_dict(self.search_execution_receipt)
            expected_digest = s_rcpt.compute_digest()
            if s_rcpt.receipt_digest != expected_digest:
                raise ReceiptValidationError(
                    f"SEARCH_EXECUTION_RECEIPT_DIGEST_MISMATCH: {s_rcpt.receipt_digest} != {expected_digest}"
                )

            # Cross-check search_execution_receipt properties against replay receipt
            if s_rcpt.run_id != self.search_run_ref:
                raise ReplayContractError(
                    f"SEARCH_RUN_REF_MISMATCH: receipt search_run_ref '{self.search_run_ref}' != SearchExecutionReceipt '{s_rcpt.run_id}'"
                )
            if s_rcpt.nodes_expanded != self.nodes_expanded:
                raise ReplayContractError(
                    f"METRICS_DISAGREEMENT: nodes_expanded ({self.nodes_expanded}) != SearchExecutionReceipt ({s_rcpt.nodes_expanded})"
                )
            if s_rcpt.nodes_evaluated != self.nodes_evaluated:
                raise ReplayContractError(
                    f"METRICS_DISAGREEMENT: nodes_evaluated ({self.nodes_evaluated}) != SearchExecutionReceipt ({s_rcpt.nodes_evaluated})"
                )
            if s_rcpt.problem_digest != self.problem_digest:
                raise ReplayContractError(
                    f"PROBLEM_DIGEST_MISMATCH: {self.problem_digest} != {s_rcpt.problem_digest}"
                )
            if s_rcpt.candidate_id != self.candidate_id:
                raise ReplayContractError(
                    f"CANDIDATE_MISMATCH: candidate_id '{self.candidate_id}' != SearchExecutionReceipt '{s_rcpt.candidate_id}'"
                )
            if s_rcpt.candidate_enabled != self.candidate_enabled:
                raise ReplayContractError(
                    f"CANDIDATE_ENABLED_MISMATCH: candidate_enabled ({self.candidate_enabled}) != SearchExecutionReceipt ({s_rcpt.candidate_enabled})"
                )

        # Section 7: Trace binding invariants
        if len(self.execution_trace_refs) != len(self.execution_trace_digests):
            raise ReceiptValidationError(
                f"TRACE_COUNT_MISMATCH: execution_trace_refs count ({len(self.execution_trace_refs)}) != execution_trace_digests count ({len(self.execution_trace_digests)})"
            )
        if self.evidence_origin in ("EXECUTED_SEARCH_RUN", "CERTIFIED_SEARCH_REPLAY") and self.backend_calls > 0:
            if not self.execution_trace_refs:
                raise ReceiptValidationError(
                    "MISSING_TRACE_REFS: execution_trace_refs cannot be empty for executed search run with backend_calls > 0"
                )

        # Section 6 & 19: Cross-check metrics against bound SearchRun
        if self.bound_search_run is not None:
            sr_dict = self.bound_search_run.to_dict()
            expected_sr_digest = hashlib.sha256(json.dumps(sr_dict, sort_keys=True).encode("utf-8")).hexdigest()
            if self.search_run_digest != expected_sr_digest:
                raise ReplayContractError(
                    f"SEARCH_RUN_DIGEST_MISMATCH: search_run_digest '{self.search_run_digest}' != recomputed '{expected_sr_digest}'"
                )
            if self.search_run_ref != self.bound_search_run.run_id:
                raise ReplayContractError(
                    f"SEARCH_RUN_REF_MISMATCH: search_run_ref '{self.search_run_ref}' != '{self.bound_search_run.run_id}'"
                )
            if self.nodes_expanded != self.bound_search_run.nodes_expanded:
                raise ReplayContractError(
                    f"METRICS_DISAGREEMENT: nodes_expanded ({self.nodes_expanded}) != SearchRun ({self.bound_search_run.nodes_expanded})"
                )
            if self.nodes_evaluated != self.bound_search_run.nodes_evaluated:
                raise ReplayContractError(
                    f"METRICS_DISAGREEMENT: nodes_evaluated ({self.nodes_evaluated}) != SearchRun ({self.bound_search_run.nodes_evaluated})"
                )
            sr_solved = (self.bound_search_run.terminal_status == "SOLVED")
            if self.solved != sr_solved:
                raise ReplayContractError(
                    f"METRICS_DISAGREEMENT: solved ({self.solved}) != SearchRun ({sr_solved})"
                )

    @classmethod
    def from_search_run(
        cls,
        search_run: SearchRun,
        contract: PairedReplayContract,
        arm: str,
        receipt_id: Optional[str] = None,
        evidence_origin: str = "SYNTHETIC_FIXTURE",
        replay_mode: str = "EXECUTED_HELD_OUT_REPLAY",
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None,
    ) -> ReplayRunReceipt:
        sr_dict = search_run.to_dict()
        sr_digest = hashlib.sha256(json.dumps(sr_dict, sort_keys=True).encode("utf-8")).hexdigest()
        now_iso = datetime.now(timezone.utc).isoformat()
        b_digest = hashlib.sha256(json.dumps(contract.search_budget, sort_keys=True).encode("utf-8")).hexdigest()
        p_digest = hashlib.sha256(json.dumps(search_run.policy_configuration, sort_keys=True).encode("utf-8")).hexdigest()
        c_digest = hashlib.sha256(json.dumps(contract.corpus_context, sort_keys=True).encode("utf-8")).hexdigest()
        is_solved = (search_run.terminal_status == "SOLVED")
        branch_count = int(search_run.branching_factor_effective * search_run.nodes_expanded)
        candidate_enabled = (arm == "ABSTRACTED")

        trace_refs = list(search_run.execution_trace_refs)
        trace_digests = list(search_run.execution_trace_digests)
        if not trace_refs and search_run.resulting_trace_id:
            trace_refs = [search_run.resulting_trace_id]
            trace_digests = [search_run.resulting_trace_digest] if search_run.resulting_trace_digest else ["0" * 64]

        return cls(
            receipt_id=receipt_id or f"rcpt-replay-{arm.lower()}-{contract.problem_id}",
            replay_mode=replay_mode,
            arm=arm,
            paired_contract_digest=contract.contract_digest(),
            experimental_unit_id=contract.problem_digest,
            problem_id=contract.problem_id,
            problem_digest=contract.problem_digest,
            backend_id=contract.backend_id,
            search_policy_kind=contract.search_policy_kind,
            search_policy_configuration_digest=p_digest,
            search_budget_digest=b_digest,
            random_seed=contract.random_seed,
            corpus_context_digest=c_digest,
            candidate_id=contract.candidate_id,
            candidate_enabled=candidate_enabled,
            started_at=started_at or now_iso,
            completed_at=completed_at or now_iso,
            nodes_expanded=search_run.nodes_expanded,
            nodes_evaluated=search_run.nodes_evaluated,
            branch_count=branch_count,
            solved=is_solved,
            wall_time_ms=search_run.total_wall_time_ms,
            backend_calls=1 if trace_refs else 0,
            search_run_ref=search_run.run_id,
            search_run_digest=sr_digest,
            execution_trace_refs=trace_refs,
            execution_trace_digests=trace_digests,
            evidence_origin=evidence_origin,
            authority="NONE",
            bound_search_run=search_run,
            search_execution_receipt=search_run.search_execution_receipt,
        )

    @classmethod
    def from_search_execution_bundle(
        cls,
        bundle: SearchExecutionBundle,
        contract: PairedReplayContract,
        arm: str,
        receipt_id: Optional[str] = None,
    ) -> ReplayRunReceipt:
        sr = bundle.search_run
        rcpt = bundle.search_execution_receipt
        c_digest = hashlib.sha256(json.dumps(contract.corpus_context, sort_keys=True).encode("utf-8")).hexdigest()
        is_solved = (sr.terminal_status == "SOLVED")
        branch_count = int(sr.branching_factor_effective * sr.nodes_expanded)
        candidate_enabled = (arm == "ABSTRACTED")

        return cls(
            receipt_id=receipt_id or f"rcpt-replay-{arm.lower()}-{contract.problem_id}",
            replay_mode="EXECUTED_HELD_OUT_REPLAY",
            arm=arm,
            paired_contract_digest=contract.contract_digest(),
            experimental_unit_id=contract.problem_digest,
            problem_id=contract.problem_id,
            problem_digest=contract.problem_digest,
            backend_id=contract.backend_id,
            search_policy_kind=contract.search_policy_kind,
            search_policy_configuration_digest=rcpt.search_policy_configuration_digest,
            search_budget_digest=rcpt.search_budget_digest,
            random_seed=contract.random_seed,
            corpus_context_digest=c_digest,
            candidate_id=contract.candidate_id,
            candidate_enabled=candidate_enabled,
            started_at=rcpt.started_at,
            completed_at=rcpt.completed_at,
            nodes_expanded=rcpt.nodes_expanded,
            nodes_evaluated=rcpt.nodes_evaluated,
            branch_count=branch_count,
            solved=is_solved,
            wall_time_ms=rcpt.wall_time_ms,
            backend_calls=rcpt.backend_calls,
            search_run_ref=rcpt.search_run_id,
            search_run_digest=rcpt.search_run_digest,
            execution_trace_refs=list(rcpt.execution_trace_refs),
            execution_trace_digests=list(rcpt.execution_trace_digests),
            evidence_origin="EXECUTED_SEARCH_RUN",
            authority="NONE",
            bound_search_run=sr,
            search_execution_receipt=rcpt.to_dict(),
        )


@dataclass
class PairedReplayContract:
    """Contract binding all non-abstraction variables identically across arms (Sections 20 & 21)."""
    problem_id: str
    problem_digest: str
    backend_id: str
    search_policy_kind: str
    search_budget: Dict[str, Any]
    random_seed: int
    corpus_context: Dict[str, Any]
    baseline_configuration: Dict[str, Any]
    abstracted_configuration: Dict[str, Any]
    candidate_id: str
    candidate_enabled_in_abstracted: bool = True
    backend_configuration: Dict[str, Any] = field(default_factory=dict)
    source_graph_context: Dict[str, Any] = field(default_factory=dict)
    environment_identity: Dict[str, Any] = field(default_factory=dict)
    search_policy_configuration: Dict[str, Any] = field(default_factory=dict)

    def contract_digest(self) -> str:
        """Deterministic SHA-256 digest of contract content (Section 8 & 20)."""
        payload = {
            "problem_id": self.problem_id,
            "problem_digest": self.problem_digest,
            "backend_id": self.backend_id,
            "backend_configuration": self.backend_configuration,
            "search_policy_kind": self.search_policy_kind,
            "search_policy_configuration": self.search_policy_configuration,
            "search_budget": self.search_budget,
            "random_seed": self.random_seed,
            "corpus_context": self.corpus_context,
            "source_graph_context": self.source_graph_context,
            "environment_identity": self.environment_identity,
            "candidate_id": self.candidate_id,
            "candidate_enabled_in_abstracted": self.candidate_enabled_in_abstracted,
            "baseline_configuration": self.baseline_configuration,
            "abstracted_configuration": self.abstracted_configuration,
        }
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def validate(self) -> None:
        """Enforce full arm parity (Section 9 & 21)."""
        if not HEX_DIGEST_PATTERN.match(self.problem_digest):
            raise ValueError(
                f"Invalid problem_digest: {self.problem_digest}. Must be 64-char lowercase hex."
            )

        if not self.candidate_enabled_in_abstracted:
            raise ReplayContractError(
                "CANDIDATE_NOT_ENABLED_IN_ABSTRACTED_ARM: Candidate must be explicitly enabled in abstracted configuration"
            )

        base_budget = self.baseline_configuration.get("budget", self.search_budget)
        abs_budget = self.abstracted_configuration.get("budget", self.search_budget)
        if base_budget != abs_budget:
            raise ReplayContractError(
                f"BUDGET_MISMATCH: Baseline budget {base_budget} does not match abstracted budget {abs_budget}"
            )

        base_seed = self.baseline_configuration.get("seed", self.random_seed)
        abs_seed = self.abstracted_configuration.get("seed", self.random_seed)
        if base_seed != abs_seed:
            raise ReplayContractError(
                f"SEED_MISMATCH: Random seed must be identical across baseline ({base_seed}) and abstracted ({abs_seed})"
            )

        # Baseline must NOT enable candidate
        if (
            self.baseline_configuration.get("candidate_enabled") is True
            or self.baseline_configuration.get("enable_candidate") is True
        ):
            raise ReplayContractError(
                "BASELINE_CANDIDATE_ENABLED: Baseline configuration must have candidate disabled"
            )

        # Abstracted must enable candidate
        if (
            self.abstracted_configuration.get("candidate_enabled") is False
            or self.abstracted_configuration.get("enable_candidate") is False
        ):
            raise ReplayContractError(
                "ABSTRACTED_CANDIDATE_NOT_ENABLED: Abstracted configuration must have candidate enabled"
            )
        if (
            "candidate_id" in self.abstracted_configuration
            and self.abstracted_configuration["candidate_id"] != self.candidate_id
        ):
            raise ReplayContractError(
                f"ABSTRACTED_CANDIDATE_MISMATCH: Abstracted candidate_id '{self.abstracted_configuration.get('candidate_id')}' != '{self.candidate_id}'"
            )

        # Normalized configuration parity after removing prospective abstraction delta
        ignore_keys = {"candidate_id", "candidate_enabled", "enable_candidate"}
        norm_base = {k: v for k, v in self.baseline_configuration.items() if k not in ignore_keys}
        norm_abs = {k: v for k, v in self.abstracted_configuration.items() if k not in ignore_keys}
        if norm_base != norm_abs:
            raise ReplayContractError(
                f"ARM_CONFIGURATION_DRIFT: Non-abstraction configuration drifted between arms: baseline {norm_base} != abstracted {norm_abs}"
            )


def _validate_receipt_against_contract(
    contract: PairedReplayContract,
    receipt: ReplayRunReceipt,
    expected_arm: str,
) -> None:
    """Validate receipt cross-consistency with contract (Section 22)."""
    receipt.validate()

    if receipt.arm != expected_arm:
        raise ReplayContractError(f"WRONG_REPLAY_ARM: expected {expected_arm}, got {receipt.arm}")

    if expected_arm == "BASELINE":
        if receipt.candidate_enabled is not False:
            raise ReplayContractError("BASELINE_CANDIDATE_ENABLED: Baseline receipt has candidate_enabled != False")
    elif expected_arm == "ABSTRACTED":
        if receipt.candidate_enabled is not True:
            raise ReplayContractError("ABSTRACTED_CANDIDATE_DISABLED: Abstracted receipt has candidate_enabled != True")
        if receipt.candidate_id != contract.candidate_id:
            raise ReplayContractError(
                f"ABSTRACTED_CANDIDATE_MISMATCH: candidate_id '{receipt.candidate_id}' != '{contract.candidate_id}'"
            )

    # Contract digest check
    expected_contract_digest = contract.contract_digest()
    if receipt.paired_contract_digest != expected_contract_digest:
        raise ReplayContractError(
            f"CONTRACT_DIGEST_MISMATCH: receipt paired_contract_digest '{receipt.paired_contract_digest}' != '{expected_contract_digest}'"
        )

    # Cross-checks with contract
    if receipt.problem_id != contract.problem_id:
        raise ReplayContractError(f"PROBLEM_ID_MISMATCH: {receipt.problem_id} != {contract.problem_id}")
    if receipt.problem_digest != contract.problem_digest:
        raise ReplayContractError(f"PROBLEM_DIGEST_MISMATCH: {receipt.problem_digest} != {contract.problem_digest}")
    if receipt.backend_id != contract.backend_id:
        raise ReplayContractError(f"BACKEND_MISMATCH: {receipt.backend_id} != {contract.backend_id}")
    if receipt.search_policy_kind != contract.search_policy_kind:
        raise ReplayContractError(f"SEARCH_POLICY_MISMATCH: {receipt.search_policy_kind} != {contract.search_policy_kind}")
    if receipt.random_seed != contract.random_seed:
        raise ReplayContractError(f"SEED_MISMATCH: {receipt.random_seed} != {contract.random_seed}")

    expected_budget_digest = hashlib.sha256(json.dumps(contract.search_budget, sort_keys=True).encode("utf-8")).hexdigest()
    if receipt.search_budget_digest != expected_budget_digest:
        raise ReplayContractError(
            f"SEARCH_BUDGET_DIGEST_MISMATCH: {receipt.search_budget_digest} != {expected_budget_digest}"
        )

    expected_corpus_digest = hashlib.sha256(json.dumps(contract.corpus_context, sort_keys=True).encode("utf-8")).hexdigest()
    if receipt.corpus_context_digest != expected_corpus_digest:
        raise ReplayContractError(
            f"CORPUS_CONTEXT_DIGEST_MISMATCH: {receipt.corpus_context_digest} != {expected_corpus_digest}"
        )


@dataclass
class ReplayComparison:
    """Comparison of search performance derived from observed run receipts."""
    problem_id: str
    baseline_receipt: ReplayRunReceipt
    abstracted_receipt: ReplayRunReceipt

    @property
    def baseline_nodes_expanded(self) -> int:
        return self.baseline_receipt.nodes_expanded

    @property
    def abstracted_nodes_expanded(self) -> int:
        return self.abstracted_receipt.nodes_expanded

    @property
    def baseline_branches(self) -> int:
        return self.baseline_receipt.branch_count

    @property
    def abstracted_branches(self) -> int:
        return self.abstracted_receipt.branch_count

    @property
    def baseline_time_ms(self) -> float:
        return self.baseline_receipt.wall_time_ms

    @property
    def abstracted_time_ms(self) -> float:
        return self.abstracted_receipt.wall_time_ms

    @property
    def solved_with_abstraction(self) -> bool:
        return self.abstracted_receipt.solved

    @property
    def node_reduction_ratio(self) -> float:
        if self.baseline_nodes_expanded == 0:
            return 1.0
        return 1.0 - (self.abstracted_nodes_expanded / self.baseline_nodes_expanded)

    @property
    def branch_reduction(self) -> float:
        return float(self.baseline_branches - self.abstracted_branches)


class HeldOutReplayEngine:
    """Evaluates abstraction candidates against strictly held-out qualification problems."""

    @staticmethod
    def validate_candidate_admissibility(candidate: AbstractionCandidate) -> None:
        """Independently validate candidate's admissibility receipt against candidate (Section 21)."""
        if not candidate.admissibility_receipt:
            raise ReceiptValidationError("MISSING_ADMISSIBILITY_RECEIPT: Candidate has no admissibility receipt")

        rcpt_dict = candidate.admissibility_receipt.to_dict() if hasattr(candidate.admissibility_receipt, "to_dict") else candidate.admissibility_receipt
        if ADMISSIBILITY_RECEIPT_SCHEMA_PATH.exists():
            schema_data = json.loads(ADMISSIBILITY_RECEIPT_SCHEMA_PATH.read_text(encoding="utf-8"))
            try:
                jsonschema.validate(rcpt_dict, schema_data)
            except jsonschema.ValidationError as e:
                raise ReceiptValidationError(f"ADMISSIBILITY_RECEIPT_SCHEMA_FAILED: {e.message}") from e

        rcpt = AdmissibilityReceipt.from_dict(rcpt_dict)
        rcpt.validate()

        if rcpt.lgg_digest != candidate.anti_unification_evidence.deterministic_digest:
            raise ReceiptValidationError(
                f"ADMISSIBILITY_LGG_MISMATCH: Receipt LGG digest '{rcpt.lgg_digest}' != candidate '{candidate.anti_unification_evidence.deterministic_digest}'"
            )

        status_val = rcpt.admissibility_status.value if hasattr(rcpt.admissibility_status, "value") else str(rcpt.admissibility_status)
        if status_val != "ADMISSIBLE":
            raise ReceiptValidationError(
                f"ADMISSIBILITY_STATUS_INVALID: Receipt admissibility status is '{status_val}', expected 'ADMISSIBLE'"
            )

        if set(rcpt.source_trace_ids) != set(candidate.discovery_set_trace_ids):
            raise ReceiptValidationError(
                f"ADMISSIBILITY_TRACE_MISMATCH: Receipt source traces {rcpt.source_trace_ids} != candidate {candidate.discovery_set_trace_ids}"
            )

        if set(rcpt.discovery_problem_digests) != set(candidate.discovery_problem_digests):
            raise ReceiptValidationError(
                f"ADMISSIBILITY_PROBLEM_DIGEST_MISMATCH: Receipt problem digests {rcpt.discovery_problem_digests} != candidate {candidate.discovery_problem_digests}"
            )

        if rcpt.meaningful_shared_constructor_count < 1:
            raise ReceiptValidationError(
                f"TRIVIAL_STRUCTURAL_GENERALIZATION: Meaningful shared constructor count must be >= 1, got {rcpt.meaningful_shared_constructor_count}"
            )

        expected_digest = rcpt.compute_digest()
        if rcpt.receipt_digest != expected_digest:
            raise ReceiptValidationError(
                f"ADMISSIBILITY_RECEIPT_DIGEST_MISMATCH: Receipt digest '{rcpt.receipt_digest}' != recomputed '{expected_digest}'"
            )

    @staticmethod
    def verify_held_out_disjointness(
        candidate_or_disc_traces: Any,
        qualification_traces_or_contracts: Any = None,
        qualification_trace_ids: Optional[Sequence[str]] = None,
        qualification_problem_digests: Optional[Sequence[str]] = None,
        qualification_contracts: Optional[Sequence[PairedReplayContract]] = None,
    ) -> None:
        """Enforce strict invariant: DISCOVERY_PROBLEM_DIGESTS ∩ QUALIFICATION_PROBLEM_DIGESTS = ∅ (Section 16, 17, 18)."""
        # Handle call styles: candidate object vs list of trace ids
        if isinstance(candidate_or_disc_traces, AbstractionCandidate):
            if not candidate_or_disc_traces.discovery_problem_digests:
                raise HeldOutDataLeakageError(
                    "HELD_OUT_DATA_LEAKAGE: Missing discovery problem digests prohibits qualification (fail-closed experimental unit rule)"
                )
            for d in candidate_or_disc_traces.discovery_problem_digests:
                if not HEX_DIGEST_PATTERN.match(d):
                    raise HeldOutDataLeakageError(
                        f"Invalid discovery problem digest '{d}': must be 64-char lowercase hex"
                    )
            disc_digests = set(candidate_or_disc_traces.discovery_problem_digests)
            disc_traces = set(candidate_or_disc_traces.discovery_set_trace_ids)
        else:
            disc_traces = set(candidate_or_disc_traces)
            disc_digests = set()

        qual_digests = set(qualification_problem_digests or [])
        qual_traces = set(qualification_trace_ids or [])

        if qualification_contracts:
            for c in qualification_contracts:
                qual_digests.add(c.problem_digest)
                qual_traces.add(c.problem_id)

        if qualification_traces_or_contracts:
            for item in qualification_traces_or_contracts:
                if isinstance(item, PairedReplayContract):
                    qual_digests.add(item.problem_digest)
                    qual_traces.add(item.problem_id)
                elif isinstance(item, ExecutionTrace):
                    if item.problem_digest:
                        qual_digests.add(item.problem_digest)
                    qual_traces.add(item.trace_id)
                elif isinstance(item, str):
                    qual_traces.add(item)

        for d in qual_digests:
            if not HEX_DIGEST_PATTERN.match(d):
                raise HeldOutDataLeakageError(
                    f"Invalid qualification problem digest '{d}': must be 64-char lowercase hex"
                )

        # Check problem digest disjointness (canonical experimental unit)
        if disc_digests and qual_digests:
            digest_overlap = disc_digests.intersection(qual_digests)
            if digest_overlap:
                raise HeldOutDataLeakageError(
                    f"HELD_OUT_DATA_LEAKAGE: Problem digest(s) {sorted(digest_overlap)} appear in both discovery set and qualification set"
                )

        # Check trace ID disjointness
        if disc_traces and qual_traces:
            trace_overlap = disc_traces.intersection(qual_traces)
            if trace_overlap:
                raise HeldOutDataLeakageError(
                    f"DISCOVERY_SET_DATA_LEAKAGE: Traces {sorted(trace_overlap)} appear in both discovery set and qualification set"
                )

    def evaluate_synthetic_replay_fixture(
        self,
        candidate: AbstractionCandidate,
        qualification_traces: Sequence[ExecutionTrace],
        simulated_comparisons: Optional[Sequence[ReplayComparison]] = None,
    ) -> AbstractionValueReport:
        """Run synthetic fixture replay.
        
        Invariant (Sections 17 & 24):
        - Uses mode SYNTHETIC_REPLAY_FIXTURE.
        - CANNOT qualify candidate into QUALIFIED_HELD_OUT status.
        - Authority remains NONE.
        """
        qual_ids = [t.trace_id for t in qualification_traces]
        qual_problem_ids = [t.problem_id for t in qualification_traces]
        qual_digests = [t.problem_digest for t in qualification_traces if t.problem_digest]
        self.verify_held_out_disjointness(
            candidate,
            qualification_traces_or_contracts=qualification_traces,
            qualification_trace_ids=qual_ids,
            qualification_problem_digests=qual_digests,
        )

        # Build report with explicit SYNTHETIC_REPLAY_FIXTURE mode
        report = AbstractionValueReport(
            candidate_id=candidate.candidate_id,
            supporting_trace_count=len(candidate.discovery_set_trace_ids),
            structural_compression_ratio=1.0,
            proof_branch_reduction=0.0,
            candidate_evaluation_reduction=0.0,
            held_out_success_rate_delta=0.0,
            wall_time_delta_pct=0.0,
            portability_across_instances=0.0,
            portability_across_formal_systems=0.0,
            human_inspectable_representation_size=len(str(candidate.formal_specification)),
            is_held_out_disjoint_from_discovery=True,
            replay_mode="SYNTHETIC_REPLAY_FIXTURE",
        )

        # Freeze invariant: synthetic replay leaves status at PROPOSED or CANDIDATE_ONLY
        candidate.qualification_trace_ids = qual_ids
        candidate.qualification_problem_ids = qual_problem_ids
        candidate.qualification_problem_digests = qual_digests
        candidate.held_out_evaluation = report.to_dict()
        if candidate.status != CandidateStatus.REJECTED:
            candidate.status = CandidateStatus.CANDIDATE_ONLY

        return report

    def evaluate_candidate_on_held_out(
        self,
        candidate: AbstractionCandidate,
        qualification_traces: Sequence[ExecutionTrace],
    ) -> AbstractionValueReport:
        """Compatibility wrapper invoking synthetic replay fixture mode."""
        return self.evaluate_synthetic_replay_fixture(candidate, qualification_traces)

    def execute_paired_replay(
        self,
        candidate: AbstractionCandidate,
        contracts: Sequence[PairedReplayContract],
        runner_fn: Callable[[PairedReplayContract, str], Union[ReplayRunReceipt, SearchExecutionBundle]],
    ) -> AbstractionValueReport:
        """Execute genuine paired replay across held-out problems (Sections 18-23)."""
        qual_digests = [c.problem_digest for c in contracts]
        qual_problem_ids = [c.problem_id for c in contracts]
        self.verify_held_out_disjointness(
            candidate,
            qualification_contracts=contracts,
            qualification_problem_digests=qual_digests,
        )

        def _run_and_adapt(contract: PairedReplayContract, arm: str) -> ReplayRunReceipt:
            result = runner_fn(contract, arm)
            if isinstance(result, SearchExecutionBundle):
                return ReplayRunReceipt.from_search_execution_bundle(result, contract, arm)
            return result

        comparisons: List[ReplayComparison] = []
        for contract in contracts:
            contract.validate()
            base_rcpt = _run_and_adapt(contract, "BASELINE")
            abs_rcpt = _run_and_adapt(contract, "ABSTRACTED")

            # Section 18 & 22: Validate receipts against contract & schema & cross-consistency
            _validate_receipt_against_contract(contract, base_rcpt, "BASELINE")
            _validate_receipt_against_contract(contract, abs_rcpt, "ABSTRACTED")

            comparisons.append(ReplayComparison(contract.problem_id, base_rcpt, abs_rcpt))

        qual_trace_ids: List[str] = []
        for comp in comparisons:
            for ref in comp.baseline_receipt.execution_trace_refs + comp.abstracted_receipt.execution_trace_refs:
                if ref not in qual_trace_ids:
                    qual_trace_ids.append(ref)

        candidate.qualification_problem_ids = qual_problem_ids
        candidate.qualification_problem_digests = qual_digests
        candidate.qualification_trace_ids = qual_trace_ids

        if not comparisons:
            report = AbstractionValueReport(
                candidate_id=candidate.candidate_id,
                supporting_trace_count=len(candidate.discovery_set_trace_ids),
                structural_compression_ratio=1.0,
                proof_branch_reduction=0.0,
                candidate_evaluation_reduction=0.0,
                held_out_success_rate_delta=0.0,
                wall_time_delta_pct=0.0,
                portability_across_instances=0.0,
                portability_across_formal_systems=0.0,
                human_inspectable_representation_size=len(str(candidate.formal_specification)),
                is_held_out_disjoint_from_discovery=True,
                replay_mode="EXECUTED_HELD_OUT_REPLAY",
            )
            candidate.held_out_evaluation = report.to_dict()
            return report

        total_base_nodes = sum(c.baseline_nodes_expanded for c in comparisons)
        total_abs_nodes = sum(c.abstracted_nodes_expanded for c in comparisons)
        total_base_time = sum(c.baseline_time_ms for c in comparisons)
        total_abs_time = sum(c.abstracted_time_ms for c in comparisons)
        avg_branch_red = sum(c.branch_reduction for c in comparisons) / len(comparisons)

        compression = total_base_nodes / max(1, total_abs_nodes)
        eval_reduction = (total_base_nodes - total_abs_nodes) / max(1, total_base_nodes)
        time_delta_pct = (
            ((total_abs_time - total_base_time) / max(0.001, total_base_time)) * 100.0
            if total_base_time > 0 else 0.0
        )

        base_solves = sum(1 for c in comparisons if c.baseline_receipt.solved)
        abs_solves = sum(1 for c in comparisons if c.abstracted_receipt.solved)
        success_delta = (abs_solves - base_solves) / len(comparisons)

        all_executed_or_certified = all(
            c.baseline_receipt.evidence_origin in ("EXECUTED_SEARCH_RUN", "CERTIFIED_SEARCH_REPLAY")
            and c.abstracted_receipt.evidence_origin in ("EXECUTED_SEARCH_RUN", "CERTIFIED_SEARCH_REPLAY")
            for c in comparisons
        )
        replay_mode = "EXECUTED_HELD_OUT_REPLAY" if all_executed_or_certified else "SYNTHETIC_REPLAY_FIXTURE"

        report = AbstractionValueReport(
            candidate_id=candidate.candidate_id,
            supporting_trace_count=len(candidate.discovery_set_trace_ids),
            structural_compression_ratio=compression,
            proof_branch_reduction=avg_branch_red,
            candidate_evaluation_reduction=eval_reduction,
            held_out_success_rate_delta=success_delta,
            wall_time_delta_pct=time_delta_pct,
            portability_across_instances=abs_solves / len(comparisons),
            portability_across_formal_systems=0.0,
            human_inspectable_representation_size=len(str(candidate.formal_specification)),
            is_held_out_disjoint_from_discovery=True,
            replay_mode=replay_mode,
        )

        candidate.held_out_evaluation = report.to_dict()

        # Section 15 & 23: Promotion to QUALIFIED_HELD_OUT requires ALL of:
        # - candidate.admissibility_status == AdmissibilityStatus.ADMISSIBLE
        # - candidate.admissibility_receipt is valid
        # - disjoint experimental units
        # - valid paired contracts with arm parity
        # - two valid receipts per experimental unit
        # - candidate.discovery_origin in ("EXECUTED_OBSERVED", "CERTIFIED_REPLAY")
        # - evidence_origin in ("EXECUTED_SEARCH_RUN", "CERTIFIED_SEARCH_REPLAY")
        # - observed benefit meeting threshold
        # - no success-rate degradation
        is_admissible = (candidate.admissibility_status == AdmissibilityStatus.ADMISSIBLE)
        has_receipt = candidate.admissibility_receipt is not None
        no_degradation = (success_delta >= 0.0)
        is_non_synthetic_discovery = candidate.discovery_origin in ("EXECUTED_OBSERVED", "CERTIFIED_REPLAY")

        if (
            is_admissible
            and has_receipt
            and all_executed_or_certified
            and no_degradation
            and is_non_synthetic_discovery
            and report.is_qualified_for_promotion()
        ):
            # Independently validate admissibility receipt per Section 21
            self.validate_candidate_admissibility(candidate)
            candidate.status = CandidateStatus.QUALIFIED_HELD_OUT
        else:
            candidate.status = CandidateStatus.CANDIDATE_ONLY

        return report
