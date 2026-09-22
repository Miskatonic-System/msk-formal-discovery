"""Tests for WO-FORMAL-HAMILTONIAN-VARIATIONAL-BRIDGE-01C (replays from the committed package; no Maxima run)."""
from __future__ import annotations

import json
import shutil

import pytest
import sympy as sp

from msk_formal_discovery.topological_galois import bridge_01b_finalize as fin_b
from msk_formal_discovery.topological_galois import bridge_01c as c
from msk_formal_discovery.topological_galois import bridge_01c_finalize as fin
from msk_formal_discovery.topological_galois import bridge_experiment as bx
from msk_formal_discovery.topological_galois import bridge_validate as bv
from msk_formal_discovery.topological_galois import qualification as q01

BASE = c.EXPERIMENT_DIR


@pytest.fixture(scope="module")
def pkg():
    return fin.load(BASE)


@pytest.fixture(scope="module")
def preds():
    return bv.load(c.DIR_01A), fin_b.load(c.DIR_01B), q01.load_artifacts(c.DIR_TG)


# --- Phase A: controlled family ---------------------------------------------------------------------------------
def test_controlled_family_reproduces_canonical_n3_member():
    pc1 = c.pc1_n3_member_identity()
    assert pc1["pass"] and pc1["P_3"] == "q**3 - q - 1" and pc1["f_3"] == "-2*q**3 + 2*q" and pc1["E"] == "-1" and pc1["roots"] == ["-1", "0", "1"]
    assert all(pc1["lane_equations_identical_to_bx_target_equation"].values())


@pytest.mark.parametrize("n", c.DEGREES)
def test_controlled_family_checks(n):
    fam = c.controlled_family(n)
    assert fam["all_checks_pass"]
    roots = [sp.Rational(r) for r in fam["roots_ordered"]]
    assert len(roots) == n and sum(roots) == 0 and all(roots[i + 1] - roots[i] == 1 for i in range(n - 1))
    assert sp.Poly(sp.sympify(fam["P_n"]), sp.Symbol("q")).degree() == n
    assert fam["equation_class"] == ("CANONICAL_N3_LAME_MEMBER" if n == 3 else f"ALGEBRAIC_NVE_{n}")


def test_target_equation_is_exact_rational_and_same_gauge():
    eq = c.target_equation_n(6, sp.Rational(1, 2), sp.Rational(3, 8))
    for s in (eq["original"]["c2"], eq["original"]["c1"], eq["original"]["c0"], eq["reduced"]["r"]):
        assert "." not in s
    assert eq["poles_of_r"] == c.controlled_family(6)["roots_ordered"]


# --- Phase B/C: signatures, lanes, anchors -----------------------------------------------------------------------
def test_degree_ladder_labels_are_mechanically_corroborated():
    props = {n: c.degree_ladder_properties(n) for n in c.DEGREES}
    assert props[3]["S_n_solvable"] and props[4]["S_n_solvable"] and not props[5]["S_n_solvable"] and not props[6]["S_n_solvable"]
    assert props[5]["A_n_perfect"] and props[6]["A_n_perfect"] and props[6]["Out_S_n_exceptional"] and not props[5]["Out_S_n_exceptional"]
    assert "not load-bearing" in props[6]["label"]


def test_coupling_signature_fixed_across_degrees_and_background_signature_varies(pkg, preds):
    pre = pkg["preregistration.v0.1.json"]
    for lane in pre["lanes"]:
        sigs = {x["coupling_signature"] for x in pre["cells"] if x["lane"] == lane["lane"]}
        assert sigs == {lane["coupling_signature"]} == {c.coupling_signature(lane["lambda"], lane["mu"])}
    assert len({v["BACKGROUND_SIGNATURE"] for v in pre["background_signatures"].values()}) == 4
    assert c.coupling_signature("3/8", "0") != c.coupling_signature("3/8", "1/2")


def test_anchors_are_consumed_not_recomputed(pkg, preds):
    pkg_a, pkg_b, _ = preds
    for lane in c.LANES:
        a = pkg["preregistration.v0.1.json"]["anchors"][lane["lane"]]
        assert a == c.consume_anchor(lane, pkg_a, pkg_b) and a["origin"] == "CONSUMED_CANONICAL" and a["ABELIAN_IDENTITY_COMPONENT"] == lane["accepted_n3_predicate"]
    seq = {L: pkg["preregistration.v0.1.json"]["anchors"][L]["ABELIAN_IDENTITY_COMPONENT"] for L in "ABCD"}
    assert seq == {"A": "TRUE", "B": "FALSE", "C": "TRUE", "D": "FALSE"}


def test_preregistration_replays(pkg, preds):
    pre = pkg["preregistration.v0.1.json"]
    assert bx.canonical_digest(c.preregistration(*preds)) == bx.canonical_digest(pre)
    assert pre["new_cell_count"] == 12 and pre["panel_size"] == 16 and pre["expectations"]["target_predicate_expectations"] == "NONE_RECORDED"
    assert all(x["equation_class"] == f"ALGEBRAIC_NVE_{x['n']}" for x in pre["cells"])


# --- adjudication logic on synthetic sequences ------------------------------------------------------------------
def _fake_cells(pre, values):
    return [{"cell": f"n{n}_{L}", "ABELIAN_IDENTITY_COMPONENT": values[(n, L)]} for n in c.NEW_DEGREES for L in "ABCD"]


