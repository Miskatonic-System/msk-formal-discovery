"""Authoritative eight-way adjudication logic (WO-MATH-FORMAL-DISCOVERY-01B-R1 Sections 15 & 16)."""
from __future__ import annotations

import hashlib
import statistics
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


class AdjudicationDisposition(str, Enum):
    """Authoritative eight-way adjudication disposition."""
    EXPERIMENT_INFRASTRUCTURE_BLOCKED = "EXPERIMENT_INFRASTRUCTURE_BLOCKED"
    CANDIDATE_DISCOVERY_FAILED = "CANDIDATE_DISCOVERY_FAILED"
    APPLICATION_SEMANTICS_FAILED = "APPLICATION_SEMANTICS_FAILED"
    SELECTIVITY_FAILURE = "SELECTIVITY_FAILURE"
    CANDIDATE_NOT_APPLIED_ON_POSITIVE_SET = "CANDIDATE_NOT_APPLIED_ON_POSITIVE_SET"
    ABSTRACTION_SEARCH_BENEFIT_NOT_OBSERVED = "ABSTRACTION_SEARCH_BENEFIT_NOT_OBSERVED"
    ABSTRACTION_SEARCH_BENEFIT_HETEROGENEOUS = "ABSTRACTION_SEARCH_BENEFIT_HETEROGENEOUS"
    ABSTRACTION_SEARCH_BENEFIT_SUPPORTED = "ABSTRACTION_SEARCH_BENEFIT_SUPPORTED"


def get_adjudicator_implementation_digest() -> str:
    """SHA-256 digest of adjudication.py file bytes."""
    path = Path(__file__).resolve()
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class AdjudicationSummary:
    """Evaluation summary for authoritative adjudication."""
    disposition: AdjudicationDisposition
    positive_total_baseline_nodes: int
    positive_total_abstracted_nodes: int
    positive_node_delta: int
    positive_node_reduction_pct: float
    positive_median_delta: float
    positive_improved_count: int
    positive_total_count: int
    negative_total_baseline_nodes: int
    negative_total_abstracted_nodes: int
    negative_node_delta: int
    negative_applications_count: int
    all_smt_verified: bool
    replays_verified: bool
    no_regressions: bool
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "disposition": self.disposition.value,
            "positive_total_baseline_nodes": self.positive_total_baseline_nodes,
            "positive_total_abstracted_nodes": self.positive_total_abstracted_nodes,
            "positive_node_delta": self.positive_node_delta,
            "positive_node_reduction_pct": round(self.positive_node_reduction_pct, 4),
            "positive_median_delta": round(self.positive_median_delta, 4),
            "positive_improved_count": self.positive_improved_count,
            "positive_total_count": self.positive_total_count,
            "negative_total_baseline_nodes": self.negative_total_baseline_nodes,
            "negative_total_abstracted_nodes": self.negative_total_abstracted_nodes,
            "negative_node_delta": self.negative_node_delta,
            "negative_applications_count": self.negative_applications_count,
            "all_smt_verified": self.all_smt_verified,
            "replays_verified": self.replays_verified,
            "no_regressions": self.no_regressions,
            "details": self.details,
            "adjudicator_implementation_digest": get_adjudicator_implementation_digest(),
        }


