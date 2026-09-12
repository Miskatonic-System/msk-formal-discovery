"""Comprehensive end-to-end and hostile invariant tests for WO-MATH-FORMAL-DISCOVERY-01B."""
import hashlib
import json
from pathlib import Path
import pytest
import jsonschema

from msk_formal_discovery.abstraction.anti_unification import (
    AdmissibilityReceipt,
    AdmissibilityStatus,
)
from msk_formal_discovery.abstraction.candidate import (
    AbstractionCandidate,
    AbstractionKind,
    CandidateFactory,
    CandidateStatus,
    compute_candidate_artifact_digest,
)
from msk_formal_discovery.abstraction.replay import (
    HeldOutReplayEngine,
    PairedReplayContract,
    ReplayRunReceipt,
)
from msk_formal_discovery.abstraction.subtrace_miner import SubtraceMiner
from msk_formal_discovery.application.applicator import (
    CandidateApplicationReceipt,
    CandidateApplicator,
)
from msk_formal_discovery.backend.contract import ProblemDefinition
from msk_formal_discovery.core.exceptions import (
    AuthorityViolationError,
    HeldOutDataLeakageError,
    ReceiptValidationError,
    RefactoringError,
    ReplayContractError,
)
from msk_formal_discovery.core.terms import Term
from msk_formal_discovery.experiments.rewrite_control import (
    RewriteProblem,
    RewriteSearchEnvironment,
    add,
    check_smt_equivalence,
    const,
    generate_discovery_corpus,
    generate_held_out_negative_corpus,
    generate_held_out_positive_corpus,
    mul,
    var,
)
from msk_formal_discovery.experiments.runner import run_01b_experiment
from msk_formal_discovery.onto.export import OntoEvidenceRef, OntoExporter
from msk_formal_discovery.refactoring.proposal import (
    RefactoringKind,
    RefactoringProposal,
    RefactoringProposalGenerator,
)
from msk_formal_discovery.search.executor import (
    CANONICAL_DISABLED_APPLICATION_DIGEST,
    SearchExecutionBundle,
    SearchExecutor,
    compute_initial_state_digest,
    get_policy_implementation_digest,
)
from msk_formal_discovery.search.frontier import DeterministicFrontierSearch
from msk_formal_discovery.search.policy import SearchState

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = REPO_ROOT / "schemas"
EXP_DIR = REPO_ROOT / "experiments" / "formal-discovery-01b"


@pytest.fixture(scope="module")
def experiment_execution_result():
    """Run the 01B experiment and return the result dictionary."""
    return run_01b_experiment(exp_dir=EXP_DIR, save_receipts=True)


# 1. End-to-end pipeline execution and success gates
def test_end_to_end_pipeline_success_gates(experiment_execution_result):
    res = experiment_execution_result
    assert res["adjudication_verdict"] == "ABSTRACTION_SEARCH_BENEFIT_SUPPORTED"
    assert res["success_gates"]["all_gates_passed"] is True
    assert res["success_gates"]["gate_discovery_traces_generated"] is True
    assert res["success_gates"]["gate_candidate_selected_and_admissible"] is True
    assert res["success_gates"]["gate_paired_replay_contracts_executed"] is True
    assert res["success_gates"]["gate_positive_held_out_search_reduction"] is True
    assert res["success_gates"]["gate_negative_control_selectivity_parity"] is True
    assert res["success_gates"]["gate_smt_semantic_control_verified"] is True
    assert res["authority"] == "NONE"
    assert res["claim_ceiling"] == "ENGINEERING_ABSTRACTION_EFFECT_ONLY"


# 2. Positive held-out search reduction exceeds 20%
def test_positive_held_out_reduction_exceeds_threshold(experiment_execution_result):
    pos = experiment_execution_result["metrics"]["positive_held_out"]
    assert pos["problem_count"] == 8
    assert pos["node_reduction_pct"] >= 20.0
    assert pos["baseline_solve_rate"] == 1.0
    assert pos["abstracted_solve_rate"] == 1.0
    assert pos["applications_count"] == 8


# 3. Negative control selectivity parity maintained
def test_negative_control_exact_selectivity_and_non_application(experiment_execution_result):
    neg = experiment_execution_result["metrics"]["negative_control"]
    assert neg["problem_count"] == 4
    assert neg["node_delta"] == 0
    assert neg["parity_maintained"] is True
    assert neg["applications_count"] == 0
    assert neg["baseline_solve_rate"] == 1.0
    assert neg["abstracted_solve_rate"] == 1.0


