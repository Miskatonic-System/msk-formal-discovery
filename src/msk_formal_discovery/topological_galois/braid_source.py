"""Exact source-side constructions for WO-FORMAL-TOPOLOGICAL-GALOIS-SOURCE-REPRESENTATION-01A.

Every formula here is bound to a content-hashed source locator recorded in
``qualification.CONVENTION_FREEZE`` (Birman-Brendle, arXiv:math/0409205v2):

  * braid words multiply by juxtaposition, X Y = X then Y            (BB Sec.1, Fig.1)
  * relations sigma_i sigma_k = sigma_k sigma_i (|i-k|>=2),
    sigma_i sigma_{i+1} sigma_i = sigma_{i+1} sigma_i sigma_{i+1}    (BB eq.(2))
  * pi_perm : sigma_i -> s_i = (i i+1)                                (BB Sec.4.1)
  * Artin action sigma_i x_j sigma_i^{-1} =
        x_{i+1}                 if j = i
        x_{i+1}^{-1} x_i x_{i+1} if j = i+1
        x_j                     otherwise                             (BB eq.(20))
  * unreduced Burau sigma_i -> I_{i-1} (+) [[1-t, t],[1, 0]] (+) I_{n-i-1}     (BB Sec.4.2)
  * reduced Burau   sigma_i -> I_{i-2} (+) [[1,-t,0],[0,-t,0],[0,-1,1]] (+) I_{n-i-2},
    the -t in the (i,i) spot                                          (BB Sec.4.2)

Nothing here is a theorem. Everything is a finite exact computation whose result is
recorded in a certificate.
"""
from __future__ import annotations

import itertools
from fractions import Fraction
from typing import Dict, List, Sequence, Tuple

from .freegroup import Endo, Word, gen, inverse, mul, word_str

BraidWord = Tuple[Tuple[int, int], ...]   # letters (i, e): sigma_i^e, multiplied LEFT TO RIGHT
Matrix = Tuple[Tuple[Fraction, ...], ...]

# ---------------------------------------------------------------------------
# braid words
# ---------------------------------------------------------------------------

def sigma(i: int, e: int = 1) -> BraidWord:
    return ((i, e),)


def bmul(*ws: BraidWord) -> BraidWord:
    """Juxtaposition: bmul(X, Y) is the braid X followed by Y (BB Fig.1)."""
    out: List[Tuple[int, int]] = []
    for w in ws:
        out.extend(w)
    return tuple(out)


def binv(w: BraidWord) -> BraidWord:
    return tuple((i, -e) for i, e in reversed(w))


def braid_relation_pairs(n: int) -> List[Tuple[str, BraidWord, BraidWord]]:
    """The defining relations of B_n as pairs of words that must agree (BB eq.(2))."""
    rels = []
    for i in range(1, n - 1):
        rels.append((f"braid({i},{i + 1})", bmul(sigma(i), sigma(i + 1), sigma(i)), bmul(sigma(i + 1), sigma(i), sigma(i + 1))))
    for i in range(1, n):
        for k in range(i + 2, n):
            rels.append((f"far({i},{k})", bmul(sigma(i), sigma(k)), bmul(sigma(k), sigma(i))))
    return rels


# ---------------------------------------------------------------------------
# S1: permutation quotient. Permutations are tuples p with p[k-1] = image of k.
#     Composition is LEFT TO RIGHT to match juxtaposition: (p * q)(k) = q(p(k)).
# ---------------------------------------------------------------------------

def perm_identity(n: int) -> Tuple[int, ...]:
    return tuple(range(1, n + 1))


def perm_mul(p: Sequence[int], q: Sequence[int]) -> Tuple[int, ...]:
    """Apply p first, then q."""
    return tuple(q[p[k] - 1] for k in range(len(p)))


def perm_of_generator(n: int, i: int) -> Tuple[int, ...]:
    p = list(range(1, n + 1))
    p[i - 1], p[i] = p[i], p[i - 1]
    return tuple(p)


def perm_of_word(n: int, w: BraidWord) -> Tuple[int, ...]:
    p = perm_identity(n)
    for i, _e in w:                      # sigma_i and sigma_i^{-1} have the same image (s_i^2 = 1)
        p = perm_mul(p, perm_of_generator(n, i))
    return p


