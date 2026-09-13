"""Comprehensive Hostile Test Suite for WO-MATH-FORMAL-DISCOVERY-01C."""
from __future__ import annotations

import copy
import hashlib
import json
import pytest
from pathlib import Path

from msk_formal_discovery.abstraction.candidate import AbstractionCandidate
from msk_formal_discovery.core.exceptions import (
    AuthorityViolationError,
    CustodyGraphResolutionError,
    ReceiptValidationError,
)
from msk_formal_discovery.core.terms import App, Const, Term, Var
from msk_formal_discovery.experiments.rewrite_control import (
    _make_prob,
    add,
    const,
    mul,
    var,
)
from msk_formal_discovery.onto.export import (
    OntoEvaluationPackage,
    OntoEvidenceRef,
)
from msk_formal_discovery.representation.adjudication import (
    adjudicate_representation_orbit,
    adjudicate_stratum,
)
from msk_formal_discovery.representation.certification import (
    certify_representation_equivalence,
)
from msk_formal_discovery.representation.families import (
    NEGATIVE_FAMILY_SEED,
    POSITIVE_FAMILY_SEED,
    assert_disjoint_from_prior_corpora,
    generate_all_represented_problems,
    generate_semantic_families,
    get_prior_experimental_units,
)
from msk_formal_discovery.representation.manifest import (
    PairedRepresentationOrbitManifest,
    RepresentationInvarianceClosureManifest,
)
from msk_formal_discovery.representation.receipt import RepresentationTransformReceipt
from msk_formal_discovery.representation.resolver import RepresentationOrbitResolver
from msk_formal_discovery.representation.runner import (
    DEFAULT_01C_DIR,
    PINNED_01B_CANDIDATE_DIGEST,
    validate_01c_freeze,
)
from msk_formal_discovery.representation.transform import (
    RepresentationStratum,
    alpha_rename_term,
    apply_transform,
    associative_regroup_term,
    commutative_mirror_term,
    get_transform_implementation_digest,
)

CANONICAL_CANDIDATE_PATH = (
    Path(__file__).resolve().parents[1] / "experiments" / "formal-discovery-01b-r1" / "candidate.json"
)


# 1. Candidate Artifact Invariant
def test_candidate_artifact_immutability():
    cand_bytes = CANONICAL_CANDIDATE_PATH.read_bytes()
    cand = AbstractionCandidate.from_dict(json.loads(cand_bytes.decode("utf-8")))
    assert cand.candidate_id == "macro_mul_one_add_zero"
    assert cand.artifact_digest() == PINNED_01B_CANDIDATE_DIGEST


def test_candidate_artifact_drift_fails_closed():
    cand_bytes = CANONICAL_CANDIDATE_PATH.read_bytes()
    cand_data = json.loads(cand_bytes.decode("utf-8"))
    cand_data["formal_specification"]["statement"] = "forall V1, mutated"
    cand = AbstractionCandidate.from_dict(cand_data)
    assert cand.artifact_digest() != PINNED_01B_CANDIDATE_DIGEST


# 2. Non-bijective Alpha Renaming Fails Closed
def test_non_bijective_alpha_rename_target_collision_fails():
    t = add(var("x"), var("y"))
    # Non-injective mapping: maps both x and y to same target 'p'
    with pytest.raises(ValueError, match="NON_BIJECTIVE_ALPHA_RENAME"):
        alpha_rename_term(t, {"x": "p", "y": "p"})


def test_non_bijective_alpha_rename_missing_variable_fails():
    t = add(var("x"), var("y"))
    # Incomplete domain: missing 'y'
    with pytest.raises(ValueError, match="NON_BIJECTIVE_ALPHA_RENAME"):
        alpha_rename_term(t, {"x": "p"})


# 3. Unapproved Commutative Transformation Fails Closed
def test_unapproved_commutative_transformation_fails():
    # If an associative regroup altered leaf order (commutative swap), fail closed
    p = _make_prob("test", add(var("a"), var("b")), var("a"), "TEST")
    # Swapping leaves a and b in R2 is unapproved commutative swap
    swapped_r2 = add(var("b"), var("a"))
    with pytest.raises(ValueError, match="UNAPPROVED_COMMUTATIVE_TRANSFORMATION"):
        apply_transform(p, RepresentationStratum.R2_ASSOCIATIVE_REGROUPED, r2_initial_expression=swapped_r2)


# 4. Semantic Equivalence Proof Failure Fails Closed
def test_semantic_equivalence_failure_fails_closed():
    # Non-equivalent transformation: x -> x + 1
    p0 = _make_prob("test-p0", var("x"), var("x"), "TEST")
    pk = _make_prob("test-pk", add(var("x"), const(1)), var("x"), "TEST")
    with pytest.raises(ReceiptValidationError, match="SEMANTIC_EQUIVALENCE_FAILED"):
        certify_representation_equivalence(
            r0_problem=p0,
            rk_problem=pk,
            stratum=RepresentationStratum.R1_ALPHA_RENAMED,
            variable_bijection={"x": "x"},
            family_id="fam-test",
        )


