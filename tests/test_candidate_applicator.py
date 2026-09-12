"""Unit and hostile invariant tests for CandidateApplicator and CandidateApplicationReceipt (WO-MATH-FORMAL-DISCOVERY-01B)."""
import hashlib
import json
from pathlib import Path
import pytest
import jsonschema

from msk_formal_discovery.abstraction.candidate import (
    AbstractionCandidate,
    AbstractionKind,
    CandidateFactory,
    CandidateStatus,
)
from msk_formal_discovery.abstraction.subtrace_miner import SubtraceMiner
from msk_formal_discovery.application.applicator import (
    CandidateApplicationReceipt,
    CandidateApplicationResult,
    CandidateApplicator,
    get_applicator_implementation_digest,
)
from msk_formal_discovery.backend.contract import ProblemDefinition
from msk_formal_discovery.core.exceptions import AuthorityViolationError, ReceiptValidationError
from msk_formal_discovery.core.terms import App, Const, Term, Var
from msk_formal_discovery.experiments.rewrite_control import (
    RewriteProblem,
    RewriteSearchEnvironment,
    add,
    const,
    generate_discovery_corpus,
    generate_held_out_negative_corpus,
    generate_held_out_positive_corpus,
    mul,
    neg,
    run_discovery_episode,
    var,
)
from msk_formal_discovery.search.executor import SearchExecutor
from msk_formal_discovery.search.frontier import DeterministicFrontierSearch
from msk_formal_discovery.search.policy import SearchState

SCHEMAS_DIR = Path(__file__).resolve().parents[1] / "schemas"
RECEIPT_SCHEMA = json.loads((SCHEMAS_DIR / "candidate-application-receipt.v0.1.schema.json").read_text())


@pytest.fixture(scope="module")
def top_mined_candidate() -> AbstractionCandidate:
    disc = generate_discovery_corpus()
    traces = [run_discovery_episode(p) for p in disc]
    miner = SubtraceMiner(min_length=2, min_support=2)
    patterns = miner.mine_traces(traces)
    assert len(patterns) > 0
    top = patterns[0]
    cand = CandidateFactory.from_pattern(
        top,
        candidate_kind=AbstractionKind.TACTIC_MACRO,
        candidate_id="macro_mul_one_add_zero",
    )
    return cand


def test_applicator_receipt_schema_validation():
    """Verify CandidateApplicationReceipt validates against official schema."""
    rcpt = CandidateApplicationReceipt(
        application_id="app-test-01",
        candidate_id="cand-01",
        candidate_artifact_digest="0" * 64,
        candidate_kind="TACTIC_MACRO",
        applicator_id="msk-candidate-applicator-v0.1",
        applicator_version="0.1.0",
        applicator_implementation_digest="1" * 64,
        experimental_unit_id="unit-01",
        problem_digest="2" * 64,
        input_state_digest="3" * 64,
        candidate_pattern_digest="4" * 64,
        substitution_witness={"V1": "x"},
        primitive_expansion=["MUL_ONE_LEFT", "ADD_ZERO_RIGHT"],
        primitive_expansion_digest="5" * 64,
        pre_action_surface_digest="6" * 64,
        post_action_surface_digest="7" * 64,
        output_macro_action_digest="8" * 64,
        output_state_digest="9" * 64,
        transition_model_digest="a" * 64,
        application_status="APPLIED",
        started_at="2026-09-12T10:00:00Z",
        completed_at="2026-09-12T10:00:01Z",
    )
    rcpt.validate()
    jsonschema.validate(rcpt.to_dict(), RECEIPT_SCHEMA)
    assert rcpt.authority == "NONE"


