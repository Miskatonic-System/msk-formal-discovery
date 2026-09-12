"""Tests for term AST, structural anti-unification kernel, and candidate generation."""
from pathlib import Path
import json
import pytest
import jsonschema

from msk_formal_discovery.abstraction.anti_unification import (
    StructuralAntiUnifier,
    AntiUnificationResult,
)
from msk_formal_discovery.abstraction.candidate import (
    AbstractionCandidate,
    AbstractionKind,
    CandidateStatus,
)
from msk_formal_discovery.core.exceptions import AntiUnificationError
from msk_formal_discovery.core.terms import App, Const, Term, Var
from msk_formal_discovery.refactoring.proposal import (
    RefactoringKind,
    RefactoringProposalGenerator,
)


SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"
CANDIDATE_SCHEMA_PATH = SCHEMAS_DIR / "abstraction-candidate.v0.1.schema.json"
REFACTORING_SCHEMA_PATH = SCHEMAS_DIR / "refactoring-proposal.v0.1.schema.json"


@pytest.fixture
def candidate_schema():
    with open(CANDIDATE_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def refactoring_schema():
    with open(REFACTORING_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_term_parsing():
    t1 = Term.parse("c")
    assert isinstance(t1, Const)
    assert t1.name == "c"

    t2 = Term.parse("?x")
    assert isinstance(t2, Var)
    assert t2.name == "x"

    t3 = Term.parse("f(a, g(x))")
    assert isinstance(t3, App)
    assert t3.fn == "f"
    assert len(t3.args) == 2
    assert isinstance(t3.args[0], Const)
    assert t3.args[0].name == "a"
    assert isinstance(t3.args[1], App)
    assert t3.args[1].fn == "g"


def test_anti_unification_identical_terms():
    au = StructuralAntiUnifier()
    t1 = Term.parse("f(a, b)")
    t2 = Term.parse("f(a, b)")

    res = au.anti_unify([("tr1", t1), ("tr2", t2)])
    assert str(res.lgg_term) == "f(a, b)"
    assert res.substitution_witnesses["tr1"] == {}
    assert res.substitution_witnesses["tr2"] == {}
    assert res.verify_reconstruction({"tr1": t1, "tr2": t2}) is True


def test_anti_unification_distinct_leaves():
    au = StructuralAntiUnifier()
    t1 = Term.parse("f(a)")
    t2 = Term.parse("f(b)")

    res = au.anti_unify([("tr1", t1), ("tr2", t2)])
    assert str(res.lgg_term) == "f(V1)"
    assert str(res.substitution_witnesses["tr1"]["V1"]) == "a"
    assert str(res.substitution_witnesses["tr2"]["V1"]) == "b"
    assert res.verify_reconstruction({"tr1": t1, "tr2": t2}) is True


def test_anti_unification_nonlinear_variable_sharing():
    """Identical difference pairs (a, b) map to identical generalized variable."""
    au = StructuralAntiUnifier()
    t1 = Term.parse("f(a, a)")
    t2 = Term.parse("f(b, b)")

    res = au.anti_unify([("tr1", t1), ("tr2", t2)])
    assert str(res.lgg_term) == "f(V1, V1)"
    assert len(res.substitution_witnesses["tr1"]) == 1
    assert res.verify_reconstruction({"tr1": t1, "tr2": t2}) is True


def test_anti_unification_complex_nested():
    au = StructuralAntiUnifier()
    t1 = Term.parse("f(a, g(x))")
    t2 = Term.parse("f(b, g(y))")

    res = au.anti_unify([("tr1", t1), ("tr2", t2)])
    assert str(res.lgg_term) == "f(V1, g(V2))"
    assert str(res.substitution_witnesses["tr1"]["V1"]) == "a"
    assert str(res.substitution_witnesses["tr1"]["V2"]) == "x"
    assert str(res.substitution_witnesses["tr2"]["V1"]) == "b"
    assert str(res.substitution_witnesses["tr2"]["V2"]) == "y"
    assert res.verify_reconstruction({"tr1": t1, "tr2": t2}) is True


def test_anti_unification_insufficient_terms():
    au = StructuralAntiUnifier()
    with pytest.raises(AntiUnificationError):
        au.anti_unify([("tr1", Term.parse("f(a)"))])


def test_abstraction_candidate_schema_conformance(candidate_schema):
    au = StructuralAntiUnifier()
    t1 = Term.parse("f(a, g(x))")
    t2 = Term.parse("f(b, g(y))")
    res = au.anti_unify([("tr1", t1), ("tr2", t2)])

    candidate = AbstractionCandidate(
        candidate_id="cand-001",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={
            "name": "helper_f_g",
            "statement": "forall V1 V2, f(V1, g(V2))",
            "canonical_representation": "f(V1, g(V2))",
        },
        anti_unification_evidence=res,
        discovery_set_trace_ids=["tr1", "tr2"],
        qualification_trace_ids=["tr3", "tr4"],
        status=CandidateStatus.PROPOSED,
        blueprint_family="MICRO_LEMMA",
    )

    data = candidate.to_dict()
    assert candidate.authority == "NONE"
    jsonschema.validate(instance=data, schema=candidate_schema)


def test_refactoring_proposal_generation_and_schema_conformance(refactoring_schema):
    au = StructuralAntiUnifier()
    t1 = Term.parse("f(a, g(x))")
    t2 = Term.parse("f(b, g(y))")
    res = au.anti_unify([("tr1", t1), ("tr2", t2)])

    candidate = AbstractionCandidate(
        candidate_id="cand-001",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={
            "name": "helper_f_g",
            "statement": "forall V1 V2, f(V1, g(V2))",
            "canonical_representation": "f(V1, g(V2))",
        },
        anti_unification_evidence=res,
        discovery_set_trace_ids=["tr1", "tr2"],
        qualification_trace_ids=["tr3", "tr4"],
        status=CandidateStatus.QUALIFIED_HELD_OUT,
        held_out_evaluation={"structural_compression_ratio": 1.4},
    )

    proposal = RefactoringProposalGenerator.generate(
        candidate=candidate,
        refactoring_kind=RefactoringKind.EXTRACTED_HELPER_LEMMA,
    )
    assert proposal.canonical_library_mutated is False
    assert proposal.authority == "NONE"

    data = proposal.to_dict()
    jsonschema.validate(instance=data, schema=refactoring_schema)
    proposal.validate(REFACTORING_SCHEMA_PATH)