def test_adjudication_split_partial_and_no_effect(pkg):
    pre = pkg["preregistration.v0.1.json"]
    vals = {(n, L): {"A": "TRUE", "B": "FALSE", "C": "TRUE", "D": "FALSE"}[L] for n in c.NEW_DEGREES for L in "ABCD"}
    vals[(5, "A")] = "FALSE"; vals[(4, "C")] = "UNRESOLVED"
    adj = c.adjudicate(pre, _fake_cells(pre, vals))
    assert adj["verdict"] == "BO3_DEGREE_CONDITIONED_VARIATION_OBSERVED" and adj["lanes_with_split"] == ["A"] and adj["lanes_partial"] == ["C"]
    A = adj["lanes"]["A"]
    assert A["transitions"] == {"3->4": "NO_CHANGE", "4->5": "CHANGES", "5->6": "CHANGES"} and A["falsifiers"]["F1"] == c.FALSIFIER_TEXT["F1"]
    assert A["falsifiers"]["F2"].startswith("NOT_TRIGGERED") and A["witness"]["FALSE"]["cell"] == "n5_A"
    B = adj["lanes"]["B"]
    assert B["lane_result"] == "NO_DEGREE_EFFECT_OBSERVED_ON_FROZEN_LANE" and B["falsifiers"]["F2"] == c.FALSIFIER_TEXT["F2"] and B["falsifiers"]["F3"] == c.FALSIFIER_TEXT["F3"]
    C = adj["lanes"]["C"]
    assert C["lane_result"] == "LANE_PARTIAL" and C["transitions"]["3->4"] == "UNRESOLVED" and C["falsifiers"]["F1"].startswith("NOT_ADJUDICABLE")
    assert all(e["causal_attribution"] == "NONE" for t in adj["transitions"].values() for e in t.values() if isinstance(e, dict))
    assert "caused" not in json.dumps(adj).lower() or "no causal" in json.dumps(adj).lower()
    vals = {(n, L): {"A": "TRUE", "B": "FALSE", "C": "TRUE", "D": "FALSE"}[L] for n in c.NEW_DEGREES for L in "ABCD"}
    assert c.adjudicate(pre, _fake_cells(pre, vals))["verdict"] == "BO3_NO_VARIATION_ON_FROZEN_COUPLINGS"
    vals[(6, "D")] = "UNRESOLVED"
    assert c.adjudicate(pre, _fake_cells(pre, vals))["verdict"] == "BO3_PARTIAL"


# --- committed package --------------------------------------------------------------------------------------------
def test_committed_package_validates():
    assert fin.validate(BASE) == []


def test_every_cell_rule_admissible_and_false_needs_case4(pkg):
    for r in pkg["cell-results.v0.1.json"]["cells"]:
        assert r["ABELIAN_IDENTITY_COMPONENT"] in ("TRUE", "FALSE", "UNRESOLVED")
        if r["ABELIAN_IDENTITY_COMPONENT"] in ("TRUE", "FALSE"):
            assert r["rule"].startswith(fin.ALLOWED)
        if r["ABELIAN_IDENTITY_COMPONENT"] == "FALSE":
            assert r["provider_verdict_original_form"] == r["provider_verdict_reduced_form"] == "NO_LIOUVILLIAN_SOLUTION"
        assert r["equation_class"] == f"ALGEBRAIC_NVE_{r['n']}"


def test_result_matches_adjudication_and_firewalls(pkg):
    res, adj = pkg["result.v0.1.json"], pkg["adjudication.v0.1.json"]
    assert res["disposition"] == adj["verdict"] and res["panel"] == {L: adj["lanes"][L]["TARGET_SEQUENCE"] for L in "ABCD"}
    assert res["BO2"] == "CANONICALLY_REFUTED_NOT_REOPENED" and res["BO3"] == "EXECUTED_BOUNDEDLY_IN_01C" and res["BO1"] == "NOT_EXECUTED"
    assert res["MORALES_RAMIS"] == "NOT_APPLIED" and res["LAME"] == "N3_ONLY" and res["COUPLING_PAIR_UNIVERSALLY_SUFFICIENT"] is None and res["DEGREE_IRRELEVANT"] is None
    for L in "ABCD":
        assert res["panel"][L]["3"] == pkg["preregistration.v0.1.json"]["anchors"][L]["ABELIAN_IDENTITY_COMPONENT"]
        lane = adj["lanes"][L]
        assert lane["COUPLING_PAIR_ALONE_INSUFFICIENT_ACROSS_DEGREE_LADDER"] == (set(lane["TARGET_SEQUENCE"].values()) >= {"TRUE", "FALSE"})


def test_all_hostile_controls_rejected(pkg, tmp_path):
    results = fin.run_hostile(BASE, tmp_path)
    assert len(results) == 22 and all(r["rejected"] for r in results), [r["id"] for r in results if not r["rejected"]]
    assert pkg["hostile-controls.v0.1.json"]["all_rejected"] and pkg["hostile-controls.v0.1.json"]["count"] == 22


def test_memoization_does_not_bypass_script_binding(tmp_path):
    dst = tmp_path / "pkg"
    shutil.copytree(BASE, dst)
    p = dst / "cells" / "n6_B_red.mac"
    p.write_text(p.read_text(encoding="utf-8").replace("'diff(y,x,2)=(", "'diff(y,x,2)=(1+", 1), encoding="utf-8")
    errs = fin.validate(dst, check_git=False)
    assert any("input binding broken" in e for e in errs) and any("digest (red) differs" in e for e in errs)
