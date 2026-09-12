"""Hostile Invariant Test Suite (Section 18).

Enforces all 10 hostile rejection and authority-boundary invariants.
"""
from pathlib import Path
import json
import pytest
import jsonschema

from fixtures.fixture_matrix import make_sample_trace
from msk_formal_discovery.abstraction.anti_unification import StructuralAntiUnifier
from msk_formal_discovery.abstraction.candidate import (
    AbstractionCandidate,
    AbstractionKind,
    CandidateStatus,
)
from msk_formal_discovery.abstraction.replay import HeldOutReplayEngine
from msk_formal_discovery.backend.contract import (
    BackendFamily,
    LogicalAuthorityClass,
    ReasoningBackend,
)
from msk_formal_discovery.backend.registry import BackendRegistry
from msk_formal_discovery.core.exceptions import (
    AuthorityViolationError,
    FormalDiscoveryError,
    HeldOutDataLeakageError,
    RefactoringError,
    TraceValidationError,
)
from msk_formal_discovery.core.pipeline import (
    CANONICAL_PIPELINE_SEQUENCE,
    PipelineStage,
    verify_pipeline_sequence,
)
from msk_formal_discovery.core.terms import Term
from msk_formal_discovery.refactoring.proposal import RefactoringKind, RefactoringProposal
from msk_formal_discovery.search.mcts import MCTSSearch
from msk_formal_discovery.search.policy import SearchPolicyKind, SearchRun, SearchState


SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"
TRACE_SCHEMA = json.loads((SCHEMAS_DIR / "execution-trace.v0.1.schema.json").read_text())
SEARCH_SCHEMA = json.loads((SCHEMAS_DIR / "search-run.v0.1.schema.json").read_text())
REFACTOR_SCHEMA = json.loads((SCHEMAS_DIR / "refactoring-proposal.v0.1.schema.json").read_text())