def s1_certificate(n: int) -> dict:
    gens = {i: perm_of_generator(n, i) for i in range(1, n)}
    relations = [{"relation": name, "lhs": perm_of_word(n, a), "rhs": perm_of_word(n, b), "holds": perm_of_word(n, a) == perm_of_word(n, b)}
                 for name, a, b in braid_relation_pairs(n)]
    squares = {i: perm_of_word(n, bmul(sigma(i), sigma(i))) == perm_identity(n) for i in range(1, n)}
    # surjectivity: closure of the generators under left-to-right composition
    seen = {perm_identity(n)}
    frontier = [perm_identity(n)]
    while frontier:
        nxt = []
        for p in frontier:
            for g in gens.values():
                q = perm_mul(p, g)
                if q not in seen:
                    seen.add(q)
                    nxt.append(q)
        frontier = nxt
    factorial = 1
    for k in range(2, n + 1):
        factorial *= k
    transposition = {i: sorted(k + 1 for k in range(n) if gens[i][k] != k + 1) == [i, i + 1] for i in range(1, n)}
    passed = all(r["holds"] for r in relations) and all(squares.values()) and len(seen) == factorial and all(transposition.values())
    return {
        "object": "S1", "n": n, "map": "pi_perm: B_n -> S_n, sigma_i -> (i i+1)",
        "composition_convention": "permutations composed left to right, (p*q)(k) = q(p(k)), matching braid juxtaposition",
        "generators": {f"sigma_{i}": list(p) for i, p in gens.items()},
        "generator_is_transposition_(i,i+1)": {f"sigma_{i}": v for i, v in transposition.items()},
        "relations": relations,
        "sigma_i_squared_maps_to_identity": {f"sigma_{i}": v for i, v in squares.items()},
        "image_size": len(seen), "expected_size_n_factorial": factorial, "surjective": len(seen) == factorial,
        "result": "PASS" if passed else "FAIL",
    }


# ---------------------------------------------------------------------------
# S2: Artin action, BB eq.(20). LEFT action: alpha(XY) = alpha(X) o alpha(Y).
# ---------------------------------------------------------------------------

def artin_generator(n: int, i: int, e: int = 1) -> Endo:
    x = gen
    if e == 1:
        return Endo(n, {i: x(i + 1), i + 1: mul(inverse(x(i + 1)), x(i), x(i + 1))})
    # inverse, derived by solving (20) for sigma_i^{-1} x_j sigma_i; verified below as an exact inverse
    return Endo(n, {i + 1: x(i), i: mul(x(i), x(i + 1), inverse(x(i)))})


def artin_of_word(n: int, w: BraidWord) -> Endo:
    alpha = Endo(n, {})
    for i, e in w:                       # left to right, so alpha(XY) = alpha(X) o alpha(Y)
        alpha = alpha.compose(artin_generator(n, i, e))
    return alpha


def boundary_word(n: int) -> Word:
    """The frozen product word x_1 x_2 ... x_n (invariant under the action; see the certificate)."""
    return mul(*[gen(i) for i in range(1, n + 1)])


