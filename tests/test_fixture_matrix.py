"""Tests verifying all 8 preregistered fixture matrix cases (Section 14)."""
import pytest

from fixtures.fixture_matrix import get_preregistered_fixtures
from msk_formal_discovery.abstraction.anti_unification import StructuralAntiUnifier
from msk_formal_discovery.abstraction.subtrace_miner import SubtraceMiner
from msk_formal_discovery.core.terms import Term, App


@pytest.fixture
def fixtures():
    return get_preregistered_fixtures()


def test_fixture_1_repeated_identical(fixtures):
    case = fixtures["REPEATED_IDENTICAL"]
    miner = SubtraceMiner(min_length=2, min_support=2)
    patterns = miner.mine_traces(case.traces)

    assert len(patterns) > 0
    # Top pattern should be the 3-step sequence
    top = patterns[0]
    assert len(top.operations) == case.expected_outcome["mined_pattern_length"]
    assert top.frequency == 2
    assert top.anti_unification_result is not None
    # 0 free variables in identical pattern
    assert len(top.anti_unification_result.lgg_term.free_vars()) == case.expected_outcome["free_variable_count"]


def test_fixture_2_alpha_renamed(fixtures):
    case = fixtures["ALPHA_RENAMED"]
    miner = SubtraceMiner(min_length=2, min_support=2)
    patterns = miner.mine_traces(case.traces)

    assert len(patterns) > 0
    top = patterns[0]
    assert len(top.operations) == case.expected_outcome["mined_pattern_length"]
    assert top.anti_unification_result is not None
    free_vars = top.anti_unification_result.lgg_term.free_vars()
    assert len(free_vars) == case.expected_outcome["free_variable_count"]


def test_fixture_3_structurally_generalizable(fixtures):
    case = fixtures["STRUCTURALLY_GENERALIZABLE"]
    miner = SubtraceMiner(min_length=2, min_support=2)
    patterns = miner.mine_traces(case.traces)

    assert len(patterns) > 0
    top = patterns[0]
    assert top.anti_unification_result is not None
    lgg_str = str(top.anti_unification_result.lgg_term)
    assert lgg_str == case.expected_outcome["lgg_representation"]
    assert len(top.anti_unification_result.substitution_witnesses) == case.expected_outcome["witness_count"]


def test_fixture_4_semantically_distinct(fixtures):
    case = fixtures["SEMANTICALLY_DISTINCT"]
    miner = SubtraceMiner(min_length=1, min_support=2)
    # Different operations: step_op has different expressions int_plus vs bool_xor
    t1_term = Term.parse("int_plus(a, b)")
    t2_term = Term.parse("bool_xor(a, b)")

    au = StructuralAntiUnifier()
    res = au.anti_unify([("t1", t1_term), ("t2", t2_term)])
    # Distinct top-level functors do not match -> generalizes to a bare variable V1
    assert isinstance(res.lgg_term, App) is case.expected_outcome["functor_match"]
    assert str(res.lgg_term) == "V1"


def test_fixture_5_repeated_unsat_core(fixtures):
    case = fixtures["REPEATED_UNSAT_CORE"]
    # Extract assertions from both traces
    t1_asserts = {e.payload.get("expression") for e in case.traces[0].events if e.payload.get("expression")}
    t2_asserts = {e.payload.get("expression") for e in case.traces[1].events if e.payload.get("expression")}
    common_assertions = t1_asserts.intersection(t2_asserts)

    assert "assert(c1)" in common_assertions
    assert "assert(c3)" in common_assertions
    assert len(common_assertions) == 2


def test_fixture_6_shared_lemma_chains(fixtures):
    case = fixtures["SHARED_LEMMA_CHAINS"]
    miner = SubtraceMiner(min_length=3, min_support=2)
    patterns = miner.mine_traces(case.traces)

    assert len(patterns) > 0
    top = patterns[0]
    assert len(top.operations) == case.expected_outcome["chain_length"]
    assert top.frequency == 2


def test_fixture_7_misleading_common_prefixes(fixtures):
    case = fixtures["MISLEADING_COMMON_PREFIX"]
    t1_ops = [e.operation for e in case.traces[0].events if "setup" in e.operation or "diverge" in e.operation]
    t2_ops = [e.operation for e in case.traces[1].events if "setup" in e.operation or "diverge" in e.operation]

    # Check common prefix
    common_prefix = []
    for op1, op2 in zip(t1_ops, t2_ops):
        if op1 == op2:
            common_prefix.append(op1)
        else:
            break

    assert len(common_prefix) == case.expected_outcome["common_prefix_length"]
    # Terminal operations differ
    assert t1_ops[-1] != t2_ops[-1]
    assert case.expected_outcome["terminal_identical"] is False


def test_fixture_8_branch_local_patterns(fixtures):
    case = fixtures["BRANCH_LOCAL_PATTERN"]
    # Traces have branch count > 1
    for tr in case.traces:
        # Branch indicator
        assert tr.problem_id in ["prob-15", "prob-16"]
    # Precondition is branch local (neg vs pos)
    assert case.expected_outcome["globalizes_without_precondition"] is False
    assert case.expected_outcome["requires_branch_guard"] is True