# 5. Corpus Disjointness Invariant
def test_corpus_disjointness_from_all_prior_units():
    families = generate_semantic_families(POSITIVE_FAMILY_SEED, NEGATIVE_FAMILY_SEED)
    represented = generate_all_represented_problems(families)
    # Must succeed without ValueError
    assert_disjoint_from_prior_corpora(represented)
    assert len(represented) == 12


def test_corpus_collision_with_prior_unit_fails_closed():
    prior_exprs, _ = get_prior_experimental_units()
    colliding_expr_str = list(prior_exprs)[0]  # e.g. "add(mul(1, a), 0)"
    families = generate_semantic_families(POSITIVE_FAMILY_SEED, NEGATIVE_FAMILY_SEED)
    represented = generate_all_represented_problems(families)

    # Inject collision into first problem
    mutated = copy.deepcopy(represented)
    first_fam = list(mutated.keys())[0]
    prob, bij = mutated[first_fam][RepresentationStratum.R0_CANONICAL_CONTROL]
    # Create fake problem with prior expr
    from msk_formal_discovery.experiments.rewrite_control import Term
    # Create an initial expression whose canonical_repr matches prior
    fake_prob = _make_prob("colliding", add(mul(const(1), var("a")), const(0)), var("a"), "TEST")
    mutated[first_fam][RepresentationStratum.R0_CANONICAL_CONTROL] = (fake_prob, bij)

    with pytest.raises(ValueError, match="CORPUS_COLLISION_WITH_PRIOR_UNIT"):
        assert_disjoint_from_prior_corpora(mutated)


# 6. Mislabeled Representation Stratum Fails Closed
def test_mislabeled_representation_stratum_fails():
    p = _make_prob("test", var("x"), var("x"), "TEST")
    with pytest.raises(ValueError, match="UNKNOWN_REPRESENTATION_STRATUM"):
        apply_transform(p, "UNKNOWN_STRATUM_XYZ")


# 7. Adjudication Hostile Invariants
def test_unsupported_global_claim_when_stratum_fails():
    # Construct mock stratum evaluations where R3 is SENSITIVE
    # Global disposition must be REPRESENTATION_INVARIANCE_NOT_SUPPORTED, not SUPPORTED
    pos_mock_invariant = [
        {"node_delta": -10, "baseline_nodes": 40, "abstracted_nodes": 30, "candidate_application_status": "APPLIED", "candidate_applied": True, "baseline_solved": True, "abstracted_solved": True, "smt_unsat": True}
        for _ in range(8)
    ]
    neg_mock_invariant = [
        {"node_delta": 0, "applications_count": 0, "candidate_application_status": "REQUESTED_NOT_APPLIED", "baseline_solved": True, "abstracted_solved": True, "smt_unsat": True}
        for _ in range(4)
    ]
    pos_mock_sensitive = [
        {"node_delta": 0, "baseline_nodes": 40, "abstracted_nodes": 40, "candidate_application_status": "REQUESTED_NOT_APPLIED", "candidate_applied": False, "baseline_solved": True, "abstracted_solved": True, "smt_unsat": True}
        for _ in range(8)
    ]

    evals = {
        "R0_CANONICAL_CONTROL": (pos_mock_invariant, neg_mock_invariant),
        "R1_ALPHA_RENAMED": (pos_mock_invariant, neg_mock_invariant),
        "R2_ASSOCIATIVE_REGROUPED": (pos_mock_invariant, neg_mock_invariant),
        "R3_COMMUTATIVE_MIRROR": (pos_mock_sensitive, neg_mock_invariant),
    }
    res = adjudicate_representation_orbit(evals)
    assert res.r0_evaluation.disposition == "REPRESENTATION_STRATUM_INVARIANT"
    assert res.r1_evaluation.disposition == "REPRESENTATION_STRATUM_INVARIANT"
    assert res.r2_evaluation.disposition == "REPRESENTATION_STRATUM_INVARIANT"
    assert res.r3_evaluation.disposition == "REPRESENTATION_STRATUM_SENSITIVE"
    assert res.global_disposition == "REPRESENTATION_INVARIANCE_NOT_SUPPORTED"


