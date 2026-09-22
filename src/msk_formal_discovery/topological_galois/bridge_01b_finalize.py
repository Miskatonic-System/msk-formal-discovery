"""Finalize / validate the 01B package (WO-FORMAL-HAMILTONIAN-VARIATIONAL-BRIDGE-01B).

  python -m msk_formal_discovery.topological_galois.bridge_01b_finalize          rebuild adjudication / result / hostile controls from the saved log, validate
  python -m msk_formal_discovery.topological_galois.bridge_01b_finalize --check  validate only

validate():
  * Gate 0 pins; 01A package still replays; provider identity parity (digest recorded == 01A's);
  * preregistration replays exactly (Lame map, grid, equations, SOURCE_SIGNATURE) and its blob equals the commit's;
  * provider input script regenerated from the preregistration and digest-bound; log digest-bound; every cell rebuilt
    from the bound log (entire record); all cells share the 01A SOURCE_SIGNATURE; rationals only; n = 3 only;
  * every resolved predicate carries an admissible rule; adjudication recomputed; BO-2 not reopened; no LAMBDA_SUFFICIENT;
    Morales-Ruiz not upgraded; ell never conflated with n.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import sympy as sp

from . import bridge_01b as b
from . import bridge_experiment as bx
from . import bridge_runner as br
from . import bridge_validate as bv

BASE = b.EXPERIMENT_DIR
PREREG_COMMIT_01B = "752e897d37d6c12ed3ed85819082e9cca3e87595"
ALLOWED = bv.ALLOWED_RULE_PREFIXES
FORBIDDEN = bv.FORBIDDEN_INFERENCES | {"LAMBDA_NOT_FALSIFIED->LAMBDA_SUFFICIENT", "FINITE_GRID->UNIVERSAL_SUFFICIENCY", "BO2_REOPENED", "ELL=N"}


def load(base: Path = BASE) -> Dict[str, Any]:
    return {p.name: json.loads(p.read_text(encoding="utf-8")) for p in sorted(base.glob("*.json"))}


def dump(base: Path, name: str, obj) -> None:
    (base / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def validate(base: Path = BASE, check_git: bool = True) -> List[str]:
    errors: List[str] = []
    pkg = load(base)
    need = ["preregistration.v0.1.json", "cell-results.v0.1.json", "adjudication.v0.1.json", "result.v0.1.json", "source-ledger.v0.1.json", "hostile-controls.v0.1.json"]
    for n in need:
        if n not in pkg:
            errors.append(f"missing artifact {n}")
    if errors:
        return errors
    pre, cells, adj, res, led = (pkg[n] for n in need[:5])
    pkg_a = bv.load(b.DIR_01A)

    # gate 0 / predecessor (the full 01A replay only at top level; hostile fixtures mutate the 01B package, not 01A)
    if check_git and bv.validate(b.DIR_01A):
        errors.append("01A package no longer validates")
    if pre["gate0"]["formal_discovery_start"] != b.FD_START or pre["gate0"]["01a_result_digest"] != bx.canonical_digest(pkg_a["result.v0.1.json"]):
        errors.append("gate 0 pins or 01A result digest differ")
    if pre["gate0"]["provider_identity"]["kovacicODE_sha256"] != pkg_a["provider-qualification.v0.1.json"]["implementation_sha256_recorded"]:
        errors.append("PROVIDER_REQUALIFICATION_REQUIRED: provider identity differs from 01A")

    # preregistration replay + blob binding
    fresh = b.preregistration(pkg_a)
    fresh["phase_c"] = b.phase_c(pkg_a["cell-results.v0.1.json"]["cells"])
    if bx.canonical_digest(fresh) != bx.canonical_digest(pre):
        errors.append("preregistration differs from a fresh replay (Lame map / grid / equations / SOURCE_SIGNATURE / phase C)")
    if check_git:
        try:
            committed = subprocess.check_output(["git", "rev-parse", f"{PREREG_COMMIT_01B}:experiments/hamiltonian-variational-bridge-01b/preregistration.v0.1.json"], text=True, cwd=str(bx.REPO_ROOT)).strip()
            if bv.git_blob(base / "preregistration.v0.1.json") != committed:
                errors.append(f"preregistration blob differs from the blob committed at {PREREG_COMMIT_01B[:12]} (post-hoc grid edit)")
        except (subprocess.CalledProcessError, OSError):
            pass
    if not pre["lame_parameter_map"]["converse_check_qprime_sq_equals_f_of_q_given_wp_relation"] or not pre["lame_parameter_map"]["algebraic_form_identity"]["identity_holds"]:
        errors.append("Lame parameter map not established")
    if pre["frozen_member"]["n"] != 3 or any(c.get("n", 3) != 3 for c in pre["cells"]):
        errors.append("degree other than n = 3 present")
    for c in pre["cells"]:
        if c["lame"]["ell"] == "3" or c["lame"].get("ell") == str(pre["frozen_member"]["n"]) and c["lambda"] != "6":
            errors.append(f"cell {c['cell']}: ell conflated with n")
    if [c["cell"] for c in pre["cells"]] != [g["cell"] for g in pre["grid"]]:
        errors.append("cells do not match the preregistered grid")
    lambdas = {c["lambda"] for c in pre["grid"]}
    hist = {c["lambda"]: c["ABELIAN_IDENTITY_COMPONENT"] for c in pkg_a["cell-results.v0.1.json"]["cells"]}
    if not any(hist.get(l) == "TRUE" for l in lambdas) or not any(hist.get(l) == "FALSE" for l in lambdas):
        errors.append("grid must include one lambda already classified TRUE and one already classified FALSE in 01A")

    # execution edge binding + rebuild
    sig = pre["source_signature"]["SOURCE_SIGNATURE"]
    if sig != pkg_a["preregistration.v0.1.json"]["source_signature"]["SOURCE_SIGNATURE"]:
        errors.append("SOURCE_SIGNATURE differs from 01A")
    macp, logp = base / "cells" / "target_cells.mac", base / "cells" / "target_cells.log"
    if not macp.exists() or not logp.exists():
        errors.append("provider script or log missing")
    else:
        if macp.read_text(encoding="utf-8") != br.cell_script(pre["cells"]):
            errors.append("provider script differs from cell_script(preregistration cells): input binding broken")
        if br.sha256(macp.read_bytes()) != cells["script_digest"] or br.sha256(logp.read_bytes()) != cells["log_digest"]:
            errors.append("provider script/log digest differs from the cell-results binding")
        rebuilt = br.reclassify_from_log(pre, base / "cells")
        for a, bb in zip(rebuilt["cells"], cells["cells"]):
            if {k: v for k, v in bb.items() if k not in ("SOURCE_SIGNATURE", "claimed_inferences")} != a:
                errors.append(f"cell {bb['cell']} record differs from a rebuild from the provider log")
    if len(cells["cells"]) != len(pre["cells"]):
        errors.append("not every preregistered cell is reported")
    pre_cells = {c["cell"]: c for c in pre["cells"]}
    for c in cells["cells"]:
        pc = pre_cells.get(c["cell"])
        if pc is None or (c["mu"], c["lambda"], c["original_digest"], c["reduced_digest"]) != (pc["mu"], pc["lambda"], pc["original_digest"], pc["reduced_digest"]):
            errors.append(f"cell {c['cell']} not preregistered or altered")
        if c.get("SOURCE_SIGNATURE") != sig:
            errors.append(f"cell {c['cell']} carries a different SOURCE_SIGNATURE")
        for k in ("mu", "lambda"):
            if "." in str(c[k]) or "e" in str(c[k]).lower():
                errors.append(f"cell {c['cell']} has a floating-point {k}")
        pred, rule = c["ABELIAN_IDENTITY_COMPONENT"], c.get("rule") or ""
        if pred in ("TRUE", "FALSE") and not rule.startswith(ALLOWED):
            errors.append(f"cell {c['cell']}: predicate without an admissible rule")
        if pred == "FALSE" and not (c["provider_verdict_original_form"] == c["provider_verdict_reduced_form"] == "NO_LIOUVILLIAN_SOLUTION"):
            errors.append(f"cell {c['cell']}: FALSE requires case 4 on both forms")
        for inf in c.get("claimed_inferences", []):
            if inf in FORBIDDEN:
                errors.append(f"cell {c['cell']}: forbidden inference {inf}")

    # adjudication recomputed
    fresh_adj = b.adjudicate_d(pre, cells["cells"], pkg_a["cell-results.v0.1.json"]["cells"])
    for k in ("verdict", "same_lambda_same_source_different_mu_different_predicate", "unresolved_cells", "pooled_summary", "mu_dependence_scope"):
        if fresh_adj[k] != adj.get(k):
            errors.append(f"adjudication field {k} differs from recomputation")
    # R1: pooled cardinality recomputed independently from the pooled rows and compared with BOTH summary surfaces
    stats = b.pooled_statistics(pkg_a["cell-results.v0.1.json"]["cells"], cells["cells"])
    for surface, obj in (("adjudication", adj.get("pooled_summary")), ("result", res.get("pooled_summary"))):
        if obj is None:
            errors.append(f"{surface}: pooled_summary missing")
            continue
        for k in ("pooled_cell_count", "distinct_lambda_count", "distinct_lambdas"):
            if obj.get(k) != stats[k]:
                errors.append(f"{surface}: {k} = {obj.get(k)!r} differs from recomputation {stats[k]!r}")
    for surface, obj in (("adjudication", adj.get("mu_dependence_scope")), ("result", res.get("mu_dependence_scope"))):
        if obj is None:
            errors.append(f"{surface}: mu_dependence_scope missing")
            continue
        if obj.get("universal_half_integer_only_claim") is not False:
            errors.append(f"{surface}: forbidden universal claim 'mu dependence only for half-integer ell'")
        if obj.get("observed_split_lambdas") != fresh_adj["mu_dependence_scope"]["observed_split_lambdas"]:
            errors.append(f"{surface}: observed_split_lambdas differs from recomputation")
    mmi = res.get("minimal_missing_information")
    if not isinstance(mmi, dict) or "smallest OF THE THREE TESTED CANDIDATE SIGNATURES" not in mmi.get("ORIGINAL + (lambda, mu)", ""):
        errors.append("minimal-signature statement not scoped to the tested candidates")
    if res.get("UNIVERSALLY_MINIMAL_SUFFICIENT_SIGNATURE_CLAIMED") is True:
        errors.append("universally minimal sufficient signature claimed")
    if res.get("verdict_phase_d") != adj["verdict"]:
        errors.append("result verdict differs from the adjudication")
    if res.get("LAMBDA_SUFFICIENT") is True or res.get("UNIVERSAL_SUFFICIENCY_CLAIMED") is True:
        errors.append("sufficiency claimed from a finite grid")
    if res.get("BO2") != "CANONICALLY_REFUTED_NOT_REOPENED":
        errors.append("BO-2 status altered")
    if res.get("degrees_executed") != [3] or res.get("BO3") != "PARKED":
        errors.append("BO-3 / degree firewall breached")
    if res.get("MORALES_RAMIS") != "NOT_APPLIED" or res.get("FTT") != "NOT_REQUIRED" or res.get("BURAU") != "CONTROL_ONLY":
        errors.append("authority block altered")
    for inf in res.get("claimed_inferences", []):
        if inf in FORBIDDEN:
            errors.append(f"result: forbidden inference {inf}")
    ids = {s["source_id"]: s for s in led["sources"]}
    mr = led["consumed_ledgers"][0]["records_relied_on"].get("src-hvb-morales-ruiz-1999-attempt", {})
    if mr.get("status") not in ("UNAVAILABLE", "IDENTIFIED"):
        errors.append("Morales-Ruiz 1999 upgraded")
    for sid in ("src-hvb-maier-2002", "src-hvb-chou-wang-wu-2024"):
        if ids.get(sid, {}).get("status") != "BOUND" or len(ids.get(sid, {}).get("content_digest") or "") != 64:
            errors.append(f"{sid} must be BOUND with a SHA-256 digest")
    return errors


# ---------------------------------------------------------------------------
# hostile fixtures
# ---------------------------------------------------------------------------
HOSTILE: List[Dict[str, Any]] = []


def hostile(hid, pattern):
    def deco(fn):
        HOSTILE.append({"id": hid, "pattern": pattern, "mutate": fn})
        return fn
    return deco


def _edit(path: Path, fn) -> None:
    d = json.loads(path.read_text(encoding="utf-8"))
    fn(d)
    path.write_text(json.dumps(d, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


@hostile("B01", "cell added after results were inspected")
def _b01(dst):
    def f(d):
        d["grid"].append({"cell": "d11", "mu": "7", "lambda": "3/8", "role": "post hoc"})
        d["cells"].append(dict(d["cells"][-1], cell="d11", mu="7"))
    _edit(dst / "preregistration.v0.1.json", f)


@hostile("B02", "lambda changed on a 'same-lambda' row")
def _b02(dst):
    _edit(dst / "cell-results.v0.1.json", lambda d: d["cells"][7].update({"lambda": "1/2"}))


@hostile("B03", "split faked by resealing a predicate")
def _b03(dst):
    _edit(dst / "cell-results.v0.1.json", lambda d: d["cells"][3].update({"ABELIAN_IDENTITY_COMPONENT": "TRUE", "rule": "R2L: resealed"}))


@hostile("B04", "BO-2 reopened in the result")
def _b04(dst):
    _edit(dst / "result.v0.1.json", lambda d: d.update({"BO2": "NOT_FALSIFIED"}))


@hostile("B05", "n = 4 added")
def _b05(dst):
    _edit(dst / "result.v0.1.json", lambda d: d.update({"degrees_executed": [3, 4]}))


@hostile("B06", "LAMBDA_SUFFICIENT claimed from the finite grid")
def _b06(dst):
    _edit(dst / "result.v0.1.json", lambda d: d.update({"LAMBDA_SUFFICIENT": True}))


@hostile("B07", "Morales-Ruiz 1999 upgraded to BOUND")
def _b07(dst):
    _edit(dst / "source-ledger.v0.1.json", lambda d: d["consumed_ledgers"][0]["records_relied_on"]["src-hvb-morales-ruiz-1999-attempt"].update({"status": "BOUND"}))


@hostile("B08", "Lame index ell conflated with polynomial degree n")
def _b08(dst):
    def f(d):
        d["cells"][0]["lame"]["ell"] = "3"
    _edit(dst / "preregistration.v0.1.json", f)


@hostile("B09", "provider identity drifted without requalification")
def _b09(dst):
    _edit(dst / "preregistration.v0.1.json", lambda d: d["gate0"]["provider_identity"].update({"kovacicODE_sha256": "0" * 64}))


@hostile("B10", "provider input script mutated (d7 runs a different equation), log and results unchanged")
def _b10(dst):
    p = dst / "cells" / "target_cells.mac"
    t = p.read_text(encoding="utf-8")
    p.write_text(t.replace('print("RESULT_d7_orig", kovacicODE((-2*x^3 + 2*x)*\'diff(y,x,2)+(1 - 3*x^2)*\'diff(y,x)+(3*x/8)*y=0', 'print("RESULT_d7_orig", kovacicODE((-2*x^3 + 2*x)*\'diff(y,x,2)+(1 - 3*x^2)*\'diff(y,x)+(5*x/8)*y=0'), encoding="utf-8")
    assert p.read_text(encoding="utf-8") != t


@hostile("B11", "SOURCE_SIGNATURE differs from 01A on one cell (source recomputed)")
def _b11(dst):
    _edit(dst / "cell-results.v0.1.json", lambda d: d["cells"][6].update({"SOURCE_SIGNATURE": "f" * 64}))


@hostile("B12", "Morales-Ramis applied")
def _b12(dst):
    _edit(dst / "result.v0.1.json", lambda d: d.update({"MORALES_RAMIS": "APPLIED"}))


def _edit_both_summaries(dst, fn):
    _edit(dst / "adjudication.v0.1.json", fn)
    _edit(dst / "result.v0.1.json", fn)


@hostile("B13", "R1: pooled_cell_count = 17 claimed while the pooled rows are unchanged")
def _b13(dst):
    _edit_both_summaries(dst, lambda d: d["pooled_summary"].update({"pooled_cell_count": 17}))


@hostile("B14", "R1: distinct_lambda_count = 5 claimed while the rows contain six exact lambda values")
def _b14(dst):
    _edit_both_summaries(dst, lambda d: d["pooled_summary"].update({"distinct_lambda_count": 5}))


@hostile("B15", "R1: distinct_lambdas omits 3/8")
def _b15(dst):
    _edit_both_summaries(dst, lambda d: d["pooled_summary"].update({"distinct_lambdas": [l for l in d["pooled_summary"]["distinct_lambdas"] if l != "3/8"]}))


@hostile("B16", "R1: universal 'mu dependence only for half-integer ell' claim")
def _b16(dst):
    _edit(dst / "result.v0.1.json", lambda d: d["mu_dependence_scope"].update({"universal_half_integer_only_claim": True}))


@hostile("B17", "R1: pooled_cell_count = 19 / distinct_lambda_count = 7 (summary-only edit)")
def _b17(dst):
    _edit(dst / "result.v0.1.json", lambda d: d["pooled_summary"].update({"pooled_cell_count": 19, "distinct_lambda_count": 7}))


@hostile("B18", "R1: distinct_lambda_count = 4 (summary-only edit, adjudication surface)")
def _b18(dst):
    _edit(dst / "adjudication.v0.1.json", lambda d: d["pooled_summary"].update({"distinct_lambda_count": 4}))


@hostile("B19", "R1: distinct_lambdas misordered lexically / duplicated")
def _b19(dst):
    _edit_both_summaries(dst, lambda d: d["pooled_summary"].update({"distinct_lambdas": sorted(d["pooled_summary"]["distinct_lambdas"]) + ["3/8"]}))


def run_hostile(base: Path, tmp: Path) -> List[Dict[str, Any]]:
    out = []
    for h in HOSTILE:
        dst = tmp / "pkg"
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(base, dst)
        h["mutate"](dst)
        errs = validate(dst, check_git=False)
        out.append({"id": h["id"], "pattern": h["pattern"], "rejected": bool(errs), "errors": errs[:3]})
    return out


def build() -> Dict[str, Any]:
    pkg_a = bv.load(b.DIR_01A)
    pre = json.loads((BASE / "preregistration.v0.1.json").read_text(encoding="utf-8"))
    cells = json.loads((BASE / "cell-results.v0.1.json").read_text(encoding="utf-8"))
    adj = b.adjudicate_d(pre, cells["cells"], pkg_a["cell-results.v0.1.json"]["cells"])
    adj.update({"schema_version": "miskatonic.formal-discovery.hvb-01b-adjudication.v0.1", "work_order": b.WORK_ORDER, "phase_c": pre["phase_c"]})
    dump(BASE, "adjudication.v0.1.json", adj)
    outcomes = {c["cell"]: c["ABELIAN_IDENTITY_COMPONENT"] for c in cells["cells"]}
    result = {
        "schema_version": "miskatonic.formal-discovery.hvb-01b-result.v0.1", "work_order": b.WORK_ORDER,
        "canonical_start": b.FD_START, "preregistration_commit": PREREG_COMMIT_01B,
        "disposition": "LAME_PARAMETER_MAP_ESTABLISHED + " + adj["verdict"],
        "disposition_status": "PROPOSED_BY_EXECUTING_AGENT_PENDING_INDEPENDENT_REVIEW",
        "phase_a": "LAME_PARAMETER_MAP_ESTABLISHED (q = -2 wp, g2 = 1, g3 = 0; ell(ell+1) = 2 lambda, B = -mu; algebraic NVE == Lame algebraic form, factor 1)",
        "phase_b": {"LAME_CLASSIFICATION_AUTHORITY": "PARTIAL", "bound": ["src-hvb-maier-2002", "src-hvb-chou-wang-wu-2024"], "unavailable_not_upgraded": ["Morales-Ruiz 1999"]},
        "pooled_summary": adj["pooled_summary"],
        "mu_dependence_scope": adj["mu_dependence_scope"],
        "phase_c": {"question_1": f"lambda / ell(ell+1) is consistent with being load-bearing on the pooled sample (01A + 01B: {adj['pooled_summary']['pooled_cell_count']} cells, {adj['pooled_summary']['distinct_lambda_count']} distinct lambda values {adj['pooled_summary']['distinct_lambdas']}); the predicate is constant across the sampled mu at every sampled lambda except lambda = 3/8",
                    "question_2": "mu is NOT merely accessory: at lambda = 3/8 (ell = 1/2) it changes the predicate on the sampled cells. Scope: " + adj["mu_dependence_scope"]["statement"]},
        "verdict_phase_d": adj["verdict"], "splits": adj["same_lambda_same_source_different_mu_different_predicate"],
        "outcomes_01b": outcomes,
        "minimal_missing_information": {
            "ORIGINAL": "insufficient (BO-2, canonical)",
            "ORIGINAL + lambda": "insufficient (split at lambda = 3/8)",
            "ORIGINAL + ell(ell+1)": "equivalent relabelling of ORIGINAL + lambda, therefore insufficient",
            "ORIGINAL + (lambda, mu)": f"smallest OF THE THREE TESTED CANDIDATE SIGNATURES on which the predicate is a function across the {adj['pooled_summary']['pooled_cell_count']} sampled cells",
            "not_promoted_to": ["globally minimal sufficient signature", "universal sufficient statistic", "lambda and mu always determine G_diff^0", "no other hidden coordinate exists"],
            "bhc_note": "the observed split at ell = 1/2 sits at B = 0, the point the bound Brioschi-Halphen-Crawford characterization (p_0(B) proportional to B) singles out as finite projective monodromy; the FALSE cells at ell = 1/2 remain provider-decided, not theorem-derived",
        },
        "BO2": "CANONICALLY_REFUTED_NOT_REOPENED", "BO1": "NOT_EXECUTED", "BO3": "PARKED", "degrees_executed": [3],
        "MORALES_RAMIS": "NOT_APPLIED", "INTEGRABILITY": "NO_NEW_CLAIM", "CHAOS": "NO_CLAIM", "FTT": "NOT_REQUIRED", "BURAU": "CONTROL_ONLY",
        "LAMBDA_SUFFICIENT": None, "UNIVERSAL_SUFFICIENCY_CLAIMED": False, "claimed_inferences": [],
        "claim_ceiling": ["finite-grid statements about the frozen n = 3 member only", "TRUE/FALSE cells rest on the same rules and provider as 01A (FALSE: provider completeness, case 1 independently excluded)", "the integer-ell Liouvillian expectation and the 'non-finite half-integer => SL_2' expectation are NOT source-bound; the provider decided them on the sampled cells"],
        "permanent": ["POLYNOMIAL_DEGREE_n != LAME_INDEX_ell", "LAMBDA_ALONE_INSUFFICIENT (sampled: ell = 1/2 splits on mu)", "NOT_FALSIFIED != SUFFICIENT",
                      "ONLY_OBSERVED_SPLIT_AT_HALF_INTEGER != MU_DEPENDENCE_ONLY_AT_HALF_INTEGER", "MINIMAL_AMONG_TESTED_CANDIDATES != UNIVERSALLY_MINIMAL_SUFFICIENT_SIGNATURE",
                      "MEMOIZATION != EXECUTION_INPUT_AUTHORITY", "NONABELIAN_G0 != CHAOS", "SOURCE_GROUP_ACTION != TARGET_MONODROMY_REPRESENTATION"],
    }
    dump(BASE, "result.v0.1.json", result)
    dump(BASE, "hostile-controls.v0.1.json", {"schema_version": "miskatonic.formal-discovery.hvb-01b-hostile-controls.v0.1", "work_order": b.WORK_ORDER, "all_rejected": None, "count": 0, "results": []})
    with tempfile.TemporaryDirectory() as tmp:
        hostile = run_hostile(BASE, Path(tmp))
    dump(BASE, "hostile-controls.v0.1.json", {"schema_version": "miskatonic.formal-discovery.hvb-01b-hostile-controls.v0.1", "work_order": b.WORK_ORDER, "all_rejected": all(h["rejected"] for h in hostile), "count": len(hostile), "results": hostile})
    return result


def main() -> int:
    if "--check" not in sys.argv:
        r = build()
        print("disposition:", r["disposition"], "| splits:", [(s["lambda"], s["TRUE"]["cell"], s["FALSE"]["cell"]) for s in r["splits"]])
    errors = validate(BASE)
    if errors:
        print("FAILED:", file=sys.stderr)
        for e in errors:
            print("  -", e, file=sys.stderr)
        return 1
    h = json.loads((BASE / "hostile-controls.v0.1.json").read_text())
    print(f"PASS: 01B package validates; hostile {sum(x['rejected'] for x in h['results'])}/{h['count']} rejected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