def s2_certificate(n: int) -> dict:
    gens = {i: artin_generator(n, i, 1) for i in range(1, n)}
    invs = {i: artin_generator(n, i, -1) for i in range(1, n)}
    automorphism = {i: gens[i].compose(invs[i]).is_identity() and invs[i].compose(gens[i]).is_identity() for i in range(1, n)}
    relations = [{"relation": name, "holds": artin_of_word(n, a) == artin_of_word(n, b)} for name, a, b in braid_relation_pairs(n)]
    # induced permutation: the abelianization sends x_j to a unit vector e_{p(j)}; p must equal pi_perm(sigma_i)
    induced = {}
    for i, g in gens.items():
        ab = g.abelianization_image()
        p = []
        ok = True
        for j in range(1, n + 1):
            nz = [k for k, v in ab[j].items() if v != 0]
            if len(nz) != 1 or ab[j][nz[0]] != 1:
                ok = False
                break
            p.append(nz[0])
        induced[i] = {"induced_permutation": p, "agrees_with_S1": ok and tuple(p) == perm_of_generator(n, i)}
    bw = boundary_word(n)
    reversed_bw = mul(*[gen(i) for i in range(n, 0, -1)])
    product = {i: gens[i](bw) == bw for i in range(1, n)}
    reversed_product = {i: gens[i](reversed_bw) == reversed_bw for i in range(1, n)}
    # left-action check: alpha(XY)(w) == alpha(X)(alpha(Y)(w)) on a word, for X = sigma_1, Y = sigma_2 (n >= 3)
    X, Y = sigma(1), sigma(2)
    probe = mul(gen(1), gen(3), inverse(gen(2))) if n >= 3 else gen(1)
    left_action = artin_of_word(n, bmul(X, Y))(probe) == artin_of_word(n, X)(artin_of_word(n, Y)(probe))
    right_would_be = artin_of_word(n, bmul(X, Y))(probe) == artin_of_word(n, Y)(artin_of_word(n, X)(probe))
    passed = (all(automorphism.values()) and all(r["holds"] for r in relations) and all(v["agrees_with_S1"] for v in induced.values())
              and all(product.values()) and left_action)
    return {
        "object": "S2", "n": n, "map": "alpha: B_n -> Aut(F_n), Birman-Brendle eq.(20)",
        "action_side": "LEFT: alpha(XY) = alpha(X) o alpha(Y); for a braid word the RIGHTMOST letter acts on F_n first",
        "generator_action": {f"sigma_{i}": g.to_json() for i, g in gens.items()},
        "inverse_generator_action": {f"sigma_{i}^-1": g.to_json() for i, g in invs.items()},
        "generator_is_automorphism": {f"sigma_{i}": v for i, v in automorphism.items()},
        "relations": relations,
        "induced_permutation": {f"sigma_{i}": v for i, v in induced.items()},
        "product_word": word_str(bw),
        "product_word_invariant": {f"sigma_{i}": v for i, v in product.items()},
        "reversed_product_word_invariant": {f"sigma_{i}": v for i, v in reversed_product.items()},
        "left_action_verified_on_probe": left_action,
        "right_action_law_holds_on_probe": right_would_be,
        "result": "PASS" if passed else "FAIL",
    }


# ---------------------------------------------------------------------------
# exact rational matrices (for Hurwitz tuples and Burau)
# ---------------------------------------------------------------------------

def mat(rows) -> Matrix:
    return tuple(tuple(Fraction(x) for x in r) for r in rows)


def identity(k: int) -> Matrix:
    return tuple(tuple(Fraction(int(i == j)) for j in range(k)) for i in range(k))


def mmul(A: Matrix, B: Matrix) -> Matrix:
    return tuple(tuple(sum(A[i][k] * B[k][j] for k in range(len(B))) for j in range(len(B[0]))) for i in range(len(A)))


def mtranspose(A: Matrix) -> Matrix:
    return tuple(tuple(A[i][j] for i in range(len(A))) for j in range(len(A[0])))


def minv(A: Matrix) -> Matrix:
    k = len(A)
    M = [list(A[i]) + [Fraction(int(i == j)) for j in range(k)] for i in range(k)]
    for c in range(k):
        piv = next(r for r in range(c, k) if M[r][c] != 0)
        M[c], M[piv] = M[piv], M[c]
        pv = M[c][c]
        M[c] = [x / pv for x in M[c]]
        for r in range(k):
            if r != c and M[r][c] != 0:
                f = M[r][c]
                M[r] = [a - f * b for a, b in zip(M[r], M[c])]
    return tuple(tuple(row[k:]) for row in M)


def mpow(A: Matrix, e: int) -> Matrix:
    return A if e == 1 else minv(A)


def trace(A: Matrix) -> Fraction:
    return sum(A[i][i] for i in range(len(A)))


def det2(A: Matrix) -> Fraction:
    return A[0][0] * A[1][1] - A[0][1] * A[1][0]


def mat_json(A: Matrix):
    return [[str(x) for x in r] for r in A]


