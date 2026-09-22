"""Tests for WO-FORMAL-TOPOLOGICAL-GALOIS-SOURCE-REPRESENTATION-01A."""
from __future__ import annotations

import copy
import json
from fractions import Fraction

import pytest

from msk_formal_discovery.topological_galois import braid_source as bs
from msk_formal_discovery.topological_galois import qualification as q
from msk_formal_discovery.topological_galois.freegroup import Endo, gen, inverse, mul, parse, reduce_word, word_str

DEGREES = (3, 4, 5, 6)


@pytest.fixture(scope="module")
def pkg():
    return q.load_artifacts()


# --- free group ------------------------------------------------------------------------------------------------
def test_free_reduction_and_inverse():
    w = mul(gen(1), gen(2), inverse(gen(2)), gen(3))
    assert w == ((1, 1), (3, 1))
    assert mul(w, inverse(w)) == ()
    assert parse(word_str(w)) == w
    assert reduce_word([(1, 1), (1, -1)]) == ()


# --- S1 --------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("n", DEGREES)
def test_s1_certificate_passes_and_is_surjective(n):
    c = bs.s1_certificate(n)
    assert c["result"] == "PASS"
    assert c["surjective"] and c["image_size"] == c["expected_size_n_factorial"]
    assert all(c["sigma_i_squared_maps_to_identity"].values())


def test_s1_composition_is_left_to_right_matching_juxtaposition():
    # sigma_1 sigma_2 in B_3: strand at position 1 goes to 2 under sigma_1, then to 3 under sigma_2
    assert bs.perm_of_word(3, bs.bmul(bs.sigma(1), bs.sigma(2))) == (3, 1, 2)


def test_permutation_quotient_is_not_faithful_witness():
    w = bs.permutation_quotient_kernel_witness(3)
    assert w["pi_perm_image_is_identity"] and not w["artin_image_is_identity"]


# --- S2 --------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("n", DEGREES)
def test_s2_certificate_passes(n):
    c = bs.s2_certificate(n)
    assert c["result"] == "PASS"
    assert c["left_action_verified_on_probe"] and not c["right_action_law_holds_on_probe"]
    assert all(c["product_word_invariant"].values()) and not all(c["reversed_product_word_invariant"].values())


def test_frozen_artin_generator_matches_birman_brendle_eq20():
    a = bs.artin_generator(3, 1, 1).to_json()
    assert a == {"x1": "x2", "x2": "x2^-1 x1 x2", "x3": "x3"}
    inv = bs.artin_generator(3, 1, -1).to_json()
    assert inv == {"x1": "x1 x2 x1^-1", "x2": "x1", "x3": "x3"}


def test_artin_action_is_a_homomorphism_from_juxtaposition():
    X, Y = bs.sigma(1), bs.sigma(2)
    assert bs.artin_of_word(3, bs.bmul(X, Y)) == bs.artin_of_word(3, X).compose(bs.artin_of_word(3, Y))
    assert bs.artin_of_word(3, bs.bmul(X, Y)) != bs.artin_of_word(3, Y).compose(bs.artin_of_word(3, X))


# --- Hurwitz -----------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("label", ["n3_generic", "n4_involutions_00A", "n5_generic", "n6_generic"])
def test_hurwitz_certificate_passes(label):
    c = bs.hurwitz_certificate(label, bs.frozen_tuples()[label])
    assert c["result"] == "PASS"


def test_hurwitz_left_and_right_variants_differ_and_both_preserve_product():
    tup = bs.frozen_tuples()["n3_generic"]
    L = bs.hurwitz_left(3, bs.sigma(1), tup)
    R = bs.hurwitz_right(3, bs.sigma(1), tup)
    assert L != R
    prod = bs.rho_eval(tup, bs.boundary_word(3))
    assert bs.rho_eval(L, bs.boundary_word(3)) == prod == bs.rho_eval(R, bs.boundary_word(3))


# --- S3 / Burau -----------------------------------------------------------------------------------------------
@pytest.mark.parametrize("n", DEGREES)
def test_s3_certificate_passes(n):
    c = bs.s3_certificate(n)
    assert c["result"] == "PASS"
    assert c["unreduced_at_t=1_is_permutation_matrix_of_pi_perm"]


