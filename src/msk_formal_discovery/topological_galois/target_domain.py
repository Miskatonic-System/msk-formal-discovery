"""Target topological-domain derivation for WO-FORMAL-TOPOLOGICAL-GALOIS-SOURCE-REPRESENTATION-01A.

Re-derives, from the accepted CAND-1 freeze, the normal variational equation and its
algebraic form, and freezes the puncture accounting of the target base:

    P^1_q minus ({roots of f_{a,E}} U {infinity}),   f_{a,E}(q) = 2(E - P_n(q; a))

This module needs sympy. It computes NO differential Galois group, NO monodromy matrix,
and touches NO value of (mu, lambda).
"""
from __future__ import annotations

import sympy as sp


def derive(n: int) -> dict:
    q1, q2, p1, p2, t, E, mu, lam, q, rho = sp.symbols("q1 q2 p1 p2 t E mu lambda q rho")
    a = sp.symbols(f"a0:{n + 1}")
    Pn = sum(a[k] * q1 ** k for k in range(n + 1))
    H = sp.Rational(1, 2) * (p1 ** 2 + p2 ** 2) + Pn + sp.Rational(1, 2) * (mu + lam * q1) * q2 ** 2
    X = sp.Matrix([sp.diff(H, p1), sp.diff(H, p2), -sp.diff(H, q1), -sp.diff(H, q2)])
    plane = {q2: 0, p2: 0}
    invariant = X[1].subs(plane) == 0 and X[3].subs(plane) == 0
    energy_on_plane = sp.expand(H.subs(plane))
    f = sp.expand(2 * (E - Pn.subs(q1, q)))                     # the singular polynomial: E - P_n, NOT P_n
    energy_relation = sp.simplify(2 * (E - energy_on_plane) - (2 * E - 2 * Pn - p1 ** 2)) == 0  # p1^2 = f(q1) on H = E
    J = X.jacobian([q1, q2, p1, p2]).subs(plane)
    split = all(J[r, c] == 0 for r in (0, 2) for c in (1, 3)) and all(J[r, c] == 0 for r in (1, 3) for c in (0, 2))
    nve = "xi'' + (mu + lambda*q1(t)) xi = 0"
    nve_ok = J[1, 3] == 1 and sp.simplify(J[3, 1] + mu + lam * q1) == 0
    # algebraization with x = q1: xi(t) = y(q1(t)), (q1')^2 = f(q1), q1'' = f'(q1)/2  =>  f y'' + f'/2 y' + (mu + lambda q) y = 0
    y = sp.Function("y")
    qt = sp.Function("q1")(t)
    composed = sp.diff(y(qt), t, 2)
    composed = composed.subs(sp.Derivative(qt, (t, 2)), sp.Rational(1, 2) * sp.diff(f, q).subs(q, qt)).subs(sp.Derivative(qt, t) ** 2, f.subs(q, qt))
    algebraic = f * sp.diff(y(q), q, 2) + sp.Rational(1, 2) * sp.diff(f, q) * sp.diff(y(q), q) + (mu + lam * q) * y(q)
    alg_ok = sp.simplify(composed.doit() + (mu + lam * qt) * y(qt) - algebraic.subs(q, qt).doit()) == 0
    # Fuchsian data: finite singular points are exactly the roots of f (coefficient f'/2f has simple poles there, (mu+lam q)/f too)
    finite_exponents = sorted(sp.solve(rho * (rho - 1) + sp.Rational(1, 2) * rho, rho))
    c0 = sp.limit(q ** 2 * (mu + lam * q) / f, q, sp.oo)
    inf_exponents = [sp.simplify(e) for e in sp.solve(rho ** 2 + (1 - sp.Rational(n, 2)) * rho + c0, rho)]
    inf_regular = sp.degree(sp.Poly(f, q)) - 1 >= 2
    discriminant = sp.discriminant(f, q)
    squarefree_generic = discriminant != 0
    return {
        "n": n,
        "hamiltonian": str(H),
        "invariant_plane": "q2 = p2 = 0", "invariant_plane_verified": bool(invariant),
        "energy_on_plane": str(energy_on_plane),
        "energy_relation": "p1^2 = f_{a,E}(q1)", "energy_relation_verified": bool(energy_relation),
        "singular_polynomial": "f_{a,E}(q) = 2(E - P_n(q; a))  [NOT P_n; equals 2(E - P_n), roots = roots of E - P_n]",
        "f_expanded": str(f),
        "variational_equation_splits": bool(split),
        "nve": nve, "nve_verified": bool(nve_ok),
        "algebraic_nve": "f y'' + (f'/2) y' + (mu + lambda q) y = 0  with x = q = q1", "algebraic_nve_verified": bool(alg_ok),
        "finite_singular_set": "the n roots of f_{a,E} (simple when disc(f) != 0)",
        "finite_exponents_at_simple_root": [str(e) for e in finite_exponents],
        "infinity_is_singular": True, "infinity_regular_singular": bool(inf_regular),
        "exponents_at_infinity": [str(e) for e in inf_exponents],
        "discriminant_of_f_nonzero_as_polynomial_in_(a,E)": bool(squarefree_generic),
        "puncture_count": n + 1,
        "base": f"P^1_q minus ({n} finite roots of f_{{a,E}} + infinity)",
        "pi_1": {
            "rank": n,
            "isomorphic_to": f"F_{n}",
            "generators": [f"x_{j}: loop based at the basepoint d_0, travelling counterclockwise once around the j-th root r_j (roots ordered by the frozen ordering below)" for j in range(1, n + 1)]
            + ["x_inf: loop counterclockwise around infinity in the local coordinate 1/q"],
            "relation": "x_1 x_2 ... x_n x_inf = 1  (so x_inf = (x_1 ... x_n)^{-1} and the group is free on x_1..x_n)",
            "basepoint": "d_0 on the boundary of a disk D containing all n finite roots; D minus the roots is the n-punctured disk D_n of BB Sec.4.4",
            "ordering": "roots r_1..r_n ordered by the position of the corresponding puncture in D_n, matching the strand ordering 1..n of B_n; any reordering is a relabelling by an element of S_n and is recorded, not assumed",
            "loop_orientation": "counterclockwise (BB Sec.4.4)",
            "derivation": "P^1 minus infinity = C; C minus the n roots deformation-retracts onto D_n; pi_1(D_n, d_0) is free on x_1..x_n (BB Sec.4.4). Adding the puncture at infinity back as a generator x_inf introduces exactly the relation x_1...x_n x_inf = 1. LOCAL_DERIVED elementary; the free-group statement is BB Sec.4.4.",
            "rank_if_infinity_omitted": n - 1,
            "rank_if_infinity_omitted_note": "P^1 minus n points has pi_1 free of rank n-1: omitting infinity changes the rank, so infinity MUST be counted",
        },
        "result": "PASS" if (invariant and energy_relation and split and nve_ok and alg_ok and inf_regular and finite_exponents == [0, sp.Rational(1, 2)] and squarefree_generic) else "FAIL",
    }


def derive_all(degrees=(3, 4, 5, 6)) -> dict:
    per = {str(n): derive(n) for n in degrees}
    return {
        "schema_version": "miskatonic.formal-discovery.tg-target-domain-derivation.v0.1",
        "work_order": "WO-FORMAL-TOPOLOGICAL-GALOIS-SOURCE-REPRESENTATION-01A",
        "candidate": "CAND-1 (frozen; digest 889cc252226d801491a83bdd594e366fffc5a8bd1ef9379f5088bf9f65d78425)",
        "scope": "NVE derived and algebrized; puncture accounting frozen. No differential Galois group, no monodromy matrix, no (mu, lambda) value, no Kovacic run.",
        "permanent": ["B_n != F_n", "SINGULAR_POLYNOMIAL = E - P_n, NOT P_n (E is a free parameter, not frozen to 0)", "INFINITY_IS_A_PUNCTURE"],
        "degrees": per,
        "result": "PASS" if all(v["result"] == "PASS" for v in per.values()) else "FAIL",
    }
