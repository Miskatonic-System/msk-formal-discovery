"""Validation gate and hostile controls for WO-FORMAL-HAMILTONIAN-VARIATIONAL-BRIDGE-01A.

validate(base) recomputes everything deterministic from the committed package and returns a list of errors:
  * preregistration replays exactly (frozen member, grid, exact equations, SOURCE_SIGNATURE) and its git blob equals
    the preregistration commit's blob (no post-hoc grid edits);
  * every cell shares the SOURCE_SIGNATURE; only (mu, lambda) differ; all coefficients are exact rationals;
  * cell records are rebuilt from the SAVED provider log (digest-bound) and compared with the committed records;
  * the predicate of every cell is justified by a named rule (R4 / R2L / RU / RD), never by the word "Liouvillian";
  * the adjudication is recomputed from the cell records;
  * forbidden inferences are absent; Burau is not on the critical path; n = 3 only; no FTT.

Hostile fixtures mutate a copy of the package in one specific way and must make validate() fail.
"""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import sympy as sp

from . import bridge_experiment as bx
from . import bridge_runner as br

EXPERIMENT_DIR = bx.EXPERIMENT_DIR
PREREG_COMMIT = "e22dd8cfa6d71e022e7fe6e4ed6b9f9e1f9a9ee2"
ALLOWED_RULE_PREFIXES = ("R4:", "R2L", "RU", "RD:")
FORBIDDEN_INFERENCES = {"NONABELIAN_G0->CHAOS", "NONABELIAN_G0->NONINTEGRABILITY_CLAIM", "NONINTEGRABILITY->CHAOS", "MORALES_RAMIS_APPLIED",
                        "SOLVABLE_GROUP->ABELIAN_IDENTITY_COMPONENT", "LIOUVILLIAN->ABELIAN_IDENTITY_COMPONENT", "NO_LIOUVILLIAN->CHAOS",
                        "MONODROMY_GROUP->G_DIFF_WITHOUT_CLOSURE", "NOT_FALSIFIED->SOURCE_DATA_SUFFICIENT"}


def load(base: Path = EXPERIMENT_DIR) -> Dict[str, Any]:
    out = {}
    for p in sorted(base.glob("*.json")):
        out[p.name] = json.loads(p.read_text(encoding="utf-8"))
    return out


def git_blob(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], text=True).strip()


def committed_prereg_blob() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", f"{PREREG_COMMIT}:experiments/hamiltonian-variational-bridge-01a/preregistration.v0.1.json"],
                                       text=True, cwd=str(bx.REPO_ROOT)).strip()
    except (subprocess.CalledProcessError, OSError):
        return None


