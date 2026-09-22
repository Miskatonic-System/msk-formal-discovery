"""WO-FORMAL-HAMILTONIAN-VARIATIONAL-BRIDGE-01A — frozen n = 3 member, coupling grid, exact target equations.

This module owns everything that must exist BEFORE any differential-Galois computation:

  * the frozen member  (n = 3, P_3, E, f_{a,E}, roots)               -> frozen_member()
  * the SOURCE_SIGNATURE (digest over source data + 01A certificates) -> source_signature()
  * the preregistered coupling grid                                    -> GRID
  * for each cell the exact target ODE, its reduced form y'' = r y,
    the normalization derivation and the digests                        -> cell_equations()

Everything is exact (sympy Rational / Integer). No floating point. No Galois computation here.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

import sympy as sp

from . import qualification as q01

WORK_ORDER = "WO-FORMAL-HAMILTONIAN-VARIATIONAL-BRIDGE-01A"
REPO_ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT_DIR = REPO_ROOT / "experiments" / "hamiltonian-variational-bridge-01a"
PRED_DIR = q01.EXPERIMENT_DIR

FD_START = "a85dd51c1ecf9a94e88ff4a742029d1b321a2512"
MATH_SHA = "2337c7d744f176274997374a7d4057c7272f715d"
CANDIDATE_FREEZE_DIGEST = "889cc252226d801491a83bdd594e366fffc5a8bd1ef9379f5088bf9f65d78425"

q = sp.Symbol("q")
N = 3

# ---------------------------------------------------------------------------
# frozen member (chosen so that the roots of E - P_3 are rational and distinct; E != 0 deliberately)
# ---------------------------------------------------------------------------
A_COEFFS = [sp.Integer(-1), sp.Integer(-1), sp.Integer(0), sp.Integer(1)]   # P_3(q) = q^3 - q - 1
ENERGY = sp.Integer(-1)

# preregistered coupling grid (mu, lambda): (0,0) transparent control; several nonzero lambda; small; frozen BEFORE any Galois run.
# Rationale recorded for the reviewer (this is design intent, not an output): with f = -2(q^3 - q) the algebraic NVE is a
# Lame-form equation with n(n+1) = 2*lambda and B = 2*mu; the grid deliberately spans lambda values with 2*lambda a
# triangular-type value (0, 2, 6 <-> lambda 0, 1, 3) and lambda values that are not (2, -1), so that a fixed-source
# difference in the predicate is POSSIBLE. Expectations are recorded, cells are not chosen from outputs.
GRID: List[Dict[str, Any]] = [
    {"cell": "c1", "mu": "0", "lambda": "0", "role": "TRANSPARENT_CONTROL (0,0): direct Picard-Vessiot derivation required"},
    {"cell": "c2", "mu": "1", "lambda": "0", "role": "lambda = 0, mu != 0"},
    {"cell": "c3", "mu": "0", "lambda": "1", "role": "2*lambda = 2 = 1*2"},
    {"cell": "c4", "mu": "1", "lambda": "1", "role": "2*lambda = 2 = 1*2, mu != 0"},
    {"cell": "c5", "mu": "0", "lambda": "2", "role": "2*lambda = 4, not of the form m(m+1) with m integer"},
    {"cell": "c6", "mu": "1", "lambda": "2", "role": "2*lambda = 4, mu != 0"},
    {"cell": "c7", "mu": "0", "lambda": "3", "role": "2*lambda = 6 = 2*3"},
    {"cell": "c8", "mu": "1", "lambda": "-1", "role": "2*lambda = -2, negative"},
]
PRIOR_EXPECTATIONS = {
    "recorded_before_any_galois_run": True,
    "expected_abelian_identity_component": ["c1", "c2", "c3", "c4", "c7"],
    "expected_nonabelian_identity_component": ["c5", "c6", "c8"],
    "basis": "Lame-form correspondence n(n+1) = 2*lambda (Lame-Hermite integer-n cases are Liouvillian); expectation only, no authority; recorded so a result cannot be reframed afterwards",
}


def canonical_digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


def frozen_member() -> Dict[str, Any]:
    P3 = sum(c * q ** k for k, c in enumerate(A_COEFFS))
    f = sp.expand(2 * (ENERGY - P3))
    roots = sorted(sp.roots(sp.Poly(f, q)).items(), key=lambda kv: (sp.re(kv[0]), sp.im(kv[0])))
    disc = sp.discriminant(f, q)
    assert disc != 0 and all(m == 1 for _, m in roots) and len(roots) == N
    return {
        "n": N,
        "P_3": str(P3), "a": [str(c) for c in A_COEFFS], "E": str(ENERGY),
        "f_{a,E} = 2(E - P_3)": str(f),
        "singular_polynomial_note": "f_{a,E} = 2(E - P_3(q; a)); its roots are the roots of E - P_3, NOT of P_3 (E = -1 != 0)",
        "roots_of_f_ordered": [str(r) for r, _ in roots],
        "root_ordering_convention": "increasing real part (then imaginary part); this is the puncture ordering r_1 < r_2 < r_3 that the 01A convention freeze binds to strand ordering; any other ordering is an element of S_3 and must be recorded",
        "discriminant_of_f": str(disc),
        "phase_curve": "p1^2 = f(q1): nonsingular genus-1 curve (disc != 0, deg 3)",
    }


def source_signature(pkg: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Digest over everything on the SOURCE side: it must be identical for every coupling cell."""
    pkg = pkg or q01.load_artifacts(PRED_DIR)
    m = frozen_member()
    cert_s1 = pkg["certificates/s1-permutation-quotient.v0.1.json"]["3"]
    cert_s2 = pkg["certificates/s2-artin-action.v0.1.json"]["3"]
    cert_hz = pkg["certificates/hurwitz-action.v0.1.json"]["n3_generic"]
    hurwitz_convention = pkg["convention-freeze.v0.1.json"]["conventions"]["hurwitz_action_convention"]
    payload = {
        "n": m["n"], "a": m["a"], "E": m["E"], "root_configuration": m["roots_of_f_ordered"], "root_ordering": m["root_ordering_convention"],
        "pi_perm_certificate_digest": canonical_digest(cert_s1),
        "artin_certificate_digest": canonical_digest(cert_s2),
        "hurwitz_certificate_digest": canonical_digest(cert_hz),
        "hurwitz_convention": hurwitz_convention,
    }
    return {"payload": payload, "SOURCE_SIGNATURE": canonical_digest(payload)}


