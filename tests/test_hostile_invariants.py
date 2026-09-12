"""Hostile Invariant Test Suite (Section 23, WO-MATH-FORMAL-DISCOVERY-01A-R1).

Enforces all 16+ hostile rejection, authority firewall, and qualification de-fabrication invariants.
"""
import dataclasses
import hashlib
from pathlib import Path
import json
import pytest
import jsonschema

from fixtures.fixture_matrix import make_sample_trace
from msk_formal_discovery.abstraction.anti_unification import (
    AdmissibilityReceipt,
    AdmissibilityStatus,
    StructuralAntiUnifier,
    compute_shared_meaningful_constructors,
    create_admissibility_receipt,
)
from msk_formal_discovery.abstraction.candidate import (
    AbstractionCandidate,
    AbstractionKind,
    CandidateFactory,
    CandidateStatus,
)
from msk_formal_discovery.abstraction.replay import (
    HeldOutReplayEngine,
    PairedReplayContract,
    ReplayRunReceipt,
    _validate_receipt_against_contract,
)
from msk_formal_discovery.abstraction.subtrace_miner import (
    RecurringSubtracePattern,
    SubtraceMiner,
)
from msk_formal_discovery.backend.contract import (
    BackendExecutionReceipt,
    BackendFamily,
    ExecutionOrigin,
    LogicalAuthorityClass,
    ProblemDefinition,
    ReasoningBackend,
    derive_authority,
)
from msk_formal_discovery.backend.lean4_adapter import Lean4Adapter
from msk_formal_discovery.backend.rocq_adapter import RocqAdapter
from msk_formal_discovery.backend.z3_adapter import Z3Adapter
from msk_formal_discovery.core.exceptions import (
    AuthorityViolationError,
    BackendUnavailableError,
    HeldOutDataLeakageError,
    ReceiptValidationError,
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
from msk_formal_discovery.onto.export import OntoEvidenceRef, OntoExporter
from msk_formal_discovery.refactoring.proposal import RefactoringKind, RefactoringProposal
from msk_formal_discovery.search.mcts import MCTSSearch
from msk_formal_discovery.search.executor import SearchExecutionReceipt
from msk_formal_discovery.search.policy import SearchPolicyKind, SearchRun
from msk_formal_discovery.trace.events import EventOrigin, ExecutionTraceEvent, TraceEventType
from msk_formal_discovery.trace.ir import ExecutionTrace


SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"
RECEIPT_SCHEMA = json.loads((SCHEMAS_DIR / "backend-execution-receipt.v0.1.schema.json").read_text())
REPLAY_RECEIPT_SCHEMA = json.loads((SCHEMAS_DIR / "replay-run-receipt.v0.1.schema.json").read_text())
TRACE_SCHEMA = json.loads((SCHEMAS_DIR / "execution-trace.v0.1.schema.json").read_text())
SEARCH_SCHEMA = json.loads((SCHEMAS_DIR / "search-run.v0.1.schema.json").read_text())
CANDIDATE_SCHEMA = json.loads((SCHEMAS_DIR / "abstraction-candidate.v0.1.schema.json").read_text())


def make_valid_search_execution_receipt(
    run_id: str,
    problem_id: str,
    problem_digest: str,
    candidate_id: str | None = None,
    candidate_enabled: bool = False,
    nodes_expanded: int = 10,
    nodes_evaluated: int = 20,
    branch_count: int = 2,
    wall_time_ms: float = 10.0,
) -> SearchExecutionReceipt:
    return SearchExecutionReceipt(
        executor_id="msk-search-executor-v0.1",
        executor_version="0.1.0",
        executor_implementation_digest="0" * 64,
        run_id=run_id,
        problem_id=problem_id,
        problem_digest=problem_digest,
        backend_id="lean4",
        backend_configuration_digest="0" * 64,
        search_policy="MCTS",
        search_policy_configuration_digest="0" * 64,
        search_budget_digest="0" * 64,
        random_seed=42,
        corpus_context_digest="0" * 64,
        source_graph_context_digest="0" * 64,
        environment_identity_digest="0" * 64,
        candidate_id=candidate_id,
        candidate_enabled=candidate_enabled,
        started_at="2026-09-12T12:00:00Z",
        completed_at="2026-09-12T12:01:00Z",
        nodes_expanded=nodes_expanded,
        nodes_evaluated=nodes_evaluated,
        branch_count=branch_count,
        terminal_status="SOLVED",
        wall_time_ms=wall_time_ms,
        resulting_trace_refs=["t1"],
        resulting_trace_digests=["0" * 64],
    )


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
        discovery_problem_digests=["0" * 64],
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
        discovery_problem_digests=["0" * 64],
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


def _make_valid_backend_receipt(
    backend_id="lean4",
    backend_family=BackendFamily.PROOF_ASSISTANT,
    execution_origin=ExecutionOrigin.EXECUTED_NATIVE,
    terminal_classification="PROVEN",
    exit_code=0,
    logical_authority_class=LogicalAuthorityClass.DEDUCTIVE_PROOF_AUTHORITY,
) -> BackendExecutionReceipt:
    return BackendExecutionReceipt(
        receipt_id="rcpt-test-valid-01",
        backend_id=backend_id,
        backend_family=backend_family,
        execution_origin=execution_origin,
        executable_path=f"/usr/bin/{backend_id}",
        executable_version="1.0.0",
        executable_sha256="0" * 64,
        command=[backend_id, "test_file"],
        input_digest="0" * 64,
        started_at="2026-09-12T10:00:00Z",
        completed_at="2026-09-12T10:00:01Z",
        exit_code=exit_code,
        timeout_status=False,
        stdout_digest="0" * 64,
        stderr_digest="0" * 64,
        terminal_classification=terminal_classification,
        logical_authority_class=logical_authority_class,
    )


# 19. Native solver authority without receipt rejected
def test_native_solver_authority_without_receipt_rejected():
    with pytest.raises(AuthorityViolationError) as excinfo:
        ExecutionTrace(
            trace_id="t-solver-no-rcpt",
            problem_id="p-solver-1",
            backend_id="z3",
            backend_version="5.1.0",
            execution_origin=ExecutionOrigin.EXECUTED_NATIVE.value,
            logical_authority_class=LogicalAuthorityClass.SOLVER_SAT_OR_UNSAT.value,
            created_at="2026-09-12T12:00:00Z",
            terminal_verdict="SAT",
            execution_receipt=None,
        )
    assert "RECEIPT_REQUIRED_FOR_NON_NONE_AUTHORITY" in str(excinfo.value)

    # Schema-level hostile validation
    d = {
        "trace_id": "t-solver-no-rcpt",
        "problem_id": "p-solver-1",
        "backend_id": "z3",
        "backend_version": "5.1.0",
        "execution_origin": "EXECUTED_NATIVE",
        "logical_authority_class": "SOLVER_SAT_OR_UNSAT",
        "created_at": "2026-09-12T12:00:00Z",
        "events": [],
        "terminal_verdict": "SAT",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(d, TRACE_SCHEMA)

    auth = derive_authority(
        backend_family=BackendFamily.SMT_SOLVER,
        execution_origin=ExecutionOrigin.EXECUTED_NATIVE,
        receipt=None,
        terminal_classification="SAT",
    )
    assert auth == LogicalAuthorityClass.NONE


# 20. Native model-checker authority without receipt rejected
def test_native_model_checker_authority_without_receipt_rejected():
    with pytest.raises(AuthorityViolationError) as excinfo:
        ExecutionTrace(
            trace_id="t-mc-no-rcpt",
            problem_id="p-mc-1",
            backend_id="spin",
            backend_version="6.5.2",
            execution_origin=ExecutionOrigin.EXECUTED_NATIVE.value,
            logical_authority_class=LogicalAuthorityClass.BOUNDED_EXHAUSTIVE_VERDICT.value,
            created_at="2026-09-12T12:00:00Z",
            terminal_verdict="COUNTEREXAMPLE_FOUND",
            execution_receipt=None,
        )
    assert "RECEIPT_REQUIRED_FOR_NON_NONE_AUTHORITY" in str(excinfo.value)

    d = {
        "trace_id": "t-mc-no-rcpt",
        "problem_id": "p-mc-1",
        "backend_id": "spin",
        "backend_version": "6.5.2",
        "execution_origin": "EXECUTED_NATIVE",
        "logical_authority_class": "BOUNDED_EXHAUSTIVE_VERDICT",
        "created_at": "2026-09-12T12:00:00Z",
        "events": [],
        "terminal_verdict": "COUNTEREXAMPLE_FOUND",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(d, TRACE_SCHEMA)

    auth = derive_authority(
        backend_family=BackendFamily.MODEL_CHECKER,
        execution_origin=ExecutionOrigin.EXECUTED_NATIVE,
        receipt=None,
        terminal_classification="COUNTEREXAMPLE_FOUND",
    )
    assert auth == LogicalAuthorityClass.NONE


# 21. Receipt/trace backend mismatch rejected
def test_receipt_trace_backend_mismatch_rejected():
    rcpt = _make_valid_backend_receipt(backend_id="z3", backend_family=BackendFamily.SMT_SOLVER)
    with pytest.raises(AuthorityViolationError) as excinfo:
        ExecutionTrace(
            trace_id="t-mismatch-backend",
            problem_id="p-1",
            backend_id="lean4",  # Mismatch with rcpt.backend_id="z3"!
            backend_version="1.0.0",
            execution_origin=ExecutionOrigin.EXECUTED_NATIVE.value,
            logical_authority_class=LogicalAuthorityClass.DEDUCTIVE_PROOF_AUTHORITY.value,
            created_at="2026-09-12T12:00:00Z",
            terminal_verdict="PROVEN",
            execution_receipt=rcpt,
        )
    assert "backend_id mismatch" in str(excinfo.value)


# 22. Receipt/trace origin mismatch rejected
def test_receipt_trace_origin_mismatch_rejected():
    rcpt = _make_valid_backend_receipt(execution_origin=ExecutionOrigin.SIMULATED)
    with pytest.raises(AuthorityViolationError) as excinfo:
        ExecutionTrace(
            trace_id="t-mismatch-origin",
            problem_id="p-1",
            backend_id="lean4",
            backend_version="1.0.0",
            execution_origin=ExecutionOrigin.EXECUTED_NATIVE.value,  # Mismatch!
            logical_authority_class=LogicalAuthorityClass.DEDUCTIVE_PROOF_AUTHORITY.value,
            created_at="2026-09-12T12:00:00Z",
            terminal_verdict="PROVEN",
            execution_receipt=rcpt,
        )
    assert "execution_origin mismatch" in str(excinfo.value)


# 23. Receipt/trace terminal mismatch rejected
def test_receipt_trace_terminal_mismatch_rejected():
    rcpt = _make_valid_backend_receipt(terminal_classification="FAILED")
    with pytest.raises(AuthorityViolationError) as excinfo:
        ExecutionTrace(
            trace_id="t-mismatch-term",
            problem_id="p-1",
            backend_id="lean4",
            backend_version="1.0.0",
            execution_origin=ExecutionOrigin.EXECUTED_NATIVE.value,
            logical_authority_class=LogicalAuthorityClass.DEDUCTIVE_PROOF_AUTHORITY.value,
            created_at="2026-09-12T12:00:00Z",
            terminal_verdict="PROVEN",  # Mismatch with rcpt.terminal_classification="FAILED"!
            execution_receipt=rcpt,
        )
    assert "terminal mismatch" in str(excinfo.value)


# 24. Z3 nonzero exit plus "sat" cannot confer solver authority
def test_z3_nonzero_exit_plus_sat_cannot_confer_solver_authority():
    rcpt = BackendExecutionReceipt(
        receipt_id="rcpt-z3-crash",
        backend_id="z3",
        backend_family=BackendFamily.SMT_SOLVER,
        execution_origin=ExecutionOrigin.EXECUTED_NATIVE,
        executable_path="/usr/bin/z3",
        executable_version="5.1.0",
        executable_sha256="0" * 64,
        command=["z3", "-smt2"],
        input_digest="0" * 64,
        started_at="2026-09-12T10:00:00Z",
        completed_at="2026-09-12T10:00:01Z",
        exit_code=1,  # Nonzero exit code
        timeout_status=False,
        stdout_digest=hashlib.sha256(b"sat\n(error \"out of memory\")\n").hexdigest(),
        stderr_digest=hashlib.sha256(b"fatal error").hexdigest(),
        terminal_classification="FAILED",
        logical_authority_class=LogicalAuthorityClass.NONE,
    )
    auth = derive_authority(
        backend_family=BackendFamily.SMT_SOLVER,
        execution_origin=ExecutionOrigin.EXECUTED_NATIVE,
        receipt=rcpt,
        terminal_classification="FAILED",
    )
    assert auth == LogicalAuthorityClass.NONE

    # Even if someone forged terminal_classification="SAT" with exit_code=1
    forged_rcpt = BackendExecutionReceipt(
        receipt_id="rcpt-z3-forged",
        backend_id="z3",
        backend_family=BackendFamily.SMT_SOLVER,
        execution_origin=ExecutionOrigin.EXECUTED_NATIVE,
        executable_path="/usr/bin/z3",
        executable_version="5.1.0",
        executable_sha256="0" * 64,
        command=["z3", "-smt2"],
        input_digest="0" * 64,
        started_at="2026-09-12T10:00:00Z",
        completed_at="2026-09-12T10:00:01Z",
        exit_code=1,
        timeout_status=False,
        stdout_digest=hashlib.sha256(b"sat\n").hexdigest(),
        stderr_digest=hashlib.sha256(b"").hexdigest(),
        terminal_classification="SAT",
        logical_authority_class=LogicalAuthorityClass.SOLVER_SAT_OR_UNSAT,
    )
    auth_forged = derive_authority(
        backend_family=BackendFamily.SMT_SOLVER,
        execution_origin=ExecutionOrigin.EXECUTED_NATIVE,
        receipt=forged_rcpt,
        terminal_classification="SAT",
    )
    assert auth_forged == LogicalAuthorityClass.NONE


# 25. Plain UNSAT result does not create UNSAT_CORE event
def test_plain_unsat_result_does_not_create_unsat_core_event():
    adapter = Z3Adapter()
    script = "(set-logic QF_UF)\n(declare-const p Bool)\n(assert p)\n(assert (not p))\n(check-sat)\n"
    trace = adapter.run_smt(
        problem_id="p-plain-unsat",
        smtlib_script=script,
        execution_mode="REAL" if adapter.z3_binary else "SIMULATED",
    )
    assert trace.terminal_verdict in ("UNSAT", "UNSAT_REFUTED", "SYNTHETIC_UNSAT")
    event_types = [e.event_type for e in trace.events]
    assert TraceEventType.UNSAT_CORE.value not in event_types
    assert "UNSAT_CORE" not in event_types


# 26. Plain SAT result does not create SAT_MODEL event
def test_plain_sat_result_does_not_create_sat_model_event():
    adapter = Z3Adapter()
    script = "(set-logic QF_UF)\n(declare-const p Bool)\n(assert p)\n(check-sat)\n"
    trace = adapter.run_smt(
        problem_id="p-plain-sat",
        smtlib_script=script,
        execution_mode="REAL" if adapter.z3_binary else "SIMULATED",
    )
    assert trace.terminal_verdict in ("SAT", "REFUTED_SAT", "SYNTHETIC_SAT")
    event_types = [e.event_type for e in trace.events]
    assert TraceEventType.SAT_MODEL.value not in event_types
    assert "SAT_MODEL" not in event_types


# 27. Real Lean caller tactic hint is not BACKEND_OBSERVED
def test_real_lean_caller_tactic_hint_is_not_backend_observed():
    adapter = Lean4Adapter()
    if not adapter.lean_binary:
        pytest.skip("Lean binary not installed on host")
    code = "theorem simple_id (p : Prop) (h : p) : p := h\n"
    trace = adapter.run_proof(
        problem_id="p-lean-tactic-obs",
        theorem_name="simple_id",
        code=code,
        execution_mode="REAL",
        tactics=["intro h", "exact h"],
    )
    tactic_events = [e for e in trace.events if e.event_type == TraceEventType.TACTIC_APPLICATION.value]
    assert len(tactic_events) == 2
    for ev in tactic_events:
        assert ev.event_origin == EventOrigin.CLIENT_DECLARED.value
        assert ev.event_origin != EventOrigin.BACKEND_OBSERVED.value

    terminal_ev = [e for e in trace.events if e.event_type == TraceEventType.TERMINAL_VERDICT.value][0]
    assert terminal_ev.event_origin == EventOrigin.BACKEND_OBSERVED.value


# 28. Real Rocq caller tactic hint is not BACKEND_OBSERVED
def test_real_rocq_caller_tactic_hint_is_not_backend_observed():
    adapter = RocqAdapter()
    trace = adapter.run_proof(
        problem_id="p-rocq-tactic-obs",
        theorem_name="simple_lemma",
        code="Lemma simple_lemma : True. exact I. Qed.",
        execution_mode="SYNTHETIC",
        tactics=["exact I"],
    )
    tactic_events = [e for e in trace.events if e.event_type == TraceEventType.TACTIC_APPLICATION.value]
    assert len(tactic_events) >= 1
    for ev in tactic_events:
        assert ev.event_origin == EventOrigin.CLIENT_DECLARED.value
        assert ev.event_origin != EventOrigin.BACKEND_OBSERVED.value


# 29. CLIENT_DECLARED event excluded from abstraction mining
def test_client_declared_event_excluded_from_abstraction_mining():
    def make_mixed_trace(tid, pid):
        tr = ExecutionTrace(
            trace_id=tid,
            problem_id=pid,
            backend_id="lean4",
            backend_version="1.0.0",
            execution_origin="SIMULATED",
            logical_authority_class="NONE",
            created_at="2026-09-12T12:00:00Z",
            terminal_verdict="PROVEN",
            wall_time_ms=10.0,
        )
        init_ev = tr.add_event(
            TraceEventType.INITIAL_PROBLEM,
            operation="init",
            state_digest="0" * 64,
            result_digest="0" * 64,
            event_origin=EventOrigin.CLIENT_DECLARED,
        )
        # Client declared unobserved step
        ev_client = tr.add_event(
            TraceEventType.TACTIC_APPLICATION,
            operation="client_hint_macro",
            state_digest="0" * 64,
            result_digest="1" * 64,
            parent_event_id=init_ev.event_id,
            payload={"expression": "hint_macro(a)"},
            event_origin=EventOrigin.CLIENT_DECLARED,
        )
        # Backend observed steps
        ev1 = tr.add_event(
            TraceEventType.TACTIC_APPLICATION,
            operation="observed_rewrite",
            state_digest="1" * 64,
            result_digest="2" * 64,
            parent_event_id=ev_client.event_id,
            payload={"expression": "rewrite(x)"},
            event_origin=EventOrigin.BACKEND_OBSERVED,
        )
        ev2 = tr.add_event(
            TraceEventType.TACTIC_APPLICATION,
            operation="observed_simplify",
            state_digest="2" * 64,
            result_digest="3" * 64,
            parent_event_id=ev1.event_id,
            payload={"expression": "simplify(x)"},
            event_origin=EventOrigin.BACKEND_OBSERVED,
        )
        tr.add_event(
            TraceEventType.TERMINAL_VERDICT,
            operation="qed",
            state_digest="3" * 64,
            result_digest="3" * 64,
            parent_event_id=ev2.event_id,
            event_origin=EventOrigin.BACKEND_OBSERVED,
        )
        return tr

    tr1 = make_mixed_trace("t-mix-1", "p-1")
    tr2 = make_mixed_trace("t-mix-2", "p-2")

    miner = SubtraceMiner(min_length=1, min_support=2)
    patterns = miner.mine_traces([tr1, tr2])
    all_ops = [op for p in patterns for op in p.operations]
    assert "observed_rewrite" in all_ops
    assert "observed_simplify" in all_ops
    assert "client_hint_macro" not in all_ops


# 30. Same problem digest under different trace IDs triggers leakage
def test_same_problem_digest_under_different_trace_ids_triggers_leakage():
    leak_digest = hashlib.sha256(b"identical_algebraic_problem_statement").hexdigest()
    au = StructuralAntiUnifier()
    terms = [("t-disc-A", Term.parse("f(x)")), ("t-disc-B", Term.parse("f(y)"))]
    res = au.anti_unify(terms)
    candidate = AbstractionCandidate(
        candidate_id="c-leakage-test",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={"name": "lem", "canonical_representation": "f(V1)"},
        anti_unification_evidence=res,
        discovery_set_trace_ids=["t-disc-A", "t-disc-B"],
        discovery_problem_digests=[leak_digest],
        admissibility_status=AdmissibilityStatus.ADMISSIBLE,
        admissibility_receipt=create_admissibility_receipt(
            terms=terms,
            result=res,
            status=AdmissibilityStatus.ADMISSIBLE,
            discovery_problem_digests=[leak_digest],
        ),
    )

    contract = PairedReplayContract(
        problem_id="t-qual-DIFFERENT_ID",
        problem_digest=leak_digest,  # SAME DIGEST
        backend_id="lean4",
        search_policy_kind="MCTS",
        search_budget={"max_depth": 5},
        random_seed=42,
        corpus_context={},
        baseline_configuration={},
        abstracted_configuration={"candidate_id": "c-leakage-test"},
        candidate_id="c-leakage-test",
        candidate_enabled_in_abstracted=True,
    )

    def dummy_runner(c, arm):
        return ReplayRunReceipt(
            receipt_id=f"r-{arm}",
            arm=arm,
            problem_id=c.problem_id,
            problem_digest=c.problem_digest,
            paired_contract_digest=c.contract_digest(),
            backend_id=c.backend_id,
            search_policy_kind=c.search_policy_kind,
            candidate_id=c.candidate_id,
            candidate_enabled=(arm == "ABSTRACTED"),
            random_seed=c.random_seed,
            search_budget_digest=hashlib.sha256(json.dumps(c.search_budget, sort_keys=True).encode("utf-8")).hexdigest(),
            corpus_context_digest=hashlib.sha256(json.dumps(c.corpus_context, sort_keys=True).encode("utf-8")).hexdigest(),
            nodes_expanded=10,
            nodes_evaluated=15,
            branch_count=2,
            solved=True,
            wall_time_ms=5.0,
            evidence_origin="EXECUTED_SEARCH_RUN",
        )

    engine = HeldOutReplayEngine()
    with pytest.raises(HeldOutDataLeakageError) as excinfo:
        engine.execute_paired_replay(candidate, [contract], dummy_runner)
    assert "HELD_OUT_DATA_LEAKAGE" in str(excinfo.value)


# 31. Arbitrary fabricated ReplayRunReceipt cannot qualify
def test_arbitrary_fabricated_replay_run_receipt_cannot_qualify():
    with pytest.raises((ReceiptValidationError, jsonschema.ValidationError)):
        ReplayRunReceipt(
            receipt_id="r-fab-1",
            arm="BASELINE",
            problem_id="p-1",
            problem_digest="0" * 64,
            paired_contract_digest="",  # Missing!
            backend_id="lean4",
            search_policy_kind="MCTS",
            candidate_id="cand-1",
            candidate_enabled=False,
        ).validate()

    bad_dict = {
        "receipt_id": "r-bad",
        "replay_mode": "SYNTHETIC_REPLAY_FIXTURE",
        "arm": "INVALID_ARM",
        "problem_id": "p-1",
        "problem_digest": "0" * 64,
        "paired_contract_digest": "1" * 64,
        "backend_id": "lean4",
        "search_policy_kind": "MCTS",
        "candidate_id": "c-1",
        "candidate_enabled": False,
        "random_seed": 42,
        "nodes_expanded": -1,
        "nodes_evaluated": 0,
        "branch_count": 0,
        "solved": True,
        "wall_time_ms": 1.0,
        "evidence_origin": "SYNTHETIC_FIXTURE",
        "authority": "NONE",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad_dict, REPLAY_RECEIPT_SCHEMA)


# 32. SYNTHETIC_FIXTURE replay receipt cannot qualify even with favorable metrics
def test_synthetic_fixture_replay_receipt_cannot_qualify_even_with_favorable_metrics():
    cand_terms = [("t1", Term.parse("f(a)")), ("t2", Term.parse("f(b)"))]
    cand_res = StructuralAntiUnifier().anti_unify(cand_terms)
    cand = AbstractionCandidate(
        candidate_id="c-synth-favorable",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={"name": "lem", "canonical_representation": "f(V1)"},
        anti_unification_evidence=cand_res,
        discovery_set_trace_ids=["t1", "t2"],
        discovery_problem_digests=["0" * 64],
        admissibility_status=AdmissibilityStatus.ADMISSIBLE,
        admissibility_receipt=create_admissibility_receipt(
            terms=cand_terms,
            result=cand_res,
            status=AdmissibilityStatus.ADMISSIBLE,
            discovery_problem_digests=["0" * 64],
        ),
    )
    contract = PairedReplayContract(
        problem_id="p-held-out",
        problem_digest="1" * 64,
        backend_id="lean4",
        search_policy_kind="MCTS",
        search_budget={"max_depth": 10},
        random_seed=123,
        corpus_context={},
        baseline_configuration={},
        abstracted_configuration={"candidate_id": "c-synth-favorable"},
        candidate_id="c-synth-favorable",
        candidate_enabled_in_abstracted=True,
    )

    def synthetic_favorable_runner(c, arm):
        return ReplayRunReceipt(
            receipt_id=f"r-{arm}",
            arm=arm,
            problem_id=c.problem_id,
            problem_digest=c.problem_digest,
            paired_contract_digest=c.contract_digest(),
            backend_id=c.backend_id,
            search_policy_kind=c.search_policy_kind,
            candidate_id=c.candidate_id,
            candidate_enabled=(arm == "ABSTRACTED"),
            random_seed=c.random_seed,
            search_budget_digest=hashlib.sha256(json.dumps(c.search_budget, sort_keys=True).encode("utf-8")).hexdigest(),
            corpus_context_digest=hashlib.sha256(json.dumps(c.corpus_context, sort_keys=True).encode("utf-8")).hexdigest(),
            nodes_expanded=100 if arm == "BASELINE" else 10,
            nodes_evaluated=200 if arm == "BASELINE" else 20,
            branch_count=20 if arm == "BASELINE" else 2,
            solved=True,
            wall_time_ms=500.0 if arm == "BASELINE" else 50.0,
            evidence_origin="SYNTHETIC_FIXTURE",
        )

    engine = HeldOutReplayEngine()
    report = engine.execute_paired_replay(cand, [contract], synthetic_favorable_runner)
    assert report.structural_compression_ratio == 10.0
    assert report.candidate_evaluation_reduction == 0.9
    assert cand.status == CandidateStatus.CANDIDATE_ONLY
    assert cand.status != CandidateStatus.QUALIFIED_HELD_OUT


# 33. Replay contract violations: wrong arm, wrong digests, wrong seed, wrong policy, etc.
def test_paired_replay_contract_cross_consistency_violations():
    contract = PairedReplayContract(
        problem_id="p-cross",
        problem_digest="a" * 64,
        backend_id="lean4",
        search_policy_kind="MCTS",
        search_budget={"max_depth": 5},
        random_seed=42,
        corpus_context={"domain": "algebra"},
        baseline_configuration={"budget": {"max_depth": 5}},
        abstracted_configuration={"budget": {"max_depth": 5}, "candidate_id": "cand-01"},
        candidate_id="cand-01",
        candidate_enabled_in_abstracted=True,
    )
    contract.validate()

    valid_base = ReplayRunReceipt(
        receipt_id="r-base",
        arm="BASELINE",
        problem_id=contract.problem_id,
        problem_digest=contract.problem_digest,
        paired_contract_digest=contract.contract_digest(),
        backend_id=contract.backend_id,
        search_policy_kind=contract.search_policy_kind,
        candidate_id=contract.candidate_id,
        candidate_enabled=False,
        random_seed=contract.random_seed,
        search_budget_digest=hashlib.sha256(json.dumps(contract.search_budget, sort_keys=True).encode("utf-8")).hexdigest(),
        corpus_context_digest=hashlib.sha256(json.dumps(contract.corpus_context, sort_keys=True).encode("utf-8")).hexdigest(),
        nodes_expanded=50,
        nodes_evaluated=70,
        branch_count=10,
        solved=True,
        wall_time_ms=100.0,
    )

    # 1. Wrong arm
    with pytest.raises(ReplayContractError) as exc:
        _validate_receipt_against_contract(contract, valid_base, "ABSTRACTED")
    assert "WRONG_REPLAY_ARM" in str(exc.value)

    # 2. Wrong problem digest
    rcpt_bad_pdigest = dataclasses.replace(valid_base, problem_digest="f" * 64)
    with pytest.raises(ReplayContractError) as exc:
        _validate_receipt_against_contract(contract, rcpt_bad_pdigest, "BASELINE")
    assert "PROBLEM_DIGEST_MISMATCH" in str(exc.value)

    # 3. Wrong backend
    rcpt_bad_backend = dataclasses.replace(valid_base, backend_id="z3")
    with pytest.raises(ReplayContractError) as exc:
        _validate_receipt_against_contract(contract, rcpt_bad_backend, "BASELINE")
    assert "BACKEND_MISMATCH" in str(exc.value)

    # 4. Wrong search policy
    rcpt_bad_policy = dataclasses.replace(valid_base, search_policy_kind="ASTAR")
    with pytest.raises(ReplayContractError) as exc:
        _validate_receipt_against_contract(contract, rcpt_bad_policy, "BASELINE")
    assert "SEARCH_POLICY_MISMATCH" in str(exc.value)

    # 5. Wrong seed
    rcpt_bad_seed = dataclasses.replace(valid_base, random_seed=999)
    with pytest.raises(ReplayContractError) as exc:
        _validate_receipt_against_contract(contract, rcpt_bad_seed, "BASELINE")
    assert "SEED_MISMATCH" in str(exc.value)

    # 6. Wrong corpus context digest
    rcpt_bad_corpus = dataclasses.replace(valid_base, corpus_context_digest="0" * 64)
    with pytest.raises(ReplayContractError) as exc:
        _validate_receipt_against_contract(contract, rcpt_bad_corpus, "BASELINE")
    assert "CORPUS_CONTEXT_DIGEST_MISMATCH" in str(exc.value)

    # 7. Wrong contract digest
    rcpt_bad_cdigest = dataclasses.replace(valid_base, paired_contract_digest="9" * 64)
    with pytest.raises(ReplayContractError) as exc:
        _validate_receipt_against_contract(contract, rcpt_bad_cdigest, "BASELINE")
    assert "CONTRACT_DIGEST_MISMATCH" in str(exc.value)

    # 8. Baseline candidate enabled rejected
    rcpt_base_enabled = dataclasses.replace(valid_base, candidate_enabled=True)
    with pytest.raises(ReplayContractError) as exc:
        _validate_receipt_against_contract(contract, rcpt_base_enabled, "BASELINE")
    assert "BASELINE_CANDIDATE_ENABLED" in str(exc.value)

    # 9. Abstracted wrong candidate rejected
    valid_abs = ReplayRunReceipt(
        receipt_id="r-abs",
        arm="ABSTRACTED",
        problem_id=contract.problem_id,
        problem_digest=contract.problem_digest,
        paired_contract_digest=contract.contract_digest(),
        backend_id=contract.backend_id,
        search_policy_kind=contract.search_policy_kind,
        candidate_id="other-cand-999",
        candidate_enabled=True,
        random_seed=contract.random_seed,
        search_budget_digest=hashlib.sha256(json.dumps(contract.search_budget, sort_keys=True).encode("utf-8")).hexdigest(),
        corpus_context_digest=hashlib.sha256(json.dumps(contract.corpus_context, sort_keys=True).encode("utf-8")).hexdigest(),
        nodes_expanded=20,
        nodes_evaluated=30,
        branch_count=5,
        solved=True,
        wall_time_ms=40.0,
    )
    with pytest.raises(ReplayContractError) as exc:
        _validate_receipt_against_contract(contract, valid_abs, "ABSTRACTED")
    assert "ABSTRACTED_CANDIDATE_MISMATCH" in str(exc.value)


# 34. Arbitrary non-abstraction configuration drift rejected
def test_arbitrary_non_abstraction_configuration_drift_rejected():
    drift_contract = PairedReplayContract(
        problem_id="p-drift",
        problem_digest="b" * 64,
        backend_id="lean4",
        search_policy_kind="MCTS",
        search_budget={"max_depth": 5},
        random_seed=42,
        corpus_context={},
        baseline_configuration={"heuristic_weight": 1.0, "max_depth": 5},
        abstracted_configuration={"heuristic_weight": 2.5, "max_depth": 5, "candidate_id": "c1"},
        candidate_id="c1",
        candidate_enabled_in_abstracted=True,
    )
    with pytest.raises(ReplayContractError) as excinfo:
        drift_contract.validate()
    assert "CONFIGURATION_DRIFT" in str(excinfo.value)


# 35. Replay metrics disagreeing with SearchRun rejected
def test_replay_metrics_disagreeing_with_search_run_rejected():
    sr = SearchRun(
        run_id="sr-100",
        problem_id="p-100",
        search_policy=SearchPolicyKind.MCTS,
        policy_configuration={},
        nodes_expanded=50,
        nodes_evaluated=100,
        max_depth_reached=4,
        branching_factor_effective=2.0,
        total_wall_time_ms=80.0,
        terminal_status="SOLVED",
        resulting_trace_id="t-100",
    )
    sr_digest = hashlib.sha256(json.dumps(sr.to_dict(), sort_keys=True).encode("utf-8")).hexdigest()
    receipt = ReplayRunReceipt(
        receipt_id="r-disagree",
        arm="BASELINE",
        problem_id="p-100",
        problem_digest="0" * 64,
        paired_contract_digest="c" * 64,
        backend_id="lean4",
        search_policy_kind="MCTS",
        candidate_id="c-1",
        candidate_enabled=False,
        nodes_expanded=20,  # Disagrees with sr.nodes_expanded=50
        nodes_evaluated=100,
        branch_count=5,
        solved=True,
        wall_time_ms=80.0,
        bound_search_run=sr,
        search_run_ref=sr.run_id,
        search_run_digest=sr_digest,
    )
    with pytest.raises(ReplayContractError) as excinfo:
        receipt.validate()
    assert "METRICS_DISAGREEMENT" in str(excinfo.value)


# 36. Candidate default admissibility is UNASSESSED
def test_candidate_default_admissibility_is_unassessed():
    au = StructuralAntiUnifier()
    res = au.anti_unify([("t1", Term.parse("g(a)")), ("t2", Term.parse("g(b)"))])
    cand = AbstractionCandidate(
        candidate_id="c-unassessed-default",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={"name": "lem", "canonical_representation": "g(V1)"},
        anti_unification_evidence=res,
        discovery_set_trace_ids=["t1", "t2"],
    )
    assert cand.admissibility_status == AdmissibilityStatus.UNASSESSED
    d = cand.to_dict()
    assert d["admissibility_status"] == "UNASSESSED"


# 37. Unassessed candidate cannot qualify
def test_unassessed_candidate_cannot_qualify():
    au = StructuralAntiUnifier()
    res = au.anti_unify([("t1", Term.parse("h(a)")), ("t2", Term.parse("h(b)"))])
    cand = AbstractionCandidate(
        candidate_id="c-unassessed-no-qual",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={"name": "lem", "canonical_representation": "h(V1)"},
        anti_unification_evidence=res,
        discovery_set_trace_ids=["t1", "t2"],
        discovery_problem_digests=["0" * 64],
        admissibility_status=AdmissibilityStatus.UNASSESSED,
    )
    contract = PairedReplayContract(
        problem_id="p-qual-unassessed",
        problem_digest="1" * 64,
        backend_id="lean4",
        search_policy_kind="MCTS",
        search_budget={"max_depth": 5},
        random_seed=42,
        corpus_context={},
        baseline_configuration={},
        abstracted_configuration={"candidate_id": cand.candidate_id},
        candidate_id=cand.candidate_id,
        candidate_enabled_in_abstracted=True,
    )

    def executed_runner(c, arm):
        cand_enabled = (arm == "ABSTRACTED")
        nodes_exp = 100 if arm == "BASELINE" else 20
        nodes_eval = 150 if arm == "BASELINE" else 30
        branch_cnt = 10 if arm == "BASELINE" else 2
        w_time = 100.0 if arm == "BASELINE" else 20.0
        s_rcpt = make_valid_search_execution_receipt(
            run_id=f"r-{arm}",
            problem_id=c.problem_id,
            problem_digest=c.problem_digest,
            candidate_id=c.candidate_id,
            candidate_enabled=cand_enabled,
            nodes_expanded=nodes_exp,
            nodes_evaluated=nodes_eval,
            branch_count=branch_cnt,
            wall_time_ms=w_time,
        )
        return ReplayRunReceipt(
            receipt_id=f"r-{arm}",
            arm=arm,
            problem_id=c.problem_id,
            problem_digest=c.problem_digest,
            paired_contract_digest=c.contract_digest(),
            backend_id=c.backend_id,
            search_policy_kind=c.search_policy_kind,
            candidate_id=c.candidate_id,
            candidate_enabled=cand_enabled,
            random_seed=c.random_seed,
            search_budget_digest=hashlib.sha256(json.dumps(c.search_budget, sort_keys=True).encode("utf-8")).hexdigest(),
            corpus_context_digest=hashlib.sha256(json.dumps(c.corpus_context, sort_keys=True).encode("utf-8")).hexdigest(),
            nodes_expanded=nodes_exp,
            nodes_evaluated=nodes_eval,
            branch_count=branch_cnt,
            solved=True,
            wall_time_ms=w_time,
            search_run_ref=f"r-{arm}",
            search_run_digest="0" * 64,
            backend_calls=1,
            execution_trace_refs=["t1"],
            execution_trace_digests=["0" * 64],
            evidence_origin="EXECUTED_SEARCH_RUN",
            search_execution_receipt=s_rcpt.to_dict(),
        )

    engine = HeldOutReplayEngine()
    engine.execute_paired_replay(cand, [contract], executed_runner)
    assert cand.status == CandidateStatus.CANDIDATE_ONLY
    assert cand.status != CandidateStatus.QUALIFIED_HELD_OUT


# 38. seq(V1)-only meaningful structure rejected
def test_seq_v1_only_meaningful_structure_rejected():
    au = StructuralAntiUnifier()
    t1 = Term.parse("seq(f(a))")
    t2 = Term.parse("seq(g(b))")
    res = au.anti_unify([("t1", t1), ("t2", t2)])
    assert str(res.lgg_term) == "seq(V1)"
    assert compute_shared_meaningful_constructors(res.lgg_term) == 0

    status = au.assess_admissibility([("t1", t1), ("t2", t2)], res)
    assert status in (
        AdmissibilityStatus.STRUCTURAL_GENERALIZATION_TRIVIAL,
        AdmissibilityStatus.TRIVIAL_OR_SEMANTICALLY_INCOMPATIBLE_GENERALIZATION,
    )

    t3 = Term.parse("seq(x)")
    t4 = Term.parse("seq(y)")
    res2 = au.anti_unify([("t3", t3), ("t4", t4)])
    status2 = au.assess_admissibility([("t3", t3), ("t4", t4)], res2)
    assert status2 == AdmissibilityStatus.STRUCTURAL_GENERALIZATION_TRIVIAL


# 39. Branch guards derived from trace evidence
def test_branch_guards_derived_from_trace_evidence():
    def make_guarded_trace(tid, pid, guard):
        tr = ExecutionTrace(
            trace_id=tid,
            problem_id=pid,
            backend_id="lean4",
            backend_version="1.0.0",
            execution_origin="SIMULATED",
            logical_authority_class="NONE",
            created_at="2026-09-12T12:00:00Z",
            terminal_verdict="PROVEN",
            wall_time_ms=10.0,
        )
        init_ev = tr.add_event(
            TraceEventType.INITIAL_PROBLEM,
            operation="init",
            state_digest="0" * 64,
            result_digest="0" * 64,
            event_origin=EventOrigin.CLIENT_DECLARED,
        )
        ev_branch = tr.add_event(
            TraceEventType.BRANCH,
            operation="case_split",
            state_digest="0" * 64,
            result_digest="1" * 64,
            parent_event_id=init_ev.event_id,
            payload={"branch_condition": guard},
            event_origin=EventOrigin.BACKEND_OBSERVED,
        )
        ev_tactic = tr.add_event(
            TraceEventType.TACTIC_APPLICATION,
            operation="rewrite_shared",
            state_digest="1" * 64,
            result_digest="2" * 64,
            parent_event_id=ev_branch.event_id,
            payload={"expression": "rewrite(shared_term)"},
            event_origin=EventOrigin.BACKEND_OBSERVED,
        )
        tr.add_event(
            TraceEventType.TERMINAL_VERDICT,
            operation="qed",
            state_digest="2" * 64,
            result_digest="2" * 64,
            parent_event_id=ev_tactic.event_id,
            event_origin=EventOrigin.BACKEND_OBSERVED,
        )
        return tr

    tr1 = make_guarded_trace("t-g-1", "p-1", "x > 0")
    tr2 = make_guarded_trace("t-g-2", "p-2", "x <= 0")

    miner = SubtraceMiner(min_length=1, min_support=2)
    patterns = miner.mine_traces([tr1, tr2])
    assert len(patterns) > 0
    top = patterns[0]
    assert "x > 0" in top.branch_guards
    assert "x <= 0" in top.branch_guards

    cand = CandidateFactory.from_pattern(
        top,
        candidate_kind=AbstractionKind.TACTIC_MACRO,
        candidate_id="c-guarded",
        discovery_problem_digests=[hashlib.sha256(b"p-1").hexdigest(), hashlib.sha256(b"p-2").hexdigest()],
    )
    assert cand.admissibility_status == AdmissibilityStatus.REQUIRES_BRANCH_GUARD


# 40. Naked positive ONTO evidence rejected
def test_naked_positive_onto_evidence_rejected():
    au = StructuralAntiUnifier()
    res = au.anti_unify([("t1", Term.parse("f(a)")), ("t2", Term.parse("f(b)"))])
    cand = AbstractionCandidate(
        candidate_id="c-onto-naked",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={"name": "lem", "canonical_representation": "f(V1)"},
        anti_unification_evidence=res,
        discovery_set_trace_ids=["t1", "t2"],
    )

    with pytest.raises(ValueError) as excinfo:
        OntoExporter.export(cand, functional_evidence=True)
    assert "NAKED_BOOLEAN_PROHIBITED" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        OntoExporter.export(cand, representation_evidence=True)
    assert "NAKED_BOOLEAN_PROHIBITED" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        OntoExporter.export(cand, cross_policy_evidence=True)
    assert "NAKED_BOOLEAN_PROHIBITED" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        OntoExporter.export(cand, cross_formal_system_evidence=True)
    assert "NAKED_BOOLEAN_PROHIBITED" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        OntoExporter.export(cand, functional_evidence="SUPPORTED")
    assert "NAKED_BOOLEAN_PROHIBITED" in str(excinfo.value)


# 41. Validated executed-replay evidence can populate functional-benefit evidence state
def test_validated_executed_replay_evidence_can_populate_functional_benefit():
    au = StructuralAntiUnifier()
    terms = [("t1", Term.parse("f(a)")), ("t2", Term.parse("f(b)"))]
    res = au.anti_unify(terms)
    cand = AbstractionCandidate(
        candidate_id="c-executed-benefit",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={"name": "lem", "canonical_representation": "f(V1)"},
        anti_unification_evidence=res,
        discovery_set_trace_ids=["t1", "t2"],
        discovery_problem_digests=["0" * 64],
        admissibility_status=AdmissibilityStatus.ADMISSIBLE,
        admissibility_receipt=create_admissibility_receipt(
            terms=terms,
            result=res,
            status=AdmissibilityStatus.ADMISSIBLE,
            discovery_problem_digests=["0" * 64],
        ),
    )
    contract = PairedReplayContract(
        problem_id="p-qual-exec",
        problem_digest="1" * 64,
        backend_id="lean4",
        search_policy_kind="MCTS",
        search_budget={"max_depth": 10},
        random_seed=42,
        corpus_context={},
        baseline_configuration={},
        abstracted_configuration={"candidate_id": cand.candidate_id},
        candidate_id=cand.candidate_id,
        candidate_enabled_in_abstracted=True,
    )

    def executed_benefit_runner(c, arm):
        cand_enabled = (arm == "ABSTRACTED")
        nodes_exp = 100 if arm == "BASELINE" else 30
        nodes_eval = 150 if arm == "BASELINE" else 45
        branch_cnt = 10 if arm == "BASELINE" else 3
        w_time = 100.0 if arm == "BASELINE" else 35.0
        s_rcpt = make_valid_search_execution_receipt(
            run_id=f"r-{arm}",
            problem_id=c.problem_id,
            problem_digest=c.problem_digest,
            candidate_id=c.candidate_id,
            candidate_enabled=cand_enabled,
            nodes_expanded=nodes_exp,
            nodes_evaluated=nodes_eval,
            branch_count=branch_cnt,
            wall_time_ms=w_time,
        )
        return ReplayRunReceipt(
            receipt_id=f"r-{arm}",
            arm=arm,
            problem_id=c.problem_id,
            problem_digest=c.problem_digest,
            paired_contract_digest=c.contract_digest(),
            backend_id=c.backend_id,
            search_policy_kind=c.search_policy_kind,
            candidate_id=c.candidate_id,
            candidate_enabled=cand_enabled,
            random_seed=c.random_seed,
            search_budget_digest=hashlib.sha256(json.dumps(c.search_budget, sort_keys=True).encode("utf-8")).hexdigest(),
            corpus_context_digest=hashlib.sha256(json.dumps(c.corpus_context, sort_keys=True).encode("utf-8")).hexdigest(),
            nodes_expanded=nodes_exp,
            nodes_evaluated=nodes_eval,
            branch_count=branch_cnt,
            solved=True,
            wall_time_ms=w_time,
            search_run_ref=f"r-{arm}",
            search_run_digest="0" * 64,
            backend_calls=1,
            execution_trace_refs=["t1"],
            execution_trace_digests=["0" * 64],
            evidence_origin="EXECUTED_SEARCH_RUN",
            search_execution_receipt=s_rcpt.to_dict(),
        )

    engine = HeldOutReplayEngine()
    report = engine.execute_paired_replay(cand, [contract], executed_benefit_runner)
    assert cand.status == CandidateStatus.QUALIFIED_HELD_OUT

    # ONTO export automatically derives SUPPORTED from valid executed held-out evaluation
    onto_pkg = OntoExporter.export(cand)
    assert onto_pkg.functional_search_benefit == "SUPPORTED"

    # Also supports explicit OntoEvidenceRef
    ref = OntoEvidenceRef(
        evidence_kind="HELD_OUT_REPLAY",
        artifact_ref="receipt-executed-123",
        artifact_digest=hashlib.sha256(b"receipt-data").hexdigest(),
        evidence_status="SUPPORTED",
        source_experimental_units=["p-qual-exec"],
    )
    OntoExporter.register_artifact(ref.artifact_ref, ref.artifact_digest)
    onto_pkg_explicit = OntoExporter.export(cand, functional_evidence=ref)
    assert onto_pkg_explicit.functional_search_benefit == "SUPPORTED"
    assert len(onto_pkg_explicit.evidence_refs) == 1
    assert onto_pkg_explicit.evidence_refs[0].artifact_ref == "receipt-executed-123"


# ======================================================================
# Section 27: Positive Hostile Control
# ======================================================================

def test_positive_hostile_control_fabricated_executed_receipt_rejected():
    """Positive hostile control (Section 27):
    - Construct an abstraction candidate with favorable metrics
    - Fabricate a SearchRun with favorable speedup
    - Construct a ReplayRunReceipt with evidence_origin = EXECUTED_SEARCH_RUN
    - Verify that without a valid SearchExecutionReceipt from a real SearchExecutor invocation, the receipt is REJECTED
    - Verify that with a valid SearchExecutionReceipt, the receipt is ACCEPTED
    """
    from msk_formal_discovery.backend.contract import ProblemDefinition
    from msk_formal_discovery.search.executor import SearchExecutor
    from msk_formal_discovery.search.policy import SearchState

    au = StructuralAntiUnifier()
    terms = [("t1", Term.parse("f(a)")), ("t2", Term.parse("f(b)"))]
    res = au.anti_unify(terms)
    p_disc_digest = hashlib.sha256(b"p-disc-positive-hostile").hexdigest()
    cand = AbstractionCandidate(
        candidate_id="c-positive-hostile-control",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={"name": "lem", "canonical_representation": "f(V1)"},
        anti_unification_evidence=res,
        discovery_set_trace_ids=["t1", "t2"],
        discovery_problem_digests=[p_disc_digest],
        discovery_origin="EXECUTED_OBSERVED",
        admissibility_status=AdmissibilityStatus.ADMISSIBLE,
        admissibility_receipt=create_admissibility_receipt(
            terms=terms,
            result=res,
            status=AdmissibilityStatus.ADMISSIBLE,
            discovery_problem_digests=[p_disc_digest],
        ),
    )

    exec_prob_digest = hashlib.sha256(b"eval(True)").hexdigest()
    contract = PairedReplayContract(
        problem_id="p-qual-control",
        problem_digest=exec_prob_digest,
        backend_id="lean4",
        search_policy_kind="MCTS",
        search_budget={"max_depth": 5},
        random_seed=42,
        corpus_context={},
        baseline_configuration={},
        abstracted_configuration={"candidate_id": cand.candidate_id},
        candidate_id=cand.candidate_id,
        candidate_enabled_in_abstracted=True,
    )

    # 1. Fabricate SearchRun with favorable speedup
    sr_fab = SearchRun(
        run_id="sr-fab-control",
        problem_id="p-qual-control",
        search_policy=SearchPolicyKind.MCTS,
        policy_configuration={},
        nodes_expanded=5,
        nodes_evaluated=10,
        max_depth_reached=3,
        branching_factor_effective=1.5,
        total_wall_time_ms=25.0,
        terminal_status="SOLVED",
        resulting_trace_id="t-fab",
    )

    # 2. Fabricate ReplayRunReceipt claiming EXECUTED_SEARCH_RUN without SearchExecutionReceipt
    rcpt_fab = ReplayRunReceipt(
        receipt_id="r-fab-no-exec-rcpt",
        arm="ABSTRACTED",
        problem_id=contract.problem_id,
        problem_digest=contract.problem_digest,
        paired_contract_digest=contract.contract_digest(),
        backend_id=contract.backend_id,
        search_policy_kind=contract.search_policy_kind,
        candidate_id=cand.candidate_id,
        candidate_enabled=True,
        random_seed=contract.random_seed,
        search_budget_digest=hashlib.sha256(json.dumps(contract.search_budget, sort_keys=True).encode("utf-8")).hexdigest(),
        corpus_context_digest=hashlib.sha256(json.dumps(contract.corpus_context, sort_keys=True).encode("utf-8")).hexdigest(),
        nodes_expanded=5,
        nodes_evaluated=10,
        branch_count=2,
        solved=True,
        wall_time_ms=25.0,
        evidence_origin="EXECUTED_SEARCH_RUN",
        bound_search_run=sr_fab,
        search_execution_receipt=None,  # Missing!
    )
    with pytest.raises(ReceiptValidationError) as excinfo:
        rcpt_fab.validate()
    assert "MISSING_SEARCH_EXECUTION_RECEIPT" in str(excinfo.value) or "search_execution_receipt" in str(excinfo.value)

    # 3. Genuine SearchExecutor invocation producing real SearchExecutionReceipt
    exec_prob = ProblemDefinition(
        problem_id="p-qual-control",
        formal_syntax="eval(True)",
        context={},
        goals=["True"],
        assumptions=[],
    )
    executor = SearchExecutor()
    bundle_base = executor.execute(
        policy=MCTSSearch({"max_rollouts": 3}),
        problem=exec_prob,
        initial_state=SearchState(state_id="init_0", goal="True", depth=0),
        budget={"max_depth": 5, "max_nodes": 10},
        candidate_id=cand.candidate_id,
        candidate_enabled=False,
        random_seed=42,
    )
    bundle_abs = executor.execute(
        policy=MCTSSearch({"max_rollouts": 3}),
        problem=exec_prob,
        initial_state=SearchState(state_id="init_0", goal="True", depth=0),
        budget={"max_depth": 5, "max_nodes": 10},
        candidate_id=cand.candidate_id,
        candidate_enabled=True,
        random_seed=42,
    )

    valid_base_rcpt = ReplayRunReceipt.from_search_run(
        search_run=bundle_base.search_run,
        contract=contract,
        arm="BASELINE",
        evidence_origin="EXECUTED_SEARCH_RUN",
    )
    valid_abs_rcpt = ReplayRunReceipt.from_search_run(
        search_run=bundle_abs.search_run,
        contract=contract,
        arm="ABSTRACTED",
        evidence_origin="EXECUTED_SEARCH_RUN",
    )

    # Verify both receipts validate against schema and domain rules
    valid_base_rcpt.validate()
    valid_abs_rcpt.validate()
    assert valid_base_rcpt.search_execution_receipt is not None
    assert valid_abs_rcpt.search_execution_receipt is not None


# ======================================================================
# Section 28: Required Hostile Test Cases
# ======================================================================

# 1. Forged backend receipt dict rejected
def test_forged_backend_receipt_dict_rejected():
    forged_receipt = {"fake": "receipt", "schema_version": "invalid"}
    with pytest.raises((TraceValidationError, ReceiptValidationError)) as excinfo:
        ExecutionTrace(
            trace_id="t-forged-backend",
            problem_id="p-1",
            backend_id="lean4",
            backend_version="1.0.0",
            execution_origin="EXECUTED_NATIVE",
            logical_authority_class="DEDUCTIVE_PROOF_AUTHORITY",
            created_at="2026-09-12T12:00:00Z",
            terminal_verdict="PROVEN",
            wall_time_ms=10.0,
            execution_receipt=forged_receipt,
        )
    assert "INVALID_BACKEND_RECEIPT_SCHEMA" in str(excinfo.value) or "FORGED_OR_INVALID_BACKEND_RECEIPT" in str(excinfo.value)


# 2. Backend version mismatch in receipt rejected
def test_backend_version_mismatch_in_receipt_rejected():
    mismatched_receipt = BackendExecutionReceipt(
        receipt_id="rcpt-v-mismatch",
        backend_id="lean4",
        backend_family=BackendFamily.PROOF_ASSISTANT,
        execution_origin=ExecutionOrigin.EXECUTED_NATIVE,
        executable_path="/usr/bin/lean",
        executable_version="2.0.0",  # Mismatch with trace's 1.0.0!
        executable_sha256="0" * 64,
        command=["lean", "file.lean"],
        input_digest="0" * 64,
        started_at="2026-09-12T12:00:00Z",
        completed_at="2026-09-12T12:00:01Z",
        exit_code=0,
        timeout_status=False,
        stdout_digest="0" * 64,
        stderr_digest="0" * 64,
        terminal_classification="PROVEN",
        logical_authority_class=LogicalAuthorityClass.DEDUCTIVE_PROOF_AUTHORITY,
    )
    with pytest.raises((TraceValidationError, AuthorityViolationError)) as excinfo:
        ExecutionTrace(
            trace_id="t-version-mismatch",
            problem_id="p-1",
            problem_digest="0" * 64,
            backend_id="lean4",
            backend_version="1.0.0",
            execution_origin="EXECUTED_NATIVE",
            logical_authority_class="DEDUCTIVE_PROOF_AUTHORITY",
            created_at="2026-09-12T12:00:00Z",
            terminal_verdict="PROVEN",
            wall_time_ms=10.0,
            execution_receipt=mismatched_receipt.to_dict(),
        )
    assert "RECEIPT_TRACE_MISMATCH" in str(excinfo.value)
    assert "backend_version mismatch" in str(excinfo.value)


# 3. SYNTHETIC_FIXTURE event excluded from production mining
def test_synthetic_fixture_event_excluded_from_production_mining():
    tr1 = ExecutionTrace(
        trace_id="t-synth-mining-1",
        problem_id="p-1",
        backend_id="lean4",
        backend_version="1.0.0",
        execution_origin="SIMULATED",
        logical_authority_class="NONE",
        created_at="2026-09-12T12:00:00Z",
        terminal_verdict="PROVEN",
        wall_time_ms=10.0,
    )
    init1 = tr1.add_event(TraceEventType.INITIAL_PROBLEM, "init", "0" * 64, "0" * 64)
    tr1.add_event(
        TraceEventType.TACTIC_APPLICATION,
        operation="synthetic_magic_rewrite",
        state_digest="0" * 64,
        result_digest="1" * 64,
        parent_event_id=init1.event_id,
        event_origin=EventOrigin.SYNTHETIC_FIXTURE,
    )

    tr2 = ExecutionTrace(
        trace_id="t-synth-mining-2",
        problem_id="p-2",
        backend_id="lean4",
        backend_version="1.0.0",
        execution_origin="SIMULATED",
        logical_authority_class="NONE",
        created_at="2026-09-12T12:00:00Z",
        terminal_verdict="PROVEN",
        wall_time_ms=10.0,
    )
    init2 = tr2.add_event(TraceEventType.INITIAL_PROBLEM, "init", "0" * 64, "0" * 64)
    tr2.add_event(
        TraceEventType.TACTIC_APPLICATION,
        operation="synthetic_magic_rewrite",
        state_digest="0" * 64,
        result_digest="1" * 64,
        parent_event_id=init2.event_id,
        event_origin=EventOrigin.SYNTHETIC_FIXTURE,
    )

    # In production mode (synthetic_algorithm_test_mode=False), SYNTHETIC_FIXTURE events are excluded
    miner = SubtraceMiner(min_length=1, min_support=2, synthetic_algorithm_test_mode=False)
    patterns = miner.mine_traces([tr1, tr2])
    all_ops = [op for p in patterns for op in p.operations]
    assert "synthetic_magic_rewrite" not in all_ops


# 4. Synthetic-discovery candidate cannot qualify into QUALIFIED_HELD_OUT
def test_synthetic_discovery_candidate_cannot_qualify():
    au = StructuralAntiUnifier()
    terms = [("t1", Term.parse("f(a)")), ("t2", Term.parse("f(b)"))]
    res = au.anti_unify(terms)
    p_disc = hashlib.sha256(b"disc-prob").hexdigest()
    cand = AbstractionCandidate(
        candidate_id="c-synth-disc",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={"name": "lem", "canonical_representation": "f(V1)"},
        anti_unification_evidence=res,
        discovery_set_trace_ids=["t1", "t2"],
        discovery_problem_digests=[p_disc],
        discovery_origin="SYNTHETIC_SEARCH",  # Synthetic discovery origin!
        admissibility_status=AdmissibilityStatus.ADMISSIBLE,
        admissibility_receipt=create_admissibility_receipt(
            terms=terms,
            result=res,
            status=AdmissibilityStatus.ADMISSIBLE,
            discovery_problem_digests=[p_disc],
        ),
    )
    contract = PairedReplayContract(
        problem_id="p-qual-synth-disc",
        problem_digest=hashlib.sha256(b"p-qual-synth-disc").hexdigest(),
        backend_id="lean4",
        search_policy_kind="MCTS",
        search_budget={"max_depth": 5},
        random_seed=42,
        corpus_context={},
        baseline_configuration={},
        abstracted_configuration={"candidate_id": cand.candidate_id},
        candidate_id=cand.candidate_id,
        candidate_enabled_in_abstracted=True,
    )

    def executed_benefit_runner(c, arm):
        cand_enabled = (arm == "ABSTRACTED")
        nodes_exp = 100 if arm == "BASELINE" else 30
        nodes_eval = 150 if arm == "BASELINE" else 45
        branch_cnt = 10 if arm == "BASELINE" else 3
        w_time = 100.0 if arm == "BASELINE" else 35.0
        s_rcpt = make_valid_search_execution_receipt(
            run_id=f"r-{arm}",
            problem_id=c.problem_id,
            problem_digest=c.problem_digest,
            candidate_id=c.candidate_id,
            candidate_enabled=cand_enabled,
            nodes_expanded=nodes_exp,
            nodes_evaluated=nodes_eval,
            branch_count=branch_cnt,
            wall_time_ms=w_time,
        )
        return ReplayRunReceipt(
            receipt_id=f"r-{arm}",
            arm=arm,
            problem_id=c.problem_id,
            problem_digest=c.problem_digest,
            paired_contract_digest=c.contract_digest(),
            backend_id=c.backend_id,
            search_policy_kind=c.search_policy_kind,
            candidate_id=c.candidate_id,
            candidate_enabled=cand_enabled,
            random_seed=c.random_seed,
            search_budget_digest=hashlib.sha256(json.dumps(c.search_budget, sort_keys=True).encode("utf-8")).hexdigest(),
            corpus_context_digest=hashlib.sha256(json.dumps(c.corpus_context, sort_keys=True).encode("utf-8")).hexdigest(),
            nodes_expanded=nodes_exp,
            nodes_evaluated=nodes_eval,
            branch_count=branch_cnt,
            solved=True,
            wall_time_ms=w_time,
            search_run_ref=f"r-{arm}",
            search_run_digest="0" * 64,
            backend_calls=1,
            execution_trace_refs=["t1"],
            execution_trace_digests=["0" * 64],
            evidence_origin="EXECUTED_SEARCH_RUN",
            search_execution_receipt=s_rcpt.to_dict(),
        )

    engine = HeldOutReplayEngine()
    report = engine.execute_paired_replay(cand, [contract], executed_benefit_runner)
    assert cand.status != CandidateStatus.QUALIFIED_HELD_OUT
    assert cand.status == CandidateStatus.CANDIDATE_ONLY


# 5. Candidate with empty discovery problem digests cannot qualify
def test_candidate_with_empty_discovery_problem_digests_cannot_qualify():
    au = StructuralAntiUnifier()
    terms = [("t1", Term.parse("f(a)")), ("t2", Term.parse("f(b)"))]
    res = au.anti_unify(terms)
    cand = AbstractionCandidate(
        candidate_id="c-empty-digests",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={"name": "lem", "canonical_representation": "f(V1)"},
        anti_unification_evidence=res,
        discovery_set_trace_ids=["t1", "t2"],
        discovery_problem_digests=[],  # Empty!
        discovery_origin="EXECUTED_OBSERVED",
    )
    contract = PairedReplayContract(
        problem_id="p-qual-empty",
        problem_digest="1" * 64,
        backend_id="lean4",
        search_policy_kind="MCTS",
        search_budget={"max_depth": 5},
        random_seed=42,
        corpus_context={},
        baseline_configuration={},
        abstracted_configuration={"candidate_id": cand.candidate_id},
        candidate_id=cand.candidate_id,
        candidate_enabled_in_abstracted=True,
    )
    engine = HeldOutReplayEngine()
    with pytest.raises(HeldOutDataLeakageError) as excinfo:
        engine.execute_paired_replay(cand, [contract], lambda c, arm: None)
    assert "HELD_OUT_DATA_LEAKAGE" in str(excinfo.value)


# 6. Non-hex problem digest rejected
def test_non_hex_problem_digest_rejected():
    au = StructuralAntiUnifier()
    res = au.anti_unify([("t1", Term.parse("f(a)")), ("t2", Term.parse("f(b)"))])
    with pytest.raises(ValueError):
        AbstractionCandidate(
            candidate_id="c-bad-hex",
            candidate_kind=AbstractionKind.LEMMA,
            formal_specification={"name": "lem", "canonical_representation": "f(V1)"},
            anti_unification_evidence=res,
            discovery_set_trace_ids=["t1", "t2"],
            discovery_problem_digests=["not_valid_hex_string_64_chars_long_0000000000000000000000000000000000"],
        )


# 7. Problem-label-as-digest rejected
def test_problem_label_as_digest_rejected():
    au = StructuralAntiUnifier()
    res = au.anti_unify([("t1", Term.parse("f(a)")), ("t2", Term.parse("f(b)"))])
    with pytest.raises(ValueError):
        AbstractionCandidate(
            candidate_id="c-label-digest",
            candidate_kind=AbstractionKind.LEMMA,
            formal_specification={"name": "lem", "canonical_representation": "f(V1)"},
            anti_unification_evidence=res,
            discovery_set_trace_ids=["t1", "t2"],
            discovery_problem_digests=["problem_label_identifier"],
        )


# 8. Forged admissibility dict rejected
def test_forged_admissibility_dict_rejected():
    cand = AbstractionCandidate(
        candidate_id="c-forged-adm",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={"name": "lem", "canonical_representation": "f(V1)"},
        anti_unification_evidence=StructuralAntiUnifier().anti_unify([("t1", Term.parse("f(a)")), ("t2", Term.parse("f(b)"))]),
        discovery_set_trace_ids=["t1", "t2"],
        discovery_problem_digests=["0" * 64],
        admissibility_status=AdmissibilityStatus.ADMISSIBLE,
        admissibility_receipt={"schema_version": "miskatonic.admissibility-receipt.v0.1", "fake": "data"},
    )
    with pytest.raises(ReceiptValidationError):
        HeldOutReplayEngine.validate_candidate_admissibility(cand)


# 9. Admissibility receipt LGG mismatch rejected
def test_admissibility_receipt_lgg_mismatch_rejected():
    terms = [("t1", Term.parse("f(a)")), ("t2", Term.parse("f(b)"))]
    res = StructuralAntiUnifier().anti_unify(terms)
    p_disc = "0" * 64
    rcpt = create_admissibility_receipt(
        terms=terms,
        result=res,
        status=AdmissibilityStatus.ADMISSIBLE,
        discovery_problem_digests=[p_disc],
    )
    rcpt_dict = rcpt.to_dict()
    rcpt_dict["lgg_digest"] = "f" * 64  # Tampered!
    rcpt_tampered = AdmissibilityReceipt.from_dict(rcpt_dict)
    rcpt_dict["receipt_digest"] = rcpt_tampered.compute_digest()

    cand = AbstractionCandidate(
        candidate_id="c-lgg-mismatch",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={"name": "lem", "canonical_representation": "f(V1)"},
        anti_unification_evidence=res,
        discovery_set_trace_ids=["t1", "t2"],
        discovery_problem_digests=[p_disc],
        admissibility_status=AdmissibilityStatus.ADMISSIBLE,
        admissibility_receipt=rcpt_dict,
    )
    with pytest.raises(ReceiptValidationError) as excinfo:
        HeldOutReplayEngine.validate_candidate_admissibility(cand)
    assert "ADMISSIBILITY_LGG_MISMATCH" in str(excinfo.value)


# 10. Admissibility receipt problem-digest mismatch rejected
def test_admissibility_receipt_problem_digest_mismatch_rejected():
    terms = [("t1", Term.parse("f(a)")), ("t2", Term.parse("f(b)"))]
    res = StructuralAntiUnifier().anti_unify(terms)
    rcpt = create_admissibility_receipt(
        terms=terms,
        result=res,
        status=AdmissibilityStatus.ADMISSIBLE,
        discovery_problem_digests=["1" * 64],  # Mismatch with candidate's "0" * 64!
    )
    cand = AbstractionCandidate(
        candidate_id="c-pdigest-mismatch",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={"name": "lem", "canonical_representation": "f(V1)"},
        anti_unification_evidence=res,
        discovery_set_trace_ids=["t1", "t2"],
        discovery_problem_digests=["0" * 64],
        admissibility_status=AdmissibilityStatus.ADMISSIBLE,
        admissibility_receipt=rcpt.to_dict(),
    )
    with pytest.raises(ReceiptValidationError) as excinfo:
        HeldOutReplayEngine.validate_candidate_admissibility(cand)
    assert "ADMISSIBILITY_PROBLEM_DIGEST_MISMATCH" in str(excinfo.value)


# 11. Contract environment drift changes contract digest
def test_contract_environment_drift_changes_contract_digest():
    c1 = PairedReplayContract(
        problem_id="p-1",
        problem_digest="0" * 64,
        backend_id="lean4",
        search_policy_kind="MCTS",
        search_budget={"depth": 5},
        random_seed=42,
        corpus_context={},
        baseline_configuration={},
        abstracted_configuration={"candidate_id": "cand-1"},
        candidate_id="cand-1",
        environment_identity={"node_id": "compute-01"},
    )
    c2 = PairedReplayContract(
        problem_id="p-1",
        problem_digest="0" * 64,
        backend_id="lean4",
        search_policy_kind="MCTS",
        search_budget={"depth": 5},
        random_seed=42,
        corpus_context={},
        baseline_configuration={},
        abstracted_configuration={"candidate_id": "cand-1"},
        candidate_id="cand-1",
        environment_identity={"node_id": "compute-02"},
    )
    assert c1.contract_digest() != c2.contract_digest()


# 12. Contract backend configuration drift changes contract digest
def test_contract_backend_configuration_drift_changes_contract_digest():
    c1 = PairedReplayContract(
        problem_id="p-1",
        problem_digest="0" * 64,
        backend_id="lean4",
        search_policy_kind="MCTS",
        search_budget={"depth": 5},
        random_seed=42,
        corpus_context={},
        baseline_configuration={},
        abstracted_configuration={"candidate_id": "cand-1"},
        candidate_id="cand-1",
        backend_configuration={"timeout_s": 5},
    )
    c2 = PairedReplayContract(
        problem_id="p-1",
        problem_digest="0" * 64,
        backend_id="lean4",
        search_policy_kind="MCTS",
        search_budget={"depth": 5},
        random_seed=42,
        corpus_context={},
        baseline_configuration={},
        abstracted_configuration={"candidate_id": "cand-1"},
        candidate_id="cand-1",
        backend_configuration={"timeout_s": 10},
    )
    assert c1.contract_digest() != c2.contract_digest()


# 13. Contract source-graph context drift changes contract digest
def test_contract_source_graph_context_drift_changes_contract_digest():
    c1 = PairedReplayContract(
        problem_id="p-1",
        problem_digest="0" * 64,
        backend_id="lean4",
        search_policy_kind="MCTS",
        search_budget={"depth": 5},
        random_seed=42,
        corpus_context={},
        baseline_configuration={},
        abstracted_configuration={"candidate_id": "cand-1"},
        candidate_id="cand-1",
        source_graph_context={"file_path": "Math/Algebra.lean"},
    )
    c2 = PairedReplayContract(
        problem_id="p-1",
        problem_digest="0" * 64,
        backend_id="lean4",
        search_policy_kind="MCTS",
        search_budget={"depth": 5},
        random_seed=42,
        corpus_context={},
        baseline_configuration={},
        abstracted_configuration={"candidate_id": "cand-1"},
        candidate_id="cand-1",
        source_graph_context={"file_path": "Math/Topology.lean"},
    )
    assert c1.contract_digest() != c2.contract_digest()


# 14. Fabricated SearchRun cannot produce EXECUTED_SEARCH_RUN
def test_fabricated_search_run_cannot_produce_executed_search_run():
    sr = SearchRun(
        run_id="sr-fab",
        problem_id="p-1",
        search_policy=SearchPolicyKind.MCTS,
        policy_configuration={},
        nodes_expanded=10,
        nodes_evaluated=20,
        max_depth_reached=2,
        branching_factor_effective=2.0,
        total_wall_time_ms=50.0,
        terminal_status="SOLVED",
    )
    contract = PairedReplayContract(
        problem_id="p-1",
        problem_digest="0" * 64,
        backend_id="lean4",
        search_policy_kind="MCTS",
        search_budget={"depth": 5},
        random_seed=42,
        corpus_context={},
        baseline_configuration={},
        abstracted_configuration={"candidate_id": "cand-1"},
        candidate_id="cand-1",
    )
    # When sr was fabricated without search_execution_receipt, building receipt with EXECUTED_SEARCH_RUN fails validation
    rcpt = ReplayRunReceipt.from_search_run(
        search_run=sr,
        contract=contract,
        arm="BASELINE",
        evidence_origin="EXECUTED_SEARCH_RUN",
    )
    with pytest.raises(ReceiptValidationError) as excinfo:
        rcpt.validate()
    assert "MISSING_SEARCH_EXECUTION_RECEIPT" in str(excinfo.value) or "search_execution_receipt" in str(excinfo.value)


# 15. Missing trace digest with backend_calls > 0 rejected
def test_missing_trace_digest_with_backend_calls_greater_than_zero_rejected():
    s_rcpt = make_valid_search_execution_receipt(
        run_id="r-base-calls",
        problem_id="p-1",
        problem_digest="0" * 64,
        candidate_id="cand-1",
        nodes_expanded=10,
        nodes_evaluated=20,
        branch_count=2,
        wall_time_ms=10.0,
    )
    rcpt = ReplayRunReceipt(
        receipt_id="r-base-calls",
        arm="BASELINE",
        problem_id="p-1",
        problem_digest="0" * 64,
        paired_contract_digest="c" * 64,
        backend_id="lean4",
        search_policy_kind="MCTS",
        candidate_id="cand-1",
        candidate_enabled=False,
        nodes_expanded=10,
        nodes_evaluated=20,
        branch_count=2,
        wall_time_ms=10.0,
        backend_calls=2,  # Calls > 0
        execution_trace_refs=[],  # Missing refs!
        execution_trace_digests=[],
        evidence_origin="EXECUTED_SEARCH_RUN",
        search_run_ref="r-base-calls",
        search_run_digest="0" * 64,
        search_execution_receipt=s_rcpt.to_dict(),
    )
    with pytest.raises(ReceiptValidationError) as excinfo:
        rcpt.validate()
    assert "MISSING_TRACE_REFS" in str(excinfo.value)


# 16. Search run digest mismatch rejected
def test_search_run_digest_mismatch_rejected():
    sr = SearchRun(
        run_id="sr-1",
        problem_id="p-1",
        search_policy=SearchPolicyKind.MCTS,
        policy_configuration={},
        nodes_expanded=10,
        nodes_evaluated=20,
        max_depth_reached=2,
        branching_factor_effective=2.0,
        total_wall_time_ms=50.0,
        terminal_status="SOLVED",
        resulting_trace_id="t1",
    )
    rcpt = ReplayRunReceipt(
        receipt_id="r-mismatch",
        arm="BASELINE",
        problem_id="p-1",
        problem_digest="0" * 64,
        paired_contract_digest="c" * 64,
        backend_id="lean4",
        search_policy_kind="MCTS",
        bound_search_run=sr,
        search_run_ref=sr.run_id,
        search_run_digest="f" * 64,  # Does not match sha256(sr)
        nodes_expanded=10,
        nodes_evaluated=20,
        solved=True,
    )
    with pytest.raises(ReplayContractError) as excinfo:
        rcpt.validate()
    assert "SEARCH_RUN_DIGEST_MISMATCH" in str(excinfo.value)


# 17. CLIENT_DECLARED event carrying proof authority rejected
def test_client_declared_event_carrying_proof_authority_rejected():
    with pytest.raises(AuthorityViolationError) as excinfo:
        ExecutionTraceEvent(
            event_id="ev-illegal-auth",
            sequence=1,
            event_type=TraceEventType.TACTIC_APPLICATION,
            operation="hint",
            state_digest="0" * 64,
            result_digest="1" * 64,
            backend_id="lean4",
            backend_version="1.0.0",
            parent_event_id=None,
            provenance={"timestamp": "2026-09-12T12:00:00Z", "origin": "client"},
            event_origin=EventOrigin.CLIENT_DECLARED,
            logical_authority_class=LogicalAuthorityClass.DEDUCTIVE_PROOF_AUTHORITY.value,
        )
    assert "AUTHORITY_VIOLATION" in str(excinfo.value)


# 18. Z3 unknown trace schema-valid and authority NONE
def test_z3_unknown_trace_schema_valid_and_authority_none():
    adapter = Z3Adapter()
    prob = ProblemDefinition(
        problem_id="prob-unknown",
        formal_syntax="(check-sat-using (then simplify unknown))",
        context={"execution_mode": "SYNTHETIC"},
        goals=["unknown"],
        assumptions=[],
    )
    trace = adapter.solve(prob)
    assert trace.terminal_verdict == "UNKNOWN"
    assert trace.logical_authority_class == "NONE"
    jsonschema.validate(trace.to_dict(), TRACE_SCHEMA)


# 19. ONTO SUPPORTED without resolvable evidence rejected
def test_onto_supported_without_resolvable_evidence_rejected():
    au = StructuralAntiUnifier()
    cand = AbstractionCandidate(
        candidate_id="c-onto-unresolvable",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={"name": "lem", "canonical_representation": "f(V1)"},
        anti_unification_evidence=au.anti_unify([("t1", Term.parse("f(a)")), ("t2", Term.parse("f(b)"))]),
        discovery_set_trace_ids=["t1", "t2"],
        discovery_problem_digests=["0" * 64],
    )
    ref = OntoEvidenceRef(
        evidence_kind="HELD_OUT_REPLAY",
        artifact_ref="nonexistent-artifact-file-12345.json",
        artifact_digest="0" * 64,
        evidence_status="SUPPORTED",
        source_experimental_units=["unit-1"],
    )
    with pytest.raises(ReceiptValidationError) as excinfo:
        OntoExporter.export(cand, functional_evidence=ref)
    assert "UNRESOLVABLE_EVIDENCE_ARTIFACT" in str(excinfo.value)

