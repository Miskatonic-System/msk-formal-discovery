# Lamé Parameter Map and Minimal Missing-Information Qualification (01B)

**Work order:** `WO-FORMAL-HAMILTONIAN-VARIATIONAL-BRIDGE-01B`  
**Proposed disposition:** `LAME_PARAMETER_MAP_ESTABLISHED` + `LAMBDA_ALONE_INSUFFICIENT` — R1 applied (pooled cardinality derived mechanically; accessory-parameter scope corrected) — `PROPOSED_BY_EXECUTING_AGENT_PENDING_INDEPENDENT_REVIEW`  
**Canonical start:** `11c6e8cda42eb0b23c480a346f35c1bfe337a0fe` (01A + R1 merged) · **Package:** `experiments/hamiltonian-variational-bridge-01b/` · **Code:** `bridge_01b.py`, `bridge_01b_finalize.py`

BO-2 is canonically refuted and is **not reopened** here. The question of this work order is the next one: *which target-side coordinate is actually load-bearing?*

## Result in one paragraph

On the frozen 01A member (`P_3 = q³ − q − 1`, `E = −1`, `f = −2q³ + 2q`, one `SOURCE_SIGNATURE = a8407db0…`), the NVE is exactly a Lamé equation with `ℓ(ℓ+1) = 2λ`, `B = −μ` on the lemniscatic curve `℘'² = 4℘³ − ℘`. Across the canonical 01A cells plus ten new pre-registered cells, `ABELIAN_IDENTITY_COMPONENT(G_diff)` is constant in `μ` at every sampled `λ` that has at least two sampled `μ` values and integer or irrational `ℓ` (`λ = 0, 1, 2`; `λ = −1` and `λ = 3` have a single sampled `μ`), but at `λ = 3/8` (`ℓ = ½`, the Brioschi–Halphen–Crawford family) it is **TRUE at `μ = 0` and FALSE at `μ ∈ {½, −1, 2}`** — same source data, same `λ`, different `μ`, different predicate. So `λ` alone is **insufficient**; across the 18 pooled sampled cells, `AUGMENTED_FULL = ORIGINAL + (λ, μ)` is the smallest **of the three tested candidate signatures** on which the predicate is a function. The only *observed* within-λ split sits at `ℓ = ½`, at the point (`B = 0`) the bound theorem singles out; no claim is made that μ can matter only there, and no sufficiency is claimed from a finite grid.

## Gate 0

Formal Discovery main `11c6e8cd` (= origin/main; 01A-R1 `58a31f49` ancestor); 01A package `bridge_finalize --check` PASS (21/21 hostile); provider identity parity: Maxima 5.49.0, `kovacicODE.mac` SHA-256 `ab7f476a…` — identical to 01A, **no requalification needed**; freeze digest `889cc252…` carried through the 01A preregistration.

## Phase A — exact parameter map (`LAME_PARAMETER_MAP_ESTABLISHED`)

```text
q'² = f(q) = −2q³ + 2q        (on the invariant plane, p₁ = q₁', H = E)
q = −2℘(t)   ⇒   4℘'² = f(−2℘) = 16℘³ − 4℘   ⇒   ℘'² = 4℘³ − ℘        g₂ = 1, g₃ = 0   (lemniscatic, J = 1)
converse (imposing ℘'² = 4℘³ − ℘):  q'² − f(q) = 0  exactly
NVE  ξ'' + (μ + λq)ξ = 0   ⇒   ξ'' = [2λ℘(t) − μ] ξ   =   [ℓ(ℓ+1)℘ + B] ξ   with   ℓ(ℓ+1) = 2λ,  B = −μ
```

The algebraic NVE over `C(q)` classified in 01A, rewritten in `x = ℘ = −q/2`, **is** the Lamé algebraic form `p(x)Y'' + (p'/2)Y' − (ℓ(ℓ+1)x + B)Y = 0`, `p = 4x³ − x` (coefficient-wise identity, factor 1); `C(q) = C(x)`, so the 01A Galois groups are the Galois groups of the algebraic Lamé equation. Singular points `e_i = {−½, 0, ½}`: Maier's harmonic case `α{−1,0,1}`, `α = ½`.

```text
POLYNOMIAL_DEGREE_n (= 3)   !=   LAME_INDEX_ell   (ℓ(ℓ+1) = 2λ)
```

