"""Held-out replay engine, paired replay contracts, and empirical search measurement (WO-MATH-FORMAL-DISCOVERY-01A-R1)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Set

from msk_formal_discovery.abstraction.anti_unification import AdmissibilityStatus
from msk_formal_discovery.abstraction.candidate import AbstractionCandidate, CandidateStatus
from msk_formal_discovery.abstraction.value_metrics import AbstractionValueReport
from msk_formal_discovery.core.exceptions import (
    HeldOutDataLeakageError,
    ReplayContractError,
)
from msk_formal_discovery.trace.ir import ExecutionTrace


@dataclass
class ReplayRunReceipt:
    """Observed run receipt from executing an arm of a paired replay."""
    run_id: str
    arm: str  # "BASELINE" or "ABSTRACTED"
    problem_id: str
    nodes_expanded: int
    nodes_evaluated: int
    branch_count: int
    solved: bool
    wall_time_ms: float
    backend_calls: int = 1
    execution_receipts: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class PairedReplayContract:
    """Contract binding all non-abstraction variables identically across arms (Section 12)."""
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
    candidate_enabled_in_abstracted: bool

    def validate(self) -> None:
        """Enforce paired replay invariants."""
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
    def verify_held_out_disjointness(
        discovery_trace_ids: Sequence[str],
        qualification_trace_ids: Sequence[str],
    ) -> None:
        """Enforce strict invariant: DISCOVERY_SET != QUALIFICATION_SET.
        
        Raises HeldOutDataLeakageError if any trace appears in both sets.
        """
        disc_set = set(discovery_trace_ids)
        qual_set = set(qualification_trace_ids)
        overlap = disc_set.intersection(qual_set)
        if overlap:
            raise HeldOutDataLeakageError(
                f"DISCOVERY_SET_DATA_LEAKAGE: Traces {sorted(overlap)} appear in both discovery set and qualification set"
            )

    def evaluate_synthetic_replay_fixture(
        self,
        candidate: AbstractionCandidate,
        qualification_traces: Sequence[ExecutionTrace],
        simulated_comparisons: Optional[Sequence[ReplayComparison]] = None,
    ) -> AbstractionValueReport:
        """Run synthetic fixture replay.
        
        Invariant (Sections 10 & 11):
        - Uses mode SYNTHETIC_REPLAY_FIXTURE.
        - CANNOT qualify candidate into QUALIFIED_HELD_OUT status.
        - Authority remains NONE.
        """
        qual_ids = [t.trace_id for t in qualification_traces]
        self.verify_held_out_disjointness(candidate.discovery_set_trace_ids, qual_ids)

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
        runner_fn: Callable[[PairedReplayContract, str], ReplayRunReceipt],
    ) -> AbstractionValueReport:
        """Execute genuine paired replay across held-out problems (Sections 11-14).
        
        Only this mode may establish held-out qualification.
        """
        qual_ids = [c.problem_id for c in contracts]
        self.verify_held_out_disjointness(candidate.discovery_set_trace_ids, qual_ids)

        comparisons: List[ReplayComparison] = []
        for contract in contracts:
            contract.validate()
            base_rcpt = runner_fn(contract, "BASELINE")
            abs_rcpt = runner_fn(contract, "ABSTRACTED")
            comparisons.append(ReplayComparison(contract.problem_id, base_rcpt, abs_rcpt))

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
            replay_mode="EXECUTED_HELD_OUT_REPLAY",
        )

        candidate.qualification_trace_ids = qual_ids
        candidate.held_out_evaluation = report.to_dict()

        # Gate check for promotion to QUALIFIED_HELD_OUT:
        # Requires: admissibility == ADMISSIBLE, report qualified, and success not degraded
        is_admissible = (candidate.admissibility_status == AdmissibilityStatus.ADMISSIBLE)
        if is_admissible and report.is_qualified_for_promotion():
            candidate.status = CandidateStatus.QUALIFIED_HELD_OUT
        else:
            candidate.status = CandidateStatus.CANDIDATE_ONLY

        return report