# ---------------------------------------------------------------------------
# Hurwitz action on tuples, DERIVED from the frozen Artin action.
#   rho : F_n -> GL, rho(x_j) = M_j, extended to words left to right.
#   LEFT action on Hom(F_n, GL):  (beta . rho) = rho o alpha(beta^{-1}).
# ---------------------------------------------------------------------------

def rho_eval(tup: Sequence[Matrix], w: Word) -> Matrix:
    k = len(tup[0])
    out = identity(k)
    for g, e in w:
        out = mmul(out, mpow(tup[g - 1], e))
    return out


def hurwitz_left(n: int, w: BraidWord, tup: Sequence[Matrix]) -> Tuple[Matrix, ...]:
    """beta . rho = rho o alpha(beta^{-1}), read off on the generators."""
    alpha_inv = artin_of_word(n, binv(w))
    return tuple(rho_eval(tup, alpha_inv.images[j]) for j in range(1, n + 1))


def hurwitz_right(n: int, w: BraidWord, tup: Sequence[Matrix]) -> Tuple[Matrix, ...]:
    """rho . beta = rho o alpha(beta): the RIGHT-action variant (recorded, NOT the frozen convention)."""
    alpha = artin_of_word(n, w)
    return tuple(rho_eval(tup, alpha.images[j]) for j in range(1, n + 1))


def tuple_move_left(i: int, tup: Sequence[Matrix]) -> Tuple[Matrix, ...]:
    """Closed form of the frozen left action of sigma_i: (M_i, M_{i+1}) -> (M_i M_{i+1} M_i^{-1}, M_i)."""
    t = list(tup)
    t[i - 1], t[i] = mmul(mmul(tup[i - 1], tup[i]), minv(tup[i - 1])), tup[i - 1]
    return tuple(t)


def tuple_move_right_variant(i: int, tup: Sequence[Matrix]) -> Tuple[Matrix, ...]:
    """Closed form of the right variant of sigma_i: (M_i, M_{i+1}) -> (M_{i+1}, M_{i+1}^{-1} M_i M_{i+1})."""
    t = list(tup)
    t[i - 1], t[i] = tup[i], mmul(mmul(minv(tup[i]), tup[i - 1]), tup[i])
    return tuple(t)


def reflection(v, wv) -> Matrix:
    """An involution 1 - 2 v w^T / (w^T v) in GL_2(Q)."""
    v = [Fraction(x) for x in v]
    wv = [Fraction(x) for x in wv]
    d = wv[0] * v[0] + wv[1] * v[1]
    return tuple(tuple(Fraction(int(i == j)) - 2 * v[i] * wv[j] / d for j in range(2)) for i in range(2))


def frozen_tuples() -> Dict[str, Tuple[Matrix, ...]]:
    return {
        "n3_generic": (mat([[2, 1], [1, 1]]), mat([[1, 3], [0, 1]]), mat([[0, -1], [1, 2]])),
        "n4_involutions_00A": (reflection([1, 2], [3, 1]), reflection([2, -1], [1, 1]), reflection([1, 1], [1, 4]), reflection([3, 1], [1, -2])),
        "n5_generic": (mat([[1, 1], [0, 1]]), mat([[1, 0], [1, 1]]), mat([[2, 0], [0, Fraction(1, 2)]]), mat([[0, 1], [-1, 0]]), mat([[1, 2], [3, 7]])),
        "n6_generic": (mat([[1, 1], [0, 1]]), mat([[1, 0], [1, 1]]), mat([[3, 1], [2, 1]]), mat([[0, 1], [-1, 0]]), mat([[1, -1], [1, 0]]), mat([[2, 3], [1, 2]])),
    }