| `λ` | `2λ = ℓ(ℓ+1)` | `ℓ` | class |
|---|---|---|---|
| 0 | 0 | 0 | integer |
| 1 | 2 | 1 | integer |
| 3 | 6 | 2 | integer |
| 2 | 4 | `(−1+√17)/2` | irrational |
| −1 | −2 | `(−1±i√7)/2` | complex |
| 3/8 | 3/4 | ½ | half-integer (BHC, `m = 0`) |

## Phase B — source custody (`LAME_CLASSIFICATION_AUTHORITY = PARTIAL`)

| Source | Status | What is bound |
|---|---|---|
| Maier, *Algebraic solutions of the Lamé equation, revisited* (arXiv:math/0206285v1; JDE 198, 2004) | **BOUND** `3be9cb7a…` | algebraic form (1.1) with exponents; Weierstrass form = strong pullback by `x = ℘(t)` (§5); harmonic case (Def. 3.2); classical facts "never cyclic, dihedral only if `2ℓ ∈ Z`"; Thm 3.1 / 5.1 finite-monodromy necessary conditions for `2ℓ ∉ Z` |
| Chou–Wang–Wu, *Characterization and enumeration on Lamé equations with finite monodromy* (arXiv:2402.16286v1) | **BOUND** `d95ac0f9…` | algebraic form (1.2); **Theorem 1.2 (Brioschi–Halphen–Crawford):** for `m ∈ Z≥0` there is a weighted-homogeneous `p_m(B; g₂, g₃)` of degree `m+1` in `B`, coefficients in `Z[g₂/4, g₃/4]`, with `p_m(B) = 0` iff the algebraic Lamé equation with `ℓ = m + ½` has finite projective monodromy `K₄`; Thm 1.5 (Beukers–van der Waall) |
| Morales-Ruiz 1999 | **UNAVAILABLE** (not upgraded) | — |

**Not bound** (expectation only, decided computationally): the integer-`ℓ` Lamé–Hermite Liouvillian statement, and "`p_m(B) ≠ 0 ⇒ SL₂`" for half-integer `ℓ`.

For `m = 0` the bound theorem is sharp by weights: `B` has weight 2 and no monomial in `g₂` (weight 4), `g₃` (weight 6) has weight 2, so `p_0(B) = c·B` and the finite case is exactly `B = 0`, i.e. `μ = 0`. This is what made `λ = 3/8` the designed falsifier.

## Phase C — missing-information decomposition (historical 01A evidence)

`ORIGINAL_SOURCE_SIGNATURE = {n, a, E, roots, π_perm, Artin/Hurwitz}`; candidates `AUGMENTED_LAMBDA`, `AUGMENTED_LAME_INDEX` (`= ORIGINAL + ℓ(ℓ+1) = 2λ`, a bijective relabelling of the former), `AUGMENTED_FULL`.

| `λ` (01A) | `μ = 0` | `μ = 1` | `ℓ` | constant in `μ`? |
|---|---|---|---|---|
| 0 | TRUE | TRUE | 0 | yes |
| 1 | TRUE | TRUE | 1 | yes |
| 2 | FALSE | FALSE | irrational | yes |
| 3 | TRUE | — | 2 | (one cell) |
| −1 | — | FALSE | complex | (one cell) |

**Q1:** consistent with `λ` / `ℓ(ℓ+1)` being load-bearing — but no half-integer `ℓ` was sampled in 01A. **Q2:** on 01A's cells `μ` never changed the predicate; whether it *can* is what Phase D tests, and the bound BHC theorem predicts it does precisely at half-integer `ℓ`.

## Phase D — pre-registered accessory-parameter test

Grid frozen and committed at `752e897d` **before** any provider run: `λ = 1` (TRUE class) × `μ ∈ {−1, ½, 3}`; `λ = 2` (FALSE class) × `μ ∈ {−1, ½, 3}`; `λ = 3/8` (`ℓ = ½`) × `μ ∈ {0, ½, −1, 2}`. Same member, same `SOURCE_SIGNATURE`, same provider (`nix` Maxima, digest parity), same four rules (R4 / R2L / RU / RD) as 01A. Prior expectations recorded in the commit.