# 1. Hostile Case 1: Untyped / raw string trace injected without schema conformance
def test_hostile_case_1_untyped_raw_trace_rejected():
    raw_invalid_trace = {
        "trace_id": "bad-trace-001",
        "raw_string": "this is an unstructured log string",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(raw_invalid_trace, TRACE_SCHEMA)


# 2. Hostile Case 2: SMT backend claiming DEDUCTIVE_PROOF_AUTHORITY
def test_hostile_case_2_smt_claiming_deductive_proof_authority_rejected():
    class RogueSMT(ReasoningBackend):
        def solve(self, problem): pass
        def supported_operations(self): return ["assert"]

    with pytest.raises(AuthorityViolationError) as excinfo:
        RogueSMT(
            backend_id="rogue_smt",
            backend_family=BackendFamily.SMT_SOLVER,
            backend_version="1.0.0",
            logical_authority_class=LogicalAuthorityClass.DEDUCTIVE_PROOF_AUTHORITY,
        )
    assert "SOLVER_SAT_RESULT_CANNOT_CLAIM_PROOF_AUTHORITY" in str(excinfo.value)


# 3. Hostile Case 3: Model checker claiming DEDUCTIVE_PROOF_AUTHORITY
def test_hostile_case_3_model_checker_claiming_deductive_authority_rejected():
    class RogueModelChecker(ReasoningBackend):
        def solve(self, problem): pass
        def supported_operations(self): return ["model_check"]

    with pytest.raises(AuthorityViolationError) as excinfo:
        RogueModelChecker(
            backend_id="rogue_mc",
            backend_family=BackendFamily.MODEL_CHECKER,
            backend_version="1.0.0",
            logical_authority_class=LogicalAuthorityClass.DEDUCTIVE_PROOF_AUTHORITY,
        )
    assert "MODEL_CHECKER_MISLABELED_AS_PROOF_ASSISTANT" in str(excinfo.value)


# 4. Hostile Case 4: Corpus-guided MCTS claiming corpus authority
def test_hostile_case_4_corpus_guided_mcts_cannot_claim_corpus_authority():
    mcts = MCTSSearch(c_param=1.414)
    assert mcts.authority == "NONE"

    # Search run schema rejects any authority other than "NONE"
    bad_search_run = {
        "schema_version": "miskatonic.search-run.v0.1",
        "run_id": "run-hostile-001",
        "problem_id": "prob-001",
        "search_policy": "MCTS",
        "policy_configuration": {},
        "metrics": {
            "nodes_expanded": 10,
            "nodes_evaluated": 10,
            "max_depth_reached": 2,
            "total_wall_time_ms": 5.0,
        },
        "terminal_status": "SUCCESS",
        "authority": "CORPUS_AUTHORITY",  # Attempt to claim corpus authority
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad_search_run, SEARCH_SCHEMA)


# 5. Hostile Case 5: Search policy or candidate claiming proof authority
def test_hostile_case_5_search_policy_claiming_authority_rejected():
    mcts = MCTSSearch()
    assert mcts.authority == "NONE"

    au = StructuralAntiUnifier()
    res = au.anti_unify([("t1", Term.parse("f(a)")), ("t2", Term.parse("f(b)"))])
    cand = AbstractionCandidate(
        candidate_id="cand-001",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={"name": "test"},
        anti_unification_evidence=res,
        discovery_set_trace_ids=["t1", "t2"],
    )
    assert cand.authority == "NONE"


# 6. Hostile Case 6: Held-out data leakage (overlap between discovery and qualification sets)
def test_hostile_case_6_held_out_data_leakage_rejected():
    engine = HeldOutReplayEngine()
    discovery_ids = ["trace-001", "trace-002", "trace-003"]
    leaked_qualification_ids = ["trace-003", "trace-004"]  # trace-003 overlaps!

    with pytest.raises(HeldOutDataLeakageError) as excinfo:
        engine.verify_held_out_disjointness(discovery_ids, leaked_qualification_ids)
    assert "DISCOVERY_SET_DATA_LEAKAGE" in str(excinfo.value)


# 7. Hostile Case 7: Canonical library mutation attempted in refactoring proposal
def test_hostile_case_7_canonical_library_mutation_prohibited():
    with pytest.raises(RefactoringError) as excinfo:
        RefactoringProposal(
            proposal_id="prop-mut-001",
            candidate_id="cand-001",
            refactoring_kind=RefactoringKind.EXTRACTED_HELPER_LEMMA,
            before_state={},
            proposed_after_state={},
            semantic_obligations=[],
            affected_traces=[],
            expected_compression=1.2,
            replay_plan={},
            canonical_library_mutated=True,  # Prohibited in 01A
            authority="NONE",
        )
    assert "CANONICAL_LIBRARY_MUTATION_PROHIBITED" in str(excinfo.value)


# 8. Hostile Case 8: Refactoring proposal claiming non-NONE authority
def test_hostile_case_8_refactoring_proposal_authority_escalation():
    with pytest.raises(RefactoringError) as excinfo:
        RefactoringProposal(
            proposal_id="prop-auth-001",
            candidate_id="cand-001",
            refactoring_kind=RefactoringKind.EXTRACTED_HELPER_LEMMA,
            before_state={},
            proposed_after_state={},
            semantic_obligations=[],
            affected_traces=[],
            expected_compression=1.2,
            replay_plan={},
            canonical_library_mutated=False,
            authority="DEDUCTIVE_PROOF_AUTHORITY",  # Prohibited!
        )
    assert "REFACTORING_AUTHORITY_INVALID" in str(excinfo.value)


# 9. Hostile Case 9: Pipeline sequence jumping or out-of-order execution
def test_hostile_case_9_pipeline_sequence_violation():
    # Out of order: ABSTRACTION_MINING before SEARCH
    invalid_order = [
        PipelineStage.SOURCE_CORPUS,
        PipelineStage.ABSTRACTION_MINING,
        PipelineStage.SEARCH,
    ]
    assert verify_pipeline_sequence(invalid_order) is False

    # Empty sequence
    assert verify_pipeline_sequence([]) is False


# 10. Hostile Case 10: Untyped internal backend fields leaked into trace payload
def test_hostile_case_10_trace_internal_backend_leakage():
    trace = make_sample_trace("trace-leak-hostile", "prob-leak", [("s1", "e1")])
    trace.events[1].payload["internal_backend_solver_pointer"] = 0xDEADBEEF
    with pytest.raises(TraceValidationError) as excinfo:
        trace.validate()
    assert "BACKEND_LEAK_WITHOUT_TYPED_EXTENSION" in str(excinfo.value)
