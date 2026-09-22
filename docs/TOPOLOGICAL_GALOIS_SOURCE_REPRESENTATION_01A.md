# Topological Galois Source-Representation Qualification (01A)

**Work order:** `WO-FORMAL-TOPOLOGICAL-GALOIS-SOURCE-REPRESENTATION-01A`  
**Proposed disposition:** `TOPOLOGICAL_GALOIS_SOURCE_REPRESENTATION_QUALIFIED` — `PROPOSED_BY_EXECUTING_AGENT_PENDING_INDEPENDENT_REVIEW`  
**Authority:** `NONE` (no theorem; bridge `NOT_EXECUTED`; `G_diff` `NOT_COMPUTED`; Morales-Ramis `NOT_AUTHORIZED`; FTT `NOT_REQUIRED`)  
**Package:** `experiments/topological-galois-source-representation-01a/` · **Code:** `src/msk_formal_discovery/topological_galois/`

## Gate 0 — canonical integration

| Check | Value |
|---|---|
| Mathematics main | `2337c7d744f176274997374a7d4057c7272f715d` (= origin/main; R1 `71b9a147` is an ancestor) |
| Formal Discovery main | `60b92dcb3069fe8312ee8901860f24233df1562f` (= origin/main; this branch starts there) |
| candidate freeze digest | `889cc252…` recomputed from the blob `e0c5d462…` — **exact** |
| reconstruction digest | `5dbaab30…` in both `determination` (blob `a2098a65…`) and `reconstruction-receipt` (blob `fff84ffc…`) — **exact** |
| predecessor artifacts | all six present at the pin; blob SHAs recorded in `source-representation-manifest.v0.1.json#/gate0` |

## 1. Protocol

1. Freeze every convention the work order names, each bound to a locator in a content-hashed source (§2).
2. Build S1–S3 with exact integer / free-group arithmetic for `n = 3, 4, 5, 6`; derive the Hurwitz action from the frozen Artin action rather than assuming it; record machine-readable certificates.
3. Re-derive the target topological domain from the accepted CAND-1 freeze, including infinity.
4. Freeze the single admissible source/target relation (an action, not an identification, not an intertwiner of representations).
5. Run 16 hostile fixtures and their repaired counterparts through a typed gate; run PC1–PC6 by execution.
6. Classify each source object under the dependency-minimization rule and output the minimal package.

Reproduce: `python -m msk_formal_discovery.topological_galois.runner --check` (~5 s). Since R1 the check **replays** `target_domain.derive_all()` with sympy, compares its canonical digest to the committed artifact, and rebuilds every other artifact from the replayed object; it fails closed if sympy is unavailable. `--write` regenerates.

## 2. Convention freeze (source: Birman–Brendle, *Braids: A Survey*, arXiv:math/0409205v2, SHA-256 `a2e02e79…`)

| Convention | Frozen value | Locator |
|---|---|---|
| braid multiplication | juxtaposition; `X Y` = `X` then `Y`; words read left to right | §1, Fig. 1 |
| `σ_i` | elementary braid exchanging strands `i, i+1`; orientation pinned by eq. (20) | §1.2 eq. (2), §4.7 |
| `F_n` generators | `x_i` = loop at `d_0 ∈ ∂D_n`, **counterclockwise** about puncture `q_i` | §4.4 |
| action side | **left**: `α(XY) = α(X)∘α(Y)`; rightmost letter of a word acts first | §4.7 (19), (20); verified S2 |
| Artin action | `σ_i·x_i = x_{i+1}`, `σ_i·x_{i+1} = x_{i+1}⁻¹ x_i x_{i+1}`, `σ_i·x_j = x_j` otherwise | eq. (20) |
| inverse (derived, verified) | `σ_i⁻¹·x_{i+1} = x_i`, `σ_i⁻¹·x_i = x_i x_{i+1} x_i⁻¹` | S2 certificate |
| Hurwitz action | **left** on `Hom(F_n, G)`: `β·ρ = ρ∘α(β⁻¹)`; closed form `(M_i, M_{i+1}) ↦ (M_i M_{i+1} M_i⁻¹, M_i)` | derived; HURWITZ certificate |
| right variant (recorded, not frozen) | `ρ∘α(β)`: `(M_i, M_{i+1}) ↦ (M_{i+1}, M_{i+1}⁻¹ M_i M_{i+1})` | HURWITZ certificate |
| `B_n → S_n` | `σ_i ↦ (i i+1)`; permutations composed left to right so the map is a homomorphism | §1.1 (1), §4.1 |
| Burau, unreduced | `σ_i ↦ I_{i−1} ⊕ [[1−t, t],[1, 0]] ⊕ I_{n−i−1}` in `GL_n` | §4.2 |
| Burau, reduced | `σ_i ↦ I_{i−2} ⊕ [[1, −t, 0],[0, −t, 0],[0, −1, 1]] ⊕ I_{n−i−2}` in `GL_{n−1}`, `−t` at `(i,i)` | §4.2 p. 46, **signs read from the rendered page** |
| specialization | `t = −1` frozen; `t = 2` control; `t = 1` = permutation representation | BMP §1; BB §4.2 |
| matrix action | column vectors, from the left; `β(XY) = β(X)β(Y)` | S3 certificate |
| conjugation | `a b a⁻¹` | eq. (20) |