| Cell | `(μ, λ)` | `ℓ` | `B` | provider orig/red | predicate | rule |
|---|---|---|---|---|---|---|
| d1 | (−1, 1) | 1 | 1 | Liouv./Liouv. | **TRUE** | R2L |
| d2 | (½, 1) | 1 | −½ | Liouv./Liouv. | **TRUE** | RU |
| d3 | (3, 1) | 1 | −3 | Liouv./Liouv. | **TRUE** | R2L |
| d4 | (−1, 2) | irr. | 1 | nil/nil | **FALSE** | R4 |
| d5 | (½, 2) | irr. | −½ | nil/nil | **FALSE** | R4 |
| d6 | (3, 2) | irr. | −3 | nil/nil | **FALSE** | R4 |
| d7 | (0, 3/8) | ½ | 0 | Liouv./Liouv. | **TRUE** | R2L |
| d8 | (½, 3/8) | ½ | −½ | nil/nil | **FALSE** | R4 |
| d9 | (−1, 3/8) | ½ | 1 | nil/nil | **FALSE** | R4 |
| d10 | (2, 3/8) | ½ | −2 | nil/nil | **FALSE** | R4 |

All ten outcomes coincide with the pre-registered expectations, including the bound prediction that only `B = 0` is finite at `ℓ = ½`.

**Adjudication (pooled 01A + 01B: `pooled_cell_count = 18`, `distinct_lambda_count = 6`, `distinct_lambdas = [−1, 0, 3/8, 1, 2, 3]`, ordered by exact rational value — all derived mechanically and recomputed by the validator):**

```text
λ = 3/8:  same SOURCE_SIGNATURE, same λ,  μ = 0 → TRUE (d7)   vs   μ = ½ → FALSE (d8)     [also d9, d10]
                                          ⇒  LAMBDA_ALONE_INSUFFICIENT
λ = 0, 1, 2:         predicate constant across all sampled μ (≥ 2 values each)
λ = −1, 3:           only ONE sampled μ each — no evidence either way about μ-dependence
```

Minimal missing information, scoped exactly: `ORIGINAL` insufficient (BO-2); `ORIGINAL + λ` insufficient; `ORIGINAL + ℓ(ℓ+1)` an equivalent relabelling, therefore insufficient; `ORIGINAL + (λ, μ)` the smallest **of the three tested candidate signatures** on which the predicate is a function across the 18 sampled cells. This is **not** promoted to a globally minimal or universally sufficient signature, to "λ and μ always determine `G⁰`", or to "no other hidden coordinate exists".

**Accessory-parameter scope.** The only observed within-λ predicate split in the pooled sample occurs at `ℓ = ½` (`λ = 3/8`). No universal claim is made that μ can affect the predicate only in half-integer-ℓ classes; `λ = −1` and `λ = 3` currently have only one sampled μ value, so the absence of a split there is not evidence of μ-independence.

```text
ONLY_OBSERVED_SPLIT_AT_HALF_INTEGER   !=   MU_DEPENDENCE_ONLY_AT_HALF_INTEGER
MINIMAL_AMONG_TESTED_CANDIDATES        !=   UNIVERSALLY_MINIMAL_SUFFICIENT_SIGNATURE
```

**Not claimed:** `LAMBDA_SUFFICIENT` on any class; universal sufficiency of any signature; anything about `n ≠ 3`.

## Firewalls

BO-2 canonically refuted, not reopened · BO-1 not executed · BO-3 parked (no `n = 4..6`) · Morales-Ramis not applied · no integrability or chaos claim · FTT not required · Burau control only. Provider unchanged (identity/digest parity); K-matrix not re-run for ritual.

## Hostile controls (19, all rejected)

post-hoc cell · `λ` changed on a "same-λ" row · faked split by resealing a predicate · BO-2 reopened · `n = 4` added · `LAMBDA_SUFFICIENT` claimed · Morales-Ruiz upgraded · `ℓ` conflated with `n` · provider identity drift · provider input script mutated (d7) with log/results unchanged · `SOURCE_SIGNATURE` changed on a cell · Morales-Ramis applied · (R1) `pooled_cell_count` 17 / 19, `distinct_lambda_count` 4 / 5 / 7, `distinct_lambdas` omitting `3/8` or lexically misordered/duplicated — each a summary-only edit with the pooled rows unchanged · a universal "μ only for half-integer ℓ" claim. The validator recomputes the pooled cardinalities from the pooled rows and compares both summary surfaces, and also replays the preregistration (bound to its commit blob), regenerates the provider script, rebuilds every cell from the digest-bound log and recomputes the adjudication.

## Limitations

The FALSE cells rest on the qualified provider's completeness (case 1 independently excluded, cases 2–3 not). d7's TRUE is by R2L (two exponential solutions with algebraic log-derivative verified exactly), consistent with but not using the bound finite-`K₄` statement. Everything is a statement about the frozen `n = 3` member.

## Reproduce

```bash
python -m msk_formal_discovery.topological_galois.bridge_01b_finalize --check
python -m pytest tests/test_hamiltonian_variational_bridge_01b.py
```