def hurwitz_certificate(label: str, tup: Tuple[Matrix, ...]) -> dict:
    n = len(tup)
    prod0 = rho_eval(tup, boundary_word(n))
    relations = [{"relation": name, "holds": hurwitz_left(n, a, tup) == hurwitz_left(n, b, tup)} for name, a, b in braid_relation_pairs(n)]
    closed_form = {i: hurwitz_left(n, sigma(i), tup) == tuple_move_left(i, tup) for i in range(1, n)}
    right_closed_form = {i: hurwitz_right(n, sigma(i), tup) == tuple_move_right_variant(i, tup) for i in range(1, n)}
    left_law = all(hurwitz_left(n, bmul(sigma(i), sigma(i + 1)), tup) == hurwitz_left(n, sigma(i), hurwitz_left(n, sigma(i + 1), tup)) for i in range(1, n - 1))
    inverse_ok = {i: hurwitz_left(n, sigma(i, -1), hurwitz_left(n, sigma(i), tup)) == tup and hurwitz_left(n, sigma(i), hurwitz_left(n, sigma(i, -1), tup)) == tup for i in range(1, n)}
    product_ok = {i: rho_eval(hurwitz_left(n, sigma(i), tup), boundary_word(n)) == prod0 for i in range(1, n)}
    # induced relabel: position j of the moved tuple carries an element conjugate to M_{p(j)} where p = pi_perm(sigma_i);
    # witnessed by (trace, det) agreement, and exactly by the closed form.
    relabel = {}
    for i in range(1, n):
        moved = hurwitz_left(n, sigma(i), tup)
        p = perm_of_generator(n, i)
        relabel[i] = all((trace(moved[j - 1]), det2(moved[j - 1])) == (trace(tup[p[j - 1] - 1]), det2(tup[p[j - 1] - 1])) for j in range(1, n + 1))
    nontrivial = {i: hurwitz_left(n, sigma(i), tup) != tup for i in range(1, n)}
    passed = (all(r["holds"] for r in relations) and all(closed_form.values()) and left_law and all(inverse_ok.values())
              and all(product_ok.values()) and all(relabel.values()) and any(nontrivial.values()))
    return {
        "object": "HURWITZ", "n": n, "tuple_label": label,
        "definition": "(beta . rho)(x_j) = rho(alpha(beta^{-1})(x_j)); LEFT action on Hom(F_n, GL_2(Q)), derived from the frozen Artin action, not assumed",
        "tuple": [mat_json(M) for M in tup],
        "ordered_product_rho(x_1...x_n)": mat_json(prod0),
        "relations": relations,
        "closed_form_left_move_(M_i,M_i+1)->(M_i M_i+1 M_i^-1, M_i)": {f"sigma_{i}": v for i, v in closed_form.items()},
        "right_variant_closed_form_(M_i,M_i+1)->(M_i+1, M_i+1^-1 M_i M_i+1)": {f"sigma_{i}": v for i, v in right_closed_form.items()},
        "left_action_law_(XY).rho=X.(Y.rho)": left_law,
        "inverse_action_restores_tuple": {f"sigma_{i}": v for i, v in inverse_ok.items()},
        "ordered_product_invariant": {f"sigma_{i}": v for i, v in product_ok.items()},
        "induced_relabel_matches_pi_perm": {f"sigma_{i}": v for i, v in relabel.items()},
        "nontrivial": {f"sigma_{i}": v for i, v in nontrivial.items()},
        "result": "PASS" if passed else "FAIL",
    }


# ---------------------------------------------------------------------------
# S3: Burau (BB Sec.4.2) at an integer specialization t. Matrices act on COLUMN vectors
#     from the LEFT; beta(XY) = beta(X) beta(Y).
# ---------------------------------------------------------------------------

def burau_unreduced(n: int, i: int, t: int) -> Matrix:
    M = [[Fraction(int(r == c)) for c in range(n)] for r in range(n)]
    r = i - 1
    M[r][r], M[r][r + 1], M[r + 1][r], M[r + 1][r + 1] = Fraction(1 - t), Fraction(t), Fraction(1), Fraction(0)
    return tuple(tuple(row) for row in M)


def burau_reduced(n: int, i: int, t: int) -> Matrix:
    k = n - 1
    M = [[Fraction(int(r == c)) for c in range(k)] for r in range(k)]
    c = i - 1                                   # column i (1-indexed) carries (-t, -t, -1) at rows i-1, i, i+1 (BB p.46, read from the PDF layout)
    if c - 1 >= 0:
        M[c - 1][c] = Fraction(-t)
    M[c][c] = Fraction(-t)
    if c + 1 < k:
        M[c + 1][c] = Fraction(-1)
    return tuple(tuple(row) for row in M)


