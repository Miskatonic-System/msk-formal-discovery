"""Run / finalize / validate the 01C package (WO-FORMAL-HAMILTONIAN-VARIATIONAL-BRIDGE-01C).

  python -m msk_formal_discovery.topological_galois.bridge_01c_finalize --run      run the 24 provider scripts (once; after the preregistration commit)
  python -m msk_formal_discovery.topological_galois.bridge_01c_finalize            rebuild cell-results / adjudication / result / hostile controls from the saved logs, validate
  python -m msk_formal_discovery.topological_galois.bridge_01c_finalize --check    validate only

validate():
  * Gate 0 pins; 01A/01B/TG packages replay (top level only); provider identity parity with the 01A qualification;
  * preregistration replays exactly (family, PC1, degree/background signatures, lanes, consumed anchors, 12 cells) and its blob equals the commit's;
  * one provider script per (cell, form) regenerated from the preregistration and digest-bound; every log digest-bound; every cell record
    rebuilt from the bound logs (entire record); coupling signature identical across degrees inside a lane; n >= 4 never labelled Lame;
  * every resolved predicate carries an admissible rule; FALSE needs case 4 on both forms; adjudication (lanes, transitions, falsifiers)
    recomputed; no causal attribution; no DEGREE_IRRELEVANT / COUPLING_PAIR_UNIVERSALLY_SUFFICIENT; BO-2 not reopened; Morales-Ramis not applied.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List

from . import bridge_01b as b01b
from . import bridge_01b_finalize as fin_b
from . import bridge_01c as c
from . import bridge_experiment as bx
from . import bridge_runner as br
from . import bridge_validate as bv
from . import qualification as q01

BASE = c.EXPERIMENT_DIR
PREREG_COMMIT_01C = "24e0408caf2a8cdcaabcab7e5b70384c793e1da1"
ALLOWED = bv.ALLOWED_RULE_PREFIXES
FORBIDDEN = fin_b.FORBIDDEN | {"S5_SOLVABILITY_CLIFF->TARGET_PREDICATE_CHANGE", "OUT_S6->TARGET_PREDICATE_CHANGE", "NO_CHANGE->DEGREE_IRRELEVANT",
                               "DEGREE>=5->NONINTEGRABILITY", "SOURCE_THEOREM->TARGET_PREDICATE", "FINITE_PANEL->COUPLING_PAIR_UNIVERSALLY_SUFFICIENT"}
FORBIDDEN_PHRASES = ("caused by", "causes", "caused the", "proves that", "never matters", "degree is irrelevant", "forces the")
# R1: theorem-level degree-ladder language is admissible on a canonical surface only with bound theorem authority (none is bound in 01C)
UNEARNED_AUTHORITY_PHRASES = ("radical-solvability cliff", "radical solvability cliff", "solvable by radicals", "a_5 simple", "a_5 is simple", "a5 simple",
                              "perfect/simple", "simple core", "exceptional out(s_6) layer present", "s_n_solvability_cliff", "external_established")
CANONICAL_SURFACES = ("adjudication.v0.1.json", "result.v0.1.json", "source-ledger.v0.1.json")     # never the frozen preregistration
FORMS = ("orig", "red")
TIMEOUT_MARK = "[PROVIDER_TIMEOUT:"


def load(base: Path = BASE) -> Dict[str, Any]:
    return {p.name: json.loads(p.read_text(encoding="utf-8")) for p in sorted(base.glob("*.json"))}


def dump(base: Path, name: str, obj) -> None:
    (base / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# provider execution: one script per (cell, form)
# ---------------------------------------------------------------------------

def form_script(cell: Dict[str, Any], form: str) -> str:
    eq = cell["maxima_original"] if form == "orig" else cell["maxima_reduced"]
    return "\n".join(["display2d:false$", "load(kovacicODE)$", f'print("RESULT_{cell["cell"]}_{form}", kovacicODE({eq}, y, x))$']) + "\n"


def _run_one(cell: Dict[str, Any], form: str, workdir: Path, timeout: int) -> Dict[str, Any]:
    label = f'{cell["cell"]}_{form}'
    mac = workdir / f"{label}.mac"
    mac.write_text(form_script(cell, form), encoding="utf-8")
    cmd = ["nix", "--extra-experimental-features", "nix-command flakes", "shell", "nixpkgs#maxima", "--command",
           "maxima", "--very-quiet", f"--batch={mac.resolve()}"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=str(workdir), start_new_session=True)
    try:
        out, _ = proc.communicate(timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)         # kill maxima too, not only the nix wrapper
        out, _ = proc.communicate()
        out = (out or "") + f"\n{TIMEOUT_MARK} script exceeded {timeout} s; no retry]\n"
        timed_out = True
    (workdir / f"{label}.log").write_text(out, encoding="utf-8")
    return {"label": label, "timed_out": timed_out, "returncode": proc.returncode}


def run_provider(pre: Dict[str, Any], workdir: Path = BASE / "cells") -> List[Dict[str, Any]]:
    workdir.mkdir(parents=True, exist_ok=True)
    pol = pre["provider_policy"]
    jobs = [(cell, form) for cell in pre["cells"] for form in FORMS]
    with ThreadPoolExecutor(max_workers=pol["parallel_workers"]) as ex:
        return list(ex.map(lambda j: _run_one(j[0], j[1], workdir, pol["timeout_s_per_script"]), jobs))


# ---------------------------------------------------------------------------
# reconstruction from the bound logs (no Maxima run)
# ---------------------------------------------------------------------------
_CACHE: Dict[str, Dict[str, Any]] = {}


def _bindings(cell_id: str, workdir: Path) -> Dict[str, Any]:
    out = {}
    for form in FORMS:
        mac, log = workdir / f"{cell_id}_{form}.mac", workdir / f"{cell_id}_{form}.log"
        out[form] = {"script": f"cells/{mac.name}", "script_digest": br.sha256(mac.read_bytes()) if mac.exists() else None,
                     "log": f"cells/{log.name}", "log_digest": br.sha256(log.read_bytes()) if log.exists() else None}
    return out


def reclassify(pre: Dict[str, Any], workdir: Path) -> List[Dict[str, Any]]:
    """Rebuild every cell record from its two bound logs. Memoized per (preregistered cells, all log bytes); scripts are bound separately."""
    logs = {}
    for cell in pre["cells"]:
        for form in FORMS:
            p = workdir / f'{cell["cell"]}_{form}.log'
            logs[f'{cell["cell"]}_{form}'] = p.read_text(encoding="utf-8") if p.exists() else ""
    key = bx.canonical_digest(pre["cells"]) + ":" + br.sha256(json.dumps(logs, sort_keys=True).encode())
    if key not in _CACHE:
        recs = []
        for cell in pre["cells"]:
            lo, lr = logs[f'{cell["cell"]}_orig'], logs[f'{cell["cell"]}_red']
            log = lo + "\n" + lr
            rec = br.classify_cell(cell, br.parse_results(log), log)
            for form_log, k in ((lo, "provider_verdict_original_form"), (lr, "provider_verdict_reduced_form")):
                if TIMEOUT_MARK in form_log and rec[k] == "UNPARSED":
                    rec[k] = "PROVIDER_TIMEOUT"
            rec.update({"n": cell["n"], "lane": cell["lane"], "equation_class": cell["equation_class"], "coupling_signature": cell["coupling_signature"],
                        "background_signature": pre["background_signatures"][str(cell["n"])]["BACKGROUND_SIGNATURE"]})
            recs.append(rec)
        _CACHE[key] = recs
    out = copy.deepcopy(_CACHE[key])
    for rec in out:
        rec["provider_bindings"] = _bindings(rec["cell"], workdir)
    return out


# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------

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
    pkg_a, pkg_b, pkg_tg = bv.load(c.DIR_01A), fin_b.load(c.DIR_01B), q01.load_artifacts(c.DIR_TG)

    # gate 0 (full predecessor replays only at top level; hostile fixtures mutate the 01C package, never the predecessors)
    if check_git:
        if bv.validate(c.DIR_01A):
            errors.append("01A package no longer validates")
        if fin_b.validate(c.DIR_01B):
            errors.append("01B package no longer validates")
    g = pre["gate0"]
    if g["formal_discovery_start"] != c.FD_START or g["mathematics_sha"] != c.MATH_SHA:
        errors.append("gate 0 pins differ")
    if g["01a_result_digest"] != bx.canonical_digest(pkg_a["result.v0.1.json"]) or g["01b_result_digest"] != bx.canonical_digest(pkg_b["result.v0.1.json"]) \
            or g["01b_adjudication_digest"] != bx.canonical_digest(pkg_b["adjudication.v0.1.json"]) or g["tg_qualification_result_digest"] != bx.canonical_digest(pkg_tg["qualification-result.v0.1.json"]):
        errors.append("predecessor result/adjudication identities differ")
    if g["provider_identity"]["kovacicODE_sha256"] != pkg_a["provider-qualification.v0.1.json"]["implementation_sha256_recorded"] or g["provider_identity"]["kovacicODE_sha256"] != br.KOVACIC_MAC_SHA256:
        errors.append("PROVIDER_REQUALIFICATION_REQUIRED: provider identity differs from the 01A qualification")
    rb = pkg_b["result.v0.1.json"]
    expected_checks = {"BO2": "CANONICALLY_REFUTED_NOT_REOPENED", "01B_verdict": "LAME_PARAMETER_MAP_ESTABLISHED + LAMBDA_ALONE_INSUFFICIENT", "pooled_cell_count": 18, "distinct_lambda_count": 6, "universal_half_integer_only_claim": False}
    live_checks = {"BO2": rb["BO2"], "01B_verdict": rb["disposition"], "pooled_cell_count": rb["pooled_summary"]["pooled_cell_count"], "distinct_lambda_count": rb["pooled_summary"]["distinct_lambda_count"], "universal_half_integer_only_claim": rb["mu_dependence_scope"]["universal_half_integer_only_claim"]}
    if g["checks"] != expected_checks or live_checks != expected_checks:
        errors.append("gate 0 predecessor checks (BO2 / 01B verdict / 18 / 6 / false) differ")

    # preregistration replay + blob binding
    fresh = c.preregistration(pkg_a, pkg_b, pkg_tg)
    if bx.canonical_digest(fresh) != bx.canonical_digest(pre):
        errors.append("preregistration differs from a fresh replay (family / signatures / lanes / anchors / cells)")
    if check_git:
        try:
            committed = subprocess.check_output(["git", "rev-parse", f"{PREREG_COMMIT_01C}:experiments/hamiltonian-variational-bridge-01c/preregistration.v0.1.json"], text=True, cwd=str(bx.REPO_ROOT)).strip()
            if bv.git_blob(base / "preregistration.v0.1.json") != committed:
                errors.append(f"preregistration blob differs from the blob committed at {PREREG_COMMIT_01C[:12]} (post-hoc edit)")
        except (subprocess.CalledProcessError, OSError):
            pass
    if not pre["pc1"]["pass"] or not c.pc1_n3_member_identity()["pass"]:
        errors.append("PC1: generated n = 3 member is not the canonical member")
    for n in c.DEGREES:
        fam = c.controlled_family(n)
        if not fam["all_checks_pass"] or pre["controlled_family"][str(n)] != fam:
            errors.append(f"controlled family n = {n} differs from the frozen construction (roots / spacing / E / P_n / f_n)")
    if [l["lane"] for l in pre["lanes"]] != ["A", "B", "C", "D"] or len(pre["lanes"]) != 4:
        errors.append("lane set differs from the four frozen lanes")
    for lane in pre["lanes"]:
        if lane["coupling_signature"] != c.coupling_signature(lane["lambda"], lane["mu"]):
            errors.append(f"lane {lane['lane']}: coupling signature not derived from (lambda, mu)")
    for lane in c.LANES:
        try:
            if c.consume_anchor(lane, pkg_a, pkg_b) != pre["anchors"][lane["lane"]] or pre["anchors"][lane["lane"]]["origin"] != "CONSUMED_CANONICAL":
                errors.append(f"anchor {lane['lane']}: not the consumed canonical record")
        except (ValueError, KeyError, StopIteration):
            errors.append(f"anchor {lane['lane']}: cannot be consumed from the canonical packages")
    if [x["cell"] for x in pre["cells"]] != [f"n{n}_{L}" for n in c.NEW_DEGREES for L in "ABCD"]:
        errors.append("cells differ from the 12 preregistered (n, lane) pairs")

    # execution edge binding + whole-record rebuild
    lane_sig = {l["lane"]: l["coupling_signature"] for l in pre["lanes"]}
    lane_pair = {l["lane"]: (l["mu"], l["lambda"]) for l in pre["lanes"]}
    workdir = base / "cells"
    rebuilt = {r["cell"]: r for r in reclassify(pre, workdir)} if workdir.exists() else {}
    pre_cells = {x["cell"]: x for x in pre["cells"]}
    for x in pre["cells"]:
        for form in FORMS:
            mac, log = workdir / f'{x["cell"]}_{form}.mac', workdir / f'{x["cell"]}_{form}.log'
            if not mac.exists() or not log.exists():
                errors.append(f"cell {x['cell']}: provider script or log missing for form {form}")
            elif mac.read_text(encoding="utf-8") != form_script(x, form):
                errors.append(f"cell {x['cell']}: provider script ({form}) differs from form_script(preregistered cell): input binding broken")
    if len(cells["cells"]) != len(pre["cells"]) or {r["cell"] for r in cells["cells"]} != set(pre_cells):
        errors.append("not every preregistered cell is reported (selective omission)")
    for r in cells["cells"]:
        x = pre_cells.get(r["cell"])
        if x is None:
            errors.append(f"cell {r['cell']} not preregistered")
            continue
        if (r["mu"], r["lambda"], r["original_digest"], r["reduced_digest"], r.get("n"), r.get("lane")) != (x["mu"], x["lambda"], x["original_digest"], x["reduced_digest"], x["n"], x["lane"]):
            errors.append(f"cell {r['cell']}: coupling / equation / degree altered relative to the preregistration")
        if (r["mu"], r["lambda"]) != lane_pair.get(r.get("lane")) or r.get("coupling_signature") != lane_sig.get(r.get("lane")) or r.get("coupling_signature") != c.coupling_signature(r["lambda"], r["mu"]):
            errors.append(f"cell {r['cell']}: coupling changed inside lane {r.get('lane')}")
        if r.get("background_signature") != c.background_signature(int(r["n"]), pkg_tg)["BACKGROUND_SIGNATURE"]:
            errors.append(f"cell {r['cell']}: source degree/background signature differs from recomputation")
        if int(r["n"]) >= 4 and (r.get("equation_class") != f"ALGEBRAIC_NVE_{r['n']}" or "LAME" in str(r.get("equation_class", "")).upper()):
            errors.append(f"cell {r['cell']}: n = {r['n']} equation relabelled ({r.get('equation_class')}); only ALGEBRAIC_NVE_n is admissible")
        for k in ("mu", "lambda"):
            if "." in str(r[k]) or "e" in str(r[k]).lower():
                errors.append(f"cell {r['cell']} has a floating-point {k}")
        rb_rec = rebuilt.get(r["cell"])
        if rb_rec is None:
            errors.append(f"cell {r['cell']}: cannot be rebuilt from the provider logs")
        else:
            if {k: v for k, v in r.items() if k != "claimed_inferences"} != rb_rec:
                errors.append(f"cell {r['cell']}: record differs from a rebuild from the bound provider logs")
            for form in FORMS:
                bnd = r.get("provider_bindings", {}).get(form, {})
                mac, log = workdir / f'{r["cell"]}_{form}.mac', workdir / f'{r["cell"]}_{form}.log'
                if mac.exists() and log.exists() and (bnd.get("script_digest") != br.sha256(mac.read_bytes()) or bnd.get("log_digest") != br.sha256(log.read_bytes())):
                    errors.append(f"cell {r['cell']}: provider script/log digest ({form}) differs from the binding")
        pred, rule = r["ABELIAN_IDENTITY_COMPONENT"], r.get("rule") or ""
        if pred in ("TRUE", "FALSE") and not rule.startswith(ALLOWED):
            errors.append(f"cell {r['cell']}: predicate without an admissible rule (source-theorem labels are not target computations)")
        if pred == "FALSE" and not (r["provider_verdict_original_form"] == r["provider_verdict_reduced_form"] == "NO_LIOUVILLIAN_SOLUTION"):
            errors.append(f"cell {r['cell']}: FALSE requires case 4 on both forms")
        if pred not in ("TRUE", "FALSE", "UNRESOLVED"):
            errors.append(f"cell {r['cell']}: predicate value {pred!r} not admissible")
        for inf in r.get("claimed_inferences", []):
            if inf in FORBIDDEN:
                errors.append(f"cell {r['cell']}: forbidden inference {inf}")

    # adjudication recomputed
    fresh_adj = c.adjudicate(pre, cells["cells"])
    for k in ("verdict", "lanes", "transitions", "lanes_with_split", "lanes_partial", "unresolved_cells"):
        if fresh_adj[k] != adj.get(k):
            errors.append(f"adjudication field {k} differs from recomputation")
    for surface, obj in (("adjudication", adj), ("result", res)):
        if obj.get("COUPLING_PAIR_UNIVERSALLY_SUFFICIENT") is True:
            errors.append(f"{surface}: COUPLING_PAIR_UNIVERSALLY_SUFFICIENT emitted from a finite panel")
        if obj.get("DEGREE_IRRELEVANT") is True:
            errors.append(f"{surface}: NO_DEGREE_EFFECT promoted to DEGREE_IRRELEVANT")
        for t, block in (obj.get("transitions") or {}).items():
            for L, entry in block.items():
                if isinstance(entry, dict) and entry.get("causal_attribution") != "NONE":
                    errors.append(f"{surface}: transition {t} lane {L} carries a causal attribution ({entry.get('causal_attribution')!r}): TRANSITION_ALIGNMENT != CAUSAL_TRANSPORT")
                if isinstance(entry, str) and any(p in entry.lower() for p in FORBIDDEN_PHRASES):
                    errors.append(f"{surface}: transition {t} statement uses causal / universal language")
    for L, lane in (res.get("lanes") or {}).items():
        if lane.get("lane_result") != fresh_adj["lanes"][L]["lane_result"] or lane.get("TARGET_SEQUENCE") != fresh_adj["lanes"][L]["TARGET_SEQUENCE"]:
            errors.append(f"result: lane {L} differs from the recomputed adjudication")
    if res.get("disposition") != adj["verdict"]:
        errors.append("result disposition differs from the adjudication verdict")
    if res.get("BO2") != "CANONICALLY_REFUTED_NOT_REOPENED":
        errors.append("BO-2 status altered")
    if res.get("BO3") != "EXECUTED_BOUNDEDLY_IN_01C" or res.get("BO1") != "NOT_EXECUTED" or res.get("degrees_new") != [4, 5, 6] or res.get("panel_degrees") != [3, 4, 5, 6]:
        errors.append("BO-3 / BO-1 / degree scope altered")
    if res.get("MORALES_RAMIS") != "NOT_APPLIED" or res.get("FTT") != "NOT_REQUIRED" or res.get("BURAU") != "CONTROL_ONLY" or res.get("LAME") != "N3_ONLY":
        errors.append("authority block altered")
    for inf in res.get("claimed_inferences", []):
        if inf in FORBIDDEN:
            errors.append(f"result: forbidden inference {inf}")
    for k, v in (res.get("cliff_statements") or {}).items():
        if any(p in str(v).lower() for p in FORBIDDEN_PHRASES):
            errors.append(f"result: cliff statement {k} uses causal / universal language")
    mr = led["consumed_ledgers"][0]["records_relied_on"].get("src-hvb-morales-ruiz-1999-attempt", {})
    if mr.get("status") not in ("UNAVAILABLE", "IDENTIFIED"):
        errors.append("Morales-Ruiz 1999 upgraded")
    if led.get("LAME_AUTHORITY_SCOPE") != "N3_ONLY (consumed from 01B; not extended to n = 4, 5, 6)" or not str(led.get("DEGREE_LADDER_AUTHORITY", "")).startswith("LOCAL_DERIVED_FOR_GROUP_SOLVABILITY_AND_PERFECTNESS"):
        errors.append("ledger authority scope altered (Lame beyond n = 3 or degree-ladder authority not split LOCAL_DERIVED / IDENTIFIED_UNBOUND)")
    errors.extend(validate_degree_ladder_authority(pkg, adj, res, led))
    return errors


def validate_degree_ladder_authority(pkg, adj, res, led) -> List[str]:
    """R1: degree-ladder labels on canonical surfaces may not exceed what is LOCAL_DERIVED; the rest stays IDENTIFIED_UNBOUND."""
    errors: List[str] = []
    fresh = c.degree_ladder_authority()
    for name in CANONICAL_SURFACES:
        text = json.dumps(pkg[name], ensure_ascii=False).lower()
        for p in UNEARNED_AUTHORITY_PHRASES:
            if p in text:
                errors.append(f"{name}: unearned degree-ladder authority language {p!r} (no bound theorem source; LOCAL_DERIVED covers only group solvability / perfectness)")
    for surface, obj in (("adjudication", adj), ("result", res), ("source-ledger", led)):
        a = obj.get("degree_ladder_authority")
        if not isinstance(a, dict):
            errors.append(f"{surface}: degree_ladder_authority matrix missing")
            continue
        if a.get("local_derived") != fresh["local_derived"]:
            errors.append(f"{surface}: local_derived values differ from the exact finite-group recomputation")
        if a.get("identified_unbound", {}).get("items") != fresh["identified_unbound"]["items"]:
            errors.append(f"{surface}: identified_unbound item set altered (radical interpretation / A5 simplicity / Out(S_6) must stay unbound)")
        o = a.get("Out_S6_label", {})
        if o.get("status") != "IDENTIFIED_UNBOUND" or o.get("witnessed") is not False or o.get("load_bearing") is not False:
            errors.append(f"{surface}: Out(S_6) label promoted beyond IDENTIFIED_UNBOUND / not witnessed / not load-bearing without evidence")
        if a.get("transition_labels") != fresh["transition_labels"]:
            errors.append(f"{surface}: transition labels differ from the earned wording")
    src = next((s for s in led.get("sources", []) if s["source_id"] == "src-hvb-degree-ladder-classical-facts"), None)
    if src is None or src.get("status") != "IDENTIFIED" or src.get("content_digest"):
        errors.append("ledger: degree-ladder classical-facts record must remain IDENTIFIED with no bound digest")
    absent = next((cl for cl in led.get("consumed_ledgers", []) if "candidate-freeze" in cl.get("path", "")), {}).get("records_relied_on", {}).get("frozen.expected_controls[2]", {})
    if absent.get("status") != "ABSENT_AT_PIN":
        errors.append("ledger: the absent Mathematics degree-ladder control document must stay ABSENT_AT_PIN")
    for L, lane in (adj.get("lanes") or {}).items():
        f2 = lane.get("falsifiers", {}).get("F2", "")
        if f2.startswith("S4_TO_S5") and f2 != c.FALSIFIER_TEXT["F2"]:
            errors.append(f"adjudication: lane {L} F2 identifier altered")
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


def _cell(d, cid):
    return next(x for x in d["cells"] if x["cell"] == cid)


@hostile("C01", "coupling changed between degrees inside one lane (n5_A carries lambda = 2 while the lane is lambda = 1)")
def _c01(dst):
    _edit(dst / "cell-results.v0.1.json", lambda d: _cell(d, "n5_A").update({"lambda": "2"}))


@hostile("C02", "root spacing changed from the frozen controlled family (n = 5 roots stretched)")
def _c02(dst):
    def f(d):
        d["controlled_family"]["5"]["roots_ordered"] = ["-4", "-2", "0", "2", "4"]
        for x in d["cells"]:
            if x["n"] == 5:
                x["roots_ordered"] = ["-4", "-2", "0", "2", "4"]
    _edit(dst / "preregistration.v0.1.json", f)


@hostile("C03", "E changed for one degree (n = 4 at E = 0)")
def _c03(dst):
    def f(d):
        d["controlled_family"]["4"]["E"] = "0"
        for x in d["cells"]:
            if x["n"] == 4:
                x["E"] = "0"
    _edit(dst / "preregistration.v0.1.json", f)


@hostile("C04", "n = 3 anchor recomputed instead of consumed from canonical evidence")
def _c04(dst):
    _edit(dst / "preregistration.v0.1.json", lambda d: d["anchors"]["A"].update({"origin": "RECOMPUTED_01C", "record_digest": "0" * 64}))


@hostile("C05", "provider drift without requalification")
def _c05(dst):
    _edit(dst / "preregistration.v0.1.json", lambda d: d["gate0"]["provider_identity"].update({"kovacicODE_sha256": "0" * 64}))


@hostile("C06", "provider script differs from the preregistered equation (n4_A original form runs a different equation; log unchanged)")
def _c06(dst):
    p = dst / "cells" / "n4_A_orig.mac"
    t = p.read_text(encoding="utf-8")
    p.write_text(t.replace("+(x)*y=0", "+(2*x)*y=0", 1), encoding="utf-8")
    assert p.read_text(encoding="utf-8") != t


@hostile("C07", "source degree signature silently changed after the target result (n5_B background signature resealed)")
def _c07(dst):
    _edit(dst / "cell-results.v0.1.json", lambda d: _cell(d, "n5_B").update({"background_signature": "f" * 64}))


@hostile("C08", "unresolved (or provider-decided) cell coerced to TRUE by resealing the predicate")
def _c08(dst):
    def f(d):
        target = next((x for x in d["cells"] if x["ABELIAN_IDENTITY_COMPONENT"] == "UNRESOLVED"), None) or next(x for x in d["cells"] if x["ABELIAN_IDENTITY_COMPONENT"] == "FALSE")
        target.update({"ABELIAN_IDENTITY_COMPONENT": "TRUE", "rule": "R2L: coerced"})
    _edit(dst / "cell-results.v0.1.json", f)


@hostile("C09", "4->5 target change labelled as caused by S_5 nonsolvability")
def _c09(dst):
    _edit_both(dst, lambda d: d["transitions"]["4->5"]["A"].update({"causal_attribution": "S_5_NONSOLVABILITY"}))


@hostile("C10", "4->5 no-change labelled proof that source degree never matters")
def _c10(dst):
    _edit(dst / "result.v0.1.json", lambda d: d.update({"DEGREE_IRRELEVANT": True}))


@hostile("C11", "5->6 transition labelled as caused by Out(S_6)")
def _c11(dst):
    _edit(dst / "result.v0.1.json", lambda d: d.update({"claimed_inferences": ["OUT_S6->TARGET_PREDICATE_CHANGE"]}))


@hostile("C12", "n = 5 equation relabelled Lame without derivation")
def _c12(dst):
    _edit(dst / "cell-results.v0.1.json", lambda d: _cell(d, "n5_A").update({"equation_class": "LAME"}))


@hostile("C13", "BO-2 reopened")
def _c13(dst):
    _edit(dst / "result.v0.1.json", lambda d: d.update({"BO2": "NOT_FALSIFIED"}))


@hostile("C14", "Morales-Ramis applied")
def _c14(dst):
    _edit(dst / "result.v0.1.json", lambda d: d.update({"MORALES_RAMIS": "APPLIED"}))


@hostile("C15", "new coupling lane added post hoc")
def _c15(dst):
    _edit(dst / "preregistration.v0.1.json", lambda d: d["lanes"].append({"lane": "E", "lambda": "1", "mu": "1", "coupling_signature": c.coupling_signature("1", "1"), "anchor": {"package": "01A", "cell": "c4"}, "accepted_n3_predicate": "TRUE", "design": "post hoc"}))


@hostile("C16", "selective omission of one degree from a lane (n5_B dropped)")
def _c16(dst):
    _edit(dst / "cell-results.v0.1.json", lambda d: d.update({"cells": [x for x in d["cells"] if x["cell"] != "n5_B"]}))


@hostile("C17", "coupling-pair sufficiency claimed universally from no observed split")
def _c17(dst):
    _edit(dst / "result.v0.1.json", lambda d: d.update({"COUPLING_PAIR_UNIVERSALLY_SUFFICIENT": True}))


@hostile("C18", "source-theorem label substituted for the direct target computation (n5_B: 'S_5 nonsolvable => nonabelian')")
def _c18(dst):
    _edit(dst / "cell-results.v0.1.json", lambda d: _cell(d, "n5_B").update({"ABELIAN_IDENTITY_COMPONENT": "FALSE", "rule": "THEOREM: S_5 nonsolvable => G^0 nonabelian"}))


@hostile("C19", "anchor predicate resealed in the adjudication (lane C n = 3 -> FALSE)")
def _c19(dst):
    _edit(dst / "adjudication.v0.1.json", lambda d: d["lanes"]["C"]["TARGET_SEQUENCE"].update({"3": "FALSE"}))


@hostile("C20", "transition statement rewritten in causal language")
def _c20(dst):
    _edit(dst / "result.v0.1.json", lambda d: d["transitions"]["4->5"].update({"statement": "The change on lane B was caused by the S_5 solvability cliff."}))


@hostile("C21", "Lame authority extended to n = 4..6 in the ledger")
def _c21(dst):
    _edit(dst / "source-ledger.v0.1.json", lambda d: d.update({"LAME_AUTHORITY_SCOPE": "ALL_DEGREES"}))


@hostile("C22", "provider log for n6_D reduced form swapped for the n6_C log (record unchanged)")
def _c22(dst):
    shutil.copyfile(dst / "cells" / "n6_C_red.log", dst / "cells" / "n6_D_red.log")


@hostile("C23", "R1: canonical result says 'radical-solvability cliff' while radical theorem authority remains unbound")
def _c23(dst):
    _edit(dst / "result.v0.1.json", lambda d: d["transitions"]["4->5"].update({"source_side_label": "S_4 -> S_5: source radical-solvability cliff"}))


@hostile("C24", "R1: canonical result says 'A_5 simple' with only local A_5 perfectness evidence")
def _c24(dst):
    _edit(dst / "result.v0.1.json", lambda d: d["degree_ladder_authority"]["transition_labels"].update({"4->5": "S_4 -> S_5 GROUP-SOLVABILITY TRANSITION (A_5 simple core)"}))


@hostile("C25", "R1: Out(S_6) promoted to BOUND / WITNESSED / LOCAL_DERIVED without evidence")
def _c25(dst):
    def f(d):
        d["degree_ladder_authority"]["Out_S6_label"].update({"status": "BOUND", "witnessed": True})
        d["degree_ladder_authority"]["local_derived"]["items"].append("Out_S6_exceptional_outer_automorphism")
        d["degree_ladder_authority"]["identified_unbound"]["items"].remove("Out_S6_exceptional_outer_automorphism")
    _edit_both(dst, f)


@hostile("C26", "R1: F2 renamed back to a radical-solvability theorem claim")
def _c26(dst):
    _edit_both(dst, lambda d: [d["lanes"][L]["falsifiers"].update({"F2": "S_N_SOLVABILITY_CLIFF_DOES_NOT_FORCE_TARGET_PREDICATE_CHANGE"}) for L in d["lanes"]])


@hostile("C27", "R1: degree_ladder_authority matrix deleted from the canonical result")
def _c27(dst):
    _edit(dst / "result.v0.1.json", lambda d: d.pop("degree_ladder_authority"))


@hostile("C28", "R1: preregistration-time label 'EXTERNAL_ESTABLISHED' copied onto the canonical ledger")
def _c28(dst):
    _edit(dst / "source-ledger.v0.1.json", lambda d: d["sources"][0].update({"status": "IDENTIFIED", "notes": "EXTERNAL_ESTABLISHED classical facts"}))


def _edit_both(dst, fn):
    _edit(dst / "adjudication.v0.1.json", fn)
    _edit(dst / "result.v0.1.json", fn)


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


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

def build() -> Dict[str, Any]:
    pkg_tg = q01.load_artifacts(c.DIR_TG)
    pre = json.loads((BASE / "preregistration.v0.1.json").read_text(encoding="utf-8"))
    recs = reclassify(pre, BASE / "cells")
    for r in recs:
        r["claimed_inferences"] = []
    dump(BASE, "cell-results.v0.1.json", {"schema_version": "miskatonic.formal-discovery.hvb-01c-cell-results.v0.1", "work_order": c.WORK_ORDER,
                                          "provider_policy": pre["provider_policy"], "cells": recs})
    adj = c.adjudicate(pre, recs)
    adj.update({"schema_version": "miskatonic.formal-discovery.hvb-01c-adjudication.v0.1", "work_order": c.WORK_ORDER})
    dump(BASE, "adjudication.v0.1.json", adj)
    panel = {L: adj["lanes"][L]["TARGET_SEQUENCE"] for L in adj["lanes"]}
    cliff = {}
    for t, cliff_name in (("4->5", "S_4 -> S_5 group-solvability transition (LOCAL_DERIVED: S_4 solvable, S_5 not solvable, A_5 perfect)"), ("5->6", "S_5 -> S_6 (Out(S_6) exceptional-layer label IDENTIFIED_UNBOUND, not witnessed)")):
        lanes_nc = [L for L in adj["lanes"] if adj["lanes"][L]["transitions"][t] == "NO_CHANGE"]
        lanes_ch = [L for L in adj["lanes"] if adj["lanes"][L]["transitions"][t] == "CHANGES"]
        lanes_un = [L for L in adj["lanes"] if adj["lanes"][L]["transitions"][t] == "UNRESOLVED"]
        cliff[t] = (f"{cliff_name}: target predicate unchanged on lanes {lanes_nc}, changed on lanes {lanes_ch}, unresolved on lanes {lanes_un}. "
                    f"{'Unchanged lanes establish ' + c.FALSIFIER_TEXT['F2' if t == '4->5' else 'F3'] + ' for those lanes (does not force != has no mathematical relation). ' if lanes_nc else ''}"
                    f"{'A coincident change is recorded as an alignment only; no statement that the source-side layer produced the target change is made. ' if lanes_ch else ''}"
                    "Firewall: TRANSITION_ALIGNMENT != CAUSAL_TRANSPORT; DEGREE_LADDER_ASSOCIATION != CAUSATION_BY_GROUP_THEOREM.")
    result = {
        "schema_version": "miskatonic.formal-discovery.hvb-01c-result.v0.1", "work_order": c.WORK_ORDER,
        "canonical_start": c.FD_START, "mathematics_sha": c.MATH_SHA, "preregistration_commit": PREREG_COMMIT_01C,
        "disposition": adj["verdict"], "disposition_status": "PROPOSED_BY_EXECUTING_AGENT_PENDING_INDEPENDENT_REVIEW",
        "question": "after conditioning on the target coupling pair (lambda, mu), does the controlled background degree n still change ABELIAN_IDENTITY_COMPONENT(G_diff)?",
        "controlled_family": {str(n): {k: pre["controlled_family"][str(n)][k] for k in ("P_n", "f_n", "roots_ordered", "discriminant_of_f_n", "equation_class")} for n in c.DEGREES},
        "coupling_signatures": {l["lane"]: l["coupling_signature"] for l in pre["lanes"]},
        "background_signatures": {n: v["BACKGROUND_SIGNATURE"] for n, v in pre["background_signatures"].items()},
        "panel": panel, "panel_size": pre["panel_size"], "anchors_consumed": {L: {"cell": a["cell"], "package": a["package"], "predicate": a["ABELIAN_IDENTITY_COMPONENT"]} for L, a in pre["anchors"].items()},
        "lanes": {L: {k: v[k] for k in ("lambda", "mu", "TARGET_SEQUENCE", "lane_result", "COUPLING_PAIR_ALONE_INSUFFICIENT_ACROSS_DEGREE_LADDER", "witness", "transitions", "falsifiers", "unresolved_degrees")} for L, v in adj["lanes"].items()},
        "transitions": adj["transitions"], "cliff_statements": cliff, "degree_ladder_authority": adj["degree_ladder_authority"],
        "n6_timeout_state": {"cells": [r["cell"] for r in recs if r["n"] == 6], "predicate": "UNRESOLVED", "budget_s": pre["provider_policy"]["timeout_s_per_script"], "retries": 0,
                             "note": "no RESULT return was emitted before timeout on any n = 6 form; the repeated intermediate Maxima text 'No Liouvillian solutions exist' is not a verdict (PARTIAL_PROVIDER_PROGRESS != PROVIDER_VERDICT)"},
        "lanes_with_split": adj["lanes_with_split"], "lanes_partial": adj["lanes_partial"], "unresolved_cells": adj["unresolved_cells"],
        "rules_by_cell": {r["cell"]: (r["rule"] or "").split(":")[0].split(" (")[0] for r in recs},
        "provider": {"identity": pre["gate0"]["provider_identity"], "policy": pre["provider_policy"], "timeouts": [r["cell"] + ":" + f for r in recs for f, k in (("orig", "provider_verdict_original_form"), ("red", "provider_verdict_reduced_form")) if r[k] == "PROVIDER_TIMEOUT"]},
        "BO2": "CANONICALLY_REFUTED_NOT_REOPENED", "BO1": "NOT_EXECUTED", "BO3": "EXECUTED_BOUNDEDLY_IN_01C", "degrees_new": [4, 5, 6], "panel_degrees": [3, 4, 5, 6],
        "MORALES_RAMIS": "NOT_APPLIED", "INTEGRABILITY": "NO_CLAIM", "CHAOS": "NO_CLAIM", "FTT": "NOT_REQUIRED", "BURAU": "CONTROL_ONLY", "LAME": "N3_ONLY",
        "COUPLING_PAIR_UNIVERSALLY_SUFFICIENT": None, "DEGREE_IRRELEVANT": None, "claimed_inferences": [],
        "claim_ceiling": ["statements about the controlled centred unit-spacing family at E = -1, degrees 3..6, on four frozen coupling lanes only",
                          "COUPLING_PAIR_ALONE_INSUFFICIENT_ACROSS_DEGREE_LADDER is asserted only per lane where an actual TRUE/FALSE split is observed; it does not contradict 01B, which was a statement about one frozen n = 3 background",
                          "NO_DEGREE_EFFECT_OBSERVED_ON_FROZEN_LANE is not DEGREE_IRRELEVANT; a finite panel never yields COUPLING_PAIR_UNIVERSALLY_SUFFICIENT",
                          "TRUE/FALSE cells rest on the same provider and exact rules as 01A/01B (FALSE: provider completeness, case 1 independently excluded); UNRESOLVED cells are reported as such",
                          "degree-ladder labels: S_n solvability and A_n perfectness are LOCAL_DERIVED by exact finite-group computation; the generic radical-solvability interpretation, A_5 simplicity and Out(S_6) are IDENTIFIED_UNBOUND; no target predicate rests on any of them"],
        "permanent": ["CONTROLLED_BACKGROUND_FAMILY != UNIVERSAL_DEGREE_MODEL", "DEGREE_SIGNATURE != TARGET_GALOIS_PREDICATE", "DEGREE_LADDER_ASSOCIATION != CAUSATION_BY_GROUP_THEOREM",
                      "SAME_COUPLING != SAME_TARGET_EQUATION", "TRANSITION_ALIGNMENT != CAUSAL_TRANSPORT", "N3_LAME_MAP != ALL_DEGREES_ARE_LAME",
                      "NO_DEGREE_EFFECT_OBSERVED != DEGREE_IRRELEVANT", "DOES_NOT_FORCE != NO_MATHEMATICAL_RELATION", "NONABELIAN_G0 != CHAOS", "MEMOIZATION != EXECUTION_INPUT_AUTHORITY",
                      "GROUP_SOLVABILITY_TRANSITION != GENERIC_POLYNOMIAL_RADICAL_SOLVABILITY_THEOREM", "A5_PERFECT_LOCALLY_DERIVED != A5_SIMPLICITY_ESTABLISHED_HERE",
                      "DEGREE_EQUALS_6 != OUT_S6_THEOREM_CERTIFICATE", "PARTIAL_PROVIDER_PROGRESS != PROVIDER_VERDICT"],
    }
    dump(BASE, "result.v0.1.json", result)
    dump(BASE, "hostile-controls.v0.1.json", {"schema_version": "miskatonic.formal-discovery.hvb-01c-hostile-controls.v0.1", "work_order": c.WORK_ORDER, "all_rejected": None, "count": 0, "results": []})
    with tempfile.TemporaryDirectory() as tmp:
        hostile_res = run_hostile(BASE, Path(tmp))
    dump(BASE, "hostile-controls.v0.1.json", {"schema_version": "miskatonic.formal-discovery.hvb-01c-hostile-controls.v0.1", "work_order": c.WORK_ORDER, "all_rejected": all(h["rejected"] for h in hostile_res), "count": len(hostile_res), "results": hostile_res})
    return result


def main() -> int:
    if "--run" in sys.argv:
        pre = json.loads((BASE / "preregistration.v0.1.json").read_text(encoding="utf-8"))
        for r in run_provider(pre):
            print(r)
        return 0
    if "--check" not in sys.argv:
        r = build()
        print("disposition:", r["disposition"], "| panel:", r["panel"], "| unresolved:", r["unresolved_cells"])
    errors = validate(BASE)
    if errors:
        print("FAILED:", file=sys.stderr)
        for e in errors:
            print("  -", e, file=sys.stderr)
        return 1
    h = json.loads((BASE / "hostile-controls.v0.1.json").read_text())
    print(f"PASS: 01C package validates; hostile {sum(x['rejected'] for x in h['results'])}/{h['count']} rejected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
