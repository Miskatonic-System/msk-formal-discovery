"""Authoritative Representation Orbit Adjudication for WO-MATH-FORMAL-DISCOVERY-01C."""
from __future__ import annotations

import hashlib
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from msk_formal_discovery.representation.transform import RepresentationStratum


def get_representation_adjudicator_implementation_digest() -> str:
    """SHA-256 digest of adjudication.py source bytes."""
    path = Path(__file__).resolve()
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class StratumEvaluation:
    """Evaluation result for one representation stratum."""
    stratum: str
    positive_units_count: int
    positive_improved_count: int
    positive_applied_count: int
    positive_baseline_total: int
    positive_abstracted_total: int
    positive_node_delta: int
    positive_median_delta: float
    negative_units_count: int
    negative_applied_count: int
    negative_node_delta: int
    solve_regressions: int
    smt_checks_passed: bool
    paired_terminal_checks_passed: bool
    positive_gate_passed: bool
    negative_gate_passed: bool
    disposition: str  # REPRESENTATION_STRATUM_INVARIANT, REPRESENTATION_STRATUM_SENSITIVE, REPRESENTATION_STRATUM_INVALID

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stratum": self.stratum,
            "positive_units_count": self.positive_units_count,
            "positive_improved_count": self.positive_improved_count,
            "positive_applied_count": self.positive_applied_count,
            "positive_baseline_total": self.positive_baseline_total,
            "positive_abstracted_total": self.positive_abstracted_total,
            "positive_node_delta": self.positive_node_delta,
            "positive_median_delta": self.positive_median_delta,
            "negative_units_count": self.negative_units_count,
            "negative_applied_count": self.negative_applied_count,
            "negative_node_delta": self.negative_node_delta,
            "solve_regressions": self.solve_regressions,
            "smt_checks_passed": self.smt_checks_passed,
            "paired_terminal_checks_passed": self.paired_terminal_checks_passed,
            "positive_gate_passed": self.positive_gate_passed,
            "negative_gate_passed": self.negative_gate_passed,
            "disposition": self.disposition,
        }


@dataclass
class GlobalAdjudicationResult:
    """Authoritative adjudication outcome across all representation strata."""
    r0_evaluation: StratumEvaluation
    r1_evaluation: StratumEvaluation
    r2_evaluation: StratumEvaluation
    r3_evaluation: StratumEvaluation
    global_disposition: str
    adjudicator_implementation_digest: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "r0_evaluation": self.r0_evaluation.to_dict(),
            "r1_evaluation": self.r1_evaluation.to_dict(),
            "r2_evaluation": self.r2_evaluation.to_dict(),
            "r3_evaluation": self.r3_evaluation.to_dict(),
            "global_disposition": self.global_disposition,
            "adjudicator_implementation_digest": self.adjudicator_implementation_digest,
        }