def burau_of_word(n: int, w: BraidWord, t: int, reduced: bool) -> Matrix:
    f = burau_reduced if reduced else burau_unreduced
    out = identity(n - 1 if reduced else n)
    for i, e in w:
        out = mmul(out, mpow(f(n, i, t), e))
    return out


def burau_00a_reduced_minus_one(n: int, i: int) -> Matrix:
    """Byte-for-byte replica of the matrices used by 00A check S1 (reduced_burau_minus_one, t = -1)."""
    t = -1
    k = n - 1
    M = [[Fraction(int(r == c)) for c in range(k)] for r in range(k)]
    M[i - 1][i - 1] = Fraction(-t)
    if i - 2 >= 0:
        M[i - 1][i - 2] = Fraction(t)
    if i <= n - 2:
        M[i - 1][i] = Fraction(1)
    return tuple(tuple(row) for row in M)


def nullspace_dim_and_solution(rows: List[List[Fraction]], nvars: int):
    """Gaussian elimination over Q for a homogeneous system; returns (nullity, one nonzero solution or None)."""
    M = [r[:] for r in rows]
    pivots = []
    rnk = 0
    for c in range(nvars):
        piv = next((r for r in range(rnk, len(M)) if M[r][c] != 0), None)
        if piv is None:
            continue
        M[rnk], M[piv] = M[piv], M[rnk]
        pv = M[rnk][c]
        M[rnk] = [x / pv for x in M[rnk]]
        for r in range(len(M)):
            if r != rnk and M[r][c] != 0:
                f = M[r][c]
                M[r] = [a - f * b for a, b in zip(M[r], M[rnk])]
        pivots.append(c)
        rnk += 1
    free = [c for c in range(nvars) if c not in pivots]
    if not free:
        return 0, None
    sol = [Fraction(0)] * nvars
    sol[free[0]] = Fraction(1)
    for r, c in enumerate(pivots):
        sol[c] = -M[r][free[0]]
    return len(free), sol


def rank(A: Matrix) -> int:
    rows = [list(r) for r in A]
    nullity, _ = nullspace_dim_and_solution([list(r) for r in mtranspose(A)], len(A))
    return len(A) - nullity


def invariant_alternating_forms(gens: List[Matrix]) -> Tuple[int, Matrix | None]:
    """Solve M^T J M = J for skew J over Q; return (dimension of solution space, one solution)."""
    k = len(gens[0])
    pairs = [(a, b) for a in range(k) for b in range(a + 1, k)]
    idx = {p: q for q, p in enumerate(pairs)}

    def J_of(coeffs):
        J = [[Fraction(0)] * k for _ in range(k)]
        for (a, b), q in idx.items():
            J[a][b], J[b][a] = coeffs[q], -coeffs[q]
        return tuple(tuple(r) for r in J)

    rows = []
    for M in gens:
        for q in range(len(pairs)):
            unit = [Fraction(0)] * len(pairs)
            unit[q] = Fraction(1)
            J = J_of(unit)
            R = mmul(mmul(mtranspose(M), J), M)
            diff = [[R[a][b] - J[a][b] for b in range(k)] for a in range(k)]
            rows.append((q, diff))
    # assemble the homogeneous linear system: for each generator g and matrix entry (a,b),
    # sum_q coeff_q * diff_{g,q}[a][b] = 0
    system = []
    for g in range(len(gens)):
        block = [d for qq, d in rows[g * len(pairs):(g + 1) * len(pairs)]]
        for a in range(k):
            for b in range(k):
                system.append([block[q][a][b] for q in range(len(pairs))])
    nullity, sol = nullspace_dim_and_solution(system, len(pairs))
    return nullity, (J_of(sol) if sol is not None else None)


