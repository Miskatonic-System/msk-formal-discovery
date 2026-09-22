"""Tests for WO-FORMAL-HAMILTONIAN-VARIATIONAL-BRIDGE-01B (replays from the committed package; no Maxima run)."""
from __future__ import annotations

import json
import shutil

import pytest
import sympy as sp

from msk_formal_discovery.topological_galois import bridge_01b as b
from msk_formal_discovery.topological_galois import bridge_01b_finalize as fin
from msk_formal_discovery.topological_galois import bridge_experiment as bx
from msk_formal_discovery.topological_galois import bridge_validate as bv

BASE = b.EXPERIMENT_DIR


@pytest.fixture(scope="module")
def pkg():
    return fin.load(BASE)


@pytest.fixture(scope="module")
def pkg_a():
    return bv.load(b.DIR_01A)


# --- Phase A ------------------------------------------------------------------------------------------------------
def test_lame_parameter_map_is_exact():
    m = b.lame_parameter_map()
    assert m["g2"] == "1" and m["g3"] == "0" and m["leading_coefficient_4"]
    assert m["converse_check_qprime_sq_equals_f_of_q_given_wp_relation"]
    assert m["transformed_nve"] == "xi'' = [2*lambda*wp(t) - mu] xi"
    assert m["parameter_map"] == {"ell(ell+1)": "2*lambda", "B": "-mu"}
    assert m["algebraic_form_identity"]["identity_holds"] and m["algebraic_form_identity"]["our_algebraic_nve_in_x_equals_lame_form_times"] == "1"
    assert m["e_i"] == ["-1/2", "0", "1/2"]


def test_ell_is_not_n():
    assert b.ell_of("1")["ell"] == "1" and b.ell_of("3")["ell"] == "2" and b.ell_of("3/8")["ell"] == "1/2"
    assert b.ell_of("2")["ell_kind"] == "REAL_NONHALFINTEGER" and b.ell_of("-1")["ell_kind"] == "COMPLEX"
    assert b.ell_of("6")["ell"] == "3"      # ell = 3 needs lambda = 6, never lambda = n


# --- preregistration and bindings ---------------------------------------------------------------------------------
def test_preregistration_replays_and_reuses_01a_signature(pkg, pkg_a):
    pre = pkg["preregistration.v0.1.json"]
    fresh = b.preregistration(pkg_a); fresh["phase_c"] = b.phase_c(pkg_a["cell-results.v0.1.json"]["cells"])
    assert bx.canonical_digest(fresh) == bx.canonical_digest(pre)
    assert pre["source_signature"]["SOURCE_SIGNATURE"] == pkg_a["preregistration.v0.1.json"]["source_signature"]["SOURCE_SIGNATURE"]
    assert pre["gate0"]["provider_identity"]["kovacicODE_sha256"] == pkg_a["provider-qualification.v0.1.json"]["implementation_sha256_recorded"]


def test_grid_design(pkg, pkg_a):
    g = pkg["preregistration.v0.1.json"]["grid"]
    hist = {c["lambda"]: c["ABELIAN_IDENTITY_COMPONENT"] for c in pkg_a["cell-results.v0.1.json"]["cells"]}
    lambdas = {c["lambda"] for c in g}
    assert any(hist[l] == "TRUE" for l in lambdas if l in hist) and any(hist[l] == "FALSE" for l in lambdas if l in hist)
    for l in lambdas:
        assert len([c for c in g if c["lambda"] == l]) >= 3
    assert 6 <= len(g) <= 12


def test_phase_c_historical_pattern(pkg):
    pc = pkg["preregistration.v0.1.json"]["phase_c"]
    assert all(v["predicate_constant_across_sampled_mu"] for v in pc["historical_01a_pattern_by_lambda"].values())
    assert pc["no_sufficiency_claim"] is True


# --- results ------------------------------------------------------------------------------------------------------
def test_every_cell_resolved_with_admissible_rule(pkg):
    for c in pkg["cell-results.v0.1.json"]["cells"]:
        assert c["ABELIAN_IDENTITY_COMPONENT"] in ("TRUE", "FALSE")
        assert c["rule"].startswith(fin.ALLOWED)


def test_lambda_alone_insufficient_witness(pkg):
    adj = pkg["adjudication.v0.1.json"]
    assert adj["verdict"] == "LAMBDA_ALONE_INSUFFICIENT"
    splits = adj["same_lambda_same_source_different_mu_different_predicate"]
    assert [s["lambda"] for s in splits] == ["3/8"]
    s = splits[0]
    assert s["ell"]["ell"] == "1/2" and s["TRUE"]["mu"] == "0" and s["FALSE"]["mu"] != "0"
    per = adj["per_lambda"]
    assert per["1"]["constant"] and per["2"]["constant"] and not per["3/8"]["constant"]


def test_bhc_prediction_matched(pkg):
    out = pkg["result.v0.1.json"]["outcomes_01b"]
    assert out["d7"] == "TRUE" and out["d8"] == out["d9"] == out["d10"] == "FALSE"
    assert out["d1"] == out["d2"] == out["d3"] == "TRUE" and out["d4"] == out["d5"] == out["d6"] == "FALSE"