def test_applicator_on_applicable_state(top_mined_candidate):
    """CandidateApplicator applies macro action when candidate pattern matches."""
    pos = generate_held_out_positive_corpus()
    p0 = pos[0]
    env = RewriteSearchEnvironment(p0.problem_id, p0.problem_digest, p0.goal_expression)
    st = env.create_initial_state(p0.initial_expression)
    actions = env.actions(st)

    res = CandidateApplicator.apply(
        candidate=top_mined_candidate,
        state=st,
        primitive_actions=actions,
        environment=env,
        problem_digest=p0.problem_digest,
        experimental_unit_id=p0.problem_id,
    )

    assert res.status == "APPLIED"
    assert res.macro_action is not None
    assert any(a.action_id == res.macro_action.action_id for a in res.transformed_actions)
    res.receipt.validate()
    assert res.receipt.application_status == "APPLIED"
    assert res.receipt.output_state_digest is not None


def test_applicator_on_non_applicable_state(top_mined_candidate):
    """CandidateApplicator returns NOT_APPLICABLE and preserves actions when pattern does not match."""
    neg_probs = generate_held_out_negative_corpus()
    n0 = neg_probs[0]
    env = RewriteSearchEnvironment(n0.problem_id, n0.problem_digest, n0.goal_expression)
    st = env.create_initial_state(n0.initial_expression)
    actions = env.actions(st)

    res = CandidateApplicator.apply(
        candidate=top_mined_candidate,
        state=st,
        primitive_actions=actions,
        environment=env,
        problem_digest=n0.problem_digest,
        experimental_unit_id=n0.problem_id,
    )

    assert res.status == "NOT_APPLICABLE"
    assert res.macro_action is None
    assert [a.action_id for a in res.transformed_actions] == [a.action_id for a in actions]
    res.receipt.validate()
    assert res.receipt.application_status == "NOT_APPLICABLE"


def test_applicator_preserves_unrelated_actions(top_mined_candidate):
    """CandidateApplicator replaces only the redundant primitive entry point, preserving unrelated actions."""
    pos = generate_held_out_positive_corpus()
    p0 = pos[0]
    env = RewriteSearchEnvironment(p0.problem_id, p0.problem_digest, p0.goal_expression)
    st = env.create_initial_state(p0.initial_expression)
    actions = env.actions(st)

    res = CandidateApplicator.apply(
        candidate=top_mined_candidate,
        state=st,
        primitive_actions=actions,
        environment=env,
        problem_digest=p0.problem_digest,
        experimental_unit_id=p0.problem_id,
    )

    # The action count must match
    assert len(res.transformed_actions) == len(actions)
    # Exactly one macro action was inserted
    macro_actions = [a for a in res.transformed_actions if a.operation.startswith("MACRO_")]
    assert len(macro_actions) == 1
    # All remaining actions are preserved from the original primitive actions
    non_macro_actions = [a for a in res.transformed_actions if not a.operation.startswith("MACRO_")]
    assert len(non_macro_actions) == len(actions) - 1
    orig_action_ids = {a.action_id for a in actions}
    for a in non_macro_actions:
        assert a.action_id in orig_action_ids


def test_caller_cannot_set_applied_directly():
    """Caller attempting to pass candidate_application_status='APPLIED' is strictly rejected."""
    executor = SearchExecutor()
    prob = ProblemDefinition(problem_id="prob-1", formal_syntax="x", context={}, goals=["solve"], assumptions=[], problem_digest="0" * 64)
    st = SearchState(state_id="s1", goal="g", depth=0)
    with pytest.raises(AuthorityViolationError) as excinfo:
        executor.execute(
            policy=DeterministicFrontierSearch(),
            problem=prob,
            initial_state=st,
            budget={"max_nodes": 10},
            candidate_application_status="APPLIED",
        )
    assert "CALLER_CANNOT_SET_APPLIED" in str(excinfo.value)


