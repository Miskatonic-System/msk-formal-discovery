"""WO-FORMAL-HAMILTONIAN-VARIATIONAL-BRIDGE-01C — coupling-conditioned degree-ladder residual test (BO-3).

Phase A  controlled background family  r_{n,j} = j - (n+1)/2, E = -1, P_n = -1 + prod (q - r_{n,j}), f_n = -2 prod (q - r_{n,j})   -> controlled_family()
Phase B  typed source degree/background signature per n (TG-01A certificates consumed read-only)                                   -> degree_signature()
Phase C  four frozen coupling lanes with n = 3 anchors CONSUMED from the canonical 01A/01B packages                                -> LANES, consume_anchor()
Phase D  preregistration of the 12 new (n = 4, 5, 6) x (A, B, C, D) cells, frozen BEFORE any provider run                           -> preregistration()
BO-3     per-lane TARGET_SEQUENCE, transitions 3->4, 4->5, 5->6, falsifiers F1/F2/F3                                                 -> adjudicate()

The question is NOT source topology alone -> G_diff (BO-2, canonically refuted, not reopened).  It is: once the target coupling
pair (lambda, mu) is held exactly fixed, does the controlled background degree still change ABELIAN_IDENTITY_COMPONENT(G_diff)?

Permanent:  CONTROLLED_BACKGROUND_FAMILY != UNIVERSAL_DEGREE_MODEL;  DEGREE_SIGNATURE != TARGET_GALOIS_PREDICATE;
            SAME_COUPLING != SAME_TARGET_EQUATION;  TRANSITION_ALIGNMENT != CAUSAL_TRANSPORT;  N3_LAME_MAP != ALL_DEGREES_ARE_LAME.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import sympy as sp
from sympy.combinatorics.named_groups import AlternatingGroup, SymmetricGroup

from . import bridge_01b as b01b
from . import bridge_experiment as bx
from . import bridge_runner as br
from . import qualification as q01

WORK_ORDER = "WO-FORMAL-HAMILTONIAN-VARIATIONAL-BRIDGE-01C"
FD_START = "d4a71a72b36a68fca60dfffb53737846c3cde41d"
MATH_SHA = bx.MATH_SHA
MATH_CANDIDATE_FREEZE_BLOB = "e0c5d4627dba5560ffc34740ac746c0fc632697d"      # program/hamiltonian-monodromy/controls-v0.1/candidate-freeze.v0.1.json @ MATH_SHA
EXPERIMENT_DIR = bx.REPO_ROOT / "experiments" / "hamiltonian-variational-bridge-01c"
DIR_01A = bx.EXPERIMENT_DIR
DIR_01B = b01b.EXPERIMENT_DIR
DIR_TG = q01.EXPERIMENT_DIR

q = sp.Symbol("q")
DEGREES = [3, 4, 5, 6]
NEW_DEGREES = [4, 5, 6]
ENERGY = sp.Integer(-1)
TRANSITIONS = ["3->4", "4->5", "5->6"]

# ---------------------------------------------------------------------------
# Phase A — controlled background family
# ---------------------------------------------------------------------------

def family_roots(n: int) -> List[sp.Rational]:
    return [sp.Rational(j) - sp.Rational(n + 1, 2) for j in range(1, n + 1)]


def controlled_family(n: int) -> Dict[str, Any]:
    roots = family_roots(n)
    R = sp.expand(sp.prod([q - r for r in roots]))
    P = sp.expand(ENERGY + R)                       # P_n = -1 + R_n
    f = sp.expand(2 * (ENERGY - P))                 # = -2 R_n
    froots = sorted(sp.roots(sp.Poly(f, q)).items(), key=lambda kv: (sp.re(kv[0]), sp.im(kv[0])))
    disc = sp.discriminant(f, q)
    spacing = sorted({roots[i + 1] - roots[i] for i in range(n - 1)})
    center = sum(roots) / n
    checks = {
        "deg_P_n_equals_n": sp.Poly(P, q).degree() == n,
        "f_n_equals_minus_2_R_n": sp.expand(f + 2 * R) == 0,
        "roots_of_f_n_equal_frozen_roots": [r for r, _ in froots] == roots,
        "roots_simple": all(m == 1 for _, m in froots) and len(froots) == n,
        "discriminant_nonzero": disc != 0,
        "center_zero": center == 0,
        "adjacent_spacing_one": spacing == [1],
    }
    return {
        "n": n, "E": str(ENERGY), "root_rule": "r_{n,j} = j - (n+1)/2, j = 1..n",
        "roots_ordered": [str(r) for r in roots], "R_n": str(R), "P_n": str(P), "f_n": str(f),
        "discriminant_of_f_n": str(disc), "discriminant_digest": bx.canonical_digest({"n": n, "disc": str(disc)}),
        "checks": checks, "all_checks_pass": all(checks.values()),
        "phase_curve": f"p^2 = f_{n}(q): hyperelliptic-type curve of degree {n} with {n} simple finite branch points" if n != 3 else "p^2 = f_3(q): nonsingular genus-1 curve (the canonical 01A/01B member)",
        "equation_class": "CANONICAL_N3_LAME_MEMBER" if n == 3 else f"ALGEBRAIC_NVE_{n}",
        "note": "controlled family, not a claim of natural uniqueness (CONTROLLED_BACKGROUND_FAMILY != UNIVERSAL_DEGREE_MODEL)",
    }


def target_equation_n(n: int, mu: sp.Rational, lam: sp.Rational) -> Dict[str, Any]:
    """f_n y'' + (f_n'/2) y' + (mu + lambda q) y = 0 and its exact reduced form z'' = r z (same gauge as 01A: y = f^(-1/4) z)."""
    fam = controlled_family(n)
    f = sp.sympify(fam["f_n"], locals={"q": q})
    c2, c1, c0 = f, sp.expand(sp.diff(f, q) / 2), sp.expand(mu + lam * q)
    a = sp.cancel(c1 / c2)
    b = sp.cancel(c0 / c2)
    r = sp.cancel(a ** 2 / 4 + sp.diff(a, q) / 2 - b)
    num, den = sp.fraction(sp.factor(r))
    poles = sorted(sp.roots(sp.Poly(sp.denom(sp.together(r)), q)).items(), key=lambda kv: (sp.re(kv[0]), sp.im(kv[0])))
    return {
        "mu": str(mu), "lambda": str(lam),
        "original": {"c2": str(c2), "c1": str(c1), "c0": str(c0), "equation": f"({c2}) y'' + ({c1}) y' + ({c0}) y = 0"},
        "original_digest": bx.canonical_digest({"c2": str(c2), "c1": str(c1), "c0": str(c0)}),
        "normalization": {"gauge": "y = exp(-(1/2) int a dq) z, a = c1/c2, b = c0/c2", "a": str(a), "b": str(b), "r": str(r), "r_factored": f"({num})/({den})",
                          "scope": "the gauge factor exp(-(1/2) int a) = f^(-1/4) is algebraic over C(q) (a = f'/(2f)), so the identity component of the differential Galois group is unchanged (AMW Prop 6.2/3.4, bound in the 00A ledger); Galois groups of the two forms may differ by a finite extension"},
        "reduced": {"equation": f"y'' = ({r}) y", "r": str(r)},
        "reduced_digest": bx.canonical_digest({"r": str(r)}),
        "poles_of_r": [str(p) for p, _ in poles],
        "order_of_r_at_infinity": int(sp.degree(sp.Poly(den, q)) - sp.degree(sp.Poly(num, q))),
        "maxima_original": f"({sp.sstr(c2)})*'diff(y,x,2)+({sp.sstr(c1)})*'diff(y,x)+({sp.sstr(c0)})*y=0".replace("q", "x").replace("**", "^"),
        "maxima_reduced": f"'diff(y,x,2)=({sp.sstr(r)})*y".replace("q", "x").replace("**", "^"),
    }


def pc1_n3_member_identity() -> Dict[str, Any]:
    """PC1: the generated n = 3 member is identical to the canonical 01A/01B member, equation by equation."""
    fam = controlled_family(3)
    canon = bx.frozen_member()
    same_member = fam["P_n"] == canon["P_3"] and fam["f_n"] == canon["f_{a,E} = 2(E - P_3)"] and fam["E"] == canon["E"] and fam["roots_ordered"] == canon["roots_of_f_ordered"]
    eq_checks = {}
    for lane in LANES:
        ours = target_equation_n(3, sp.Rational(lane["mu"]), sp.Rational(lane["lambda"]))
        theirs = bx.target_equation(sp.Rational(lane["mu"]), sp.Rational(lane["lambda"]))
        eq_checks[lane["lane"]] = ours == theirs
    return {"P_3": fam["P_n"], "E": fam["E"], "f_3": fam["f_n"], "roots": fam["roots_ordered"], "member_identical": bool(same_member),
            "lane_equations_identical_to_bx_target_equation": eq_checks, "pass": bool(same_member and all(eq_checks.values()))}


# ---------------------------------------------------------------------------
# Phase B — source degree / background signature (TG-01A certificates consumed read-only)
# ---------------------------------------------------------------------------
HURWITZ_KEY = {3: "n3_generic", 4: "n4_involutions_00A", 5: "n5_generic", 6: "n6_generic"}


def degree_ladder_properties(n: int) -> Dict[str, Any]:
    """Source-authority degree-ladder labels with a cheap mechanical corroboration (derived series computed exactly).

    The classical facts (S_3, S_4 solvable; S_5, S_6 not solvable with a perfect A_n core; Out(S_6) nontrivial) are labels.
    Nothing in the BO-3 adjudication depends on them: DEGREE_SIGNATURE != TARGET_GALOIS_PREDICATE.
    """
    G = SymmetricGroup(n)
    series = [int(g.order()) for g in G.derived_series()]
    A = AlternatingGroup(n)
    perfect_core = bool(A.derived_subgroup().order() == A.order())
    labels = {3: "S_3 solvable", 4: "S_4 solvable", 5: "S_5 nonsolvable; A_5 perfect/simple core appears (radical-solvability cliff 4->5)",
              6: "S_6 nonsolvable; exceptional Out(S_6) layer present (classical label; not bound; not load-bearing)"}
    return {
        "S_n_derived_series_orders": series, "S_n_solvable": bool(G.is_solvable), "A_n_perfect": perfect_core,
        "label": labels[n],
        "Out_S_n_exceptional": n == 6,
        "authority": {"classical_facts_status": "EXTERNAL_ESTABLISHED (classical); no source record bound in any consumed ledger; derived-series and perfectness corroborated mechanically here (LOCAL_DERIVED); Out(S_6) is a label only",
                      "mathematics_degree_ladder_firewall": "consumed read-only from candidate-freeze.v0.1.json@" + MATH_SHA[:12] + " (blob " + MATH_CANDIDATE_FREEZE_BLOB[:12] + "): n is an experimental coordinate; no inference degree 5 / degree 6 / degree >= 5 -> nonintegrability or chaos; no Out(S6) -> Abel-Ruffini",
                      "expected_control_absent": "docs/TOPOLOGICAL_GALOIS_DEGREE_LADDER_CONTROL.md named in the Mathematics candidate freeze does not exist at " + MATH_SHA[:12] + "; nothing was rederived to replace it"},
    }


def degree_signature(n: int, pkg_tg: Dict[str, Any]) -> Dict[str, Any]:
    fam = controlled_family(n)
    s1 = pkg_tg["certificates/s1-permutation-quotient.v0.1.json"][str(n)]
    s2 = pkg_tg["certificates/s2-artin-action.v0.1.json"][str(n)]
    hz = pkg_tg["certificates/hurwitz-action.v0.1.json"][HURWITZ_KEY[n]]
    return {
        "n": n, "roots_ordered": fam["roots_ordered"], "discriminant_digest": fam["discriminant_digest"],
        "B_n": {"generators": f"sigma_1..sigma_{n - 1}", "relations": "braid relations sigma_i sigma_{i+1} sigma_i = sigma_{i+1} sigma_i sigma_{i+1}, [sigma_i, sigma_j] = 1 for |i-j| >= 2", "strands": n},
        "pi_perm_certificate": {"key": str(n), "image_size": s1["image_size"], "surjective": s1["surjective"], "result": s1["result"], "digest": bx.canonical_digest(s1)},
        "artin_certificate": {"key": str(n), "result": s2["result"], "digest": bx.canonical_digest(s2)},
        "hurwitz_certificate": {"key": HURWITZ_KEY[n], "tuple_label": hz["tuple_label"], "result": hz["result"], "digest": bx.canonical_digest(hz),
                                "note": "n = 4 is qualified on the 00A involution tuple, not on a generic tuple" if n == 4 else "generic tuple"},
        "degree_ladder": degree_ladder_properties(n),
    }


def background_signature(n: int, pkg_tg: Dict[str, Any]) -> Dict[str, Any]:
    fam = controlled_family(n)
    ds = degree_signature(n, pkg_tg)
    payload = {"n": n, "E": fam["E"], "P_n": fam["P_n"], "f_n": fam["f_n"], "roots_ordered": fam["roots_ordered"],
               "source_degree_certificates": {"pi_perm": ds["pi_perm_certificate"]["digest"], "artin": ds["artin_certificate"]["digest"], "hurwitz": ds["hurwitz_certificate"]["digest"]}}
    return {"payload": payload, "BACKGROUND_SIGNATURE": bx.canonical_digest(payload)}


# ---------------------------------------------------------------------------
# Phase C — coupling lanes and consumed n = 3 anchors
# ---------------------------------------------------------------------------
LANES: List[Dict[str, Any]] = [
    {"lane": "A", "lambda": "1", "mu": "0", "anchor": {"package": "01A", "cell": "c3"}, "accepted_n3_predicate": "TRUE",
     "design": "accepted abelian integer-Lame point (ell = 1 on the n = 3 member)"},
    {"lane": "B", "lambda": "2", "mu": "0", "anchor": {"package": "01A", "cell": "c5"}, "accepted_n3_predicate": "FALSE",
     "design": "accepted nonabelian non-half-integer point (ell irrational on the n = 3 member)"},
    {"lane": "C", "lambda": "3/8", "mu": "0", "anchor": {"package": "01B", "cell": "d7"}, "accepted_n3_predicate": "TRUE",
     "design": "the half-integer Brioschi-Halphen-Crawford finite point (ell = 1/2, B = 0 on the n = 3 member)"},
    {"lane": "D", "lambda": "3/8", "mu": "1/2", "anchor": {"package": "01B", "cell": "d8"}, "accepted_n3_predicate": "FALSE",
     "design": "same half-integer lambda with the accessory parameter moved off the accepted finite point"},
]


def coupling_signature(lam: str, mu: str) -> str:
    return bx.canonical_digest({"lambda": str(sp.Rational(lam)), "mu": str(sp.Rational(mu))})


def consume_anchor(lane: Dict[str, Any], pkg_a: Dict[str, Any], pkg_b: Dict[str, Any]) -> Dict[str, Any]:
    """The n = 3 anchor is CONSUMED from the canonical package (record digest + log digest), never recomputed."""
    pkg = {"01A": pkg_a, "01B": pkg_b}[lane["anchor"]["package"]]
    cr = pkg["cell-results.v0.1.json"]
    rec = next(c for c in cr["cells"] if c["cell"] == lane["anchor"]["cell"])
    if (rec["mu"], rec["lambda"]) != (lane["mu"], lane["lambda"]):
        raise ValueError(f"anchor {lane['anchor']} does not carry the lane coupling")
    return {"n": 3, "cell": rec["cell"], "package": lane["anchor"]["package"], "origin": "CONSUMED_CANONICAL",
            "lambda": rec["lambda"], "mu": rec["mu"], "ABELIAN_IDENTITY_COMPONENT": rec["ABELIAN_IDENTITY_COMPONENT"], "rule": rec["rule"],
            "original_digest": rec["original_digest"], "reduced_digest": rec["reduced_digest"],
            "record_digest": bx.canonical_digest(rec), "package_log_digest": cr["log_digest"], "package_script_digest": cr["script_digest"]}


# ---------------------------------------------------------------------------
# Phase D — preregistration (frozen BEFORE any provider run)
# ---------------------------------------------------------------------------
PROVIDER_POLICY = {
    "scripts": "one Maxima script per (cell, form): cells/<cell>_orig.mac and cells/<cell>_red.mac, each digest-bound to its own log",
    "timeout_s_per_script": 1800, "retries": 0, "parallel_workers": 6,
    "timeout_semantics": "a timed-out or absent provider result is recorded as PROVIDER_TIMEOUT / UNPARSED for that form and the cell is UNRESOLVED unless a provider-independent exact rule (RU case-1 form) resolves it; UNRESOLVED is a valid outcome",
    "rules": "R4, R2L, RU, RD exactly as in 01A/01B; no rule is weakened to force resolution",
}
EXPECTATIONS = {
    "target_predicate_expectations": "NONE_RECORDED",
    "note": "no per-cell target-predicate expectation is recorded; cells are fixed by the lane x degree design, not chosen from outputs; no n >= 4 equation is labelled Lame (N3_LAME_MAP != ALL_DEGREES_ARE_LAME)",
}


def new_cells() -> List[Dict[str, Any]]:
    out = []
    for n in NEW_DEGREES:
        fam = controlled_family(n)
        for lane in LANES:
            eq = target_equation_n(n, sp.Rational(lane["mu"]), sp.Rational(lane["lambda"]))
            out.append({"cell": f"n{n}_{lane['lane']}", "n": n, "lane": lane["lane"], "E": fam["E"], "P_n": fam["P_n"], "f_n": fam["f_n"], "roots_ordered": fam["roots_ordered"],
                        "equation_class": fam["equation_class"], "coupling_signature": coupling_signature(lane["lambda"], lane["mu"]), **eq,
                        "expected_authority_ceiling": "provider (Maxima kovacicODE, qualified in 01A) + exact rules R4/R2L/RU/RD; FALSE requires case 4 on both forms; TRUE requires an exact Picard-Vessiot rule; otherwise UNRESOLVED"})
    return out


def preregistration(pkg_a: Dict[str, Any], pkg_b: Dict[str, Any], pkg_tg: Dict[str, Any]) -> Dict[str, Any]:
    res_b, adj_b = pkg_b["result.v0.1.json"], pkg_b["adjudication.v0.1.json"]
    gate0_checks = {
        "BO2": pkg_b["result.v0.1.json"]["BO2"], "01B_verdict": res_b["disposition"],
        "pooled_cell_count": res_b["pooled_summary"]["pooled_cell_count"], "distinct_lambda_count": res_b["pooled_summary"]["distinct_lambda_count"],
        "universal_half_integer_only_claim": res_b["mu_dependence_scope"]["universal_half_integer_only_claim"],
    }
    cells = new_cells()
    anchors = {lane["lane"]: consume_anchor(lane, pkg_a, pkg_b) for lane in LANES}
    lanes = [{**lane, "coupling_signature": coupling_signature(lane["lambda"], lane["mu"])} for lane in LANES]
    bgs = {str(n): background_signature(n, pkg_tg) for n in DEGREES}
    return {
        "schema_version": "miskatonic.formal-discovery.hvb-01c-preregistration.v0.1",
        "work_order": WORK_ORDER,
        "gate0": {"formal_discovery_start": FD_START, "mathematics_sha": MATH_SHA, "candidate_freeze_digest": bx.CANDIDATE_FREEZE_DIGEST,
                  "mathematics_candidate_freeze_blob": MATH_CANDIDATE_FREEZE_BLOB,
                  "01a_result_digest": bx.canonical_digest(pkg_a["result.v0.1.json"]), "01a_adjudication_digest": bx.canonical_digest(pkg_a["adjudication.v0.1.json"]),
                  "01b_result_digest": bx.canonical_digest(res_b), "01b_adjudication_digest": bx.canonical_digest(adj_b),
                  "tg_qualification_result_digest": bx.canonical_digest(pkg_tg["qualification-result.v0.1.json"]),
                  "checks": gate0_checks,
                  "provider_identity": {"maxima": "5.49.0", "kovacicODE_sha256": br.KOVACIC_MAC_SHA256, "parity_with_01a": True}},
        "source_signature_01a": pkg_a["preregistration.v0.1.json"]["source_signature"],
        "controlled_family": {str(n): controlled_family(n) for n in DEGREES},
        "pc1": pc1_n3_member_identity(),
        "degree_signatures": {str(n): degree_signature(n, pkg_tg) for n in DEGREES},
        "background_signatures": bgs,
        "lanes": lanes,
        "anchors": anchors,
        "cells": cells, "new_cell_count": len(cells), "panel_size": len(cells) + len(anchors),
        "expectations": EXPECTATIONS,
        "provider_policy": PROVIDER_POLICY,
        "rules": ["BO-2 is not reopened; BO-1 not executed; Morales-Ramis not applied",
                  "no lane, degree or cell may be added, removed or altered after the first provider run",
                  "n = 3 anchors are consumed from canonical 01A/01B evidence, never rerun",
                  "the coupling pair (lambda, mu) is identical across n = 3..6 inside a lane (one COUPLING_SIGNATURE per lane)",
                  "only the background (n, P_n, f_n, roots) varies inside a lane; E = -1 throughout; no floats",
                  "n >= 4 equations are ALGEBRAIC_NVE_n, never labelled Lame", "UNRESOLVED is a valid outcome; no rule is weakened"],
    }


def write_preregistration(base: Path = EXPERIMENT_DIR) -> Dict[str, Any]:
    base.mkdir(parents=True, exist_ok=True)
    pre = preregistration(_load(DIR_01A), _load(DIR_01B), q01.load_artifacts(DIR_TG))
    (base / "preregistration.v0.1.json").write_text(json.dumps(pre, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return pre


def _load(base: Path) -> Dict[str, Any]:
    return {p.name: json.loads(p.read_text(encoding="utf-8")) for p in sorted(base.glob("*.json"))}


# ---------------------------------------------------------------------------
# BO-3 adjudication
# ---------------------------------------------------------------------------
FALSIFIER_TEXT = {
    "F1": "FULL_COUPLING_PAIR_ALONE_INSUFFICIENT_ACROSS_BACKGROUND",
    "F2": "S_N_SOLVABILITY_CLIFF_DOES_NOT_FORCE_TARGET_PREDICATE_CHANGE",
    "F3": "OUTER_AUTOMORPHISM_S6_DOES_NOT_FORCE_TARGET_PREDICATE_CHANGE",
}


def adjudicate(pre: Dict[str, Any], cells: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_id = {c["cell"]: c for c in cells}
    lanes_out: Dict[str, Any] = {}
    transitions: Dict[str, Dict[str, Any]] = {t: {} for t in TRANSITIONS}
    for lane in pre["lanes"]:
        L = lane["lane"]
        seq = {"3": pre["anchors"][L]["ABELIAN_IDENTITY_COMPONENT"]}
        for n in NEW_DEGREES:
            rec = by_id.get(f"n{n}_{L}")
            seq[str(n)] = rec["ABELIAN_IDENTITY_COMPONENT"] if rec else "MISSING"
        resolved = {k: v for k, v in seq.items() if v in ("TRUE", "FALSE")}
        vals = set(resolved.values())
        unresolved = [k for k, v in seq.items() if v not in ("TRUE", "FALSE")]
        if len(vals) == 2:
            lane_result, insufficient = "DEGREE_CONDITIONED_TARGET_VARIATION_OBSERVED", True
        elif unresolved:
            lane_result, insufficient = "LANE_PARTIAL", False
        else:
            lane_result, insufficient = "NO_DEGREE_EFFECT_OBSERVED_ON_FROZEN_LANE", False
        witness = None
        if insufficient:
            t_ = next(k for k, v in resolved.items() if v == "TRUE"); f_ = next(k for k, v in resolved.items() if v == "FALSE")
            witness = {"TRUE": {"n": int(t_), "cell": "anchor" if t_ == "3" else f"n{t_}_{L}"}, "FALSE": {"n": int(f_), "cell": "anchor" if f_ == "3" else f"n{f_}_{L}"}}
        tr = {}
        for t in TRANSITIONS:
            a, bb = t.split("->")
            if seq[a] in ("TRUE", "FALSE") and seq[bb] in ("TRUE", "FALSE"):
                tr[t] = "CHANGES" if seq[a] != seq[bb] else "NO_CHANGE"
            else:
                tr[t] = "UNRESOLVED"
            transitions[t][L] = {"from": seq[a], "to": seq[bb], "target_predicate": tr[t], "causal_attribution": "NONE"}
        falsifiers = {}
        falsifiers["F1"] = FALSIFIER_TEXT["F1"] if insufficient else ("NOT_TRIGGERED (no TRUE/FALSE split observed on this lane)" if not unresolved else "NOT_ADJUDICABLE (unresolved cells)")
        falsifiers["F2"] = FALSIFIER_TEXT["F2"] if tr["4->5"] == "NO_CHANGE" else ("NOT_TRIGGERED (4->5 change coincided on this lane; no causal statement)" if tr["4->5"] == "CHANGES" else "NOT_ADJUDICABLE (4->5 unresolved)")
        falsifiers["F3"] = FALSIFIER_TEXT["F3"] if tr["5->6"] == "NO_CHANGE" else ("NOT_TRIGGERED (5->6 change coincided on this lane; no causal statement)" if tr["5->6"] == "CHANGES" else "NOT_ADJUDICABLE (5->6 unresolved)")
        lanes_out[L] = {"lambda": lane["lambda"], "mu": lane["mu"], "coupling_signature": lane["coupling_signature"], "TARGET_SEQUENCE": seq,
                        "unresolved_degrees": unresolved, "lane_result": lane_result,
                        "COUPLING_PAIR_ALONE_INSUFFICIENT_ACROSS_DEGREE_LADDER": insufficient, "witness": witness,
                        "transitions": tr, "falsifiers": falsifiers}
    results = [v["lane_result"] for v in lanes_out.values()]
    if any(r == "DEGREE_CONDITIONED_TARGET_VARIATION_OBSERVED" for r in results):
        verdict = "BO3_DEGREE_CONDITIONED_VARIATION_OBSERVED"
    elif all(r == "NO_DEGREE_EFFECT_OBSERVED_ON_FROZEN_LANE" for r in results):
        verdict = "BO3_NO_VARIATION_ON_FROZEN_COUPLINGS"
    else:
        verdict = "BO3_PARTIAL"
    for t in TRANSITIONS:
        transitions[t]["source_side_label"] = {"3->4": "S_3 -> S_4 (both solvable)", "4->5": "S_4 -> S_5: source radical-solvability cliff (S_5 nonsolvable, A_5 perfect core)", "5->6": "S_5 -> S_6: exceptional Out(S_6) layer present (classical label; not bound; not load-bearing)"}[t]
        transitions[t]["statement"] = _transition_statement(t, {L: transitions[t][L]["target_predicate"] for L in lanes_out})
    return {
        "verdict": verdict, "lanes": lanes_out, "transitions": transitions,
        "lanes_with_split": [L for L, v in lanes_out.items() if v["COUPLING_PAIR_ALONE_INSUFFICIENT_ACROSS_DEGREE_LADDER"]],
        "lanes_partial": [L for L, v in lanes_out.items() if v["lane_result"] == "LANE_PARTIAL"],
        "unresolved_cells": [c["cell"] for c in cells if c["ABELIAN_IDENTITY_COMPONENT"] not in ("TRUE", "FALSE")],
        "COUPLING_PAIR_UNIVERSALLY_SUFFICIENT": None, "DEGREE_IRRELEVANT": None,
        "not_claimed": "NO_DEGREE_EFFECT_OBSERVED_ON_FROZEN_LANE is never promoted to DEGREE_IRRELEVANT; a split is never promoted to a universal statement; a transition alignment is never a causal transport (TRANSITION_ALIGNMENT != CAUSAL_TRANSPORT); COUPLING_PAIR_UNIVERSALLY_SUFFICIENT is never emitted from a finite panel",
    }


def _transition_statement(t: str, by_lane: Dict[str, str]) -> str:
    cliff = {"3->4": "the 3->4 transition", "4->5": "the 4->5 source solvability cliff", "5->6": "the 5->6 transition carrying the Out(S_6) label"}[t]
    parts = []
    for L, v in by_lane.items():
        if v == "NO_CHANGE":
            parts.append(f"No target-predicate change was observed across {cliff} on lane {L}.")
        elif v == "CHANGES":
            parts.append(f"A target-predicate change coincided with {cliff} on lane {L} (coincidence recorded; no causal attribution).")
        else:
            parts.append(f"The target predicate is unresolved across {cliff} on lane {L}.")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# experiment-local source ledger (additive; nothing upstream is mutated or upgraded)
# ---------------------------------------------------------------------------
LEDGER_BLOBS = {"01A": "61c715bceab99435e8b1f10b3a579cb74add51ba", "01B": "bc6740eee0a55e9612776540df4e4fcc840667c1", "TG": "996fe1233f5e3cc286055d354a1b28aae3d799d1"}


def source_ledger() -> Dict[str, Any]:
    fd = "Miskatonic-System/msk-formal-discovery"
    return {
        "schema_version": "miskatonic.formal-discovery.hvb-01c-source-ledger.v0.1",
        "ledger_id": "hvb-01c-sources",
        "policy": "Experiment-local additive custody. Morales-Ruiz 1999 remains UNAVAILABLE and is NOT upgraded. The Lame sources (Maier 2002, Chou-Wang-Wu 2024) are consumed only as the context of the n = 3 anchors; they are NOT applied to n = 4, 5, 6 (N3_LAME_MAP != ALL_DEGREES_ARE_LAME). The degree-ladder classical facts are labels; no target predicate rests on them.",
        "consumed_ledgers": [
            {"repository": fd, "commit": FD_START, "path": "experiments/hamiltonian-variational-bridge-01a/source-ledger.v0.1.json", "blob": LEDGER_BLOBS["01A"],
             "records_relied_on": {"src-hvb-smith-1984": {"status": "BOUND", "used_for": "provider provenance (unchanged provider, identity parity)"},
                                   "src-hvb-morales-ruiz-1999-attempt": {"status": "UNAVAILABLE", "used_for": "NOTHING; not upgraded; does not block BO-3 (direct differential-Galois classification)"}}},
            {"repository": fd, "commit": FD_START, "path": "experiments/hamiltonian-variational-bridge-01b/source-ledger.v0.1.json", "blob": LEDGER_BLOBS["01B"],
             "records_relied_on": {"src-hvb-maier-2002": {"status": "BOUND", "used_for": "context of the n = 3 anchors only (lanes C/D sit on the ell = 1/2 Lame family of the n = 3 member); NOT applied to n >= 4"},
                                   "src-hvb-chou-wang-wu-2024": {"status": "BOUND", "used_for": "context of the n = 3 anchors only; NOT applied to n >= 4"}}},
            {"repository": fd, "commit": FD_START, "path": "experiments/topological-galois-source-representation-01a/source-ledger.v0.1.json", "blob": LEDGER_BLOBS["TG"],
             "records_relied_on": {"src-tg-birman-brendle-2005": {"status": "BOUND", "used_for": "convention freeze behind the consumed pi_perm / Artin / Hurwitz certificates for n = 3..6"}}},
            {"repository": "Miskatonic-System/miskatonic-mathematics", "commit": MATH_SHA, "path": "program/hamiltonian-monodromy/controls-v0.1/sources.v0.1.json", "blob": "4cafe426d4b23b82a93b74d7c946d97bb95c0b41",
             "records_relied_on": {"src-hmc-acosta-morales-weil-2010": {"status": "BOUND", "used_for": "Kovacic four cases; identity-component invariance under algebraic base change (unchanged rules)"}}},
            {"repository": "Miskatonic-System/miskatonic-mathematics", "commit": MATH_SHA, "path": "program/hamiltonian-monodromy/controls-v0.1/candidate-freeze.v0.1.json", "blob": MATH_CANDIDATE_FREEZE_BLOB,
             "records_relied_on": {"frozen.degree_ladder_firewall": {"status": "CONSUMED_READ_ONLY", "used_for": "n is an experimental coordinate; no inference degree >= 5 -> nonintegrability/chaos; no Out(S6) -> Abel-Ruffini; no G60 bridge"},
                                   "frozen.expected_controls[2]": {"status": "ABSENT_AT_PIN", "used_for": "the named docs/TOPOLOGICAL_GALOIS_DEGREE_LADDER_CONTROL.md does not exist at the pinned SHA; nothing was rederived to replace it"}}},
        ],
        "sources": [
            {"schema_version": "miskatonic.mathematics-source-record.v0.1", "source_id": "src-hvb-degree-ladder-classical-facts",
             "title": "Classical degree-ladder facts: S_3, S_4 solvable; S_5, S_6 nonsolvable with perfect A_n core; Out(S_6) nontrivial",
             "authors_or_authority": "classical (Abel-Ruffini / Galois; Sylvester-Holder for Out(S_6))", "source_type": "CLASSICAL_FACT",
             "canonical_url_or_identifier": "none bound", "version_or_date": "n/a", "retrieved_at": None, "content_digest": None,
             "claim_scope": "labels in the source degree signature and the transition table only; derived series and perfectness are corroborated mechanically (sympy.combinatorics) in degree_ladder_properties(); Out(S_6) is a label with no mechanical witness here",
             "status": "IDENTIFIED", "notes": "No document is bound. No target predicate, lane result, transition verdict or falsifier depends on these labels (DEGREE_SIGNATURE != TARGET_GALOIS_PREDICATE; DEGREE_LADDER_ASSOCIATION != CAUSATION_BY_GROUP_THEOREM)."},
        ],
        "DEGREE_LADDER_AUTHORITY": "LABELS_ONLY (classical facts IDENTIFIED, mechanical corroboration of derived series; not load-bearing)",
        "LAME_AUTHORITY_SCOPE": "N3_ONLY (consumed from 01B; not extended to n = 4, 5, 6)",
    }


def write_source_ledger(base: Path = EXPERIMENT_DIR) -> None:
    (base / "source-ledger.v0.1.json").write_text(json.dumps(source_ledger(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    pre = write_preregistration()
    write_source_ledger()
    print("preregistration digest", bx.canonical_digest(pre), "| new cells", pre["new_cell_count"], "| panel", pre["panel_size"], "| PC1", pre["pc1"]["pass"])