def validate(base: Path = EXPERIMENT_DIR, check_git: bool = True) -> List[str]:
    errors: List[str] = []
    pkg = load(base)
    need = ["preregistration.v0.1.json", "provider-qualification.v0.1.json", "cell-results.v0.1.json", "adjudication.v0.1.json", "source-ledger.v0.1.json", "hostile-controls.v0.1.json", "result.v0.1.json"]
    for n in need:
        if n not in pkg:
            errors.append(f"missing artifact {n}")
    if errors:
        return errors
    pre, pq, cells, adj, led, res = (pkg[n] for n in need[:5] + [need[6]])

    # 1. preregistration replay (needs the predecessor package for the SOURCE_SIGNATURE)
    fresh = bx.preregistration()
    if bx.canonical_digest(fresh) != bx.canonical_digest(pre):
        errors.append("preregistration differs from a fresh replay (frozen member / grid / equations / SOURCE_SIGNATURE)")
    if check_git:
        blob_now = git_blob(base / "preregistration.v0.1.json")
        blob_committed = committed_prereg_blob()
        if blob_committed is not None and blob_now != blob_committed:
            errors.append(f"preregistration blob {blob_now[:12]} differs from the blob committed at {PREREG_COMMIT[:12]} (post-hoc grid edit)")
    if pre["frozen_member"]["n"] != 3 or any(c.get("n", 3) != 3 for c in pre["cells"]):
        errors.append("degree other than n = 3 present")
    if len(pre["cells"]) != len(pre["grid"]) or [c["cell"] for c in pre["cells"]] != [g["cell"] for g in pre["grid"]]:
        errors.append("cells do not match the preregistered grid")

    # 2. source signature identical across cells; only (mu, lambda) vary; exact rationals only
    sig = pre["source_signature"]["SOURCE_SIGNATURE"]
    for c in cells["cells"]:
        if c.get("SOURCE_SIGNATURE") != sig:
            errors.append(f"cell {c['cell']} carries SOURCE_SIGNATURE {str(c.get('SOURCE_SIGNATURE'))[:12]} != {sig[:12]}")
        for k in ("mu", "lambda"):
            try:
                sp.Rational(c[k])
            except (TypeError, ValueError):
                errors.append(f"cell {c['cell']} has non-rational {k} = {c[k]!r}")
            if "." in str(c[k]) or "e" in str(c[k]).lower():
                errors.append(f"cell {c['cell']} has a floating-point {k}")
    if adj["SOURCE_SIGNATURE_shared_by_all_cells"] != sig:
        errors.append("adjudication binds a different SOURCE_SIGNATURE")
    pre_cells = {c["cell"]: c for c in pre["cells"]}
    for c in cells["cells"]:
        pc = pre_cells.get(c["cell"])
        if pc is None:
            errors.append(f"cell {c['cell']} was not preregistered")
            continue
        if (c["mu"], c["lambda"], c["original_digest"], c["reduced_digest"]) != (pc["mu"], pc["lambda"], pc["original_digest"], pc["reduced_digest"]):
            errors.append(f"cell {c['cell']} equation or coupling differs from the preregistration")
    if len(cells["cells"]) != len(pre["cells"]):
        errors.append("not every preregistered cell is reported (selective reporting)")

    # 3a. R1: execution-edge binding for the target cells — the committed input script must be exactly the script
    #     regenerated from the preregistration, and its digest must be the one the cell results bind.
    macp = base / "cells" / "target_cells.mac"
    if not macp.exists():
        errors.append("target provider script missing")
    else:
        committed_mac = macp.read_text(encoding="utf-8")
        if committed_mac != br.cell_script(pre["cells"]):
            errors.append("target provider script differs from cell_script(preregistration cells): input binding broken")
        if br.sha256(committed_mac.encode("utf-8")) != cells.get("script_digest"):
            errors.append("target provider script digest differs from the cell-results binding")

    # 3b. R1: provider-qualification binding — regenerate the K script, bind both digests, and rebuild the K matrix
    #     from the committed log; the rebuilt id / expected / verdict / pass / qualified must match exactly.
    kmac, klog = base / "provider" / "k_controls.mac", base / "provider" / "k_controls.log"
    if not kmac.exists() or not klog.exists():
        errors.append("provider K-control script or log missing")
    else:
        kmac_text, klog_text = kmac.read_text(encoding="utf-8"), klog.read_text(encoding="utf-8")
        if kmac_text != br.k_script():
            errors.append("K-control script differs from k_script(): provider input binding broken")
        if br.sha256(kmac_text.encode("utf-8")) != pq.get("k_control_script_digest"):
            errors.append("K-control script digest differs from the provider-qualification binding")
        if br.sha256(klog_text.encode("utf-8")) != pq.get("k_control_log_digest"):
            errors.append("K-control log digest differs from the provider-qualification binding")
        rebuilt_k = br.reconstruct_k_matrix(klog_text)
        committed_rows = [{k: r.get(k) for k in ("id", "expected_verdict", "provider_verdict", "pass")} for r in pq.get("rows", [])]
        if committed_rows != rebuilt_k["rows"]:
            errors.append("provider K matrix (id/expected/verdict/pass) differs from a rebuild from the committed log")
        if pq.get("qualified") is not (rebuilt_k["qualified_from_rows"] and pq.get("implementation_sha256_observed") == pq.get("implementation_sha256_recorded")):
            errors.append("provider 'qualified' flag is not what the reconstructed K matrix and digest comparison give")

    # 3. cell records rebuilt from the saved provider log
    logp = base / "cells" / "target_cells.log"
    if not logp.exists():
        errors.append("provider log missing")
    else:
        if br.sha256(logp.read_bytes()) != cells["log_digest"]:
            errors.append("provider log digest differs from the cell-results binding")
        rebuilt = br.reclassify_from_log(pre, base / "cells")
        for a, b in zip(rebuilt["cells"], cells["cells"]):
            # R1: the ENTIRE rebuilt record (verdicts, digests, predicate, rule and all evidence) must match; the exact
            # engine assigns its auxiliary symbols deterministically, so evidence strings replay byte-for-byte.
            extra = {"SOURCE_SIGNATURE", "claimed_inferences"}
            if {k: v for k, v in b.items() if k not in extra} != a:
                errors.append(f"cell {b['cell']} record differs from a rebuild from the provider log")

    # 4. rule discipline
    for c in cells["cells"]:
        pred, rule = c["ABELIAN_IDENTITY_COMPONENT"], c.get("rule") or ""
        if pred in ("TRUE", "FALSE") and not rule.startswith(ALLOWED_RULE_PREFIXES):
            errors.append(f"cell {c['cell']}: predicate {pred} without an admissible rule ({rule[:40]!r})")
        if pred == "FALSE" and not (c["provider_verdict_original_form"] == c["provider_verdict_reduced_form"] == "NO_LIOUVILLIAN_SOLUTION"):
            errors.append(f"cell {c['cell']}: FALSE requires case 4 on both forms")
        if pred == "TRUE" and rule.startswith("R4"):
            errors.append(f"cell {c['cell']}: rule/predicate mismatch")
        for inf in c.get("claimed_inferences", []):
            if inf in FORBIDDEN_INFERENCES:
                errors.append(f"cell {c['cell']}: forbidden inference {inf}")

    # 5. adjudication recomputed
    fresh_adj = br.adjudicate(pre, cells["cells"])
    for k in ("BO2", "disposition_component", "witness_pair", "predicate_by_cell"):
        if fresh_adj[k] != adj[k]:
            errors.append(f"adjudication field {k} differs from recomputation")
    if adj["BO2"] == "NOT_FALSIFIED_ON_FROZEN_N3_GRID" and res.get("SOURCE_DATA_SUFFICIENT") is True:
        errors.append("NOT_FALSIFIED was promoted to SOURCE_DATA_SUFFICIENT")
    for inf in res.get("claimed_inferences", []):
        if inf in FORBIDDEN_INFERENCES:
            errors.append(f"result: forbidden inference {inf}")

    # 6. provider, custody, scope
    if not pq.get("qualified"):
        errors.append("provider not qualified")
    if pq.get("implementation_sha256_observed") != pq.get("implementation_sha256_recorded"):
        errors.append("provider implementation digest mismatch")
    ids = {s["source_id"]: s for s in led["sources"]}
    mr = ids.get("src-hvb-morales-ruiz-1999-attempt")
    if mr and mr["status"] not in ("UNAVAILABLE", "IDENTIFIED"):
        errors.append("Morales-Ruiz 1999 status may not be promoted without a content hash")
    if mr and mr["status"] != "BOUND" and res.get("rho_tgt_used_as_evidence_about_G_diff"):
        errors.append("rho_tgt used as evidence about G_diff while the closure source is unbound")
    if res.get("BURAU_ROLE") != "CONTROL_ONLY":
        errors.append("Burau promoted into the critical path")
    if res.get("degrees_executed") != [3]:
        errors.append("degrees other than 3 executed")
    if res.get("FTT") != "NOT_REQUIRED" or res.get("MORALES_RAMIS") != "NOT_APPLIED":
        errors.append("authority block altered")
    if res.get("TARGET_VARIATIONAL_GALOIS_PREDICATE_NONABELIAN_CELLS") and res.get("NONINTEGRABILITY_CLAIM") not in (None, False, "NONE"):
        errors.append("nonintegrability claimed from a nonabelian identity component")
    return errors