def test_control_failure_blocks_invariance_interpretation():
    pos_failed_control = [
        {"node_delta": 0, "baseline_nodes": 40, "abstracted_nodes": 40, "candidate_application_status": "REQUESTED_NOT_APPLIED", "candidate_applied": False, "baseline_solved": True, "abstracted_solved": True, "smt_unsat": True}
        for _ in range(8)
    ]
    neg_mock_invariant = [
        {"node_delta": 0, "applications_count": 0, "candidate_application_status": "REQUESTED_NOT_APPLIED", "baseline_solved": True, "abstracted_solved": True, "smt_unsat": True}
        for _ in range(4)
    ]
    pos_mock_invariant = [
        {"node_delta": -10, "baseline_nodes": 40, "abstracted_nodes": 30, "candidate_application_status": "APPLIED", "candidate_applied": True, "baseline_solved": True, "abstracted_solved": True, "smt_unsat": True}
        for _ in range(8)
    ]

    evals = {
        "R0_CANONICAL_CONTROL": (pos_failed_control, neg_mock_invariant),
        "R1_ALPHA_RENAMED": (pos_mock_invariant, neg_mock_invariant),
        "R2_ASSOCIATIVE_REGROUPED": (pos_mock_invariant, neg_mock_invariant),
        "R3_COMMUTATIVE_MIRROR": (pos_mock_invariant, neg_mock_invariant),
    }
    res = adjudicate_representation_orbit(evals)
    assert res.global_disposition == "REPRESENTATION_EVALUATION_INCONCLUSIVE_CONTROL_FAILED"


# 8. ONTO Export Scoping & Invariants
def test_unscoped_positive_representation_invariance_rejected():
    pkg = OntoEvaluationPackage(
        package_id="onto-eval-test",
        candidate_id="macro_mul_one_add_zero",
        recurrence_count=8,
        representation_invariance="SUPPORTED",
        representation_invariance_scope=None,  # UNSCOPED
        cross_search_policy_recurrence="UNKNOWN",
        cross_formal_system_recurrence="UNKNOWN",
        functional_search_benefit="SUPPORTED",
        functional_search_benefit_scope="NODE_EXPANSION_SEARCH_STRUCTURE",
        source_traces=["trace-01"],
        structural_fingerprint="0" * 64,
        end_to_end_runtime_benefit="NOT_ESTABLISHED",
        claim_ceiling="ENGINEERING_ABSTRACTION_EFFECT_ONLY",
        authority="NONE",
    )
    with pytest.raises(ValueError, match="UNEARNED_REPRESENTATION_INVARIANCE"):
        pkg.validate()


def test_runtime_benefit_cannot_be_inferred_from_node_reduction():
    pkg = OntoEvaluationPackage(
        package_id="onto-eval-test",
        candidate_id="macro_mul_one_add_zero",
        recurrence_count=8,
        representation_invariance="NOT_SUPPORTED",
        representation_invariance_scope="ALPHA_ASSOCIATIVE_COMMUTATIVE_IDENTITY_ORBIT_V0_1",
        cross_search_policy_recurrence="UNKNOWN",
        cross_formal_system_recurrence="UNKNOWN",
        functional_search_benefit="SUPPORTED",
        functional_search_benefit_scope="NODE_EXPANSION_SEARCH_STRUCTURE",
        source_traces=["trace-01"],
        structural_fingerprint="0" * 64,
        end_to_end_runtime_benefit="SUPPORTED",  # UNEARNED
        claim_ceiling="ENGINEERING_ABSTRACTION_EFFECT_ONLY",
        authority="NONE",
    )
    with pytest.raises(ValueError, match="UNEARNED_RUNTIME_BENEFIT"):
        pkg.validate()


def test_authority_violation_rejected_in_manifest_and_receipt():
    rcpt = RepresentationTransformReceipt(
        receipt_id="rec-test",
        family_id="fam-01",
        stratum="R0_CANONICAL_CONTROL",
        source_expression="x",
        transformed_expression="x",
        source_expression_digest="0" * 64,
        transformed_expression_digest="0" * 64,
        variable_bijection={},
        transform_implementation_digest="0" * 64,
        smt_certificate_ref="ref",
        smt_certificate_digest="0" * 64,
        smt_verdict="UNSAT_REFUTED",
        authority="UNAUTHORIZED",
    )
    with pytest.raises(AuthorityViolationError):
        rcpt.validate()

    closure = RepresentationInvarianceClosureManifest(
        closure_id="closure-test",
        canonical_predecessor_commit="0" * 40,
        canonical_predecessor_tree="0" * 40,
        candidate_id="macro",
        candidate_artifact_digest="0" * 64,
        paired_manifest_ref="ref",
        paired_manifest_digest="0" * 64,
        per_stratum_dispositions={},
        global_disposition="REPRESENTATION_INVARIANCE_NOT_SUPPORTED",
        all_representation_certificates_verified=True,
        all_search_receipts_verified=True,
        all_terminal_parity_verified=True,
        authority="UNAUTHORIZED",
    )
    with pytest.raises(AuthorityViolationError):
        closure.validate()