def adjudicate_01b_r1(
    positive_comparisons: Sequence[Dict[str, Any]],
    negative_comparisons: Sequence[Dict[str, Any]],
    infrastructure_blocked: bool = False,
    candidate_discovery_failed: bool = False,
    replays_verified: bool = True,
    blocking_reason: Optional[str] = None,
) -> AdjudicationSummary:
    """Evaluate experimental outcome under the exact eight-way priority order (Section 16).

    Priority:
    1. EXPERIMENT_INFRASTRUCTURE_BLOCKED
    2. CANDIDATE_DISCOVERY_FAILED
    3. APPLICATION_SEMANTICS_FAILED
    4. SELECTIVITY_FAILURE
    5. CANDIDATE_NOT_APPLIED_ON_POSITIVE_SET
    6. ABSTRACTION_SEARCH_BENEFIT_NOT_OBSERVED
    7. ABSTRACTION_SEARCH_BENEFIT_HETEROGENEOUS
    8. ABSTRACTION_SEARCH_BENEFIT_SUPPORTED
    """
    # 1. EXPERIMENT_INFRASTRUCTURE_BLOCKED
    if infrastructure_blocked:
        return AdjudicationSummary(
            disposition=AdjudicationDisposition.EXPERIMENT_INFRASTRUCTURE_BLOCKED,
            positive_total_baseline_nodes=0,
            positive_total_abstracted_nodes=0,
            positive_node_delta=0,
            positive_node_reduction_pct=0.0,
            positive_median_delta=0.0,
            positive_improved_count=0,
            positive_total_count=len(positive_comparisons),
            negative_total_baseline_nodes=0,
            negative_total_abstracted_nodes=0,
            negative_node_delta=0,
            negative_applications_count=0,
            all_smt_verified=False,
            replays_verified=False,
            no_regressions=False,
            details={"reason": blocking_reason or "Infrastructure failure or drift detected"},
        )

    # 2. CANDIDATE_DISCOVERY_FAILED
    if candidate_discovery_failed:
        return AdjudicationSummary(
            disposition=AdjudicationDisposition.CANDIDATE_DISCOVERY_FAILED,
            positive_total_baseline_nodes=0,
            positive_total_abstracted_nodes=0,
            positive_node_delta=0,
            positive_node_reduction_pct=0.0,
            positive_median_delta=0.0,
            positive_improved_count=0,
            positive_total_count=len(positive_comparisons),
            negative_total_baseline_nodes=0,
            negative_total_abstracted_nodes=0,
            negative_node_delta=0,
            negative_applications_count=0,
            all_smt_verified=False,
            replays_verified=False,
            no_regressions=False,
            details={"reason": blocking_reason or "Candidate discovery failed or unrepresented"},
        )

    all_comparisons = list(positive_comparisons) + list(negative_comparisons)
    all_smt_verified = all(c.get("smt_unsat", False) is True for c in all_comparisons)
    no_regressions = all(
        (not c.get("baseline_solved", False)) or c.get("abstracted_solved", False)
        for c in all_comparisons
    )

    # 3. APPLICATION_SEMANTICS_FAILED
    if (not all_smt_verified) or (not no_regressions) or (not replays_verified):
        failure_details = []
        if not all_smt_verified:
            failure_details.append("SMT paired-terminal verification failed on one or more units")
        if not no_regressions:
            failure_details.append("Solve-rate regression: unit solved in baseline arm failed in abstracted arm")
        if not replays_verified:
            failure_details.append("Replay contract verification failed")
        return AdjudicationSummary(
            disposition=AdjudicationDisposition.APPLICATION_SEMANTICS_FAILED,
            positive_total_baseline_nodes=sum(c.get("baseline_nodes", 0) for c in positive_comparisons),
            positive_total_abstracted_nodes=sum(c.get("abstracted_nodes", 0) for c in positive_comparisons),
            positive_node_delta=0,
            positive_node_reduction_pct=0.0,
            positive_median_delta=0.0,
            positive_improved_count=0,
            positive_total_count=len(positive_comparisons),
            negative_total_baseline_nodes=sum(c.get("baseline_nodes", 0) for c in negative_comparisons),
            negative_total_abstracted_nodes=sum(c.get("abstracted_nodes", 0) for c in negative_comparisons),
            negative_node_delta=0,
            negative_applications_count=sum(c.get("applications_count", 0) for c in negative_comparisons),
            all_smt_verified=all_smt_verified,
            replays_verified=replays_verified,
            no_regressions=no_regressions,
            details={"failures": failure_details},
        )

    # 4. SELECTIVITY_FAILURE
    neg_applications = sum(c.get("applications_count", 0) for c in negative_comparisons)
    neg_base_nodes = sum(c.get("baseline_nodes", 0) for c in negative_comparisons)
    neg_abs_nodes = sum(c.get("abstracted_nodes", 0) for c in negative_comparisons)
    neg_delta = neg_abs_nodes - neg_base_nodes
    any_neg_diverged = any(
        c.get("baseline_nodes") != c.get("abstracted_nodes")
        or c.get("baseline_evaluated") != c.get("abstracted_evaluated")
        or c.get("baseline_branches") != c.get("abstracted_branches")
        or c.get("candidate_applied", False)
        for c in negative_comparisons
    )
    if neg_applications > 0 or neg_delta != 0 or any_neg_diverged:
        return AdjudicationSummary(
            disposition=AdjudicationDisposition.SELECTIVITY_FAILURE,
            positive_total_baseline_nodes=sum(c.get("baseline_nodes", 0) for c in positive_comparisons),
            positive_total_abstracted_nodes=sum(c.get("abstracted_nodes", 0) for c in positive_comparisons),
            positive_node_delta=0,
            positive_node_reduction_pct=0.0,
            positive_median_delta=0.0,
            positive_improved_count=0,
            positive_total_count=len(positive_comparisons),
            negative_total_baseline_nodes=neg_base_nodes,
            negative_total_abstracted_nodes=neg_abs_nodes,
            negative_node_delta=neg_delta,
            negative_applications_count=neg_applications,
            all_smt_verified=all_smt_verified,
            replays_verified=replays_verified,
            no_regressions=no_regressions,
            details={"reason": f"Negative controls diverged or applied candidate: applications={neg_applications}, delta={neg_delta}"},
        )

    # 5. CANDIDATE_NOT_APPLIED_ON_POSITIVE_SET
    pos_applications = sum(c.get("applications_count", 0) for c in positive_comparisons)
    if pos_applications == 0:
        return AdjudicationSummary(
            disposition=AdjudicationDisposition.CANDIDATE_NOT_APPLIED_ON_POSITIVE_SET,
            positive_total_baseline_nodes=sum(c.get("baseline_nodes", 0) for c in positive_comparisons),
            positive_total_abstracted_nodes=sum(c.get("abstracted_nodes", 0) for c in positive_comparisons),
            positive_node_delta=0,
            positive_node_reduction_pct=0.0,
            positive_median_delta=0.0,
            positive_improved_count=0,
            positive_total_count=len(positive_comparisons),
            negative_total_baseline_nodes=neg_base_nodes,
            negative_total_abstracted_nodes=neg_abs_nodes,
            negative_node_delta=neg_delta,
            negative_applications_count=0,
            all_smt_verified=all_smt_verified,
            replays_verified=replays_verified,
            no_regressions=no_regressions,
            details={"reason": "Candidate was not applied on any positive held-out units"},
        )

    # Calculate positive metrics
    pos_base_nodes = sum(c.get("baseline_nodes", 0) for c in positive_comparisons)
    pos_abs_nodes = sum(c.get("abstracted_nodes", 0) for c in positive_comparisons)
    pos_node_delta = pos_abs_nodes - pos_base_nodes
    pos_reduction_pct = (
        ((pos_base_nodes - pos_abs_nodes) / pos_base_nodes) * 100.0
        if pos_base_nodes > 0
        else 0.0
    )
    pos_deltas = [c.get("abstracted_nodes", 0) - c.get("baseline_nodes", 0) for c in positive_comparisons]
    pos_median_delta = statistics.median(pos_deltas) if pos_deltas else 0.0
    pos_improved_count = sum(1 for d in pos_deltas if d < 0)
    pos_total_count = len(positive_comparisons)

    # 6. ABSTRACTION_SEARCH_BENEFIT_NOT_OBSERVED
    # Requires total abstracted < total baseline AND median delta < 0
    if pos_abs_nodes >= pos_base_nodes or pos_median_delta >= 0:
        return AdjudicationSummary(
            disposition=AdjudicationDisposition.ABSTRACTION_SEARCH_BENEFIT_NOT_OBSERVED,
            positive_total_baseline_nodes=pos_base_nodes,
            positive_total_abstracted_nodes=pos_abs_nodes,
            positive_node_delta=pos_node_delta,
            positive_node_reduction_pct=pos_reduction_pct,
            positive_median_delta=pos_median_delta,
            positive_improved_count=pos_improved_count,
            positive_total_count=pos_total_count,
            negative_total_baseline_nodes=neg_base_nodes,
            negative_total_abstracted_nodes=neg_abs_nodes,
            negative_node_delta=neg_delta,
            negative_applications_count=0,
            all_smt_verified=all_smt_verified,
            replays_verified=replays_verified,
            no_regressions=no_regressions,
            details={"reason": f"No aggregate node reduction observed: base={pos_base_nodes}, abs={pos_abs_nodes}, median={pos_median_delta}"},
        )

    # 7. ABSTRACTION_SEARCH_BENEFIT_HETEROGENEOUS
    # Aggregate benefit exists but fewer than 6 of 8 positive units improve
    if pos_improved_count < 6:
        return AdjudicationSummary(
            disposition=AdjudicationDisposition.ABSTRACTION_SEARCH_BENEFIT_HETEROGENEOUS,
            positive_total_baseline_nodes=pos_base_nodes,
            positive_total_abstracted_nodes=pos_abs_nodes,
            positive_node_delta=pos_node_delta,
            positive_node_reduction_pct=pos_reduction_pct,
            positive_median_delta=pos_median_delta,
            positive_improved_count=pos_improved_count,
            positive_total_count=pos_total_count,
            negative_total_baseline_nodes=neg_base_nodes,
            negative_total_abstracted_nodes=neg_abs_nodes,
            negative_node_delta=neg_delta,
            negative_applications_count=0,
            all_smt_verified=all_smt_verified,
            replays_verified=replays_verified,
            no_regressions=no_regressions,
            details={"reason": f"Heterogeneous effect: {pos_improved_count}/{pos_total_count} units improved (need >= 6)"},
        )

    # 8. ABSTRACTION_SEARCH_BENEFIT_SUPPORTED
    return AdjudicationSummary(
        disposition=AdjudicationDisposition.ABSTRACTION_SEARCH_BENEFIT_SUPPORTED,
        positive_total_baseline_nodes=pos_base_nodes,
        positive_total_abstracted_nodes=pos_abs_nodes,
        positive_node_delta=pos_node_delta,
        positive_node_reduction_pct=pos_reduction_pct,
        positive_median_delta=pos_median_delta,
        positive_improved_count=pos_improved_count,
        positive_total_count=pos_total_count,
        negative_total_baseline_nodes=neg_base_nodes,
        negative_total_abstracted_nodes=neg_abs_nodes,
        negative_node_delta=neg_delta,
        negative_applications_count=0,
        all_smt_verified=all_smt_verified,
        replays_verified=replays_verified,
        no_regressions=no_regressions,
        details={"status": "All prerequisite gates passed, median delta < 0, total nodes reduced, >= 6/8 improved, zero regressions"},
    )