def intertwiner(A: List[Matrix], B: List[Matrix]):
    """Solve X A_i = B_i X for all i over Q. Returns (nullity, X) with X an invertible solution, or (nullity, None)."""
    k = len(A[0])
    system = []
    for a, b in zip(A, B):
        # entry (r, c) of X a - b X, linear in the k*k unknowns X[u][v]
        for r in range(k):
            for c in range(k):
                row = [Fraction(0)] * (k * k)
                for v in range(k):
                    row[r * k + v] += a[v][c]          # (X a)[r][c] = sum_v X[r][v] a[v][c]
                for u in range(k):
                    row[u * k + c] -= b[r][u]          # (b X)[r][c] = sum_u b[r][u] X[u][c]
                system.append(row)
    nullity, sol = nullspace_dim_and_solution(system, k * k)
    if sol is None:
        return 0, None
    X = tuple(tuple(sol[r * k + c] for c in range(k)) for r in range(k))
    return nullity, (X if rank(X) == k else None)


def dual(A: Matrix) -> Matrix:
    return mtranspose(minv(A))


def relation_between(A: List[Matrix], B: List[Matrix]) -> dict:
    """Which of {B ~ A, B ~ dual(A)} holds by an explicit invertible intertwiner."""
    out = {}
    for name, f in (("equivalent", lambda X: X), ("equivalent_to_dual_(inverse_transpose)", dual)):
        nullity, X = intertwiner([f(a) for a in A], B)
        out[name] = {"commutant_dimension": nullity, "intertwiner": mat_json(X) if X is not None else None}
    return out