def test_reduced_burau_signs_are_the_pdf_signs_not_the_text_extraction():
    # n = 3, t symbolic replaced by t = -1: block [[1,-t,0],[0,-t,0],[0,-1,1]] truncated
    assert bs.burau_reduced(3, 1, -1) == bs.mat([[1, 0], [-1, 1]])
    assert bs.burau_reduced(3, 2, -1) == bs.mat([[1, 1], [0, 1]])
    # character consistency: tr(unreduced sigma_1 sigma_2) - 1 == tr(reduced sigma_1 sigma_2)
    U = bs.burau_of_word(3, bs.bmul(bs.sigma(1), bs.sigma(2)), -1, reduced=False)
    Rr = bs.burau_of_word(3, bs.bmul(bs.sigma(1), bs.sigma(2)), -1, reduced=True)
    assert bs.trace(U) - 1 == bs.trace(Rr)


def test_wrong_sign_transcription_is_not_a_subquotient():
    """The text-extracted block with +t in the (i-1,i) slot has the wrong character and is rejected by the same check."""
    def wrong(n, i, t):
        k = n - 1
        M = [[Fraction(int(r == c)) for c in range(k)] for r in range(k)]
        c = i - 1
        if c - 1 >= 0:
            M[c - 1][c] = Fraction(t)
        M[c][c] = Fraction(-t)
        if c + 1 < k:
            M[c + 1][c] = Fraction(-1)
        return tuple(tuple(r) for r in M)
    W = bs.burau_of_word_generic([wrong(3, 1, -1), wrong(3, 2, -1)], bs.bmul(bs.sigma(1), bs.sigma(2)))
    U = bs.burau_of_word(3, bs.bmul(bs.sigma(1), bs.sigma(2)), -1, reduced=False)
    assert bs.trace(U) - 1 != bs.trace(W)


@pytest.mark.parametrize("n,self_dual", [(3, True), (4, False), (5, True), (6, False)])
def test_00a_matrices_are_equivalent_for_odd_n_and_dual_for_even_n(n, self_dual):
    rel = bs.s3_certificate(n)["comparison_with_00A_S1_matrices"]["00A_vs_BB_reduced_t=-1"]
    assert rel["equivalent_to_dual_(inverse_transpose)"]["intertwiner"] is not None
    assert (rel["equivalent"]["intertwiner"] is not None) == self_dual


@pytest.mark.parametrize("n", (4, 6))
def test_even_n_alternating_form_exists_only_for_the_dual(n):
    f = bs.s3_certificate(n)["invariant_alternating_forms_t=-1"]
    assert f["BB_reduced"]["solution_space_dimension"] == 0
    assert f["BB_reduced_dual"]["solution_space_dimension"] == 1 and f["BB_reduced_dual"]["rank_of_solution"] == n - 2


# --- gate -----------------------------------------------------------------------------------------------------
def test_all_sixteen_hostile_claims_rejected_for_exactly_the_stated_reasons():
    res = q.hostile_results()
    hostile = [r for r in res if r["expected"]]
    assert len(hostile) == 16
    assert all(r["rejected_for_exactly_the_stated_reasons"] for r in res), [r["id"] for r in res if not r["rejected_for_exactly_the_stated_reasons"]]


def test_gate_keys_on_fields_not_on_names():
    ok = {"claim_type": "ARTIN_GENERATOR_ACTION", "n": 4, "i": 2, "labelled_as": "alpha(sigma_i)", "images": q.FROZEN_ARTIN_GENERATOR[4][2]}
    assert q.gate(ok) == set()
    bad = dict(ok, images=q.FROZEN_ARTIN_INVERSE[4][2])
    assert q.gate(bad) == {"ACTION_HANDEDNESS_REVERSED:images_equal_alpha(sigma_i^-1)"}


def test_gate_rejects_unknown_claim_types():
    assert q.gate({"claim_type": "SOMETHING_ELSE"}) == {"UNKNOWN_CLAIM_TYPE:SOMETHING_ELSE"}


def test_even_degree_theorem_authority_cannot_be_earned_in_this_wo():
    assert q.gate({"claim_type": "AUTHORITY_ASSIGNMENT", "n": 4, "authority": "EXTERNAL_THEOREM_SCOPED", "source": "src-tg-birman-brendle-2005"}) == {"AUTHORITY_NOT_EARNED:no_bound_even_degree_source"}
    assert q.gate({"claim_type": "AUTHORITY_ASSIGNMENT", "n": 4, "authority": "LOCAL_ALGEBRA_CONTROL_ONLY"}) == set()


# --- package --------------------------------------------------------------------------------------------------
def test_committed_package_validates():
    assert q.validate() == []


