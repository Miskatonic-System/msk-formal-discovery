"""Hostile Invariant Test Suite (Section 23, WO-MATH-FORMAL-DISCOVERY-01A-R1).

Enforces all 16+ hostile rejection, authority firewall, and qualification de-fabrication invariants.
"""
from pathlib import Path
import json
import pytest
import jsonschema

from fixtures.fixture_matrix import make_sample_trace
from msk_formal_discovery.abstraction.anti_unification import (
    AdmissibilityStatus,
    StructuralAntiUnifier,
)
from msk_formal_discovery.abstraction.candidate import (
    AbstractionCandidate,
    AbstractionKind,
    CandidateStatus,
)
from msk_formal_discovery.abstraction.replay import (
    HeldOutReplayEngine,
    PairedReplayContract,
    ReplayRunReceipt,
)
from msk_formal_discovery.backend.contract import (
    BackendFamily,
    ExecutionOrigin,
    LogicalAuthorityClass,
    ReasoningBackend,
)
from msk_formal_discovery.backend.lean4_adapter import Lean4Adapter
from msk_formal_discovery.backend.rocq_adapter import RocqAdapter
from msk_formal_discovery.backend.z3_adapter import Z3Adapter
from msk_formal_discovery.core.exceptions import (
    AuthorityViolationError,
    BackendUnavailableError,
    HeldOutDataLeakageError,
    RefactoringError,
    ReplayContractError,
    TraceValidationError,
)
from msk_formal_discovery.core.pipeline import (
    CANONICAL_PIPELINE_SEQUENCE,
    PipelineStage,
    verify_pipeline_sequence,
)
from msk_formal_discovery.core.terms import Const, Term, Var
from msk_formal_discovery.onto.export import OntoExporter
from msk_formal_discovery.refactoring.proposal import RefactoringKind, RefactoringProposal
from msk_formal_discovery.search.mcts import MCTSSearch
from msk_formal_discovery.search.policy import SearchPolicyKind, SearchRun


SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"
RECEIPT_SCHEMA = json.loads((SCHEMAS_DIR / "backend-execution-receipt.v0.1.schema.json").read_text())
TRACE_SCHEMA = json.loads((SCHEMAS_DIR / "execution-trace.v0.1.schema.json").read_text())
SEARCH_SCHEMA = json.loads((SCHEMAS_DIR / "search-run.v0.1.schema.json").read_text())
CANDIDATE_SCHEMA = json.loads((SCHEMAS_DIR / "abstraction-candidate.v0.1.schema.json").read_text())


# 1. Simulated Lean cannot emit DEDUCTIVE_PROOF_AUTHORITY
def test_simulated_lean_cannot_emit_deductive_proof_authority():
    adapter = Lean4Adapter()
    trace = adapter.run_proof(
        problem_id="p-lean-sim",
        theorem_name="test_thm",
        code="theorem test_thm : True := trivial",
        execution_mode="SYNTHETIC",
    )
    assert trace.execution_origin == ExecutionOrigin.SYNTHETIC_FIXTURE.value
    assert trace.logical_authority_class == "NONE"
    assert trace.terminal_verdict == "SYNTHETIC_SUCCESS"

    with pytest.raises(AuthorityViolationError):
        make_sample_trace(
            trace_id="t-bad-lean",
            problem_id="p-bad",
            operations=[("s", "e")],
            logical_authority_class="DEDUCTIVE_PROOF_AUTHORITY",
            execution_origin="SYNTHETIC_FIXTURE",
        )


# 2. Invalid Lean theorem cannot emit PROVEN without checker execution
def test_invalid_lean_theorem_cannot_emit_proven_without_checker_execution():
    adapter = Lean4Adapter()
    if not adapter.lean_binary:
        pytest.skip("Lean binary not installed on host")
    bad_code = "theorem invalid_proof (p q : Prop) (h : p) : q := h\n"
    trace = adapter.run_proof(
        problem_id="p-lean-invalid",
        theorem_name="invalid_proof",
        code=bad_code,
        execution_mode="REAL",
    )
    assert trace.terminal_verdict == "FAILED"
    assert trace.logical_authority_class == "NONE"


# 3. Simulated Rocq cannot emit DEDUCTIVE_PROOF_AUTHORITY
def test_simulated_rocq_cannot_emit_deductive_proof_authority():
    adapter = RocqAdapter()
    trace = adapter.run_proof(
        problem_id="p-rocq-sim",
        theorem_name="test_thm",
        code="Lemma l : True. exact I. Qed.",
        execution_mode="SYNTHETIC",
    )
    assert trace.execution_origin == ExecutionOrigin.SYNTHETIC_FIXTURE.value
    assert trace.logical_authority_class == "NONE"


# 4. Simulated Z3 cannot emit solver SAT/UNSAT authority
def test_simulated_z3_cannot_emit_solver_sat_unsat_authority():
    adapter = Z3Adapter()
    trace = adapter.run_smt(
        problem_id="p-z3-sim",
        smtlib_script="(check-sat)",
        execution_mode="SIMULATED",
    )
    assert trace.execution_origin == ExecutionOrigin.SIMULATED.value
    assert trace.logical_authority_class == "NONE"
    assert trace.terminal_verdict in ("SYNTHETIC_SAT", "SYNTHETIC_UNSAT")