# ---------------------------------------------------------------------------
# hostile fixtures: each mutates a copy of the package and must FAIL validation
# ---------------------------------------------------------------------------

def _copy(base: Path, tmp: Path) -> Path:
    dst = tmp / "pkg"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(base, dst)
    return dst


def _edit(path: Path, fn) -> None:
    d = json.loads(path.read_text(encoding="utf-8"))
    fn(d)
    path.write_text(json.dumps(d, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


HOSTILE: List[Dict[str, Any]] = []


def hostile(hid: str, pattern: str):
    def deco(fn):
        HOSTILE.append({"id": hid, "pattern": pattern, "mutate": fn})
        return fn
    return deco


@hostile("H01", "changing P_3 between coupling cells")
def _h01(dst):
    _edit(dst / "cell-results.v0.1.json", lambda d: d["cells"][4].update({"SOURCE_SIGNATURE": "0" * 64, "original_digest": "1" * 64}))


@hostile("H02", "changing E between coupling cells")
def _h02(dst):
    _edit(dst / "cell-results.v0.1.json", lambda d: d["cells"][5].update({"SOURCE_SIGNATURE": bx.canonical_digest({"E": "0"})}))


@hostile("H03", "changing root ordering without recording relabel")
def _h03(dst):
    def f(d):
        d["frozen_member"]["roots_of_f_ordered"] = ["1", "0", "-1"]
    _edit(dst / "preregistration.v0.1.json", f)


@hostile("H04", "changing Artin/Hurwitz convention between cells")
def _h04(dst):
    def f(d):
        d["source_signature"]["payload"]["hurwitz_convention"]["value"] = "RIGHT action rho o alpha(beta)"
    _edit(dst / "preregistration.v0.1.json", f)


@hostile("H05", "adding a coupling after target results are seen")
def _h05(dst):
    def f(d):
        d["grid"].append({"cell": "c9", "mu": "2", "lambda": "5", "role": "added post hoc"})
        d["cells"].append(dict(d["cells"][0], cell="c9", mu="2", **{"lambda": "5"}))
    _edit(dst / "preregistration.v0.1.json", f)


@hostile("H06", "selecting only cells that support the expected negative")
def _h06(dst):
    # keep only the (0,0) control and the FALSE cells: the abelian non-control cells vanish from the report
    _edit(dst / "cell-results.v0.1.json", lambda d: d.update({"cells": [c for c in d["cells"] if c["cell"] == "c1" or c["ABELIAN_IDENTITY_COMPONENT"] == "FALSE"]}))


@hostile("H07", "numerical approximation substituted for exact rational equation")
def _h07(dst):
    _edit(dst / "cell-results.v0.1.json", lambda d: d["cells"][1].update({"mu": "1.0000001"}))


@hostile("H08", "Liouvillian result relabeled 'G^0 abelian' without group evidence")
def _h08(dst):
    def f(d):
        for c in d["cells"]:
            if c["ABELIAN_IDENTITY_COMPONENT"] == "UNRESOLVED" and c["provider_verdict_original_form"] == "LIOUVILLIAN_SOLUTIONS_RETURNED":
                c["ABELIAN_IDENTITY_COMPONENT"], c["rule"] = "TRUE", "Liouvillian, hence solvable, hence abelian"
                return
        d["cells"][0]["rule"] = "Liouvillian, hence solvable, hence abelian"
    _edit(dst / "cell-results.v0.1.json", f)


@hostile("H09", "no-Liouvillian result relabeled chaos")
def _h09(dst):
    _edit(dst / "cell-results.v0.1.json", lambda d: d["cells"][4].update({"claimed_inferences": ["NO_LIOUVILLIAN->CHAOS"]}))


@hostile("H10", "target monodromy relabeled G_diff without closure theorem")
def _h10(dst):
    _edit(dst / "result.v0.1.json", lambda d: d.update({"rho_tgt_used_as_evidence_about_G_diff": True}))


@hostile("H11", "source braid data recomputed differently per cell")
def _h11(dst):
    _edit(dst / "cell-results.v0.1.json", lambda d: d["cells"][2].update({"SOURCE_SIGNATURE": bx.canonical_digest({"artin": "recomputed with sigma_i^-1"})}))


@hostile("H12", "Burau promoted back into the critical path")
def _h12(dst):
    _edit(dst / "result.v0.1.json", lambda d: d.update({"BURAU_ROLE": "LOAD_BEARING"}))


@hostile("H13", "n=4..6 added after observing n=3 outcomes")
def _h13(dst):
    _edit(dst / "result.v0.1.json", lambda d: d.update({"degrees_executed": [3, 4, 5, 6]}))


@hostile("H14", "result JSON resealed after changing source signature or target predicate without semantic rejection")
def _h14(dst):
    def f(d):
        d["cells"][4]["ABELIAN_IDENTITY_COMPONENT"] = "TRUE"
        d["cells"][4]["rule"] = "R2L: resealed"
    _edit(dst / "cell-results.v0.1.json", f)
    _edit(dst / "adjudication.v0.1.json", lambda d: d["predicate_by_cell"].update({"c5": "TRUE"}))


@hostile("H15", "NOT_FALSIFIED promoted to SOURCE_DATA_SUFFICIENT")
def _h15(dst):
    _edit(dst / "adjudication.v0.1.json", lambda d: d.update({"BO2": "NOT_FALSIFIED_ON_FROZEN_N3_GRID"}))
    _edit(dst / "result.v0.1.json", lambda d: d.update({"SOURCE_DATA_SUFFICIENT": True}))


@hostile("H16", "nonabelian G^0 converted into a nonintegrability / Morales-Ramis claim")
def _h16(dst):
    _edit(dst / "result.v0.1.json", lambda d: d.update({"MORALES_RAMIS": "APPLIED", "NONINTEGRABILITY_CLAIM": "H_3 is nonintegrable"}))


@hostile("H17", "R1: target_cells.mac mutated so one RESULT_cN tag runs a different equation; preregistration, log and cell-results unchanged")
def _h17(dst):
    p = dst / "cells" / "target_cells.mac"
    t = p.read_text(encoding="utf-8")
    assert "RESULT_c5_orig" in t
    lines = t.split("\n")
    for i, ln in enumerate(lines):
        if ln.startswith('print("RESULT_c5_orig"'):
            lines[i] = ln.replace("+(2*x)*y=0", "+(3*x)*y=0") if "+(2*x)*y=0" in ln else ln.replace("*y=0", "*y+1=0")
            break
    p.write_text("\n".join(lines), encoding="utf-8")


@hostile("H18", "R1: modified K-control script with unchanged qualification and log")
def _h18(dst):
    p = dst / "provider" / "k_controls.mac"
    p.write_text(p.read_text(encoding="utf-8").replace("'diff(y,x,2)=x*y", "'diff(y,x,2)=x^2*y"), encoding="utf-8")


@hostile("H19", "R1: modified K-control log")
def _h19(dst):
    p = dst / "provider" / "k_controls.log"
    p.write_text(p.read_text(encoding="utf-8").replace("RESULT_K4a nil", "RESULT_K4a [y = x]"), encoding="utf-8")


@hostile("H20", "R1: modified provider verdict row")
def _h20(dst):
    def f(d):
        row = next(r for r in d["rows"] if r["id"] == "K4a")
        row["provider_verdict"], row["expected_verdict"] = "LIOUVILLIAN_SOLUTIONS_RETURNED", "LIOUVILLIAN_SOLUTIONS_RETURNED"
    _edit(dst / "provider-qualification.v0.1.json", f)


@hostile("H21", "R1: qualified=true with a failed reconstructed control")
def _h21(dst):
    def f(d):
        row = next(r for r in d["rows"] if r["id"] == "K3a")
        row["expected_verdict"], row["pass"] = "NO_LIOUVILLIAN_SOLUTION", False
        d["qualified"] = True
    _edit(dst / "provider-qualification.v0.1.json", f)


def run_hostile(base: Path, tmp: Path) -> List[Dict[str, Any]]:
    out = []
    for h in HOSTILE:
        dst = _copy(base, tmp)
        h["mutate"](dst)
        errs = validate(dst, check_git=False)
        out.append({"id": h["id"], "pattern": h["pattern"], "rejected": bool(errs), "errors": errs[:4]})
    return out
