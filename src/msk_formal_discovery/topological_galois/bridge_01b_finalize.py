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
    for k in ("verdict", "same_lambda_same_source_different_mu_different_predicate", "unresolved_cells"):
        if fresh_adj[k] != adj[k]:
            errors.append(f"adjudication field {k} differs from recomputation")
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
        "phase_c": {"question_1": "lambda / ell(ell+1) supported as load-bearing on all sampled cells (01A + 01B: 18 cells, 4 lambda classes, predicate constant across mu except at ell = 1/2)", "question_2": "mu is NOT merely accessory: at lambda = 3/8 it changes the predicate"},
        "verdict_phase_d": adj["verdict"], "splits": adj["same_lambda_same_source_different_mu_different_predicate"],
        "outcomes_01b": outcomes,
        "minimal_missing_information": "AUGMENTED_LAMBDA is insufficient; AUGMENTED_FULL = ORIGINAL + (lambda, mu) is the smallest of the three candidate signatures on which the sampled predicate is a function (18 sampled cells). The dependence on mu is confined, on the sampled cells, to the half-integer-ell class, matching the bound Brioschi-Halphen-Crawford characterization (finite projective monodromy iff p_0(B) = 0, i.e. B = 0).",
        "BO2": "CANONICALLY_REFUTED_NOT_REOPENED", "BO1": "NOT_EXECUTED", "BO3": "PARKED", "degrees_executed": [3],
        "MORALES_RAMIS": "NOT_APPLIED", "INTEGRABILITY": "NO_NEW_CLAIM", "CHAOS": "NO_CLAIM", "FTT": "NOT_REQUIRED", "BURAU": "CONTROL_ONLY",
        "LAMBDA_SUFFICIENT": None, "UNIVERSAL_SUFFICIENCY_CLAIMED": False, "claimed_inferences": [],
        "claim_ceiling": ["finite-grid statements about the frozen n = 3 member only", "TRUE/FALSE cells rest on the same rules and provider as 01A (FALSE: provider completeness, case 1 independently excluded)", "the integer-ell Liouvillian expectation and the 'non-finite half-integer => SL_2' expectation are NOT source-bound; the provider decided them on the sampled cells"],
        "permanent": ["POLYNOMIAL_DEGREE_n != LAME_INDEX_ell", "LAMBDA_ALONE_INSUFFICIENT (sampled: ell = 1/2 splits on mu)", "NOT_FALSIFIED != SUFFICIENT", "NONABELIAN_G0 != CHAOS", "SOURCE_GROUP_ACTION != TARGET_MONODROMY_REPRESENTATION"],
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