def test_disposition_and_minimal_package(pkg):
    r = pkg["qualification-result.v0.1.json"]
    assert r["disposition"] == "TOPOLOGICAL_GALOIS_SOURCE_REPRESENTATION_QUALIFIED"
    assert r["BURAU_ROLE"] == "CONTROL_ONLY"
    assert r["minimal_package"]["LOAD_BEARING"] == ["B_n -> S_n permutation quotient (S1)", "Artin/Hurwitz action of B_n on F_n (S2)"]
    assert all(p["result"] == "PASS" for p in r["positive_controls"]) and [p["id"] for p in r["positive_controls"]] == ["PC1", "PC2", "PC3", "PC4", "PC5", "PC6"]
    assert r["authority"]["DIFFERENTIAL_GALOIS_GROUP"] == "NOT_COMPUTED" and r["authority"]["HAMILTONIAN_BRIDGE"] == "NOT_EXECUTED"


def test_target_domain_counts_infinity_and_uses_E_minus_P_n(pkg):
    td = pkg["target-domain-derivation.v0.1.json"]
    assert td["result"] == "PASS"
    for n, v in td["degrees"].items():
        assert v["puncture_count"] == int(n) + 1 and v["pi_1"]["rank"] == int(n) and v["pi_1"]["rank_if_infinity_omitted"] == int(n) - 1
        assert "E - P_n" in v["singular_polynomial"] and v["algebraic_nve_verified"] and v["infinity_is_singular"]
    assert "B_n != F_n" in td["permanent"]


def test_gate0_pins_and_digests_recorded(pkg):
    g = pkg["source-representation-manifest.v0.1.json"]["gate0"]
    assert g["mathematics_main"] == "2337c7d744f176274997374a7d4057c7272f715d"
    assert g["candidate_freeze_digest"] == "889cc252226d801491a83bdd594e366fffc5a8bd1ef9379f5088bf9f65d78425"
    assert g["reconstruction_digest"] == "5dbaab30927ed76acc6cb5ca2e36761e0f624ed1ef57f932c041e7e6eb9cc0cb"


def test_convention_freeze_has_no_implicit_standard_convention(pkg):
    cf = pkg["convention-freeze.v0.1.json"]["conventions"]
    for name in ("braid_multiplication_order", "sigma_i_orientation", "free_group_generators_x_i", "left_vs_right_action", "function_composition_order",
                 "hurwitz_action_convention", "puncture_ordering", "loop_orientation", "B_n_to_S_n_quotient_convention", "reduced_vs_unreduced_burau",
                 "burau_specialization_value", "matrices_acting_on_rows_vs_columns", "conjugation_convention"):
        assert name in cf and cf[name]["source"] and "standard convention" not in cf[name]["value"].lower()


def test_source_ledger_custody(pkg):
    led = pkg["source-ledger.v0.1.json"]
    bb = next(s for s in led["sources"] if s["source_id"] == "src-tg-birman-brendle-2005")
    assert bb["status"] == "BOUND" and bb["content_digest"] == "a2e02e79beda1d087d12134780c99c4894a2628cc0f8f9a66940945cd9e6155c"
    consumed = led["consumed_ledgers"][0]
    assert consumed["blob"] == "4cafe426d4b23b82a93b74d7c946d97bb95c0b41"
    assert consumed["records_relied_on"]["src-hmc-morales-ruiz-1999"]["status"] == "IDENTIFIED"


def test_tampered_certificate_is_detected(tmp_path, pkg):
    import shutil
    shutil.copytree(q.EXPERIMENT_DIR, tmp_path / "x")
    p = tmp_path / "x" / "certificates" / "s2-artin-action.v0.1.json"
    d = json.loads(p.read_text())
    d["3"]["generator_action"]["sigma_1"]["x1"] = "x1"
    p.write_text(json.dumps(d))
    assert any("s2-artin-action" in e for e in q.validate(tmp_path / "x"))


def test_burau_role_downgrade_is_detected(tmp_path):
    import shutil
    shutil.copytree(q.EXPERIMENT_DIR, tmp_path / "x")
    p = tmp_path / "x" / "qualification-result.v0.1.json"
    d = json.loads(p.read_text())
    d["BURAU_ROLE"] = "LOAD_BEARING"
    p.write_text(json.dumps(d))
    errs = q.validate(tmp_path / "x")
    assert any("BURAU_ROLE" in e for e in errs)