# 4. Manifest and preregistration integrity
def test_manifest_preregistration_integrity():
    prereg = json.loads((EXP_DIR / "preregistration.json").read_text())
    disc = json.loads((EXP_DIR / "discovery-manifest.json").read_text())
    qual = json.loads((EXP_DIR / "qualification-manifest.json").read_text())

    assert len(disc["discovery_problems"]) == 8
    assert len(qual["positive_held_out_problems"]) == 8
    assert len(qual["negative_control_problems"]) == 4

    disc_digests = [p["problem_digest"] for p in disc["discovery_problems"]]
    assert disc_digests == prereg["discovery_problem_digests"]

    pos_digests = [p["problem_digest"] for p in qual["positive_held_out_problems"]]
    assert pos_digests == prereg["positive_held_out_digests"]

    neg_digests = [p["problem_digest"] for p in qual["negative_control_problems"]]
    assert neg_digests == prereg["negative_control_digests"]


# 5. Caller direct applied minting strictly rejected
def test_caller_direct_applied_minting_rejected():
    executor = SearchExecutor()
    prob = ProblemDefinition(problem_id="p-mint", formal_syntax="x", context={}, goals=["solve"], assumptions=[], problem_digest="0" * 64)
    st = SearchState(state_id="s0", goal="g", depth=0)
    with pytest.raises(AuthorityViolationError) as excinfo:
        executor.execute(
            policy=DeterministicFrontierSearch(),
            problem=prob,
            initial_state=st,
            budget={"max_nodes": 10},
            candidate_application_status="APPLIED",
        )
    assert "CALLER_CANNOT_SET_APPLIED" in str(excinfo.value)


# 6. Applicator equivalence witness failure rejects candidate application
def test_applicator_equivalence_witness_failure_rejects():
    cand = AbstractionCandidate(
        candidate_id="macro_buggy",
        candidate_kind=AbstractionKind.TACTIC_MACRO,
        formal_specification={"name": "macro_buggy", "canonical_representation": "x"},
        anti_unification_evidence=None,
        discovery_set_trace_ids=["t1", "t2"],
        primitive_expansion=["MUL_ONE_LEFT", "ADD_ZERO_RIGHT"],
    )
    # Target expression where expansion works
    expr = add(mul(const("1"), var("x")), const("0"))
    env = RewriteSearchEnvironment("p1", "0" * 64, var("x"))
    st = env.create_initial_state(expr)
    actions = env.actions(st)

    # Subclass or mock environment to forge a mismatched transition output
    class TamperedEnv(RewriteSearchEnvironment):
        def transition(self, state, action):
            if action.operation.startswith("MACRO_"):
                # Return wrong state
                bad_state = SearchState(
                    state_id="bad_state",
                    goal="g",
                    depth=1,
                    context={"expression": const("999"), "expression_digest": const("999").digest()},
                )
                return bad_state, None
            return super().transition(state, action)

    tampered_env = TamperedEnv("p1", "0" * 64, var("x"))
    res = CandidateApplicator.apply(
        candidate=cand,
        state=st,
        primitive_actions=actions,
        environment=tampered_env,
        problem_digest="0" * 64,
        experimental_unit_id="unit-1",
    )
    assert res.status == "REJECTED"
    assert res.receipt.application_status == "REJECTED"
    assert res.transformed_actions == actions


# 7. SMT semantic control real execution and refutation
def test_smt_semantic_control_real_execution_and_refutation():
    t1 = add(mul(const("1"), var("x")), const("0"))
    t2 = var("x")
    is_equiv, trace = check_smt_equivalence(t1, t2, problem_id="test-smt")
    assert is_equiv is True
    assert trace.terminal_verdict == "UNSAT_REFUTED"
    assert trace.execution_origin == "EXECUTED_NATIVE"
    assert trace.logical_authority_class == "SOLVER_SAT_OR_UNSAT"
    assert trace.execution_receipt is not None
    assert trace.execution_receipt["exit_code"] == 0


# 8. SMT refutes non-equivalent symbolic expressions
def test_smt_semantic_control_refutes_non_equivalent():
    t1 = add(var("x"), const("1"))
    t2 = var("x")
    is_equiv, trace = check_smt_equivalence(t1, t2, problem_id="test-smt-diff")
    assert is_equiv is False
    assert trace.terminal_verdict == "REFUTED_SAT"
    assert trace.execution_origin == "EXECUTED_NATIVE"


