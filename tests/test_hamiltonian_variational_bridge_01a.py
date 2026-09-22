"""Tests for WO-FORMAL-HAMILTONIAN-VARIATIONAL-BRIDGE-01A (no Maxima run: everything replays from the committed package)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import sympy as sp

from msk_formal_discovery.topological_galois import bridge_experiment as bx
from msk_formal_discovery.topological_galois import bridge_runner as br
from msk_formal_discovery.topological_galois import bridge_validate as bv

BASE = bx.EXPERIMENT_DIR
x = br.x


@pytest.fixture(scope="module")
def pkg():
    return bv.load(BASE)


# --- preregistration --------------------------------------------------------------------------------------------
def test_frozen_member_is_exact_and_squarefree():
    m = bx.frozen_member()
    assert m["n"] == 3 and m["E"] == "-1" and m["roots_of_f_ordered"] == ["-1", "0", "1"] and m["discriminant_of_f"] == "64"
    assert "E - P_3" in m["singular_polynomial_note"]


def test_preregistration_replays_exactly(pkg):
    assert bx.canonical_digest(bx.preregistration()) == bx.canonical_digest(pkg["preregistration.v0.1.json"])


def test_grid_has_transparent_control_and_several_nonzero_lambda(pkg):
    g = pkg["preregistration.v0.1.json"]["grid"]
    assert (g[0]["mu"], g[0]["lambda"]) == ("0", "0")
    assert len({c["lambda"] for c in g if c["lambda"] != "0"}) >= 3 and 4 <= len(g) <= 8


def test_no_floating_point_anywhere(pkg):
    for c in pkg["preregistration.v0.1.json"]["cells"]:
        for k in ("c2", "c1", "c0"):
            sp.Poly(sp.sympify(c["original"][k]), sp.Symbol("q"))     # exact rationals only
        assert "." not in c["reduced"]["r"]


def test_normalization_is_exact_and_identity_component_scope_stated(pkg):
    c = pkg["preregistration.v0.1.json"]["cells"][4]
    r = sp.sympify(c["reduced"]["r"])
    q = sp.Symbol("q")
    f = sp.sympify(c["original"]["c2"]); a = sp.diff(f, q) / 2 / f; b = sp.sympify(c["original"]["c0"]) / f
    assert sp.simplify(r - (a ** 2 / 4 + sp.diff(a, q) / 2 - b)) == 0
    assert "identity component" in c["normalization"]["scope"]


# --- provider ---------------------------------------------------------------------------------------------------
def test_provider_qualified_with_all_k_controls(pkg):
    pq = pkg["provider-qualification.v0.1.json"]
    assert pq["qualified"] and pq["implementation_sha256_observed"] == pq["implementation_sha256_recorded"] == br.KOVACIC_MAC_SHA256
    ids = {r["id"]: r for r in pq["rows"]}
    assert ids["K4a"]["provider_verdict"] == ids["K4b"]["provider_verdict"] == "NO_LIOUVILLIAN_SOLUTION"
    assert ids["K1"]["provider_verdict"] == "INPUT_REJECTED" and ids["K1g"]["provider_verdict"] == "LIOUVILLIAN_SOLUTIONS_RETURNED"


def test_provider_message_text_is_not_the_verdict():
    assert br.verdict_for("nil", "blah\nNo Liouvillian solutions exist\nODE is not linear!\n") == "INPUT_REJECTED"
    assert br.verdict_for("nil", "No Liouvillian solutions exist\n") == "NO_LIOUVILLIAN_SOLUTION"
    assert br.verdict_for("[y = x]", "No Liouvillian solutions exist\nNo Liouvillian solutions exist\n") == "LIOUVILLIAN_SOLUTIONS_RETURNED"


# --- exact engine -----------------------------------------------------------------------------------------------
def test_exact_engine_reduction_is_canonical():
    A = br.ExactAlgebra(sp.sqrt(x - 1) * sp.sqrt(x + 1))
    e = A.lift(sp.sqrt(x - 1) ** 2 * sp.sqrt(x + 1) ** 2 - (x ** 2 - 1))
    assert A.is_zero(e)
    assert not A.is_zero(A.lift(sp.sqrt(x - 1)) - 1)


def test_direct_derivation_c1_holds():
    c = bx.target_equation(sp.Integer(0), sp.Integer(0))
    c2, c1, c0 = (sp.sympify(c["original"][k]).subs(sp.Symbol("q"), x) for k in ("c2", "c1", "c0"))
    d = br.direct_derivation_c1(c2, c1, c0)
    assert d["y1_verified"] and d["y2_verified_via_y2'=f^(-1/2)"] and d["predicate"] == "TRUE"


# --- cells and adjudication -------------------------------------------------------------------------------------
def test_cells_rebuild_from_saved_log_and_share_signature(pkg):
    pre, cells = pkg["preregistration.v0.1.json"], pkg["cell-results.v0.1.json"]
    rebuilt = br.reclassify_from_log(pre, BASE / "cells")
    assert [c["ABELIAN_IDENTITY_COMPONENT"] for c in rebuilt["cells"]] == [c["ABELIAN_IDENTITY_COMPONENT"] for c in cells["cells"]]
    sig = pre["source_signature"]["SOURCE_SIGNATURE"]
    assert all(c["SOURCE_SIGNATURE"] == sig for c in cells["cells"])


def test_every_resolved_cell_has_an_admissible_rule(pkg):
    for c in pkg["cell-results.v0.1.json"]["cells"]:
        if c["ABELIAN_IDENTITY_COMPONENT"] in ("TRUE", "FALSE"):
            assert c["rule"].startswith(bv.ALLOWED_RULE_PREFIXES)
        if c["ABELIAN_IDENTITY_COMPONENT"] == "FALSE":
            assert c["provider_verdict_original_form"] == c["provider_verdict_reduced_form"] == "NO_LIOUVILLIAN_SOLUTION"
            assert c["independent_case1_test_on_reduced_form"]["case_1_possible"] is False


def test_bo2_adjudication(pkg):
    adj = pkg["adjudication.v0.1.json"]
    res = pkg["result.v0.1.json"]
    assert adj["BO2"] in ("REFUTED", "NOT_FALSIFIED_ON_FROZEN_N3_GRID")
    if adj["BO2"] == "REFUTED":
        assert adj["disposition_component"] == "SOURCE_DATA_ALONE_INSUFFICIENT_FOR_TARGET_PREDICATE"
        assert res["disposition"] == "HAMILTONIAN_VARIATIONAL_BRIDGE_BO2_REFUTED_SOURCE_INSUFFICIENT"
        assert adj["witness_pair"]["c1"]["predicate"] == "TRUE" and adj["witness_pair"]["c2"]["predicate"] == "FALSE"
    assert res["SOURCE_DATA_SUFFICIENT"] is None and res["MORALES_RAMIS"] == "NOT_APPLIED" and res["NONINTEGRABILITY_CLAIM"] == "NONE"
    assert res["degrees_executed"] == [3] and res["BURAU_ROLE"] == "CONTROL_ONLY" and res["rho_tgt_used_as_evidence_about_G_diff"] is False


def test_bo1_not_executed_and_bo3_unknown(pkg):
    adj = pkg["adjudication.v0.1.json"]
    assert adj["BO1"]["status"] == "NOT_EXECUTED" and adj["BO3"].startswith("UNKNOWN")


# --- custody ----------------------------------------------------------------------------------------------------
def test_source_custody(pkg):
    led = pkg["source-ledger.v0.1.json"]
    ids = {s["source_id"]: s for s in led["sources"]}
    assert ids["src-hvb-morales-ruiz-1999-attempt"]["status"] == "UNAVAILABLE" and ids["src-hvb-morales-ruiz-1999-attempt"]["content_digest"] is None
    assert ids["src-hvb-kovacic-1986"]["status"] == "IDENTIFIED"
    assert ids["src-hvb-smith-1984"]["status"] == "BOUND" and len(ids["src-hvb-smith-1984"]["content_digest"]) == 64
    amw = led["consumed_ledgers"][0]["records_relied_on"]["src-hmc-acosta-morales-weil-2010"]
    assert amw["status"] == "BOUND"


# --- validation and hostile controls ---------------------------------------------------------------------------
def test_committed_package_validates():
    assert bv.validate(BASE) == []


def test_all_hostile_controls_rejected(pkg, tmp_path):
    results = bv.run_hostile(BASE, tmp_path)
    assert len(results) == 21
    assert all(r["rejected"] for r in results), [r["id"] for r in results if not r["rejected"]]
    committed = pkg["hostile-controls.v0.1.json"]
    assert committed["all_rejected"] and committed["count"] == 21


def test_post_hoc_grid_edit_is_detected(tmp_path):
    dst = tmp_path / "pkg"
    shutil.copytree(BASE, dst)
    p = dst / "preregistration.v0.1.json"
    d = json.loads(p.read_text())
    d["grid"][2]["lambda"] = "7"
    d["cells"][2]["lambda"] = "7"
    p.write_text(json.dumps(d))
    errs = bv.validate(dst, check_git=False)
    assert any("preregistration differs" in e for e in errs)


# --- R1: provider input-to-output replay binding --------------------------------------------------------------
def test_r1_target_script_regenerates_and_binds(pkg):
    pre, cells = pkg["preregistration.v0.1.json"], pkg["cell-results.v0.1.json"]
    mac = (BASE / "cells" / "target_cells.mac").read_text(encoding="utf-8")
    assert mac == br.cell_script(pre["cells"])
    assert br.sha256(mac.encode()) == cells["script_digest"]
    assert br.sha256((BASE / "cells" / "target_cells.log").read_bytes()) == cells["log_digest"]


def test_r1_k_script_and_log_bind_and_k_matrix_reconstructs(pkg):
    pq = pkg["provider-qualification.v0.1.json"]
    kmac = (BASE / "provider" / "k_controls.mac").read_text(encoding="utf-8")
    klog = (BASE / "provider" / "k_controls.log").read_text(encoding="utf-8")
    assert kmac == br.k_script() and br.sha256(kmac.encode()) == pq["k_control_script_digest"] and br.sha256(klog.encode()) == pq["k_control_log_digest"]
    rebuilt = br.reconstruct_k_matrix(klog)
    assert rebuilt["rows"] == [{k: r[k] for k in ("id", "expected_verdict", "provider_verdict", "pass")} for r in pq["rows"]]
    assert rebuilt["qualified_from_rows"] and pq["qualified"]


def test_r1_mutated_target_script_is_rejected_with_everything_else_unchanged(tmp_path):
    dst = tmp_path / "pkg"
    shutil.copytree(BASE, dst)
    p = dst / "cells" / "target_cells.mac"
    t = p.read_text(encoding="utf-8")
    p.write_text(t.replace('print("RESULT_c5_orig", kovacicODE((-2*x^3 + 2*x)*\'diff(y,x,2)+(1 - 3*x^2)*\'diff(y,x)+(2*x)*y=0',
                           'print("RESULT_c5_orig", kovacicODE((-2*x^3 + 2*x)*\'diff(y,x,2)+(1 - 3*x^2)*\'diff(y,x)+(3*x)*y=0'), encoding="utf-8")
    assert p.read_text(encoding="utf-8") != t
    errs = bv.validate(dst, check_git=False)
    assert any("input binding broken" in e for e in errs) and any("script digest differs" in e for e in errs), errs


def test_r1_hostile_provider_controls_present_and_rejected(pkg):
    h = pkg["hostile-controls.v0.1.json"]
    ids = {r["id"]: r for r in h["results"]}
    assert h["count"] == 21 and h["all_rejected"]
    assert "input binding broken" in ids["H17"]["errors"][0]
    assert any("K-control script differs" in e for e in ids["H18"]["errors"])
    assert any("K-control log digest" in e for e in ids["H19"]["errors"])
    assert any("K matrix" in e for e in ids["H20"]["errors"])
    assert any("K matrix" in e or "qualified" in e for e in ids["H21"]["errors"])
