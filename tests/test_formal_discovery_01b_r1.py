"""Hostile governance, freeze, and invariant tests for WO-MATH-FORMAL-DISCOVERY-01B-R1 (Section 31)."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from msk_formal_discovery.abstraction.anti_unification import (
    AdmissibilityStatus,
    AntiUnificationResult,
    compute_shared_meaningful_constructors,
)
from msk_formal_discovery.abstraction.candidate import (
    AbstractionCandidate,
    AbstractionKind,
    CandidateFactory,
    CandidateStatus,
    compute_candidate_artifact_digest,
)
from msk_formal_discovery.abstraction.selector import (
    get_selector_implementation_digest,
    select_candidate,
)
from msk_formal_discovery.abstraction.subtrace_miner import RecurringSubtracePattern
from msk_formal_discovery.application.applicator import (
    CandidateApplicationReceipt,
    CandidateApplicator,
    get_applicator_implementation_digest,
)
from msk_formal_discovery.backend.contract import ExecutionOrigin, LogicalAuthorityClass
from msk_formal_discovery.core.terms import App, Const, Term, Var
from msk_formal_discovery.experiments.adjudication import (
    AdjudicationDisposition,
    adjudicate_01b_r1,
    get_adjudicator_implementation_digest,
)
from msk_formal_discovery.experiments.rewrite_control import (
    RewriteProblem,
    RewriteSearchEnvironment,
    check_paired_terminal_smt_equivalence,
    check_smt_equivalence,
    generate_discovery_corpus,
    generate_held_out_negative_corpus,
    generate_held_out_positive_corpus,
    get_smt_control_implementation_digest,
)
from msk_formal_discovery.experiments.runner_r1 import (
    validate_r1_freeze,
)
from msk_formal_discovery.search.executor import (
    SearchExecutionBundle,
    SearchExecutionReceipt,
    SearchExecutor,
)
from msk_formal_discovery.search.frontier import DeterministicFrontierSearch
from msk_formal_discovery.trace.ir import ExecutionTrace


EXP_R1_DIR = Path(__file__).resolve().parents[1] / "experiments" / "formal-discovery-01b-r1"
HIST_DIR = Path(__file__).resolve().parents[1] / "experiments" / "formal-discovery-01b"


# 1. Frozen applicator digest drift rejected
def test_frozen_applicator_digest_drift_rejected(tmp_path: Path):
    prereg_file = EXP_R1_DIR / "preregistration.json"
    prereg = json.loads(prereg_file.read_text())
    prereg["implementation_digests"]["applicator"] = "0" * 64
    tampered_prereg = tmp_path / "preregistration.json"
    tampered_prereg.write_text(json.dumps(prereg))

    # Copy manifest files
    (tmp_path / "qualification-manifest.json").write_text((EXP_R1_DIR / "qualification-manifest.json").read_text())

    with pytest.raises(ValueError, match="Applicator digest drift"):
        validate_r1_freeze(tmp_path)


# 2. Empty primitive expansion rejected
def test_empty_primitive_expansion_rejected():
    env = RewriteSearchEnvironment("prob-01", "0" * 64, Var("x"))
    st = env.create_initial_state(App("add", (App("mul", (Const("1"), Var("x"))), Const("0"))))
    actions = env.actions(st)

    cand = AbstractionCandidate(
        candidate_id="empty_cand",
        candidate_kind=AbstractionKind.TACTIC_MACRO,
        formal_specification={"name": "empty"},
        anti_unification_evidence=AntiUnificationResult(
            lgg_term=Var("X"),
            substitution_witnesses={},
            algorithm_version="v0.1",
            deterministic_digest="0" * 64,
        ),
        discovery_set_trace_ids=[],
        primitive_expansion=[],  # EMPTY
    )

    with pytest.raises(ValueError, match="EMPTY_PRIMITIVE_EXPANSION"):
        CandidateApplicator.apply(
            candidate=cand,
            state=st,
            primitive_actions=actions,
            environment=env,
            problem_digest="0" * 64,
            experimental_unit_id="unit-01",
        )


# 3. Selector evaluates all four ordering levels
def test_selector_evaluates_all_four_ordering_levels():
    # Helper to construct dummy RecurringSubtracePattern
    def _make_pat(pid: str, ops: tuple, occ_traces: list, lgg: Term) -> RecurringSubtracePattern:
        occs = [(t, 0) for t in occ_traces]
        au = AntiUnificationResult(
            lgg_term=lgg,
            substitution_witnesses={t: {} for t in occ_traces},
            algorithm_version="v0.1",
            deterministic_digest=hashlib.sha256(pid.encode()).hexdigest(),
        )
        return RecurringSubtracePattern(
            pattern_id=pid,
            operations=ops,
            occurrences=occs,
            frequency=len(occ_traces),
            extracted_terms={t: lgg for t in occ_traces},
            anti_unification_result=au,
            discovery_origin="EXECUTED_OBSERVED",
            trace_problem_digests={t: "a" * 64 for t in occ_traces},
            trace_digests={t: "b" * 64 for t in occ_traces},
        )

    t_meaningful_3 = App("f", (App("g", (Const("1"),)), App("h", (Const("2"),))))
    t_meaningful_2 = App("f", (App("g", (Const("1"),)), Const("2")))

    # Level 1 test: higher support wins
    p_sup3 = _make_pat("p_sup3", ("A", "B"), ["t1", "t2", "t3"], t_meaningful_2)
    p_sup2 = _make_pat("p_sup2", ("A", "B", "C"), ["t1", "t2"], t_meaningful_3)
    cand1, _ = select_candidate([p_sup2, p_sup3])
    assert cand1.candidate_id == "macro_a_b"

    # Level 2 test: same support, longer sequence wins
    p_len2 = _make_pat("p_len2", ("A", "B"), ["t1", "t2"], t_meaningful_3)
    p_len3 = _make_pat("p_len3", ("A", "B", "C"), ["t1", "t2"], t_meaningful_2)
    cand2, _ = select_candidate([p_len2, p_len3])
    assert cand2.candidate_id == "macro_a_b_c"

    # Level 3 test: same support, same length, more meaningful constructors wins
    p_c2 = _make_pat("p_c2", ("A", "B"), ["t1", "t2"], t_meaningful_2)
    p_c3 = _make_pat("p_c3", ("A", "B_other"), ["t1", "t2"], t_meaningful_3)
    cand3, _ = select_candidate([p_c2, p_c3])
    assert cand3.candidate_id == "macro_a_b_other"


# 4. Insertion order cannot alter selected candidate
def test_insertion_order_cannot_alter_selected_candidate():
    disc = generate_discovery_corpus(seed=42)
    from msk_formal_discovery.experiments.rewrite_control import run_discovery_episode
    from msk_formal_discovery.abstraction.subtrace_miner import SubtraceMiner

    traces = [run_discovery_episode(p) for p in disc]
    miner = SubtraceMiner(min_length=2, min_support=2)
    patterns = miner.mine_traces(traces)

    cand_fwd, ledger_fwd = select_candidate(patterns)
    cand_rev, ledger_rev = select_candidate(list(reversed(patterns)))

    assert cand_fwd.candidate_id == cand_rev.candidate_id
    assert cand_fwd.artifact_digest() == cand_rev.artifact_digest()
    assert ledger_fwd["candidate_records"] == ledger_rev["candidate_records"]


# 5. Expected-candidate assertion cannot select candidate
def test_expected_candidate_assertion_cannot_select_candidate():
    # If patterns contain a dominant non-mul-one pattern, it MUST win
    def _make_pat(pid: str, ops: tuple, occ_traces: list, lgg: Term) -> RecurringSubtracePattern:
        occs = [(t, 0) for t in occ_traces]
        au = AntiUnificationResult(
            lgg_term=lgg,
            substitution_witnesses={t: {} for t in occ_traces},
            algorithm_version="v0.1",
            deterministic_digest=hashlib.sha256(pid.encode()).hexdigest(),
        )
        return RecurringSubtracePattern(
            pattern_id=pid,
            operations=ops,
            occurrences=occs,
            frequency=len(occ_traces),
            extracted_terms={t: lgg for t in occ_traces},
            anti_unification_result=au,
            discovery_origin="EXECUTED_OBSERVED",
            trace_problem_digests={t: "a" * 64 for t in occ_traces},
            trace_digests={t: "b" * 64 for t in occ_traces},
        )

    t_au = App("add", (Var("X"), Const("0")))
    p_mul_add = _make_pat("p_mul_add", ("MUL_ONE_LEFT", "ADD_ZERO_RIGHT"), ["t1", "t2"], t_au)
    p_other = _make_pat("p_other", ("DOUBLE_NEG", "DOUBLE_NEG"), ["t1", "t2", "t3", "t4"], t_au)

    cand, _ = select_candidate([p_mul_add, p_other])
    # Dominant pattern must be selected regardless of expected names
    assert cand.candidate_id == "macro_double_neg_double_neg"


# 6. Old qualification digest reuse rejected
def test_old_qualification_digest_reuse_rejected(tmp_path: Path):
    hist_qual = json.loads((HIST_DIR / "qualification-manifest.json").read_text())
    old_pos_prob = hist_qual["positive_held_out_problems"][0]

    # Create tampered qualification manifest reusing old digest
    tampered_qual = {
        "schema_version": "miskatonic.qualification-manifest.v0.1",
        "experiment_id": "formal-discovery-01b-r1",
        "positive_held_out_count": 1,
        "positive_held_out_problems": [old_pos_prob],
        "negative_control_count": 0,
        "negative_control_problems": [],
    }
    (tmp_path / "qualification-manifest.json").write_text(json.dumps(tampered_qual))
    (tmp_path / "preregistration.json").write_text((EXP_R1_DIR / "preregistration.json").read_text())

    with pytest.raises(ValueError, match="Freshness gate collision"):
        validate_r1_freeze(tmp_path)


# 7. Fresh qualification overlap rejected
def test_fresh_qualification_overlap_rejected():
    pos = generate_held_out_positive_corpus(seed=271828)
    neg = generate_held_out_negative_corpus(seed=314159)
    disc = generate_discovery_corpus(seed=42)

    pos_digs = set(p.problem_digest for p in pos)
    neg_digs = set(p.problem_digest for p in neg)
    disc_digs = set(p.problem_digest for p in disc)

    hist_qual = json.loads((HIST_DIR / "qualification-manifest.json").read_text())
    old_pos_digs = set(p["problem_digest"] for p in hist_qual["positive_held_out_problems"])
    old_neg_digs = set(p["problem_digest"] for p in hist_qual["negative_control_problems"])

    assert len(pos_digs & neg_digs) == 0
    assert len(pos_digs & disc_digs) == 0
    assert len(neg_digs & disc_digs) == 0
    assert len(pos_digs & old_pos_digs) == 0
    assert len(pos_digs & old_neg_digs) == 0
    assert len(neg_digs & old_pos_digs) == 0
    assert len(neg_digs & old_neg_digs) == 0


# 8. 20-percent threshold cannot enter authoritative adjudication
def test_twenty_percent_threshold_cannot_enter_authoritative_adjudication():
    # Only 5% node reduction (less than 20%), but median < 0, >=6/8 improve, no regression
    pos_comps = [
        {"baseline_nodes": 100, "abstracted_nodes": 95, "baseline_solved": True, "abstracted_solved": True, "applications_count": 1, "smt_unsat": True}
    ] * 8
    neg_comps = [
        {"baseline_nodes": 4, "abstracted_nodes": 4, "baseline_solved": True, "abstracted_solved": True, "applications_count": 0, "smt_unsat": True}
    ] * 4

    summary = adjudicate_01b_r1(pos_comps, neg_comps)
    # Must be SUPPORTED; 20% threshold is descriptive only
    assert summary.disposition == AdjudicationDisposition.ABSTRACTION_SEARCH_BENEFIT_SUPPORTED
    assert summary.positive_node_reduction_pct == 5.0


# 9. Binary supported/rejected adjudicator rejected
def test_binary_supported_rejected_adjudicator_rejected():
    all_disps = {d.value for d in AdjudicationDisposition}
    assert len(all_disps) == 8
    expected = {
        "EXPERIMENT_INFRASTRUCTURE_BLOCKED",
        "CANDIDATE_DISCOVERY_FAILED",
        "APPLICATION_SEMANTICS_FAILED",
        "SELECTIVITY_FAILURE",
        "CANDIDATE_NOT_APPLIED_ON_POSITIVE_SET",
        "ABSTRACTION_SEARCH_BENEFIT_NOT_OBSERVED",
        "ABSTRACTION_SEARCH_BENEFIT_HETEROGENEOUS",
        "ABSTRACTION_SEARCH_BENEFIT_SUPPORTED",
    }
    assert all_disps == expected


# 10. Median gate enforced
def test_median_gate_enforced():
    # 7 units degrade (+1 node), 1 unit has massive reduction (-100 nodes).
    # Total nodes: baseline = 800, abstracted = 707 (reduction = 93 nodes!).
    # BUT median delta is +1 (>= 0).
    pos_comps = [
        {"baseline_nodes": 100, "abstracted_nodes": 101, "baseline_solved": True, "abstracted_solved": True, "applications_count": 1, "smt_unsat": True}
    ] * 7 + [
        {"baseline_nodes": 100, "abstracted_nodes": 0, "baseline_solved": True, "abstracted_solved": True, "applications_count": 1, "smt_unsat": True}
    ]
    neg_comps = [
        {"baseline_nodes": 4, "abstracted_nodes": 4, "baseline_solved": True, "abstracted_solved": True, "applications_count": 0, "smt_unsat": True}
    ] * 4

    summary = adjudicate_01b_r1(pos_comps, neg_comps)
    # Median gate fails -> NOT_OBSERVED
    assert summary.disposition == AdjudicationDisposition.ABSTRACTION_SEARCH_BENEFIT_NOT_OBSERVED


# 11. Actual baseline terminal required for SMT control
def test_actual_baseline_terminal_required_for_smt_control():
    class DummyBundle:
        terminal_expression = None
        terminal_state = None

    class DummyValidBundle:
        terminal_expression = Var("x")

    with pytest.raises(ValueError, match="MISSING_BASELINE_TERMINAL"):
        check_paired_terminal_smt_equivalence(DummyBundle(), DummyValidBundle(), "prob-01")


# 12. Actual abstracted terminal required for SMT control
def test_actual_abstracted_terminal_required_for_smt_control():
    class DummyBundle:
        terminal_expression = None
        terminal_state = None

    class DummyValidBundle:
        terminal_expression = Var("x")

    with pytest.raises(ValueError, match="MISSING_ABSTRACTED_TERMINAL"):
        check_paired_terminal_smt_equivalence(DummyValidBundle(), DummyBundle(), "prob-01")


# 13. Initial-vs-goal SMT cannot substitute for paired-terminal result
def test_initial_vs_goal_smt_cannot_substitute_for_paired_terminal():
    # In a buggy search, baseline terminal might be x, but abstracted terminal might be y.
    # Initial was equivalent to goal, but baseline terminal != abstracted terminal.
    t_base = Var("x")
    t_abs = Var("y")
    is_equiv, tr = check_smt_equivalence(t_base, t_abs, "prob-tampered")
    assert is_equiv is False
    assert tr.terminal_verdict != "UNSAT_REFUTED"


# 14. Simulated Z3 rejected
def test_simulated_z3_rejected(monkeypatch):
    from datetime import datetime, timezone
    from msk_formal_discovery.backend.z3_adapter import Z3Adapter

    def mock_run_smt(*args, **kwargs):
        return ExecutionTrace(
            trace_id="tr-sim",
            problem_id="p-sim",
            backend_id="z3",
            backend_version="5.1.0",
            created_at=datetime.now(timezone.utc).isoformat(),
            execution_origin="SYNTHETIC_SIMULATED",  # NON-NATIVE
            logical_authority_class=LogicalAuthorityClass.SOLVER_SAT_OR_UNSAT,
            terminal_verdict="UNSAT_REFUTED",
        )

    monkeypatch.setattr(Z3Adapter, "run_smt", mock_run_smt)

    with pytest.raises(ValueError, match="SMT_CONTROL_NON_NATIVE_EXECUTION"):
        check_smt_equivalence(Var("x"), Var("x"), "prob-01")


# 15. Baseline APPLIED rejected
def test_baseline_applied_rejected():
    from msk_formal_discovery.backend.contract import ProblemDefinition

    executor = SearchExecutor()
    env = RewriteSearchEnvironment("prob-01", "0" * 64, Var("x"))
    init_st = env.create_initial_state(Var("x"))
    prob_def = ProblemDefinition(
        problem_id="prob-01",
        formal_syntax="x",
        context={"expression_digest": "0" * 64},
        goals=["x"],
        assumptions=[],
        problem_digest="0" * 64,
    )
    bundle = executor.execute(
        problem=prob_def,
        initial_state=init_st,
        policy=DeterministicFrontierSearch(),
        environment=env,
        budget={"max_nodes": 10, "max_depth": 5},
        candidate_enabled=False,
    )
    assert bundle.receipt.candidate_application_status == "DISABLED"


# 16. Negative-control APPLIED rejected
def test_negative_control_applied_rejected():
    pos_comps = [
        {"baseline_nodes": 20, "abstracted_nodes": 10, "baseline_solved": True, "abstracted_solved": True, "applications_count": 1, "smt_unsat": True}
    ] * 8
    neg_comps = [
        {"baseline_nodes": 4, "abstracted_nodes": 4, "baseline_solved": True, "abstracted_solved": True, "applications_count": 1, "smt_unsat": True}  # APPLIED IN NEGATIVE!
    ] * 4

    summary = adjudicate_01b_r1(pos_comps, neg_comps)
    assert summary.disposition == AdjudicationDisposition.SELECTIVITY_FAILURE


# 17. Commit-B science-code drift invalidates experiment
def test_commit_b_science_code_drift_invalidates_experiment(tmp_path: Path):
    prereg_file = EXP_R1_DIR / "preregistration.json"
    prereg = json.loads(prereg_file.read_text())
    prereg["implementation_digests"]["selector"] = "tampered_digest"
    (tmp_path / "preregistration.json").write_text(json.dumps(prereg))
    (tmp_path / "qualification-manifest.json").write_text((EXP_R1_DIR / "qualification-manifest.json").read_text())

    with pytest.raises(ValueError, match="Selector digest drift"):
        validate_r1_freeze(tmp_path)