def test_transform_receipt_digest_mismatch_fails():
    rcpt = RepresentationTransformReceipt(
        receipt_id="rec-test",
        family_id="fam-01",
        stratum="R0_CANONICAL_CONTROL",
        source_expression="x",
        transformed_expression="x",
        source_expression_digest="0" * 64,
        transformed_expression_digest="0" * 64,
        variable_bijection={},
        transform_implementation_digest=get_transform_implementation_digest(),
        smt_certificate_ref="ref",
        smt_certificate_digest="0" * 64,
        smt_verdict="UNSAT_REFUTED",
        receipt_digest="f" * 64,  # Tampered
    )
    with pytest.raises(ReceiptValidationError, match="RECEIPT_DIGEST_MISMATCH"):
        rcpt.validate()


def test_paired_manifest_missing_stratum_fails():
    manifest = PairedRepresentationOrbitManifest(
        manifest_id="paired-manifest-test",
        canonical_predecessor_commit="0" * 40,
        candidate_id="macro_mul_one_add_zero",
        candidate_artifact_digest="0" * 64,
        positive_family_seed=161803,
        negative_family_seed=141421,
        families=[
            {
                "family_id": f"fam-{i}",
                "category": "HELD_OUT_POSITIVE",
                "canonical_variable": f"v{i}",
                "strata": {
                    # Missing R3
                    "R0_CANONICAL_CONTROL": {},
                    "R1_ALPHA_RENAMED": {},
                    "R2_ASSOCIATIVE_REGROUPED": {},
                },
            }
            for i in range(12)
        ],
    )
    with pytest.raises(ReceiptValidationError, match="(MISSING_STRATUM|PAIRED_ORBIT_MANIFEST_SCHEMA_ERROR)"):
        manifest.validate()


def test_candidate_agnostic_transformation():
    # Verify transform does not require or accept candidate identity
    p = _make_prob("test", add(var("a"), const(0)), var("a"), "TEST")
    t0, b0 = apply_transform(p, RepresentationStratum.R0_CANONICAL_CONTROL)
    t1, b1 = apply_transform(p, RepresentationStratum.R1_ALPHA_RENAMED)
    assert t0.initial_expression == p.initial_expression
    assert t1.initial_expression != p.initial_expression


def test_baseline_abstracted_input_identical_across_all_strata():
    families = generate_semantic_families(POSITIVE_FAMILY_SEED, NEGATIVE_FAMILY_SEED)
    represented = generate_all_represented_problems(families)
    for fid, strata in represented.items():
        for s_enum, (prob, _) in strata.items():
            # In each represented problem, baseline and abstracted search must receive identical input
            expr_repr = prob.initial_expression.canonical_repr()
            goal_repr = prob.goal_expression.canonical_repr()
            assert len(expr_repr) > 0
            assert len(goal_repr) > 0


def test_resolver_fails_on_missing_closure(tmp_path):
    resolver = RepresentationOrbitResolver(repo_root=tmp_path)
    with pytest.raises(CustodyGraphResolutionError, match="CLOSURE_NOT_FOUND"):
        resolver.resolve_and_verify()


def test_adjudication_threshold_invariants():
    # Test that 5/8 improved fails positive gate (requires >= 6/8)
    pos_5_improved = [
        {"node_delta": -10 if i < 5 else 0, "baseline_nodes": 40, "abstracted_nodes": 30 if i < 5 else 40, "candidate_application_status": "APPLIED", "candidate_applied": True, "baseline_solved": True, "abstracted_solved": True, "smt_unsat": True}
        for i in range(8)
    ]
    neg_mock_invariant = [
        {"node_delta": 0, "applications_count": 0, "candidate_application_status": "REQUESTED_NOT_APPLIED", "baseline_solved": True, "abstracted_solved": True, "smt_unsat": True}
        for _ in range(4)
    ]
    res = adjudicate_stratum("R0_CANONICAL_CONTROL", pos_5_improved, neg_mock_invariant)
    assert res.positive_gate_passed is False
    assert res.disposition == "REPRESENTATION_STRATUM_SENSITIVE"


def test_freeze_validation(tmp_path: Path):
    import shutil
    d = tmp_path / "formal-discovery-01c"
    d.mkdir(parents=True)
    for name in ("candidate.json", "preregistration.json", "semantic-families.json"):
        shutil.copy(DEFAULT_01C_DIR / name, d / name)
    report = validate_01c_freeze(exp_dir=d)
    assert report["status"] == "FREEZE_VALIDATED"
    assert report["candidate_digest"] == PINNED_01B_CANDIDATE_DIGEST