def test_no_sufficiency_or_reopening(pkg):
    r = pkg["result.v0.1.json"]
    assert r["LAMBDA_SUFFICIENT"] is None and r["UNIVERSAL_SUFFICIENCY_CLAIMED"] is False
    assert r["BO2"] == "CANONICALLY_REFUTED_NOT_REOPENED" and r["BO3"] == "PARKED" and r["degrees_executed"] == [3]
    assert r["MORALES_RAMIS"] == "NOT_APPLIED" and r["FTT"] == "NOT_REQUIRED" and r["BURAU"] == "CONTROL_ONLY"


def test_source_custody(pkg):
    led = pkg["source-ledger.v0.1.json"]
    ids = {s["source_id"]: s for s in led["sources"]}
    assert ids["src-hvb-maier-2002"]["status"] == "BOUND" and ids["src-hvb-chou-wang-wu-2024"]["status"] == "BOUND"
    assert led["consumed_ledgers"][0]["records_relied_on"]["src-hvb-morales-ruiz-1999-attempt"]["status"] == "UNAVAILABLE"
    assert led["LAME_CLASSIFICATION_AUTHORITY"].startswith("PARTIAL")


# --- validation ---------------------------------------------------------------------------------------------------
def test_committed_package_validates():
    assert fin.validate(BASE) == []


def test_all_hostile_controls_rejected(pkg, tmp_path):
    results = fin.run_hostile(BASE, tmp_path)
    assert len(results) == 19 and all(r["rejected"] for r in results), [r["id"] for r in results if not r["rejected"]]
    assert pkg["hostile-controls.v0.1.json"]["all_rejected"]


def test_post_hoc_cell_is_detected(tmp_path):
    dst = tmp_path / "pkg"
    shutil.copytree(BASE, dst)
    p = dst / "preregistration.v0.1.json"
    d = json.loads(p.read_text())
    d["grid"][0]["mu"] = "-2"; d["cells"][0]["mu"] = "-2"
    p.write_text(json.dumps(d))
    assert any("preregistration differs" in e for e in fin.validate(dst, check_git=False))


# --- R1: pooled cardinality and accessory-parameter scope ---------------------------------------------------------
def test_r1_pooled_cardinality_is_mechanical_and_ordered_by_value(pkg, pkg_a):
    stats = b.pooled_statistics(pkg_a["cell-results.v0.1.json"]["cells"], pkg["cell-results.v0.1.json"]["cells"])
    assert stats["pooled_cell_count"] == 18 and stats["distinct_lambda_count"] == 6
    assert stats["distinct_lambdas"] == ["-1", "0", "3/8", "1", "2", "3"]
    assert sorted(stats["distinct_lambdas"]) != stats["distinct_lambdas"]        # lexical order would be wrong
    for surface in (pkg["adjudication.v0.1.json"]["pooled_summary"], pkg["result.v0.1.json"]["pooled_summary"]):
        assert surface["pooled_cell_count"] == 18 and surface["distinct_lambda_count"] == 6 and surface["distinct_lambdas"] == ["-1", "0", "3/8", "1", "2", "3"]


def test_r1_scope_fields_and_retained_outcomes(pkg):
    adj, res = pkg["adjudication.v0.1.json"], pkg["result.v0.1.json"]
    scope = res["mu_dependence_scope"]
    assert scope["observed_split_lambdas"] == ["3/8"] and scope["observed_split_ells"] == ["1/2"]
    assert scope["universal_half_integer_only_claim"] is False
    assert "-1" in scope["single_sampled_mu_lambdas"] and "3" in scope["single_sampled_mu_lambdas"]
    assert adj["verdict"] == "LAMBDA_ALONE_INSUFFICIENT"
    out = res["outcomes_01b"]
    assert out["d7"] == "TRUE" and out["d8"] == out["d9"] == out["d10"] == "FALSE"
    assert "smallest OF THE THREE TESTED CANDIDATE SIGNATURES" in res["minimal_missing_information"]["ORIGINAL + (lambda, mu)"]
    assert "universal sufficient statistic" in res["minimal_missing_information"]["not_promoted_to"]


def test_r1_summary_only_edits_are_rejected(tmp_path):
    for k, v in (("pooled_cell_count", 17), ("pooled_cell_count", 19), ("distinct_lambda_count", 4), ("distinct_lambda_count", 5), ("distinct_lambda_count", 7)):
        dst = tmp_path / f"pkg_{k}_{v}"
        shutil.copytree(BASE, dst)
        p = dst / "result.v0.1.json"
        d = json.loads(p.read_text()); d["pooled_summary"][k] = v; p.write_text(json.dumps(d))
        errs = fin.validate(dst, check_git=False)
        assert any(k in e and "recomputation" in e for e in errs), (k, v, errs)
    dst = tmp_path / "pkg_scope"
    shutil.copytree(BASE, dst)
    p = dst / "adjudication.v0.1.json"
    d = json.loads(p.read_text()); d["mu_dependence_scope"]["universal_half_integer_only_claim"] = True; p.write_text(json.dumps(d))
    assert any("forbidden universal claim" in e for e in fin.validate(dst, check_git=False))


def test_r1_memoization_does_not_bypass_input_bindings(tmp_path):
    """A mutated provider script with an unchanged log must still be rejected even though the rebuild is memoized."""
    dst = tmp_path / "pkg"
    shutil.copytree(BASE, dst)
    p = dst / "cells" / "target_cells.mac"
    p.write_text(p.read_text(encoding="utf-8").replace("(3*x/8)*y=0", "(5*x/8)*y=0", 1), encoding="utf-8")
    errs = fin.validate(dst, check_git=False)
    assert any("input binding broken" in e for e in errs) and any("digest differs" in e for e in errs)