# 5. Unavailable backend fails closed
def test_unavailable_backend_fails_closed():
    adapter = Lean4Adapter(lean_binary="/nonexistent/path/to/lean")
    with pytest.raises(BackendUnavailableError):
        adapter.run_proof(
            problem_id="p-missing",
            theorem_name="t",
            code="theorem t : True := trivial",
            execution_mode="REAL",
        )


# 6. Hard-coded replay benefit prohibited
def test_hardcoded_replay_benefit_prohibited():
    engine = HeldOutReplayEngine()
    au = StructuralAntiUnifier()
    res = au.anti_unify([("t1", Term.parse("f(a)")), ("t2", Term.parse("f(b)"))])
    cand = AbstractionCandidate(
        candidate_id="c-hardcode-test",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={"name": "test_lem", "canonical_representation": "f(V1)"},
        anti_unification_evidence=res,
        discovery_set_trace_ids=["t1", "t2"],
        status=CandidateStatus.PROPOSED,
    )
    # Synthetic replay cannot fabricate a positive qualification
    report = engine.evaluate_synthetic_replay_fixture(cand, [])
    assert report.replay_mode == "SYNTHETIC_REPLAY_FIXTURE"
    assert cand.status != CandidateStatus.QUALIFIED_HELD_OUT


# 7. Synthetic replay cannot qualify candidate
def test_synthetic_replay_cannot_qualify_candidate():
    engine = HeldOutReplayEngine()
    au = StructuralAntiUnifier()
    res = au.anti_unify([("t1", Term.parse("f(a)")), ("t2", Term.parse("f(b)"))])
    cand = AbstractionCandidate(
        candidate_id="c-qual-test",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={"name": "test_lem", "canonical_representation": "f(V1)"},
        anti_unification_evidence=res,
        discovery_set_trace_ids=["t1", "t2"],
        status=CandidateStatus.PROPOSED,
    )
    t_held = make_sample_trace("t-held-1", "p-held", [("s1", "e1")])
    engine.evaluate_synthetic_replay_fixture(cand, [t_held])
    assert cand.status != CandidateStatus.QUALIFIED_HELD_OUT
    assert cand.status == CandidateStatus.CANDIDATE_ONLY


# 8. Baseline/abstracted budget mismatch rejected
def test_baseline_abstracted_budget_mismatch_rejected():
    contract = PairedReplayContract(
        problem_id="p1",
        problem_digest="d" * 64,
        backend_id="lean4",
        search_policy_kind="MCTS",
        search_budget={"max_depth": 5},
        random_seed=42,
        corpus_context={},
        baseline_configuration={"budget": {"max_depth": 5}},
        abstracted_configuration={"budget": {"max_depth": 10}},  # Mismatch!
        candidate_id="c1",
        candidate_enabled_in_abstracted=True,
    )
    with pytest.raises(ReplayContractError) as excinfo:
        contract.validate()
    assert "BUDGET_MISMATCH" in str(excinfo.value)


# 9. Candidate not actually enabled in abstracted run rejected
def test_candidate_not_actually_enabled_rejected():
    contract = PairedReplayContract(
        problem_id="p1",
        problem_digest="d" * 64,
        backend_id="lean4",
        search_policy_kind="MCTS",
        search_budget={"max_depth": 5},
        random_seed=42,
        corpus_context={},
        baseline_configuration={"budget": {"max_depth": 5}},
        abstracted_configuration={"budget": {"max_depth": 5}},
        candidate_id="c1",
        candidate_enabled_in_abstracted=False,  # Not enabled!
    )
    with pytest.raises(ReplayContractError) as excinfo:
        contract.validate()
    assert "CANDIDATE_NOT_ENABLED_IN_ABSTRACTED_ARM" in str(excinfo.value)


# 10. Representation invariance defaults UNKNOWN
def test_representation_invariance_defaults_unknown():
    au = StructuralAntiUnifier()
    res = au.anti_unify([("t1", Term.parse("f(a)")), ("t2", Term.parse("f(b)"))])
    cand = AbstractionCandidate(
        candidate_id="c-def-1",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={"name": "t", "canonical_representation": "f(V1)"},
        anti_unification_evidence=res,
        discovery_set_trace_ids=["t1", "t2"],
    )
    d = cand.to_dict()
    assert d["onto_export"]["representation_invariance"] == "UNKNOWN"


# 11. Cross-search recurrence defaults UNKNOWN
def test_cross_search_recurrence_defaults_unknown():
    au = StructuralAntiUnifier()
    res = au.anti_unify([("t1", Term.parse("f(a)")), ("t2", Term.parse("f(b)"))])
    cand = AbstractionCandidate(
        candidate_id="c-def-2",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={"name": "t", "canonical_representation": "f(V1)"},
        anti_unification_evidence=res,
        discovery_set_trace_ids=["t1", "t2"],
    )
    d = cand.to_dict()
    assert d["onto_export"]["cross_search_policy_recurrence"] == "UNKNOWN"