def adjudicate_stratum(
    stratum_name: str,
    positive_evals: List[Dict[str, Any]],
    negative_evals: List[Dict[str, Any]],
) -> StratumEvaluation:
    """Adjudicate positive and negative gates for a single representation stratum."""
    pos_count = len(positive_evals)
    neg_count = len(negative_evals)

    assert pos_count == 8, f"Expected 8 positive units for {stratum_name}, got {pos_count}"
    assert neg_count == 4, f"Expected 4 negative units for {stratum_name}, got {neg_count}"

    # Positive measures
    pos_deltas = [u["node_delta"] for u in positive_evals]
    pos_improved = sum(1 for d in pos_deltas if d < 0)
    pos_applied = sum(1 for u in positive_evals if u.get("candidate_application_status") == "APPLIED" or u.get("candidate_applied", False))
    pos_base_total = sum(u["baseline_nodes"] for u in positive_evals)
    pos_abs_total = sum(u["abstracted_nodes"] for u in positive_evals)
    pos_delta_total = pos_abs_total - pos_base_total
    pos_median_delta = statistics.median(pos_deltas)

    # Regressions
    pos_regressions = sum(1 for u in positive_evals if u.get("baseline_solved") and not u.get("abstracted_solved"))
    neg_regressions = sum(1 for u in negative_evals if u.get("baseline_solved") and not u.get("abstracted_solved"))
    total_regressions = pos_regressions + neg_regressions

    # Negative measures
    neg_deltas = [u["node_delta"] for u in negative_evals]
    neg_applied = sum(u.get("applications_count", 0) for u in negative_evals)
    neg_delta_total = sum(neg_deltas)

    # SMT checks
    all_trans_smt = all(u.get("transform_smt_passed", True) for u in positive_evals + negative_evals)
    all_term_smt = all(u.get("smt_unsat", False) or u.get("paired_terminal_smt_passed", False) for u in positive_evals + negative_evals)

    # Positive Gate:
    # 1. 8/8 valid representation certificates (all_trans_smt)
    # 2. 8/8 baseline & abstracted solve successfully
    # 3. 8/8 paired terminal SMT checks return UNSAT_REFUTED
    # 4. Zero solve regressions
    # 5. Candidate application status is APPLIED on all 8 positive abstracted arms
    # 6. At least 6/8 show delta < 0
    # 7. Median paired delta < 0
    # 8. Total abstracted nodes < total baseline nodes
    all_pos_solved = all(u.get("baseline_solved") and u.get("abstracted_solved") for u in positive_evals)
    pos_gate = (
        all_trans_smt
        and all_pos_solved
        and all_term_smt
        and pos_regressions == 0
        and pos_applied == 8
        and pos_improved >= 6
        and pos_median_delta < 0
        and pos_abs_total < pos_base_total
    )

    # Negative Gate:
    # 1. 4/4 negative families preserve solve status
    # 2. candidate applications = 0
    # 3. candidate application status is REQUESTED_NOT_APPLIED
    # 4. total node delta = 0
    all_neg_solved = all(u.get("baseline_solved") and u.get("abstracted_solved") for u in negative_evals)
    all_neg_status = all(
        u.get("candidate_application_status") in ("REQUESTED_NOT_APPLIED", "DISABLED")
        for u in negative_evals
    )
    neg_gate = (
        all_neg_solved
        and neg_applied == 0
        and all_neg_status
        and neg_delta_total == 0
        and neg_regressions == 0
    )

    if pos_gate and neg_gate:
        disposition = "REPRESENTATION_STRATUM_INVARIANT"
    else:
        disposition = "REPRESENTATION_STRATUM_SENSITIVE"

    return StratumEvaluation(
        stratum=stratum_name,
        positive_units_count=pos_count,
        positive_improved_count=pos_improved,
        positive_applied_count=pos_applied,
        positive_baseline_total=pos_base_total,
        positive_abstracted_total=pos_abs_total,
        positive_node_delta=pos_delta_total,
        positive_median_delta=pos_median_delta,
        negative_units_count=neg_count,
        negative_applied_count=neg_applied,
        negative_node_delta=neg_delta_total,
        solve_regressions=total_regressions,
        smt_checks_passed=all_trans_smt,
        paired_terminal_checks_passed=all_term_smt,
        positive_gate_passed=pos_gate,
        negative_gate_passed=neg_gate,
        disposition=disposition,
    )


def adjudicate_representation_orbit(
    evaluations_by_stratum: Dict[str, Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]],
) -> GlobalAdjudicationResult:
    """Authoritative eight-way adjudication for the 4 representation strata.
    
    Order of Adjudication:
    1. First adjudicate R0_CANONICAL_CONTROL.
       If R0 fails the structural-benefit gate:
         global disposition = REPRESENTATION_EVALUATION_INCONCLUSIVE_CONTROL_FAILED
    2. If R0 passes, independently adjudicate R1, R2, and R3.
       If R0, R1, R2, R3 all pass invariance:
         global disposition = REPRESENTATION_INVARIANCE_SUPPORTED
       If R0 passes, but at least one stratum fails invariance:
         global disposition = REPRESENTATION_INVARIANCE_NOT_SUPPORTED
    """
    strata_evals: Dict[str, StratumEvaluation] = {}
    for s_name in [
        "R0_CANONICAL_CONTROL",
        "R1_ALPHA_RENAMED",
        "R2_ASSOCIATIVE_REGROUPED",
        "R3_COMMUTATIVE_MIRROR",
    ]:
        pos_list, neg_list = evaluations_by_stratum[s_name]
        strata_evals[s_name] = adjudicate_stratum(s_name, pos_list, neg_list)

    r0_eval = strata_evals["R0_CANONICAL_CONTROL"]
    r1_eval = strata_evals["R1_ALPHA_RENAMED"]
    r2_eval = strata_evals["R2_ASSOCIATIVE_REGROUPED"]
    r3_eval = strata_evals["R3_COMMUTATIVE_MIRROR"]

    if r0_eval.disposition != "REPRESENTATION_STRATUM_INVARIANT":
        global_disp = "REPRESENTATION_EVALUATION_INCONCLUSIVE_CONTROL_FAILED"
    elif all(
        e.disposition == "REPRESENTATION_STRATUM_INVARIANT"
        for e in [r0_eval, r1_eval, r2_eval, r3_eval]
    ):
        global_disp = "REPRESENTATION_INVARIANCE_SUPPORTED"
    else:
        global_disp = "REPRESENTATION_INVARIANCE_NOT_SUPPORTED"

    return GlobalAdjudicationResult(
        r0_evaluation=r0_eval,
        r1_evaluation=r1_eval,
        r2_evaluation=r2_eval,
        r3_evaluation=r3_eval,
        global_disposition=global_disp,
        adjudicator_implementation_digest=get_representation_adjudicator_implementation_digest(),
    )
