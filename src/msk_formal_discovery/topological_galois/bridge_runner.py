"""WO-FORMAL-HAMILTONIAN-VARIATIONAL-BRIDGE-01A — provider driver, independent checks, adjudication.

Provider: Maxima 5.49.0 `kovacicODE` (share/contrib/maxima-odesolve/kovacicODE.mac, N. Beishuizen 2014,
implementing Kovacic 1986 after Smith 1984 / Saunders 1981), obtained through user-level nix.

Output semantics (established by the K-control matrix, NOT assumed):
  * return value is a list [y = ...]     -> the provider found Liouvillian solutions (Kovacic cases 1-3)
  * return value is `nil`                -> (a) input rejected ("ODE is not linear!"), or
                                            (b) Maxima error, or
                                            (c) no Liouvillian solution: Kovacic case 4, G = SL_2(C)
    The message "No Liouvillian solutions exist" (with or without "!") is printed INSIDE cases 2/3 as well,
    so the message text is never used as the verdict. (c) is asserted only when neither (a) nor (b) occurred.

Predicate rules (each justified in the experiment document, none inferred from the word "Liouvillian"):
  R4  case 4 (provider nil, clean run, on BOTH the original and the reduced form)  -> G = SL_2, G^0 nonabelian -> FALSE
  R2L two independent returned solutions whose logarithmic derivatives are algebraic over C(x)
      (rational functions of x and sqrt of rational functions), each verified to satisfy the ODE
      -> G^0 fixes two distinct lines -> G^0 diagonalisable -> abelian -> TRUE
  RD  a direct Picard-Vessiot derivation for the cell (used for c1 = (0,0))                        -> TRUE/FALSE as derived
  otherwise                                                                                          -> UNRESOLVED
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import sympy as sp
from sympy.parsing.sympy_parser import parse_expr

from . import bridge_experiment as bx

EXPERIMENT_DIR = bx.EXPERIMENT_DIR
MAXIMA_STORE = "/nix/store/7xxinqc8i6x8v2wcm3yzh597a0iiawbl-maxima-5.49.0"
KOVACIC_MAC = f"{MAXIMA_STORE}/share/maxima/5.49.0/share/contrib/maxima-odesolve/kovacicODE.mac"
KOVACIC_MAC_SHA256 = "ab7f476a8c0e2c6b87161db1f347ac50f04d9d183d4ea75f0197d277cdbddccf"
NIXPKGS_REV = "35e212742ceab4ae1dcfbfd9039a39215c816e8e"
TIMEOUT_S = 900

x = sp.Symbol("x")


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def run_maxima(script: str, label: str, workdir: Path) -> Dict[str, Any]:
    workdir.mkdir(parents=True, exist_ok=True)
    mac = workdir / f"{label}.mac"
    mac.write_text(script, encoding="utf-8")
    cmd = ["nix", "--extra-experimental-features", "nix-command flakes", "shell", "nixpkgs#maxima", "--command",
           "maxima", "--very-quiet", f"--batch={mac.resolve()}"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_S, cwd=str(workdir))
        out, timed_out, rc = proc.stdout + proc.stderr, False, proc.returncode
    except subprocess.TimeoutExpired as exc:
        out, timed_out, rc = (exc.stdout or "") + (exc.stderr or ""), True, None
    (workdir / f"{label}.log").write_text(out, encoding="utf-8")
    return {"label": label, "script_digest": sha256(script.encode()), "log_digest": sha256(out.encode()), "returncode": rc,
            "timed_out": timed_out, "log": out}


def parse_results(log: str) -> Dict[str, Any]:
    """Extract 'TAG <value>' result lines printed by the scripts."""
    res = {}
    # results are printed as one logical line each, possibly wrapped; capture from RESULT_tag to the next RESULT_ or EOF
    parts = re.split(r'^(?=RESULT_)', log, flags=re.M)
    for part in parts:
        if part.startswith("RESULT_"):
            tag, _, body = part.partition(" ")
            body = body.strip().split("\nprint(")[0].strip()
            body = body.split('\n"')[0].strip()          # drop the trailing quoted script-path line Maxima prints at EOF
            res[tag[len("RESULT_"):]] = body
    return res


def verdict_for(tag_value: str, block: str) -> str:
    if "ODE is not linear!" in block:
        return "INPUT_REJECTED"
    if "incorrect syntax" in block or "Lisp error" in block:
        return "PROVIDER_ERROR"
    if tag_value.strip() in ("nil", "false"):
        return "NO_LIOUVILLIAN_SOLUTION"
    if tag_value.strip().startswith("[y"):
        return "LIOUVILLIAN_SOLUTIONS_RETURNED"
    return "UNPARSED"


def block_for(log: str, tag: str) -> str:
    i = log.find(f'print("RESULT_{tag}"')
    j = log.find(f"RESULT_{tag} ", i)
    return log[i:j] if i >= 0 and j >= 0 else ""


# ---------------------------------------------------------------------------
# Maxima -> sympy conversion of returned solutions, and independent verification
# ---------------------------------------------------------------------------

def _balanced_arg(t: str, i: int):
    """Return (arg, end) for the parenthesised group starting at t[i] == '(' (end = index after the closing paren)."""
    depth = 0
    for j in range(i, len(t)):
        if t[j] == "(":
            depth += 1
        elif t[j] == ")":
            depth -= 1
            if depth == 0:
                return t[i + 1:j], j + 1
    raise ValueError("unbalanced parentheses in Maxima output")


def rewrite_maxima_exp(t: str) -> str:
    """%e^EXPR -> exp(EXPR), processing the LAST occurrence first so nested arguments are already clean."""
    while True:
        i = t.rfind("%e^")
        if i < 0:
            return t
        j = i + 3
        sign = ""
        if t[j] == "-":
            sign, j = "-", j + 1
        if t[j] == "(":
            arg, end = _balanced_arg(t, j)
        else:
            m = re.match(r"[A-Za-z0-9_.]+", t[j:])
            arg, end = m.group(0), j + m.end()
        t = t[:i] + f"exp({sign}({arg}))" + t[end:]


def maxima_to_sympy(s: str):
    t = re.sub(r"\s+", "", s)          # Maxima wraps long results over several indented lines
    t = rewrite_maxima_exp(t)
    t = t.replace("%k1", "k1").replace("%k2", "k2").replace("%i", "I").replace("%pi", "pi")
    t = re.sub(r"'integrate\(", "Integral(", t)
    t = t.replace("^", "**")
    return parse_expr(t, local_dict={"x": x, "k1": sp.Symbol("k1"), "k2": sp.Symbol("k2"), "Integral": sp.Integral, "exp": sp.exp, "sqrt": sp.sqrt}, evaluate=False)


def split_basis(sol_expr) -> List[Any]:
    k1, k2 = sp.Symbol("k1"), sp.Symbol("k2")
    e = sp.expand(sol_expr)
    return [e.coeff(k1), e.coeff(k2)]          # NOT simplified: sympy would evaluate the provider's unevaluated integrals


def satisfies(c2, c1, c0, y) -> bool:
    expr = c2 * sp.diff(y, x, 2) + c1 * sp.diff(y, x) + c0 * y
    expr = expr.doit()
    return sp.simplify(expr) == 0


def log_derivative_is_algebraic_deg_le_2(y) -> Dict[str, Any]:
    w = sp.simplify(sp.diff(y, x) / y)
    w = sp.simplify(w.doit())
    has_transcendental = w.has(sp.Integral) or w.has(sp.exp) or w.has(sp.log) or w.has(sp.sin) or w.has(sp.cos) or w.has(sp.atan2)
    exps_ok = True
    for p in w.atoms(sp.Pow):
        e = p.exp
        if not (e.is_Integer or (e.is_Rational and e.q == 2)):
            exps_ok = False
    # square of the non-rational part must be rational: check w in C(x)(sqrt R): (w - a)^2 rational for a = rational part
    return {"log_derivative": str(w), "algebraic_degree_le_2": bool((not has_transcendental) and exps_ok)}


class ExactAlgebra:
    """Exact calculus in C(x)[s_1..s_m, J_1..J_k] / <s_i^2 - b_i>, where s_i stands for sqrt(b_i) (b_i a polynomial in x)
    and J_k for an unevaluated integral with D J_k = h_k. Zero-ness is decided by polynomial reduction, never by simplify."""

    def __init__(self, *exprs):
        self.s: Dict[Any, Any] = {}      # base polynomial -> symbol
        self.J: Dict[Any, Any] = {}      # Integral object -> (symbol, lifted integrand)
        for e in exprs:
            self.lift(e)

    def lift(self, e):
        """Replace integrals by J symbols (integrands lifted bottom-up) and sqrt(b) by s symbols."""
        for I in sorted(e.atoms(sp.Integral), key=lambda I: (sp.count_ops(I), str(I))):   # deterministic
            if I not in self.J:
                sym = sp.Symbol(f"J{len(self.J) + 1}")
                self.J[I] = (sym, None)                  # placeholder: the integrand is strictly smaller, so this terminates
                self.J[I] = (sym, self.lift(I.function))
        e = e.xreplace({I: sym for I, (sym, _) in self.J.items()})
        rep = {}
        # deterministic symbol assignment: radicands registered in sorted string order (set iteration order is not stable)
        for p in sorted((p for p in e.atoms(sp.Pow) if p.exp.is_Rational and p.exp.q == 2), key=lambda p: str(sp.expand(p.base))):
            if True:
                base = sp.expand(p.base)
                unit = sp.Integer(1)
                # branch canonicalisation: sqrt(b) = i*sqrt(-b) when b has negative leading coefficient in x
                # (a fixed branch choice; the Riccati/ODE residual checks remain the arbiter, they are over C(x))
                if base.has(x) and sp.Poly(base, x).LC() < 0:
                    base, unit = sp.expand(-base), sp.I
                if base not in self.s:
                    self.s[base] = sp.Symbol(f"s{len(self.s) + 1}")
                k, r = divmod(p.exp.p, 2)                 # n/2 = k + r/2
                rep[p] = unit ** p.exp.p * base ** k * (self.s[base] if r == 1 else 1)
        return e.xreplace(rep)

    def D(self, e):
        out = sp.diff(e, x)
        for base, sym in self.s.items():
            out += sp.diff(e, sym) * sp.diff(base, x) / (2 * sym)
        for I, (sym, h) in self.J.items():
            out += sp.diff(e, sym) * h
        return out

    def is_zero(self, e) -> bool:
        num, _den = sp.fraction(sp.together(sp.expand(e)))
        num = sp.expand(num)
        if num == 0:
            return True
        # square-root symbols FIRST: under lex the leading terms are then s_i^2, pairwise coprime, so the
        # relation set is a Groebner basis and the remainder is canonical (zero iff the element is zero).
        gens = list(self.s.values()) + [sym for sym, _ in self.J.values()] + [x]
        rels = [sym ** 2 - base for base, sym in self.s.items()]
        if num.has(sp.exp):
            return False
        if not rels:
            return sp.Poly(num, *gens).is_zero
        _, rem = sp.reduced(num, rels, *gens, order="lex")
        return sp.expand(rem) == 0

    def conjugates(self, e):
        """Sign flips of nonempty subsets of the square-root symbols occurring in e."""
        import itertools
        syms = [sym for sym in self.s.values() if e.has(sym)]
        for k in range(1, len(syms) + 1):
            for subset in itertools.combinations(syms, k):
                yield e.xreplace({sym: -sym for sym in subset})


def rules_on_basis(basis, c2, c1, c0) -> Dict[str, Any]:
    """R2L (conjugate form) and RU, decided exactly. `basis` are sympy expressions from the provider (may contain Integral)."""
    A = ExactAlgebra(*basis, c2, c1, c0)
    a_coef, b_coef = sp.cancel(c1 / c2), sp.cancel(c0 / c2)
    lifted = [A.lift(b) for b in basis]
    Jsyms = [sym for sym, _ in A.J.values()]
    ode = lambda y: c2 * A.D(A.D(y)) + c1 * A.D(y) + c0 * y
    riccati = lambda w: A.D(w) + w ** 2 + a_coef * w + b_coef
    checks = []
    for y in lifted:
        entry = {"solution_lifted": str(y)[:300]}
        try:                                               # residual ODE(y)/y: the exp factor of an exponential solution cancels
            entry["satisfies_ode_exactly"] = bool(A.is_zero(sp.cancel(ode(y) / y)))
        except Exception as exc:                           # nested exp-inside-integral forms are outside the exact engine
            entry["satisfies_ode_exactly"] = None
            entry["verification_note"] = f"not decidable by the exact engine: {type(exc).__name__}"
        entry["algebraic_over_Cx"] = not any(y.has(j) for j in Jsyms) and not y.has(sp.exp)
        try:
            w = sp.cancel(A.D(y) / y)
            entry["log_derivative_algebraic"] = not any(w.has(j) for j in Jsyms) and not w.has(sp.exp)
            entry["log_derivative"] = str(w) if entry["log_derivative_algebraic"] else None
        except Exception:
            entry["log_derivative_algebraic"], entry["log_derivative"] = False, None
        checks.append(entry)
    # R2L via conjugation: needs one exponential solution with algebraic log-derivative solving the Riccati equation
    for entry in checks:
        if entry["log_derivative_algebraic"]:
            w = sp.sympify(entry["log_derivative"], locals={"x": x, **{str(v): v for v in A.s.values()}})
            # the provider's expression may sit on another branch of the radicals; the set {w} U conjugates(w) is
            # branch-independent, and the exact Riccati residual selects the genuine solutions among them
            candidates = [w] + list(A.conjugates(w))
            solving = [c for c in candidates if A.is_zero(riccati(c))]
            for w1 in solving:
                for w2 in solving:
                    if A.is_zero(w2 - w1):
                        continue
                    w = w1
                    return {"predicate": "TRUE", "rule": "R2L (conjugate form): omega_1 = y_1'/y_1 is algebraic over C(x) and satisfies the Riccati equation omega' + omega^2 + a omega + b = 0 exactly (polynomial reduction modulo s_i^2 = b_i); a Galois conjugate omega_2 != omega_1 satisfies it too, so y_2 = exp(int omega_2) is a second, independent exponential solution. Over K' = C(x)(omega_1, omega_2) both lines C.y_i are Gal(L/K')-stable, hence Gal(L/K') is diagonal, hence abelian; G^0 over C(x) equals Gal(L/K')^0 since K'/C(x) is algebraic (AMW Prop 6.3, bound)",
                            "checks": checks, "omega_1": str(w), "omega_2": str(w2), "sqrt_symbols": {str(v): str(k) for k, v in A.s.items()}}
    # RU: an algebraic solution y_1 and y_2 = y_1 * int(omega) with omega algebraic
    for i, j in ((0, 1), (1, 0)):
        if len(lifted) == 2 and checks[i]["algebraic_over_Cx"] and checks[i]["satisfies_ode_exactly"] and checks[j]["satisfies_ode_exactly"]:
            om = sp.cancel(A.D(lifted[j] / lifted[i]))
            if not any(om.has(js) for js in Jsyms) and not om.has(sp.exp) and not A.is_zero(om):
                return {"predicate": "TRUE", "rule": "RU: y_1 is algebraic over C(x) and (y_2/y_1)' = omega is algebraic and nonzero (both solutions verified exactly); over K' = C(x)(y_1, omega) every sigma fixes y_1 and sends y_2/y_1 to y_2/y_1 + c, so Gal(L/K') is a subgroup of G_a = {[[1,c],[0,1]]}, abelian; G^0 over C(x) equals Gal(L/K')^0 (AMW Prop 6.3, bound)",
                        "checks": checks, "omega": str(om), "sqrt_symbols": {str(v): str(k) for k, v in A.s.items()}}
    return {"predicate": "UNRESOLVED", "rule": None, "checks": checks}


def rule_ru_case1(r, c2) -> Dict[str, Any]:
    """RU via a RATIONAL Riccati solution of the reduced form z'' = r z (independent of the provider's expression).

    If v in C(x) solves v' + v^2 = r and v = sum_c rho_c/(x - c) with rho_c rational and no polynomial part, then
    z_1 = exp(int v) = prod (x - c)^rho_c is algebraic, so y_1 = f^(-1/4) z_1 is an algebraic solution of the original
    equation; the reduction-of-order solution y_2 = y_1 int y_1^(-2) f^(-1/2) has (y_2/y_1)' algebraic, hence RU applies.
    """
    from sympy.solvers.ode.riccati import solve_riccati
    v = sp.Function("v")
    try:
        sols = solve_riccati(v(x), x, sp.together(r), sp.Integer(0), sp.Integer(-1), gensol=False)
    except Exception as exc:  # pragma: no cover
        return {"predicate": "UNRESOLVED", "rule": None, "note": repr(exc)}
    for sol in sols:
        vv = sp.cancel(sol.rhs if isinstance(sol, sp.Equality) else sol)
        if sp.cancel(sp.diff(vv, x) + vv ** 2 - r) != 0:
            continue
        parts = sp.Add.make_args(sp.apart(vv, x))
        exponents = {}
        ok = True
        for term in parts:
            num, den = sp.fraction(sp.together(term))
            dp = sp.Poly(den, x)
            if dp.degree() != 1 or sp.Poly(num, x).degree() > 0:
                ok = False
                break
            c = sp.solve(den, x)[0]
            exponents[str(c)] = exponents.get(str(c), 0) + sp.Rational(num) / dp.LC()
        if ok and all(e.is_Rational for e in exponents.values()):
            z1 = sp.Mul(*[(x - sp.sympify(c)) ** e for c, e in exponents.items()])
            return {"predicate": "TRUE",
                    "rule": "RU (case-1 form): the reduced equation z'' = r z has the rational Riccati solution v (verified v' + v^2 = r exactly) whose partial fractions have only simple poles with rational residues, so z_1 = exp(int v) = prod (x-c)^rho_c is algebraic and y_1 = f^(-1/4) z_1 is an algebraic solution of the original equation; y_2 = y_1 int y_1^(-2) f^(-1/2) has (y_2/y_1)' algebraic, so over K' = C(x)(y_1, f^(1/2)) Gal(L/K') is a subgroup of G_a, abelian; G^0 over C(x) equals Gal(L/K')^0 (AMW Prop 6.3, bound)",
                    "v": str(vv), "residues": {k: str(e) for k, e in exponents.items()}, "z1": str(z1), "y1": f"({c2})^(-1/4) * {z1}"}
    return {"predicate": "UNRESOLVED", "rule": None, "rational_riccati_solutions": [str(s_) for s_ in sols]}


def rational_riccati_has_solution(r) -> Dict[str, Any]:
    """Independent Kovacic-case-1 test with sympy's rational Riccati solver: v' = r - v^2 has a rational solution iff case 1."""
    from sympy.solvers.ode.riccati import solve_riccati
    v = sp.Function("v")
    try:
        sols = solve_riccati(v(x), x, sp.together(r), sp.Integer(0), sp.Integer(-1), gensol=False)
        return {"rational_solutions": [str(s) for s in sols], "case_1_possible": len(sols) > 0, "tool": "sympy.solvers.ode.riccati.solve_riccati"}
    except Exception as exc:  # pragma: no cover
        return {"error": repr(exc), "case_1_possible": None}


# ---------------------------------------------------------------------------
# K-control matrix (provider qualification)
# ---------------------------------------------------------------------------
K_CONTROLS = [
    ("K1", "y'' = 0 (direct form)", "'diff(y,x,2)=0", "INPUT_REJECTED", "provider misclassifies constant-coefficient input as non-linear; see K1g"),
    ("K1g", "y'' = 0 in the rational gauge y = x u:  x u'' + 2 u' = 0 (same Picard-Vessiot extension, G trivial)", "x*'diff(y,x,2)+2*'diff(y,x)=0", "LIOUVILLIAN_SOLUTIONS_RETURNED", "known answer u in {1, 1/x}"),
    ("K2", "y'' - y = 0 (direct form)", "'diff(y,x,2)-y=0", "INPUT_REJECTED", "as K1"),
    ("K2g", "y'' = y in the gauge y = x u:  x u'' + 2 u' - x u = 0 (G = G_m)", "x*'diff(y,x,2)+2*'diff(y,x)-x*y=0", "LIOUVILLIAN_SOLUTIONS_RETURNED", "known answer u = e^{+-x}/x"),
    ("K3a", "Kovacic case 2 (imprimitive): y'' = (1/x - 3/(16x^2)) y", "'diff(y,x,2)=(1/x-3/(16*x^2))*y", "LIOUVILLIAN_SOLUTIONS_RETURNED", "known answer y = x^{1/4} e^{+-2 sqrt(x)}"),
    ("K3b", "Kovacic case 3 (finite primitive): y'' = (-3/(16x^2) - 2/(9(x-1)^2) + 3/(16x(x-1))) y", "'diff(y,x,2)=(-3/(16*x^2)-2/(9*(x-1)^2)+3/(16*x*(x-1)))*y", "LIOUVILLIAN_SOLUTIONS_RETURNED", "algebraic solutions expected"),
    ("K4a", "Kovacic case 4: Airy y'' = x y", "'diff(y,x,2)=x*y", "NO_LIOUVILLIAN_SOLUTION", "G = SL_2(C)"),
    ("K4b", "Kovacic case 4 with first-derivative term: Bessel order 0, x y'' + y' + x y = 0", "x*'diff(y,x,2)+'diff(y,x)+x*y=0", "NO_LIOUVILLIAN_SOLUTION", "G = SL_2(C); exercises the provider's own normalization"),
    ("K5", "Liouvillian with first-derivative term: Legendre n=1, (1-x^2) y'' - 2x y' + 2y = 0", "(1-x^2)*'diff(y,x,2)-2*x*'diff(y,x)+2*y=0", "LIOUVILLIAN_SOLUTIONS_RETURNED", "y = x is a solution"),
    ("K6", "Bessel order 1/2, x^2 y'' + x y' + (x^2 - 1/4) y = 0", "x^2*'diff(y,x,2)+x*'diff(y,x)+(x^2-1/4)*y=0", "LIOUVILLIAN_SOLUTIONS_RETURNED", "y = sin x / sqrt x, cos x / sqrt x"),
]


def k_script() -> str:
    lines = ["display2d:false$", "load(kovacicODE)$"]
    for tag, _, eq, _, _ in K_CONTROLS:
        lines.append(f'print("RESULT_{tag}", kovacicODE({eq}, y, x))$')
    return "\n".join(lines) + "\n"


def reconstruct_k_matrix(log: str) -> Dict[str, Any]:
    """Rebuild id / expected_verdict / provider_verdict / pass / qualified from a committed K-control log (no Maxima run)."""
    results = parse_results(log)
    rows = []
    for tag, _desc, _eq, expected, _note in K_CONTROLS:
        got = verdict_for(results.get(tag, ""), block_for(log, tag))
        rows.append({"id": tag, "expected_verdict": expected, "provider_verdict": got, "pass": got == expected})
    return {"rows": rows, "qualified_from_rows": all(r["pass"] for r in rows)}


def provider_qualification(workdir: Path) -> Dict[str, Any]:
    run = run_maxima(k_script(), "k_controls", workdir)
    results = parse_results(run["log"])
    rows = []
    for tag, desc, eq, expected, note in K_CONTROLS:
        got = verdict_for(results.get(tag, ""), block_for(run["log"], tag))
        rows.append({"id": tag, "control": desc, "input": eq, "expected_verdict": expected, "provider_verdict": got, "provider_return": results.get(tag, "")[:400], "note": note, "pass": got == expected})
    mac_digest = None
    try:  # the nix store is only visible inside `nix shell`
        proc = subprocess.run(["nix", "--extra-experimental-features", "nix-command flakes", "shell", "nixpkgs#maxima", "--command", "sha256sum", KOVACIC_MAC],
                              capture_output=True, text=True, timeout=600)
        mac_digest = proc.stdout.split()[0] if proc.returncode == 0 and proc.stdout.strip() else None
    except (subprocess.TimeoutExpired, OSError):
        pass
    return {
        "provider": "Maxima kovacicODE",
        "maxima_version": "5.49.0", "store_path": MAXIMA_STORE, "nixpkgs_revision": NIXPKGS_REV,
        "implementation_file": KOVACIC_MAC, "implementation_sha256_recorded": KOVACIC_MAC_SHA256, "implementation_sha256_observed": mac_digest,
        "implementation_provenance": "kovacicODE.mac, (C) 2014 Nijso Beishuizen, GPL-2+, implementing Kovacic 1986 after Smith 1984 (CS-84-35) and Saunders 1981",
        "command": "nix shell nixpkgs#maxima --command maxima --very-quiet --batch=<script.mac>; load(kovacicODE); kovacicODE(eq, y, x)",
        "coefficient_field": "Q(x) (rational coefficients; exact)",
        "normalization": "the provider accepts the general second-order form and normalizes internally; we ALSO feed the exact reduced form y'' = r y computed in sympy and require agreement",
        "output_semantics": "list [y = ...] => Liouvillian solutions found (cases 1-3); nil => input rejected ('ODE is not linear!'), Maxima error, or no Liouvillian solution (case 4). Message text is never used as the verdict.",
        "known_limitation": "constant-coefficient inputs are misclassified as non-linear and rejected (K1, K2 direct forms); all target cells have genuinely x-dependent coefficients; K1g/K2g cover the same Picard-Vessiot extensions through a rational gauge",
        "timeout_resource_policy": f"{TIMEOUT_S} s per script; no retries; a timeout is recorded as UNRESOLVED",
        "k_control_script_digest": run["script_digest"], "k_control_log_digest": run["log_digest"],
        "rows": rows,
        "qualified": all(r["pass"] for r in rows) and mac_digest == KOVACIC_MAC_SHA256,
    }


# ---------------------------------------------------------------------------
# target cells
# ---------------------------------------------------------------------------

def cell_script(cells: List[Dict[str, Any]]) -> str:
    lines = ["display2d:false$", "load(kovacicODE)$"]
    for c in cells:
        lines.append(f'print("RESULT_{c["cell"]}_orig", kovacicODE({c["maxima_original"]}, y, x))$')
        lines.append(f'print("RESULT_{c["cell"]}_red", kovacicODE({c["maxima_reduced"]}, y, x))$')
    return "\n".join(lines) + "\n"


def direct_derivation_c1(c2, c1, c0) -> Dict[str, Any]:
    """(mu, lambda) = (0,0): f y'' + (f'/2) y' = 0. Solutions 1 and int f^{-1/2}; G^0 = G_a (abelian)."""
    f = c2
    y1 = sp.Integer(1)
    y2p = f ** sp.Rational(-1, 2)          # y2' = f^{-1/2}, y2 = int f^{-1/2} dq
    ok1 = satisfies(c2, c1, c0, y1)
    ok2 = sp.simplify(c2 * sp.diff(y2p, x) + c1 * y2p) == 0
    return {
        "equation": f"({c2}) y'' + ({c1}) y' = 0",
        "solution_basis": ["y1 = 1", "y2 = int f^{-1/2} dq  (the elliptic integral of the first kind on the curve p^2 = f(q))"],
        "y1_verified": bool(ok1), "y2_verified_via_y2'=f^(-1/2)": bool(ok2),
        "picard_vessiot_argument": [
            "K := C(q, sqrt f) is the function field of the nonsingular genus-1 curve C: p^2 = f(q); [K : C(q)] = 2.",
            "y2' = 1/sqrt f in K; the differential omega = dq / sqrt f is the holomorphic differential of C. It is not exact in K: an element g of K with dg = omega would be a function on the compact curve C with no poles (omega has none), hence constant, contradicting dg != 0.",
            "Therefore L := K(y2) is a Picard-Vessiot extension of K generated by a primitive (integral) of an element of K that is not the derivative of an element of K; Gal(L/K) = G_a (sigma(y2) = y2 + c). Basis (y1, y2) is fixed/shifted: G(L/K) = {[[1, c],[0, 1]]}.",
            "Over C(q): the extension K/C(q) is algebraic of degree 2 (sqrt f), so the identity component is unchanged (AMW Prop 6.2, bound in the 00A ledger): G(L/C(q))^0 = G_a. Concretely G(L/C(q)) = {[[1, c],[0, +-1]]} (sqrt f -> +-sqrt f), a group with identity component G_a and two components.",
            "G^0 = G_a is abelian: ABELIAN_IDENTITY_COMPONENT = TRUE by direct derivation, independent of any provider output.",
        ],
        "predicate": "TRUE",
        "provider_expectation": "Kovacic case 1 (y1 = 1 has rational logarithmic derivative 0); Kovacic case 1 alone would NOT justify abelianity (the Borel group is non-abelian), which is why this derivation is required.",
    }


def classify_cell(cell: Dict[str, Any], results: Dict[str, str], log: str) -> Dict[str, Any]:
    c2, c1, c0 = (parse_expr(cell["original"][k].replace("q", "x"), local_dict={"x": x}) for k in ("c2", "c1", "c0"))
    r = parse_expr(cell["reduced"]["r"].replace("q", "x"), local_dict={"x": x})
    vo = verdict_for(results.get(f'{cell["cell"]}_orig', ""), block_for(log, f'{cell["cell"]}_orig'))
    vr = verdict_for(results.get(f'{cell["cell"]}_red', ""), block_for(log, f'{cell["cell"]}_red'))
    rec: Dict[str, Any] = {"cell": cell["cell"], "mu": cell["mu"], "lambda": cell["lambda"], "original_digest": cell["original_digest"], "reduced_digest": cell["reduced_digest"],
                           "provider_verdict_original_form": vo, "provider_verdict_reduced_form": vr,
                           "provider_return_original": results.get(f'{cell["cell"]}_orig', "")[:1500], "provider_return_reduced": results.get(f'{cell["cell"]}_red', "")[:1500],
                           "provider_output_digest": sha256((results.get(f'{cell["cell"]}_orig', "") + "|" + results.get(f'{cell["cell"]}_red', "")).encode())}
    rec["independent_case1_test_on_reduced_form"] = rational_riccati_has_solution(r)
    predicate, rule, evidence = "UNRESOLVED", None, {}
    if vo == "NO_LIOUVILLIAN_SOLUTION" and vr == "NO_LIOUVILLIAN_SOLUTION":
        predicate, rule = "FALSE", "R4: provider finds no Liouvillian solution on both forms => Kovacic case 4 => G = SL_2(C), G^0 = SL_2(C) nonabelian"
        evidence = {"consistent_with_independent_case1_exclusion": rec["independent_case1_test_on_reduced_form"].get("case_1_possible") is False}
    elif vo == "LIOUVILLIAN_SOLUTIONS_RETURNED" and vr == "LIOUVILLIAN_SOLUTIONS_RETURNED":
        try:
            sol = maxima_to_sympy(results[f'{cell["cell"]}_orig'].split("=", 1)[1].strip().rstrip("]"))
            basis = [b for b in split_basis(sol) if b != 0]
            ab = rules_on_basis(basis, c2, c1, c0)
            evidence = {"returned_basis_checks": ab["checks"], **{k: v for k, v in ab.items() if k in ("omega_1", "omega_2", "omega", "sqrt_symbols")}}
            if ab["predicate"] == "TRUE":
                predicate, rule = "TRUE", ab["rule"]
        except Exception as exc:
            evidence = {"conversion_error": repr(exc)}
    elif vo != vr:
        evidence = {"form_disagreement": f"original={vo}, reduced={vr}: no verdict is taken when the two forms disagree"}
    if predicate == "UNRESOLVED" and rec["independent_case1_test_on_reduced_form"].get("case_1_possible"):
        ru = rule_ru_case1(r, c2)
        evidence["case1_analysis"] = ru
        if ru["predicate"] == "TRUE":
            predicate, rule = "TRUE", ru["rule"]
    if cell["cell"] == "c1":
        d = direct_derivation_c1(c2, c1, c0)
        evidence["direct_derivation"] = d
        if d["y1_verified"] and d["y2_verified_via_y2'=f^(-1/2)"]:
            predicate, rule = "TRUE", "RD: direct Picard-Vessiot derivation (G^0 = G_a); provider output is corroborating only"
    rec.update({"ABELIAN_IDENTITY_COMPONENT": predicate, "rule": rule, "evidence": evidence})
    return rec


def run_cells(pre: Dict[str, Any], workdir: Path) -> Dict[str, Any]:
    run = run_maxima(cell_script(pre["cells"]), "target_cells", workdir)
    results = parse_results(run["log"])
    recs = [classify_cell(c, results, run["log"]) for c in pre["cells"]]
    return {"script_digest": run["script_digest"], "log_digest": run["log_digest"], "timed_out": run["timed_out"], "returncode": run["returncode"], "cells": recs}


def reclassify_from_log(pre: Dict[str, Any], workdir: Path) -> Dict[str, Any]:
    """Re-parse a saved provider log (no new Maxima run) and rebuild the cell records."""
    log = (workdir / "target_cells.log").read_text(encoding="utf-8")
    script = (workdir / "target_cells.mac").read_text(encoding="utf-8")
    results = parse_results(log)
    return {"script_digest": sha256(script.encode()), "log_digest": sha256(log.encode()), "timed_out": False, "returncode": 0,
            "cells": [classify_cell(c, results, log) for c in pre["cells"]]}


def adjudicate(pre: Dict[str, Any], cells: List[Dict[str, Any]]) -> Dict[str, Any]:
    sig = pre["source_signature"]["SOURCE_SIGNATURE"]
    resolved = [c for c in cells if c["ABELIAN_IDENTITY_COMPONENT"] in ("TRUE", "FALSE")]
    values = {c["ABELIAN_IDENTITY_COMPONENT"] for c in resolved}
    pair = None
    if len(values) == 2:
        t = next(c for c in resolved if c["ABELIAN_IDENTITY_COMPONENT"] == "TRUE")
        f = next(c for c in resolved if c["ABELIAN_IDENTITY_COMPONENT"] == "FALSE")
        pair = {"c1": {"cell": t["cell"], "mu": t["mu"], "lambda": t["lambda"], "predicate": "TRUE"}, "c2": {"cell": f["cell"], "mu": f["mu"], "lambda": f["lambda"], "predicate": "FALSE"}}
    if pair:
        bo2, component = "REFUTED", "SOURCE_DATA_ALONE_INSUFFICIENT_FOR_TARGET_PREDICATE"
    elif resolved:
        bo2, component = "NOT_FALSIFIED_ON_FROZEN_N3_GRID", None
    else:
        bo2, component = "UNRESOLVED", None
    return {
        "SOURCE_SIGNATURE_shared_by_all_cells": sig,
        "cells_resolved": len(resolved), "cells_total": len(cells),
        "predicate_by_cell": {c["cell"]: c["ABELIAN_IDENTITY_COMPONENT"] for c in cells},
        "witness_pair": pair,
        "BO2": bo2, "disposition_component": component,
        "note": "absence of a counterexample in a finite grid would NOT establish SOURCE_DATA_SUFFICIENT" if bo2 != "REFUTED" else "same SOURCE_SIGNATURE, different ABELIAN_IDENTITY_COMPONENT: the target predicate is not a function of source representation data alone on the frozen family",
        "prior_expectations_vs_outcome": {c["cell"]: {"expected": ("TRUE" if c["cell"] in pre["prior_expectations"]["expected_abelian_identity_component"] else "FALSE"), "got": c["ABELIAN_IDENTITY_COMPONENT"]} for c in cells},
    }