A plain-text extraction of p. 46 drops the minus signs; transcribed that way the "reduced" matrices have the wrong character (`tr = 3` instead of `1` at `n=3`) and are not a subquotient of the unreduced representation. The freeze therefore records that the signs were read from the rendered PDF, and a test pins the wrong transcription as rejected.

## 3. Results

### S1 — `π_perm: B_n → S_n` (`LOAD_BEARING`)
For each `n`: braid relations, far commutation, `σ_i ↦ (i i+1)`, `σ_i² ↦ 1`, surjectivity by closure (`|image| = n!`). **Not faithful**: `σ_1² ∈ ker π_perm` while `α(σ_1²) ≠ id` (uses only that `α` is a homomorphism, not Artin's faithfulness theorem).

### S2 — `α: B_n → Aut(F_n)` (`LOAD_BEARING`)
Each generator image is an automorphism (exact inverse), all relations hold in `Aut(F_n)`, the induced permutation on the abelianization equals `π_perm(σ_i)`, the product word `x_1⋯x_n` is invariant (the reversed product is **not**), and the left-action law holds while the right-action law fails on a probe word.

### Hurwitz action (derived)
On four frozen tuples in `GL_2(ℚ)` (`n = 3..6`): relations, closed form, `(XY)·ρ = X·(Y·ρ)`, inverse restores the tuple, ordered product invariant, induced relabel of `(tr, det)` matches `π_perm`, nontrivial.

### S3 — Burau (`CONTROL_ONLY`)
Relations at `t = −1` and `t = 2` for both variants; `t = 1` gives permutation matrices; the column all-ones vector is fixed; the row action on the sum-zero hyperplane, transposed, is **equivalent to BB's reduced representation** by an explicit intertwiner (all `n`).

### PC6 — overlap with accepted 00A controls
- 00A's S2 tuple move `(t_i, t_{i+1}) ↦ (t_i t_{i+1} t_i⁻¹, t_i)` **is** the frozen left Hurwitz move, exactly.
- 00A's S1 matrices vs BB reduced at `t = −1`: **odd `n` (3, 5): equivalent** (explicit intertwiner; self-dual). **Even `n` (4, 6): equivalent to the dual only** (intertwiner = identity, i.e. 00A's matrices are the inverse-transpose of BB's) and **not** equivalent to BB reduced.
- Consequence: BB reduced at `t = −1` has **no** invariant alternating form for `n = 4, 6`; its dual has a unique degenerate one of rank `2g`. 00A's even-`n` "rank-`2g` form" is therefore a statement about one of two inequivalent dual conventions. For odd `n` the form is unique and nondegenerate in both.

### Burau qualification matrix

| `n` | relations `t=−1` / `t=2` | invariant alternating form (BB reduced / dual) | symplectic reading | 00A vs BB |
|---|---|---|---|---|
| 3 | ✓ / ✓ | 1-dim, rank 2 / same | `CONTROL_ONLY`, source-bound (BMP, `n = 2g+1`) | equivalent |
| 4 | ✓ / ✓ | **none** / 1-dim, rank 2 | `LOCAL_ALGEBRA_CONTROL_ONLY` — `SOURCE_INSUFFICIENT` | dual only |
| 5 | ✓ / ✓ | 1-dim, rank 4 / same | `CONTROL_ONLY`, source-bound (BMP) | equivalent |
| 6 | ✓ / ✓ | **none** / 1-dim, rank 4 | `LOCAL_ALGEBRA_CONTROL_ONLY` — `SOURCE_INSUFFICIENT` | dual only |

**`BURAU_ROLE = CONTROL_ONLY`.** No source was sought for the even-degree statement: Burau is not on the bridge critical path and the work order forbids adding dependencies for symmetry.

## 4. Target topological domain (from the accepted CAND-1 freeze)

```text
H_n = (p1² + p2²)/2 + P_n(q1; a) + (μ + λ q1) q2²/2          invariant plane q2 = p2 = 0
p1² = f_{a,E}(q1),   f_{a,E}(q) = 2(E − P_n(q; a))             ← the singular polynomial is E − P_n, NOT P_n
NVE:            ξ'' + (μ + λ q1(t)) ξ = 0
algebraic NVE:  f y'' + (f'/2) y' + (μ + λ q) y = 0   (x = q = q1)
```

Verified symbolically for `n = 3..6`: invariant plane, energy relation, splitting of the VE, the NVE, the change of variable, exponents `(0, ½)` at each simple root, infinity regular-singular with exponents `(0,1)`, `(0,3/2)`, `(0,2)` for `n = 4,5,6` (and the `λ/a_3`-dependent pair for `n = 3`).

**Puncture accounting.** Base `P¹_q ∖ ({n roots of f_{a,E}} ∪ {∞})`, `n + 1` punctures. `π_1 ≅ F_n` with generators `x_1..x_n` (counterclockwise about `r_j`, based at `d_0` on the boundary of a disk containing all roots) and `x_∞ = (x_1⋯x_n)⁻¹`; relation `x_1⋯x_n x_∞ = 1`. Omitting infinity would give rank `n − 1`, which is why it must be counted. Root ordering follows the puncture ordering of `D_n`; any reordering is an element of `S_n` and is recorded, not assumed.

```text
B_n != F_n
```

## 5. Source/target relation — the only one allowed

```text
   B_n ──α──▶ Aut(F_n)                 and, separately,              ρ_tgt : F_n ─▶ GL_2(ℂ)   (NOT computed)
                                                                              │
   hence B_n acts on Hom(F_n, GL_2(ℂ))/conj by  β·[ρ] = [ρ ∘ α(β⁻¹)]  ◀──────┘
```

This is an action / semidirect-product relationship. It does **not** establish `ρ_src = ρ_tgt`, `B_n = F_n`, `Burau = NVE monodromy`, or that source data determine `G_diff`.

```text
SOURCE_GROUP_ACTION  !=  TARGET_MONODROMY_REPRESENTATION
GROUP_ACTION         !=  REPRESENTATION_VALUE
```

## 6. Hostile controls (16, each rejected for exactly its stated codes) and repaired counterparts (7, all admitted)

`B_n = F_n` · quotient as faithful · Artin direction reversed · left/right switched · word order reversed · Hurwitz tuple convention switched · reduced/unreduced conflated · specialization drift · even-`n` local form as theorem · odd source extrapolated to even · infinity omitted · `P_n` for `E − P_n` · action relabeled monodromy · monodromy relabeled `G_diff` without Zariski scope · FTT import · shared word "monodromy". Full records: `hostile-controls.v0.1.json`. The gate keys on typed fields; a repaired record with the same name is admitted.

## 7. Dependency-minimization determination

| Object | Classification | Why |
|---|---|---|
| S1 `π_perm` | **LOAD_BEARING** | BO-1 relabels roots / conjugacy classes; BO-3's degree invariants live on `S_n` |
| S2 Artin/Hurwitz | **LOAD_BEARING** | BO-1's transport map is *defined* through `α`; the only structural relation |
| S3 Burau | **CONTROL_ONLY** | no obligation mentions it; kept for the 00A overlap and as carrier of S4 |
| S4 symplectic, odd `n` | **CONTROL_ONLY** (BMP-bound) | not needed to state any obligation |
| S4 symplectic, even `n` | **SOURCE_INSUFFICIENT** (`LOCAL_ALGEBRA_CONTROL_ONLY`) | no bound source; the local form is convention-dependent |

Minimal package: **`{π_perm, α}`**. The work order's expected hypothesis was *earned*, not inherited: the even-`n` dual-convention finding is new evidence that Burau must not be load-bearing.

## 8. Remaining bridge obligation (for WO-FORMAL-HAMILTONIAN-VARIATIONAL-BRIDGE-01A)

- **BO-1** (structural, expected true) — now *statable* with S1 + S2 alone: the transport `β ↦ β·[ρ_tgt]` with its domain of validity.
- **BO-2** (predicate transport, **expected false**) — fix `(n, a, E)`, hence the root configuration and all of S1/S2's data; vary `(μ, λ)`; ask whether "`G⁰` abelian" changes. Nothing on the source side sees `(μ, λ)`. A change is `SOURCE_DATA_ALONE_INSUFFICIENT_FOR_TARGET_PREDICATE` — a mathematical negative, not an infrastructure failure.
- **BO-3** (residual, unknown).

Prerequisites carried forward from 00A: bind Morales-Ruiz 1999 (Zariski-closure / density) before `ρ_tgt` may be called evidence about `G_diff`; qualify a Kovacic implementation; preregister the member grid before any Galois computation.

## Nonclaims

No theorem. No Galois group, no `G⁰`, no `(μ, λ)` value, no Kovacic run, no integrability or chaos statement. No write to Mathematics, FTT, ONTO or Ruliology; the Mathematics root source registry is untouched.