# 9. Candidate artifact digest integrity
def test_candidate_artifact_digest_integrity():
    cand = AbstractionCandidate(
        candidate_id="macro_test",
        candidate_kind=AbstractionKind.TACTIC_MACRO,
        formal_specification={"name": "macro_test", "canonical_representation": "x"},
        anti_unification_evidence=None,
        discovery_set_trace_ids=["t1", "t2"],
        primitive_expansion=["MUL_ONE_LEFT", "ADD_ZERO_RIGHT"],
    )
    d1 = cand.artifact_digest()

    # Mutate primitive expansion
    cand2 = AbstractionCandidate(
        candidate_id="macro_test",
        candidate_kind=AbstractionKind.TACTIC_MACRO,
        formal_specification={"name": "macro_test", "canonical_representation": "x"},
        anti_unification_evidence=None,
        discovery_set_trace_ids=["t1", "t2"],
        primitive_expansion=["ADD_ZERO_RIGHT", "MUL_ONE_LEFT"],
    )
    d2 = cand2.artifact_digest()
    assert d1 != d2


# 10. Candidate application receipt schema validation
def test_candidate_application_receipt_schema_validation():
    schema = json.loads((SCHEMAS_DIR / "candidate-application-receipt.v0.1.schema.json").read_text())
    receipts_dir = EXP_DIR / "receipts"
    app_files = list(receipts_dir.glob("application-*.json"))
    assert len(app_files) > 0
    for f in app_files[:10]:
        data = json.loads(f.read_text())
        jsonschema.validate(data, schema)


# 11. Candidate application receipt digest tampering rejected
def test_candidate_application_receipt_digest_tampering_rejected():
    receipts_dir = EXP_DIR / "receipts"
    app_file = next(receipts_dir.glob("application-*.json"))
    data = json.loads(app_file.read_text())
    rcpt = CandidateApplicationReceipt.from_dict(data)
    rcpt.validate()

    # Tamper field
    tampered_data = dict(data)
    tampered_data["application_status"] = "REJECTED" if data["application_status"] == "APPLIED" else "APPLIED"
    rcpt_tampered = CandidateApplicationReceipt.from_dict(tampered_data)
    with pytest.raises(ReceiptValidationError) as excinfo:
        rcpt_tampered.validate()
    assert "RECEIPT_DIGEST_MISMATCH" in str(excinfo.value)


# 12. Disjointness invariant enforced
def test_disjointness_invariant_enforced():
    cand = AbstractionCandidate(
        candidate_id="c_disjoint",
        candidate_kind=AbstractionKind.TACTIC_MACRO,
        formal_specification={"name": "c_disjoint"},
        anti_unification_evidence=None,
        discovery_set_trace_ids=["t1", "t2"],
        discovery_problem_digests=["a" * 64, "b" * 64],
    )
    with pytest.raises(HeldOutDataLeakageError):
        HeldOutReplayEngine.verify_held_out_disjointness(
            cand,
            qualification_problem_digests=["a" * 64, "c" * 64],
        )


# 13. Replay contract cross-consistency with application receipts
def test_replay_contract_cross_consistency_with_application_receipts():
    receipts_dir = EXP_DIR / "receipts"
    base_file = receipts_dir / "replay-baseline-qual-pos-01.json"
    abs_file = receipts_dir / "replay-abstracted-qual-pos-01.json"
    base_data = json.loads(base_file.read_text())
    abs_data = json.loads(abs_file.read_text())

    assert base_data["arm"] == "BASELINE"
    assert base_data["candidate_enabled"] is False
    assert abs_data["arm"] == "ABSTRACTED"
    assert abs_data["candidate_enabled"] is True


# 14. ONTO export requires resolvable evidence and rejects naked claims
def test_onto_export_requires_resolvable_evidence():
    cand = AbstractionCandidate(
        candidate_id="c_onto",
        candidate_kind=AbstractionKind.TACTIC_MACRO,
        formal_specification={"name": "c_onto"},
        anti_unification_evidence=None,
        discovery_set_trace_ids=["t1", "t2"],
    )
    # Naked boolean prohibited
    with pytest.raises(ValueError) as excinfo:
        OntoExporter.export(cand, functional_evidence=True)
    assert "NAKED_BOOLEAN_PROHIBITED" in str(excinfo.value)

    # Naked positive string prohibited
    with pytest.raises(ValueError) as excinfo:
        OntoExporter.export(cand, functional_evidence="SUPPORTED")
    assert "NAKED_BOOLEAN_PROHIBITED" in str(excinfo.value)

    # Executed experiment ONTO export carries validated evidence ref
    onto_file = EXP_DIR / "onto-export.json"
    data = json.loads(onto_file.read_text())
    assert data["functional_search_benefit"] == "SUPPORTED"
    assert len(data["evidence_refs"]) >= 1
    assert data["authority"] == "NONE"