def target_equation(mu: sp.Rational, lam: sp.Rational) -> Dict[str, Any]:
    """f y'' + (f'/2) y' + (mu + lambda q) y = 0 and its exact reduced form y'' = r y."""
    P3 = sum(c * q ** k for k, c in enumerate(A_COEFFS))
    f = sp.expand(2 * (ENERGY - P3))
    c2, c1, c0 = f, sp.expand(sp.diff(f, q) / 2), sp.expand(mu + lam * q)
    # normal form: with y = exp(-1/2 int a) z, a = c1/c2, b = c0/c2:  z'' = r z, r = a^2/4 + a'/2 - b
    a = sp.cancel(c1 / c2)
    b = sp.cancel(c0 / c2)
    r = sp.cancel(a ** 2 / 4 + sp.diff(a, q) / 2 - b)
    num, den = sp.fraction(sp.factor(r))
    poles = sorted(sp.roots(sp.Poly(sp.denom(sp.together(r)), q)).items(), key=lambda kv: (sp.re(kv[0]), sp.im(kv[0])))
    return {
        "mu": str(mu), "lambda": str(lam),
        "original": {"c2": str(c2), "c1": str(c1), "c0": str(c0), "equation": f"({c2}) y'' + ({c1}) y' + ({c0}) y = 0"},
        "original_digest": canonical_digest({"c2": str(c2), "c1": str(c1), "c0": str(c0)}),
        "normalization": {"gauge": "y = exp(-(1/2) int a dq) z, a = c1/c2, b = c0/c2", "a": str(a), "b": str(b), "r": str(r), "r_factored": f"({num})/({den})",
                          "scope": "the gauge factor exp(-(1/2) int a) = f^(-1/4) is algebraic over C(q) (a = f'/(2f)), so the identity component of the differential Galois group is unchanged (AMW Prop 6.2/3.4, bound in the 00A ledger); Galois groups of the two forms may differ by a finite extension"},
        "reduced": {"equation": f"y'' = ({r}) y", "r": str(r)},
        "reduced_digest": canonical_digest({"r": str(r)}),
        "poles_of_r": [str(p) for p, _ in poles],
        "order_of_r_at_infinity": int(sp.degree(sp.Poly(den, q)) - sp.degree(sp.Poly(num, q))),
        "maxima_original": f"({sp.sstr(c2)})*'diff(y,x,2)+({sp.sstr(c1)})*'diff(y,x)+({sp.sstr(c0)})*y=0".replace("q", "x").replace("**", "^"),
        "maxima_reduced": f"'diff(y,x,2)=({sp.sstr(r)})*y".replace("q", "x").replace("**", "^"),
    }


def cell_equations() -> List[Dict[str, Any]]:
    out = []
    for cell in GRID:
        eq = target_equation(sp.Rational(cell["mu"]), sp.Rational(cell["lambda"]))
        out.append({**cell, **eq})
    return out


def preregistration(pkg: Dict[str, Any] | None = None) -> Dict[str, Any]:
    m = frozen_member()
    sig = source_signature(pkg)
    cells = cell_equations()
    return {
        "schema_version": "miskatonic.formal-discovery.hvb-preregistration.v0.1",
        "work_order": WORK_ORDER,
        "gate0": {"formal_discovery_start": FD_START, "mathematics_sha": MATH_SHA, "candidate_freeze_digest": CANDIDATE_FREEZE_DIGEST,
                  "predecessor_qualification_result_digest": canonical_digest((pkg or q01.load_artifacts(PRED_DIR))["qualification-result.v0.1.json"]),
                  "predecessor_convention_freeze_digest": canonical_digest((pkg or q01.load_artifacts(PRED_DIR))["convention-freeze.v0.1.json"])},
        "frozen_member": m,
        "source_signature": sig,
        "grid": GRID,
        "grid_size": len(GRID),
        "prior_expectations": PRIOR_EXPECTATIONS,
        "cells": cells,
        "rules": ["no cell may be added, removed or altered after the first target classification",
                  "every cell shares exactly the same n, a, E, f, roots and source certificates (SOURCE_SIGNATURE)",
                  "only (mu, lambda) vary", "no floating-point coefficients anywhere",
                  "n = 3 only; no n = 4..6 in this WO"],
    }


def write_preregistration(base: Path = EXPERIMENT_DIR) -> Dict[str, Any]:
    base.mkdir(parents=True, exist_ok=True)
    pre = preregistration()
    (base / "preregistration.v0.1.json").write_text(json.dumps(pre, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return pre


if __name__ == "__main__":
    pre = write_preregistration()
    print("SOURCE_SIGNATURE", pre["source_signature"]["SOURCE_SIGNATURE"])
    print("preregistration digest", canonical_digest(pre))
    for c in pre["cells"]:
        print(c["cell"], c["mu"], c["lambda"], c["reduced"]["r"])