def s3_certificate(n: int, frozen_t: int = -1, control_t: int = 2) -> dict:
    out = {"object": "S3", "n": n, "frozen_specialization_t": frozen_t, "control_specialization_t": control_t,
           "matrix_action_convention": "matrices act on column vectors from the left; beta(XY) = beta(X) beta(Y)"}
    for variant, reduced in (("unreduced", False), ("reduced", True)):
        rec = {}
        for t in (frozen_t, control_t):
            rels = [{"relation": name, "holds": burau_of_word(n, a, t, reduced) == burau_of_word(n, b, t, reduced)} for name, a, b in braid_relation_pairs(n)]
            rec[f"t={t}"] = {"generators": {f"sigma_{i}": mat_json((burau_reduced if reduced else burau_unreduced)(n, i, t)) for i in range(1, n)},
                             "relations_hold": all(r["holds"] for r in rels), "relations": rels}
        out[variant] = rec
    # t = 1: the unreduced representation factors through S_n (BB Sec.4.2): matrices are permutation matrices
    perm_at_1 = all(burau_unreduced(n, i, 1) == tuple(tuple(Fraction(int(perm_of_generator(n, i)[r] == c + 1)) for c in range(n)) for r in range(n)) for i in range(1, n))
    out["unreduced_at_t=1_is_permutation_matrix_of_pi_perm"] = perm_at_1
    # decomposition (BB: splits into 1-dim + (n-1)-dim). Column vector of ones is fixed; row-vector action preserves sum = 0.
    ones = tuple((Fraction(1),) for _ in range(n))
    fixed = all(mmul(burau_unreduced(n, i, frozen_t), ones) == ones for i in range(1, n))
    # induced matrices of the RIGHT row-action on the sum-zero hyperplane with basis f_k = e_k - e_{k+1}
    basis = [tuple(Fraction(int(c == k)) - Fraction(int(c == k + 1)) for c in range(n)) for k in range(n - 1)]
    induced = []
    for i in range(1, n):
        U = burau_unreduced(n, i, frozen_t)
        cols = []
        for f in basis:
            v = tuple(sum(f[r] * U[r][c] for r in range(n)) for c in range(n))     # row vector times U
            # express v in the basis f_k: v = sum a_k f_k  =>  a_k = sum_{r<=k} v_r
            coeffs = [sum(v[:k + 1]) for k in range(n - 1)]
            assert all(sum(coeffs[k] * basis[k][c] for k in range(n - 1)) == v[c] for c in range(n))
            cols.append(coeffs)
        induced.append(tuple(tuple(cols[c][r] for c in range(n - 1)) for r in range(n - 1)))
    reduced_gens = [burau_reduced(n, i, frozen_t) for i in range(1, n)]
    # the row action is a RIGHT action (v (U1 U2) = (v U1) U2); its transposes form a left representation
    row_rep = [mtranspose(M) for M in induced]
    row_rels = all(burau_of_word_generic(row_rep, a) == burau_of_word_generic(row_rep, b) for _, a, b in braid_relation_pairs(n))
    out["decomposition"] = {
        "column_ones_fixed_by_unreduced": fixed,
        "row_action_on_sum_zero_hyperplane_is_a_representation_after_transpose": row_rels,
        "row_representation_vs_BB_reduced": relation_between(row_rep, reduced_gens),
    }
    # 00A replica comparison
    a00 = [burau_00a_reduced_minus_one(n, i) for i in range(1, n)]
    rels00 = all(burau_of_word_generic(a00, a) == burau_of_word_generic(a00, b) for _, a, b in braid_relation_pairs(n))
    out["comparison_with_00A_S1_matrices"] = {"00A_relations_hold": rels00, "00A_vs_BB_reduced_t=-1": relation_between(a00, reduced_gens)}
    # invariant alternating forms at the frozen specialization, for BB reduced, its dual, and the 00A matrices
    forms = {}
    for label, gens_ in (("BB_reduced", reduced_gens), ("BB_reduced_dual", [dual(M) for M in reduced_gens]), ("00A_matrices", a00)):
        nullity, J = invariant_alternating_forms(gens_)
        forms[label] = {"solution_space_dimension": nullity, "rank_of_solution": rank(J) if J is not None else None,
                        "nondegenerate": (J is not None and rank(J) == n - 1)}
    forms["dimension_n_minus_1"] = n - 1
    forms["note"] = ("LOCAL algebra only. For even n the existence of an invariant alternating form is NOT invariant under passing to the dual "
                     "representation (a degenerate form on V is an intertwiner V -> V*, not V* -> V), so the 00A even-n 'rank 2g form' is a "
                     "statement about one of two dual conventions. The hyperelliptic/symplectic reading is source-bound for odd n only (S4).")
    out["invariant_alternating_forms_t=-1"] = forms
    comparable = (out["decomposition"]["row_representation_vs_BB_reduced"]["equivalent"]["intertwiner"] is not None
                  or out["decomposition"]["row_representation_vs_BB_reduced"]["equivalent_to_dual_(inverse_transpose)"]["intertwiner"] is not None)
    comparable00 = (out["comparison_with_00A_S1_matrices"]["00A_vs_BB_reduced_t=-1"]["equivalent"]["intertwiner"] is not None
                    or out["comparison_with_00A_S1_matrices"]["00A_vs_BB_reduced_t=-1"]["equivalent_to_dual_(inverse_transpose)"]["intertwiner"] is not None)
    passed = (all(out[v][f"t={t}"]["relations_hold"] for v in ("unreduced", "reduced") for t in (frozen_t, control_t)) and perm_at_1 and fixed
              and row_rels and comparable and rels00 and comparable00)
    out["result"] = "PASS" if passed else "FAIL"
    return out


def burau_of_word_generic(gens: List[Matrix], w: BraidWord) -> Matrix:
    out = identity(len(gens[0]))
    for i, e in w:
        out = mmul(out, mpow(gens[i - 1], e))
    return out


# ---------------------------------------------------------------------------
# kernel witness for the permutation quotient (used by the hostile gate): sigma_1^2 lies in
# ker(pi_perm) but alpha(sigma_1^2) != id, so sigma_1^2 != 1 in B_n and pi_perm is not faithful.
# ---------------------------------------------------------------------------

def permutation_quotient_kernel_witness(n: int) -> dict:
    w = bmul(sigma(1), sigma(1))
    return {"word": "sigma_1^2", "pi_perm_image_is_identity": perm_of_word(n, w) == perm_identity(n),
            "artin_image_is_identity": artin_of_word(n, w).is_identity(),
            "artin_image": artin_of_word(n, w).to_json(),
            "conclusion": "sigma_1^2 in ker(pi_perm) and alpha(sigma_1^2) != id, hence sigma_1^2 != 1 and pi_perm is NOT faithful (uses only that alpha is a homomorphism, not Artin's faithfulness theorem)"}