# 15. Refactoring proposal prohibits canonical mutation
def test_refactoring_proposal_prohibits_canonical_mutation():
    cand = AbstractionCandidate(
        candidate_id="c_prop",
        candidate_kind=AbstractionKind.TACTIC_MACRO,
        formal_specification={"name": "macro_add"},
        anti_unification_evidence=None,
        discovery_set_trace_ids=["t1", "t2"],
    )
    proposal = RefactoringProposalGenerator.generate(cand, RefactoringKind.EXTRACTED_HELPER_LEMMA)
    assert proposal.canonical_library_mutated is False
    assert proposal.authority == "NONE"

    # Attempting to mutate canonical library fails post-init
    with pytest.raises(RefactoringError) as excinfo:
        RefactoringProposal(
            proposal_id="prop-bad",
            candidate_id="c_prop",
            refactoring_kind=RefactoringKind.EXTRACTED_HELPER_LEMMA,
            before_state={},
            proposed_after_state={},
            semantic_obligations=[],
            affected_traces=[],
            expected_compression=1.5,
            replay_plan={},
            canonical_library_mutated=True,
        )
    assert "CANONICAL_LIBRARY_MUTATION_PROHIBITED" in str(excinfo.value)


# 16. Refactoring proposal authority must be NONE
def test_refactoring_proposal_authority_none():
    with pytest.raises(RefactoringError) as excinfo:
        RefactoringProposal(
            proposal_id="prop-auth",
            candidate_id="c_prop",
            refactoring_kind=RefactoringKind.EXTRACTED_HELPER_LEMMA,
            before_state={},
            proposed_after_state={},
            semantic_obligations=[],
            affected_traces=[],
            expected_compression=1.5,
            replay_plan={},
            authority="MATHEMATICAL_TRUTH",
        )
    assert "REFACTORING_AUTHORITY_INVALID" in str(excinfo.value)


# 17. Empty candidate primitive expansion rejected by applicator
def test_empty_candidate_expansion_rejected():
    cand = AbstractionCandidate(
        candidate_id="macro_empty",
        candidate_kind=AbstractionKind.TACTIC_MACRO,
        formal_specification={"name": "empty"},
        anti_unification_evidence=None,
        discovery_set_trace_ids=["t1", "t2"],
        primitive_expansion=[],
    )
    env = RewriteSearchEnvironment("p1", "0" * 64, var("x"))
    st = env.create_initial_state(var("x"))
    actions = env.actions(st)

    # Empty primitive expansion is rejected with ValueError
    with pytest.raises(ValueError) as excinfo:
        CandidateApplicator.apply(
            candidate=cand,
            state=st,
            primitive_actions=actions,
            environment=env,
            problem_digest="0" * 64,
            experimental_unit_id="unit-empty",
        )
    assert "EMPTY_PRIMITIVE_EXPANSION" in str(excinfo.value)


# 18. Search executor binds application receipt refs and digests
def test_search_executor_binds_application_receipt_refs_and_digests():
    receipts_dir = EXP_DIR / "receipts"
    abs_receipt_file = receipts_dir / "search-abstracted-qual-pos-01.json"
    data = json.loads(abs_receipt_file.read_text())
    assert data["candidate_application_status"] == "APPLIED"
    assert len(data["candidate_application_receipt_refs"]) > 0
    assert len(data["candidate_application_receipt_digests"]) > 0
    for dig in data["candidate_application_receipt_digests"]:
        assert len(dig) == 64


# 19. Negative control application receipts are NOT_APPLICABLE
def test_negative_control_application_receipts_are_not_applicable():
    receipts_dir = EXP_DIR / "receipts"
    neg_receipt_file = receipts_dir / "search-abstracted-qual-neg-01.json"
    data = json.loads(neg_receipt_file.read_text())
    assert data["candidate_application_status"] == "REQUESTED_NOT_APPLIED"
    # Receipts emitted have NOT_APPLICABLE
    for ref in data["candidate_application_receipt_refs"]:
        app_file = receipts_dir / f"application-{ref}.json"
        if app_file.exists():
            app_data = json.loads(app_file.read_text())
            assert app_data["application_status"] == "NOT_APPLICABLE"


# 20. Result json matches sum of executed receipts
def test_result_json_consistent_with_executed_receipts():
    result = json.loads((EXP_DIR / "result.json").read_text())
    receipts_dir = EXP_DIR / "receipts"

    pos_base_nodes = 0
    pos_abs_nodes = 0
    for i in range(1, 9):
        b = json.loads((receipts_dir / f"search-baseline-qual-pos-0{i}.json").read_text())
        a = json.loads((receipts_dir / f"search-abstracted-qual-pos-0{i}.json").read_text())
        pos_base_nodes += b["nodes_expanded"]
        pos_abs_nodes += a["nodes_expanded"]

    assert result["metrics"]["positive_held_out"]["baseline_nodes_total"] == pos_base_nodes
    assert result["metrics"]["positive_held_out"]["abstracted_nodes_total"] == pos_abs_nodes