def test_candidate_id_alone_cannot_establish_application():
    """Supplying candidate_id without CandidateApplicator execution leaves status REQUESTED_NOT_APPLIED."""
    executor = SearchExecutor()
    prob = ProblemDefinition(problem_id="prob-1", formal_syntax="x", context={}, goals=["solve"], assumptions=[], problem_digest="0" * 64)
    st = SearchState(state_id="s1", goal="g", depth=0)
    bundle = executor.execute(
        policy=DeterministicFrontierSearch(),
        problem=prob,
        initial_state=st,
        budget={"max_nodes": 10},
        candidate_id="some_candidate_id",
        candidate_enabled=True,
    )
    assert bundle.receipt.candidate_application_status == "REQUESTED_NOT_APPLIED"
    assert bundle.receipt.candidate_application_receipt_refs == []


def test_candidate_artifact_digest_mismatch_rejected():
    """Tampered candidate_artifact_digest in CandidateApplicationReceipt is rejected."""
    rcpt = CandidateApplicationReceipt(
        application_id="app-test-01",
        candidate_id="cand-01",
        candidate_artifact_digest="0" * 64,
        candidate_kind="TACTIC_MACRO",
        applicator_id="msk-candidate-applicator-v0.1",
        applicator_version="0.1.0",
        applicator_implementation_digest="1" * 64,
        experimental_unit_id="unit-01",
        problem_digest="2" * 64,
        input_state_digest="3" * 64,
        candidate_pattern_digest="4" * 64,
        substitution_witness={},
        primitive_expansion=["MUL_ONE_LEFT", "ADD_ZERO_RIGHT"],
        primitive_expansion_digest="5" * 64,
        pre_action_surface_digest="6" * 64,
        post_action_surface_digest="7" * 64,
        output_macro_action_digest="8" * 64,
        output_state_digest="9" * 64,
        transition_model_digest="a" * 64,
        application_status="APPLIED",
        started_at="2026-09-12T10:00:00Z",
        completed_at="2026-09-12T10:00:01Z",
    )
    # Tamper with candidate_artifact_digest without recomputing receipt_digest
    object.__setattr__(rcpt, "candidate_artifact_digest", "f" * 64)
    with pytest.raises(ReceiptValidationError) as excinfo:
        rcpt.validate()
    assert "RECEIPT_DIGEST_MISMATCH" in str(excinfo.value)


def test_negative_control_selectivity_exact_parity(top_mined_candidate):
    """Negative controls maintain 100% exact parity in nodes expanded, evaluated, and branches between baseline and abstracted arms."""
    neg_probs = generate_held_out_negative_corpus()
    executor = SearchExecutor()
    policy = DeterministicFrontierSearch()

    for p in neg_probs:
        env = RewriteSearchEnvironment(p.problem_id, p.problem_digest, p.goal_expression)
        st = env.create_initial_state(p.initial_expression)
        prob_def = ProblemDefinition(
            problem_id=p.problem_id,
            formal_syntax=str(p.initial_expression),
            context={},
            goals=["solve"],
            assumptions=[],
            problem_digest=p.problem_digest,
        )

        base_bundle = executor.execute(
            policy=policy,
            problem=prob_def,
            initial_state=st,
            budget={"max_nodes": 50, "max_depth": 20},
            candidate_enabled=False,
            environment=env,
        )

        abs_bundle = executor.execute(
            policy=policy,
            problem=prob_def,
            initial_state=st,
            budget={"max_nodes": 50, "max_depth": 20},
            candidate=top_mined_candidate,
            candidate_id=top_mined_candidate.candidate_id,
            candidate_enabled=True,
            environment=env,
        )

        assert base_bundle.receipt.candidate_application_status == "DISABLED"
        assert abs_bundle.receipt.candidate_application_status == "REQUESTED_NOT_APPLIED"
        assert base_bundle.receipt.nodes_expanded == abs_bundle.receipt.nodes_expanded
        assert base_bundle.receipt.nodes_evaluated == abs_bundle.receipt.nodes_evaluated
        assert base_bundle.receipt.branch_count == abs_bundle.receipt.branch_count
        assert base_bundle.receipt.terminal_status == abs_bundle.receipt.terminal_status