# 12. ONTO exporter cannot invent positive properties
def test_onto_exporter_cannot_invent_positive_properties():
    au = StructuralAntiUnifier()
    res = au.anti_unify([("t1", Term.parse("f(a)")), ("t2", Term.parse("f(b)"))])
    cand = AbstractionCandidate(
        candidate_id="c-onto-1",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={"name": "t", "canonical_representation": "f(V1)"},
        anti_unification_evidence=res,
        discovery_set_trace_ids=["t1", "t2"],
    )
    pkg = OntoExporter.export(cand)
    assert pkg.representation_invariance == "UNKNOWN"
    assert pkg.cross_search_policy_recurrence == "UNKNOWN"
    assert pkg.functional_search_benefit == "UNKNOWN"


# 13. Bare-variable LGG rejected as lemma candidate
def test_bare_variable_lgg_rejected_as_lemma_candidate():
    au = StructuralAntiUnifier()
    t1 = Term.parse("a")
    t2 = Term.parse("b")
    res = au.anti_unify([("t1", t1), ("t2", t2)])
    assert res.is_trivial_variable is True
    status = au.assess_admissibility([("t1", t1), ("t2", t2)], res)
    assert status == AdmissibilityStatus.STRUCTURAL_GENERALIZATION_TRIVIAL

    cand = AbstractionCandidate(
        candidate_id="c-bare",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={"name": "bare", "canonical_representation": "V1"},
        anti_unification_evidence=res,
        discovery_set_trace_ids=["t1", "t2"],
        admissibility_status=status,
        status=CandidateStatus.QUALIFIED_HELD_OUT,  # Attempt illegitimate promotion
    )
    # Post-init should reject bare-variable lemma promotion
    assert cand.status == CandidateStatus.REJECTED


# 14. int_plus / bool_xor candidate rejection exercised (Section 21)
def test_int_plus_bool_xor_candidate_rejection():
    au = StructuralAntiUnifier()
    t1 = Term.parse("int_plus(a, b)")
    t2 = Term.parse("bool_xor(a, b)")
    res = au.anti_unify([("t1", t1), ("t2", t2)])
    assert str(res.lgg_term) == "V1"

    status = au.assess_admissibility([("t1", t1), ("t2", t2)], res)
    assert status == AdmissibilityStatus.TRIVIAL_OR_SEMANTICALLY_INCOMPATIBLE_GENERALIZATION

    cand = AbstractionCandidate(
        candidate_id="c-sem-incompat",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={"name": "fake_bridge", "canonical_representation": "V1"},
        anti_unification_evidence=res,
        discovery_set_trace_ids=["t1", "t2"],
        admissibility_status=status,
        status=CandidateStatus.QUALIFIED_HELD_OUT,
    )
    assert cand.status == CandidateStatus.REJECTED


# 15. Branch-local pattern cannot globalize without guard (Section 20)
def test_branch_local_pattern_cannot_globalize_without_guard():
    au = StructuralAntiUnifier()
    t1 = Term.parse("scale(x)")
    t2 = Term.parse("scale(x)")
    res = au.anti_unify([("t1", t1), ("t2", t2)])

    # Observed under conflicting branch conditions
    guards = ["assume(neg)", "assume(pos)"]
    status = au.assess_admissibility([("t1", t1), ("t2", t2)], res, branch_guards=guards)
    assert status == AdmissibilityStatus.REQUIRES_BRANCH_GUARD

    cand = AbstractionCandidate(
        candidate_id="c-branch-local",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={"name": "branch_lemma", "canonical_representation": "scale(x)"},
        anti_unification_evidence=res,
        discovery_set_trace_ids=["t1", "t2"],
        admissibility_status=status,
        status=CandidateStatus.QUALIFIED_HELD_OUT,
    )
    assert cand.status == CandidateStatus.REJECTED


# 16. Fixture trace cannot claim proof authority
def test_fixture_trace_cannot_claim_proof_authority():
    with pytest.raises(AuthorityViolationError):
        make_sample_trace(
            trace_id="t-fixture-rogue",
            problem_id="p-rogue",
            operations=[("step", "intro h")],
            execution_origin="SYNTHETIC_FIXTURE",
            logical_authority_class="DEDUCTIVE_PROOF_AUTHORITY",
        )


# 17. Pipeline sequence violation detected
def test_pipeline_sequence_violation_detected():
    assert verify_pipeline_sequence([PipelineStage.SOURCE_CORPUS, PipelineStage.REASONING_BACKEND]) is True
    assert verify_pipeline_sequence([PipelineStage.REASONING_BACKEND, PipelineStage.SOURCE_CORPUS]) is False


# 18. Untyped backend internals leakage rejected
def test_untyped_backend_leakage_rejected():
    trace = make_sample_trace("t-leak", "p-leak", [("s", "e")])
    trace.events[1].payload["_raw_backend_state"] = 0x1234
    with pytest.raises(TraceValidationError):
        trace.validate()
