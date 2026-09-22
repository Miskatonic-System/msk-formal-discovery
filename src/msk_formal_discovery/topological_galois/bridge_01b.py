"""WO-FORMAL-HAMILTONIAN-VARIATIONAL-BRIDGE-01B — Lamé parameter map and minimal missing-information qualification.

Phase A  exact parameter map (q = -2 wp, g2 = 1, g3 = 0; ell(ell+1) = 2 lambda, B = -mu)     -> lame_parameter_map()
Phase C  signature decomposition over the canonical 01A cells (historical evidence)              -> phase_c()
Phase D  preregistered accessory-parameter grid (mu varied at fixed lambda), run, adjudicate     -> preregistration(), adjudicate_d()

Reuses the frozen 01A member, SOURCE_SIGNATURE, provider and rules unchanged. BO-2 is not reopened.
POLYNOMIAL_DEGREE_n (= 3) != LAME_INDEX_ell.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import sympy as sp

from . import bridge_experiment as bx
from . import bridge_runner as br

WORK_ORDER = "WO-FORMAL-HAMILTONIAN-VARIATIONAL-BRIDGE-01B"
FD_START = "11c6e8cda42eb0b23c480a346f35c1bfe337a0fe"
EXPERIMENT_DIR = bx.REPO_ROOT / "experiments" / "hamiltonian-variational-bridge-01b"
DIR_01A = bx.EXPERIMENT_DIR

q, t, x, mu, lam, ell = sp.symbols("q t x mu lambda ell")


# ---------------------------------------------------------------------------
# Phase A
# ---------------------------------------------------------------------------

def lame_parameter_map() -> Dict[str, Any]:
    wp = sp.Function("wp")(t)
    f = lambda y: sp.expand(-2 * y ** 3 + 2 * y)                      # the frozen f_{a,E}
    qq = -2 * wp
    # (i) from q'^2 = f(q) with q = -2 wp:  4 wp'^2 = f(-2 wp)  =>  wp'^2 = 4 wp^3 - wp
    wp_prime_sq = sp.expand(f(-2 * sp.Symbol("w")) / 4)               # in terms of w = wp
    w = sp.Symbol("w")
    g2 = -sp.Poly(wp_prime_sq, w).coeff_monomial(w)
    g3 = -sp.Poly(wp_prime_sq, w).coeff_monomial(1)
    lead = sp.Poly(wp_prime_sq, w).coeff_monomial(w ** 3)
    # (ii) converse: impose wp'^2 = 4 wp^3 - wp and check q'^2 - f(q) == 0 exactly
    qprime_sq = sp.expand(sp.diff(qq, t) ** 2).subs(sp.Derivative(wp, t) ** 2, 4 * wp ** 3 - wp)
    converse = sp.expand(qprime_sq - f(qq)) == 0
    # (iii) transformed NVE: xi'' + (mu + lambda q) xi = 0  ->  xi'' = [2 lambda wp - mu] xi
    rhs = sp.expand(-(mu + lam * qq))
    # (iv) the algebraic NVE in q is the Lame algebraic form in x = wp = -q/2 (same rational function field)
    fq = f(q)
    y = sp.Function("y")
    alg_q = fq * sp.diff(y(q), q, 2) + sp.diff(fq, q) / 2 * sp.diff(y(q), q) + (mu + lam * q) * y(q)
    p = 4 * x ** 3 - g2 * x - g3
    Y = sp.Function("Y")
    lame_alg = p * sp.diff(Y(x), x, 2) + sp.diff(p, x) / 2 * sp.diff(Y(x), x) - (ell * (ell + 1) * x + sp.Symbol("B")) * Y(x)
    # substitute q = -2x, y(q) = Y(x): d/dq = -(1/2) d/dx, d^2/dq^2 = (1/4) d^2/dx^2; compare coefficient-wise
    coeffs_ours = [sp.expand(fq.subs(q, -2 * x) / 4), sp.expand(-(sp.diff(fq, q) / 2).subs(q, -2 * x) / 2), sp.expand(mu - 2 * lam * x)]
    coeffs_lame = [sp.expand(p), sp.expand(sp.diff(p, x) / 2), sp.expand(-(2 * lam * x - mu))]
    factor = sp.cancel(coeffs_ours[0] / coeffs_lame[0])
    same = all(sp.expand(a - factor * b) == 0 for a, b in zip(coeffs_ours, coeffs_lame)) and factor.is_constant()
    e_roots = sorted(sp.roots(sp.Poly(p, x)).keys(), key=lambda r: (sp.re(r), sp.im(r)))
    return {
        "frozen_f": str(fq), "substitution": "q = -2 wp(t)",
        "derived_weierstrass_relation": f"wp'^2 = {sp.expand(wp_prime_sq)}", "g2": str(g2), "g3": str(g3), "leading_coefficient_4": lead == 4,
        "converse_check_qprime_sq_equals_f_of_q_given_wp_relation": bool(converse),
        "transformed_nve": f"xi'' = [{rhs}] xi", "lame_form": "xi'' = [ell(ell+1) wp(t) + B] xi",
        "parameter_map": {"ell(ell+1)": "2*lambda", "B": "-mu"},
        "algebraic_form_identity": {"x": "wp = -q/2", "lame_algebraic_form": f"({p}) Y'' + ({sp.diff(p, x) / 2}) Y' - (ell(ell+1) x + B) Y = 0", "our_algebraic_nve_in_x_equals_lame_form_times": str(factor), "identity_holds": bool(same),
                                    "note": "C(q) = C(x) (x = -q/2 is a linear change of the rational coordinate), so the differential Galois group over C(q) classified in 01A IS the Galois group of the algebraic Lame form over C(x)"},
        "e_i": [str(r) for r in e_roots], "harmonic_case": "g3 = 0: {e_i} = alpha{-1, 0, 1} with alpha = 1/2 (Maier 2002 Def. 3.2, J = 1)",
        "invariant": "POLYNOMIAL_DEGREE_n (= 3, the degree of P_3) != LAME_INDEX_ell (defined by ell(ell+1) = 2 lambda)",
        "ell_for_01a_lambdas": {str(l): [str(s) for s in sp.solve(sp.Eq(ell * (ell + 1), 2 * l), ell)] for l in (0, 1, 2, 3, -1)},
    }


def ell_of(lam_value) -> Dict[str, Any]:
    sols = sp.solve(sp.Eq(ell * (ell + 1), 2 * sp.Rational(lam_value)), ell)
    nonneg = [s for s in sols if s.is_real and s >= -sp.Rational(1, 2)]
    e = nonneg[0] if nonneg else sols[0]
    kind = ("INTEGER" if e.is_integer else "HALF_INTEGER" if (2 * e).is_integer else "REAL_NONHALFINTEGER" if e.is_real else "COMPLEX")
    return {"ell": str(e), "ell_kind": kind, "two_lambda": str(2 * sp.Rational(lam_value))}


# ---------------------------------------------------------------------------
# Phase C
# ---------------------------------------------------------------------------

def phase_c(cells_01a: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_lambda: Dict[str, Dict[str, str]] = {}
    for c in cells_01a:
        by_lambda.setdefault(c["lambda"], {})[c["mu"]] = c["ABELIAN_IDENTITY_COMPONENT"]
    consistent = {l: len(set(v.values())) == 1 for l, v in by_lambda.items()}
    return {
        "ORIGINAL_SOURCE_SIGNATURE": "{n, a, E, roots, pi_perm, Artin/Hurwitz} = 01A SOURCE_SIGNATURE (identical on all cells)",
        "candidates": {"AUGMENTED_LAMBDA": "ORIGINAL + lambda", "AUGMENTED_LAME_INDEX": "ORIGINAL + ell(ell+1) (= 2 lambda: a bijective relabelling of AUGMENTED_LAMBDA)", "AUGMENTED_FULL": "ORIGINAL + (lambda, mu)"},
        "historical_01a_pattern_by_lambda": {l: {"mu_values": v, "ell": ell_of(l), "predicate_constant_across_sampled_mu": consistent[l]} for l, v in sorted(by_lambda.items(), key=lambda kv: sp.Rational(kv[0]))},
        "question_1": "On the 8 accepted cells the predicate is constant across the sampled mu at every sampled lambda and separates lambda classes (ell integer -> TRUE; ell non-half-integer irrational or complex -> FALSE): CONSISTENT WITH lambda (equivalently ell(ell+1)) being load-bearing. Not a proof: finite grid, and no half-integer ell was sampled in 01A.",
        "question_2": "On the sampled cells mu did not change the predicate at fixed lambda. Whether mu CAN change it is exactly what Phase D tests; the Brioschi-Halphen-Crawford theorem (bound: Chou-Wang-Wu 2024 Thm 1.2) predicts a mu-dependence precisely at half-integer ell, which 01A did not sample.",
        "no_sufficiency_claim": True,
    }


# ---------------------------------------------------------------------------
# Phase D preregistration (frozen BEFORE any provider run)
# ---------------------------------------------------------------------------
GRID_D: List[Dict[str, Any]] = [
    {"cell": "d1", "mu": "-1", "lambda": "1", "role": "lambda classified TRUE in 01A (ell = 1), new mu"},
    {"cell": "d2", "mu": "1/2", "lambda": "1", "role": "lambda = 1, new mu"},
    {"cell": "d3", "mu": "3", "lambda": "1", "role": "lambda = 1, new mu"},
    {"cell": "d4", "mu": "-1", "lambda": "2", "role": "lambda classified FALSE in 01A (ell irrational), new mu"},
    {"cell": "d5", "mu": "1/2", "lambda": "2", "role": "lambda = 2, new mu"},
    {"cell": "d6", "mu": "3", "lambda": "2", "role": "lambda = 2, new mu"},
    {"cell": "d7", "mu": "0", "lambda": "3/8", "role": "ell = 1/2 (Brioschi-Halphen-Crawford family, m = 0), B = 0"},
    {"cell": "d8", "mu": "1/2", "lambda": "3/8", "role": "ell = 1/2, B = -1/2"},
    {"cell": "d9", "mu": "-1", "lambda": "3/8", "role": "ell = 1/2, B = 1"},
    {"cell": "d10", "mu": "2", "lambda": "3/8", "role": "ell = 1/2, B = -2"},
]
PRIOR_EXPECTATIONS_D = {
    "recorded_before_any_provider_run": True,
    "lambda=1": "all TRUE expected (integer ell; Lame-Hermite family) — expectation only, no bound authority for the Liouvillian integer-ell statement",
    "lambda=2": "all FALSE expected (ell irrational) — expectation only",
    "lambda=3/8": "designed falsifier: for ell = m + 1/2 with m = 0, Chou-Wang-Wu 2024 Thm 1.2 (BOUND) gives finite projective monodromy K_4 iff p_0(B) = 0 with p_0 weighted-homogeneous of degree 1 in B and coefficients in Z[g2/4, g3/4]; since B has weight 2 and no monomial in g2 (weight 4), g3 (weight 6) has weight 2, p_0(B) = c*B, so the finite case is exactly B = 0, i.e. mu = 0 (d7): expected TRUE (finite G, G^0 trivial). For mu != 0 (d8-d10) the group is NOT finite; whether it is SL_2 (FALSE) or infinite dihedral (TRUE) is NOT source-bound here and is left to the provider. A split between d7 and any of d8-d10 would establish LAMBDA_ALONE_INSUFFICIENT.",
    "basis_note": "expectations are design intent; the provider and the exact rules decide; cells are not chosen from outputs",
}


def preregistration(pkg_01a: Dict[str, Any]) -> Dict[str, Any]:
    pre_a = pkg_01a["preregistration.v0.1.json"]
    cells = []
    for g in GRID_D:
        eq = bx.target_equation(sp.Rational(g["mu"]), sp.Rational(g["lambda"]))
        cells.append({**g, **eq, "lame": ell_of(g["lambda"]), "B": str(-sp.Rational(g["mu"]))})
    return {
        "schema_version": "miskatonic.formal-discovery.hvb-01b-preregistration.v0.1",
        "work_order": WORK_ORDER,
        "gate0": {"formal_discovery_start": FD_START, "mathematics_sha": bx.MATH_SHA, "candidate_freeze_digest": bx.CANDIDATE_FREEZE_DIGEST,
                  "01a_preregistration_digest": bx.canonical_digest(pre_a), "01a_result_digest": bx.canonical_digest(pkg_01a["result.v0.1.json"]),
                  "provider_identity": {"maxima": "5.49.0", "kovacicODE_sha256": br.KOVACIC_MAC_SHA256, "parity_with_01a": True}},
        "frozen_member": pre_a["frozen_member"],
        "source_signature": pre_a["source_signature"],
        "lame_parameter_map": lame_parameter_map(),
        "grid": GRID_D, "grid_size": len(GRID_D),
        "prior_expectations": PRIOR_EXPECTATIONS_D,
        "cells": cells,
        "rules": ["BO-2 is not reopened", "no cell may be added, removed or altered after the first provider run on this grid",
                  "same frozen member, same SOURCE_SIGNATURE, same provider, same rules as 01A", "only (mu, lambda) vary; no floats", "n = 3 only"],
    }


def adjudicate_d(pre: Dict[str, Any], cells: List[Dict[str, Any]], cells_01a: List[Dict[str, Any]]) -> Dict[str, Any]:
    pooled = [{"cell": c["cell"], "mu": c["mu"], "lambda": c["lambda"], "predicate": c["ABELIAN_IDENTITY_COMPONENT"], "origin": "01A"} for c in cells_01a] + \
             [{"cell": c["cell"], "mu": c["mu"], "lambda": c["lambda"], "predicate": c["ABELIAN_IDENTITY_COMPONENT"], "origin": "01B"} for c in cells]
    by_lambda: Dict[str, List[Dict[str, Any]]] = {}
    for r in pooled:
        by_lambda.setdefault(r["lambda"], []).append(r)
    splits = []
    for l, rows in by_lambda.items():
        resolved = [r for r in rows if r["predicate"] in ("TRUE", "FALSE")]
        vals = {r["predicate"] for r in resolved}
        if len(vals) == 2:
            t_ = next(r for r in resolved if r["predicate"] == "TRUE"); f_ = next(r for r in resolved if r["predicate"] == "FALSE")
            splits.append({"lambda": l, "ell": ell_of(l), "TRUE": t_, "FALSE": f_})
    unresolved = [r["cell"] for r in pooled if r["predicate"] == "UNRESOLVED"]
    pooled_summary = pooled_statistics(cells_01a, cells)
    if splits:
        verdict = "LAMBDA_ALONE_INSUFFICIENT"
    elif unresolved:
        verdict = "ACCESSORY_PARAMETER_EFFECT_UNRESOLVED"
    else:
        verdict = "LAMBDA_NOT_FALSIFIED_AS_COORDINATE"
    single_mu = [l for l, rows in by_lambda.items() if len({r["mu"] for r in rows}) == 1]
    return {
        "pooled_summary": pooled_summary,
        "mu_dependence_scope": {
            "observed_split_lambdas": sorted({s_["lambda"] for s_ in splits}, key=lambda l: sp.Rational(l)),
            "observed_split_ells": sorted({s_["ell"]["ell"] for s_ in splits}),
            "single_sampled_mu_lambdas": sorted(single_mu, key=lambda l: sp.Rational(l)),
            "universal_half_integer_only_claim": False,
            "statement": "The only observed within-lambda predicate split in the pooled sample occurs at ell = 1/2 (lambda = 3/8). No universal claim is made that mu can affect the predicate only in half-integer-ell classes. Some other lambda classes, including lambda = -1 and lambda = 3, currently have only one sampled mu value, so absence of a split there is not evidence of mu-independence.",
        },
        "same_lambda_same_source_different_mu_different_predicate": splits,
        "per_lambda": {l: {"ell": ell_of(l), "rows": rows, "constant": len({r["predicate"] for r in rows if r["predicate"] != "UNRESOLVED"}) <= 1} for l, rows in sorted(by_lambda.items(), key=lambda kv: sp.Rational(kv[0]))},
        "unresolved_cells": unresolved,
        "verdict": verdict,
        "not_claimed": "LAMBDA_SUFFICIENT is never claimed from a finite grid. ORIGINAL + (lambda, mu) is the smallest OF THE THREE TESTED CANDIDATE SIGNATURES on which the predicate is a function across the pooled sampled cells; this is not a globally minimal or universally sufficient signature, and no claim is made that no other hidden coordinate exists.",
    }


def pooled_statistics(cells_01a: List[Dict[str, Any]], cells_01b: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Mechanically derived pooled cardinalities; lambda values ordered by exact rational value (never lexically)."""
    pooled = list(cells_01a) + list(cells_01b)
    lambdas = sorted({sp.Rational(c["lambda"]) for c in pooled})
    return {
        "pooled_cell_count": len(cells_01a) + len(cells_01b),
        "cells_01a": len(cells_01a), "cells_01b": len(cells_01b),
        "distinct_lambdas": [str(l) for l in lambdas],
        "distinct_lambda_count": len(lambdas),
        "ordering": "by exact rational numerical value, ascending",
    }
