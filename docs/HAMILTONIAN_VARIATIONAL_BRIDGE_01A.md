# Frozen CAND-1 Variational-Galois Bridge Falsification and Source-Sufficiency Test (01A)

**Work order:** `WO-FORMAL-HAMILTONIAN-VARIATIONAL-BRIDGE-01A`  
**Proposed disposition:** `HAMILTONIAN_VARIATIONAL_BRIDGE_BO2_REFUTED_SOURCE_INSUFFICIENT` — `PROPOSED_BY_EXECUTING_AGENT_PENDING_INDEPENDENT_REVIEW`  
**Canonical start:** Formal Discovery `a85dd51c1ecf9a94e88ff4a742029d1b321a2512` · Mathematics `2337c7d744f176274997374a7d4057c7272f715d` · candidate freeze `889cc252…`  
**Package:** `experiments/hamiltonian-variational-bridge-01a/` · **Code:** `src/msk_formal_discovery/topological_galois/bridge_*.py`

## Result in one paragraph

On the frozen family `n = 3`, `P_3 = q³ − q − 1`, `E = −1` (so `f_{a,E} = 2(E − P_3) = −2q³ + 2q`, roots `{−1, 0, 1}`, `disc = 64`), eight pre-registered rational couplings `(μ, λ)` were classified with every source-side object identical (one `SOURCE_SIGNATURE = a8407db0…`). The target predicate `ABELIAN_IDENTITY_COMPONENT(G_diff)` came out **TRUE** at `(0,0), (1,0), (0,1), (1,1), (0,3)` and **FALSE** at `(0,2), (1,2), (1,−1)`. Same source data, different predicate: **BO-2 is refuted** — the predicate is not a function of the qualified source representation data (`π_perm`, `α`, Hurwitz) alone. This is a mathematical negative bridge result on the frozen family, not an infrastructure failure, and it makes **no** integrability, nonintegrability or chaos claim.

## Gate 0 — canonical ratchet

| Check | Value |
|---|---|
| Formal Discovery main | `a85dd51c` (= origin/main; 01A-R1 `e7bf4026` is an ancestor) |
| Mathematics main | `2337c7d7` (= origin/main) |
| candidate freeze digest | recomputed from blob `e0c5d462…` = `889cc252…` **exact** |
| 01A package replay (`runner --check`) | PASS: `QUALIFIED`, `BURAU_ROLE = CONTROL_ONLY`, LOAD_BEARING = {S1, S2} |
| 01A convention-freeze digest | `6d5897a1…` (bound in `preregistration.v0.1.json#/gate0`) |

## Gate 1 — target evidence source custody

| Source | Status | Consequence |
|---|---|---|
| Morales-Ruiz 1999, *Differential Galois Theory and Non-Integrability of Hamiltonian Systems* (Birkhäuser PM 179) | **UNAVAILABLE** — Springer landing page only, no PDF | **No claim uses `ρ_tgt` as evidence about `G_diff`.** No target monodromy was computed. The Lamé classification is *not* used as authority (it appears only as recorded prior expectation). |
| Kovacic 1986, *J. Symbolic Computation* 2 | **IDENTIFIED_UNBOUND** — sciencedirect HTTP 403 | not the sole support of any step |
| Acosta-Humánez–Morales-Ruiz–Weil 2010 (arXiv:1008.3445v2), **BOUND** via the 00A ledger (blob `4cafe426…`) | decisive | Appendix A: Kovacic's algorithm and its four cases (the provider's decision surface); Prop 6.2/6.3, Prop 3.4: algebraic base change / algebraic gauge preserves the identity component |
| Smith 1984, *A discussion and implementation of Kovacic's algorithm* (Waterloo CS-84-35) | **BOUND**, SHA-256 `57c81203…` | provenance of the provider's implementation ([1] in its header) |
| Birman–Brendle 2005, via the 01A ledger | bound | source-side conventions, consumed through the 01A certificates in `SOURCE_SIGNATURE` |

The Mathematics root registry is untouched; custody is additive and experiment-local.

## Gate 2 — differential-Galois provider qualification

**Provider:** Maxima 5.49.0 `kovacicODE` (`share/contrib/maxima-odesolve/kovacicODE.mac`, © 2014 N. Beishuizen, GPL-2+, after Smith 1984 / Saunders 1981 / Kovacic 1986), from nixpkgs `35e21274…`, store path `/nix/store/7xxinqc8…-maxima-5.49.0`, implementation SHA-256 `ab7f476a…` (observed inside `nix shell` = recorded). Command: `maxima --very-quiet --batch=<script>; load(kovacicODE); kovacicODE(eq, y, x)`. Coefficient field `Q(x)`, exact. Timeout 900 s per script, no retries.

**Output semantics (established, not assumed):** a list `[y = …]` means Liouvillian solutions found (cases 1–3); `nil` means input rejected (`ODE is not linear!`), a Maxima error, or no Liouvillian solution (case 4). The message *"No Liouvillian solutions exist"* is printed inside cases 2/3 runs as well, so **message text is never the verdict**; case 4 is asserted only for a clean `nil` on **both** the original and the reduced form.

**Known limitation:** constant-coefficient inputs are misclassified as non-linear and rejected (K1, K2 direct forms). Every target cell has genuinely `x`-dependent coefficients.

| Id | Control | Expected | Got |
|---|---|---|---|
| K1 | `y'' = 0` direct | INPUT_REJECTED | ✓ |
| K1g | `y'' = 0` in the rational gauge `y = x·u`: `x u'' + 2u' = 0` (same PV extension) | Liouvillian `{1, 1/x}` | ✓ `[y = %k1/x+%k2]` |
| K2 | `y'' − y = 0` direct | INPUT_REJECTED | ✓ |
| K2g | `x u'' + 2u' − x u = 0` (`y = x·u`) | Liouvillian `e^{±x}/x` | ✓ |
| K3a | case 2: `y'' = (1/x − 3/16x²) y` | Liouvillian | ✓ `x^{1/4} e^{±2√x}` |
| K3b | case 3: `y'' = (−3/16x² − 2/9(x−1)² + 3/16x(x−1)) y` | Liouvillian (algebraic) | ✓ |
| K4a | case 4: Airy `y'' = x y` | NO_LIOUVILLIAN | ✓ |
| K4b | case 4 with `y'` term: Bessel 0, `x y'' + y' + x y = 0` | NO_LIOUVILLIAN | ✓ |
| K5 | Legendre 1, `(1−x²)y'' − 2xy' + 2y = 0` | Liouvillian (`y = x`) | ✓ |
| K6 | Bessel ½ | Liouvillian | ✓ |

**Qualified: 10/10.** Script/log digests in `provider-qualification.v0.1.json`.

## Primary experiment — frozen `n = 3` member and pre-registered grid

Frozen and **committed before any Galois computation** (`e22dd8cf`, blob `167ab77e…`):

```text
P_3(q) = q³ − q − 1,  a = (−1, −1, 0, 1),  E = −1
f_{a,E}(q) = 2(E − P_3(q)) = −2q³ + 2q          roots −1, 0, 1 (ordered by real part);  disc f = 64 ≠ 0
phase curve p₁² = f(q₁): nonsingular genus-1 curve
SOURCE_SIGNATURE = sha256(n, a, E, roots, ordering, π_perm cert digest (n=3), Artin cert digest (n=3), Hurwitz cert digest, Hurwitz convention)
                 = a8407db0c67a25fa92c6b70bc90acbb711f869ca37417de31d221d110ee030cc
```

Grid (rational; `(0,0)` transparent control; four distinct nonzero `λ`): `c1 (0,0)`, `c2 (1,0)`, `c3 (0,1)`, `c4 (1,1)`, `c5 (0,2)`, `c6 (1,2)`, `c7 (0,3)`, `c8 (1,−1)`. Prior expectations recorded in the same commit: abelian for c1–c4, c7; nonabelian for c5, c6, c8 (design intent from the Lamé-form correspondence `n(n+1) = 2λ`; **no authority**).

### Exact target equations

For every cell, from the same frozen `f`:

```text
original:  (−2q³ + 2q) y'' + (1 − 3q²) y' + (μ + λq) y = 0
reduced:   z'' = r z,  y = f^{−1/4} z   (algebraic gauge: identity component unchanged, AMW Prop 6.2/3.4)
r = [ (−3 + 8λ) q⁴ + 8μ q³ − (6 + 8λ) q² − 8μ q − 3 ] / [16 q² (q² − 1)²]      (poles −1, 0, 1; order 2 at ∞)
```

| Cell | `(μ, λ)` | numerator of `r` | original digest | reduced digest |
|---|---|---|---|---|
| c1 | (0,0) | `−3q⁴ − 6q² − 3` | `…` | `…` |
| c2 | (1,0) | `−3q⁴ + 8q³ − 6q² − 8q − 3` | | |
| c3 | (0,1) | `5q⁴ − 14q² − 3` | | |
| c4 | (1,1) | `5q⁴ + 8q³ − 14q² − 8q − 3` | | |
| c5 | (0,2) | `13q⁴ − 22q² − 3` | | |
| c6 | (1,2) | `13q⁴ + 8q³ − 22q² − 8q − 3` | | |
| c7 | (0,3) | `21q⁴ − 30q² − 3` | | |
| c8 | (1,−1) | `−11q⁴ + 8q³ + 2q² − 8q − 3` | | |

(Full digests of each original and normalized equation, the provider input script and output log are in `preregistration.v0.1.json` and `cell-results.v0.1.json`.) No floating-point coefficient exists anywhere in the package.

## Target predicate rules

`ABELIAN_IDENTITY_COMPONENT(G_diff) ∈ {TRUE, FALSE, UNRESOLVED}` is assigned only by one of four named rules; the word "Liouvillian" never decides it.

- **R4** — provider returns clean `nil` on **both** forms ⇒ Kovacic case 4 ⇒ `G_diff = SL₂(ℂ)`, `G⁰ = SL₂(ℂ)` **nonabelian** ⇒ FALSE. Independent partial check: sympy's rational-Riccati solver finds no rational solution (case 1 excluded).
- **R2L (conjugate form)** — `ω₁ = y₁'/y₁` is algebraic over `C(x)` and satisfies the Riccati equation `ω' + ω² + aω + b = 0` **exactly** (polynomial reduction modulo `s_i² = b_i` with the square roots as symbols; Gröbner property guaranteed by ordering); a Galois conjugate `ω₂ ≠ ω₁` satisfies it too. Then `y₂ = exp∫ω₂` is a second, independent exponential solution; over `K' = C(x)(ω₁, ω₂)` both lines `C·y_i` are `Gal(L/K')`-stable, so `Gal(L/K')` is diagonal, hence abelian; `G⁰` over `C(x)` equals `Gal(L/K')⁰` because `K'/C(x)` is algebraic (AMW Prop 6.3) ⇒ TRUE. The provider's own second solution is not needed.
- **RU** — `y₁` algebraic over `C(x)`, and `(y₂/y₁)' = ω` algebraic and nonzero (both verified exactly), or, in case-1 form, a rational Riccati solution `v` of the reduced equation with only simple poles and rational residues, so `z₁ = exp∫v = ∏(x−c)^{ρ_c}` and `y₁ = f^{−1/4} z₁` are algebraic. Then every `σ ∈ Gal(L/K')` fixes `y₁` and sends `y₂/y₁ ↦ y₂/y₁ + c`: `Gal(L/K') ⊂ G_a`, abelian ⇒ TRUE.
- **RD** — a direct Picard-Vessiot derivation (used for the `(0,0)` control).

**Why case 1 alone is not enough:** a reducible group sits in the Borel subgroup `{[[a,b],[0,a⁻¹]]}`, which is *non*-abelian; R2L/RU/RD each pin the structure further. This is the "SOLVABLE ⇏ ABELIAN identity component" firewall the work order demands.

## The `(0,0)` control — direct derivation

`f y'' + (f'/2) y' = 0`. `y₁ = 1`; `y₂' = f^{−1/2}` (verified exactly), so `y₂ = ∫ dq/√f`, the elliptic integral of the first kind on `C: p² = f(q)`. Let `K = C(q, √f)`, `[K : C(q)] = 2`. The differential `ω = dq/√f` is holomorphic on the compact genus-1 curve `C`, hence **not exact** in `K` (a primitive would be a pole-free function on `C`, i.e. constant). So `L = K(y₂)` is generated by a primitive of an element of `K` that is not a derivative in `K`: `Gal(L/K) = G_a`, `σ(y₂) = y₂ + c`. Over `C(q)`: `Gal(L/C(q)) = {[[1,c],[0,±1]]}` (the `±` from `√f ↦ ±√f`), identity component `G_a` (AMW Prop 6.2 for the degree-2 base change). **`G⁰ = G_a`, abelian: TRUE**, independent of the provider. The provider returned exactly `y = k₂ ∫ dx/(√(x−1)√x√(x+1)) + 2^{1/4} k₁` (Kovacic case 1), which corroborates but does not decide.

## Cell results

| Cell | `(μ,λ)` | provider (orig / red) | indep. case-1 test | predicate | rule | certificate |
|---|---|---|---|---|---|---|
| c1 | (0,0) | Liouvillian / Liouvillian | rational `v` exists | **TRUE** | RD | direct derivation above |
| c2 | (1,0) | Liouvillian / Liouvillian | none | **TRUE** | R2L | `ω₁ = −√2·√(x−1)√(x+1)/(2√x(x²−1))`, `ω₂ = −ω₁`, both `Riccati = 0` exactly |
| c3 | (0,1) | Liouvillian / Liouvillian | rational `v` exists | **TRUE** | RU | `y₁ = √x` (verified), `(y₂/y₁)' = √x√(x+1)√(x−1)/(x⁴−x²)` |
| c4 | (1,1) | Liouvillian / Liouvillian | none | **TRUE** | R2L | `ω₁ = [√x(x³−2x²−x+2) − √6(x−2)√(x−1)√(x+1)] / [2√x(x−2)(x³−2x²−x+2)]`, conjugate `ω₂` (sign of the `√6…` term) |
| c5 | (0,2) | **nil / nil** | none | **FALSE** | R4 | `G = SL₂(ℂ)` |
| c6 | (1,2) | **nil / nil** | none | **FALSE** | R4 | `G = SL₂(ℂ)` |
| c7 | (0,3) | Liouvillian / Liouvillian | rational `v = (7x²−1)/(4x³−4x)` | **TRUE** | RU (case-1 form) | residues `{0: ¼, −1: ¾, 1: ¾}`, `y₁ = f^{−1/4} x^{1/4}(x−1)^{3/4}(x+1)^{3/4} ∝ √(x²−1)` |
| c8 | (1,−1) | **nil / nil** | none | **FALSE** | R4 | `G = SL₂(ℂ)` |

Every provider-returned solution used as a *candidate* was re-derived or re-verified exactly; every FALSE cell agrees between the original and the reduced form and with the independent case-1 exclusion. All eight outcomes coincide with the pre-registered expectations.

## BO-2 adjudication

All eight cells carry `SOURCE_SIGNATURE = a8407db0…`. Witness pair recorded by the adjudicator: **c1 `(0,0)` TRUE vs c5 `(0,2)` FALSE**. Further pairs with the same `μ`: c2 `(1,0)` TRUE vs c6 `(1,2)` FALSE; c2 vs c8. 

```text
SOURCE_SIGNATURE(c1) == SOURCE_SIGNATURE(c5)     and     G0_ABELIAN(c1) = TRUE  !=  G0_ABELIAN(c5) = FALSE
==>  BO2 = REFUTED   :   SOURCE_DATA_ALONE_INSUFFICIENT_FOR_TARGET_PREDICATE
```

This is the frozen expected-false transport claim of CAND-1 (00A `BO-2`, prior expectation `EXPECTED_FALSE`) — now established for this family rather than anticipated. Nothing on the source side sees `(μ, λ)`; the target predicate does.

**BO-1:** NOT_EXECUTED — no exact target-monodromy tuple was constructed (the Zariski-closure source is unbound and no monodromy computation was attempted), so `STRUCTURAL_EQUIVARIANCE_SUPPORTED` is not earned; the structural action stays qualified from 01A. **BO-3:** UNKNOWN; `n = 4..6` were not run, deliberately.

## Morales-Ramis firewall

For c5, c6, c8 only `TARGET_VARIATIONAL_GALOIS_PREDICATE = NONABELIAN` is recorded. No Hamiltonian integrability or nonintegrability theorem is asserted, Morales-Ramis is not applied, and no chaos statement is made.

```text
NONABELIAN_G0 != CHAOS          NONABELIAN_G0 != AUTHORIZED_NONINTEGRABILITY_CLAIM
LIOUVILLIAN != ABELIAN_G0       NOT_FALSIFIED != SOURCE_DATA_SUFFICIENT
MONODROMY_GROUP != DIFFERENTIAL_GALOIS_GROUP (no monodromy used; closure source unbound)
```

## Hostile controls (16, all rejected by `bridge_validate.validate`)

changing `P_3` / `E` between cells · root reordering without relabel · convention change between cells · coupling added post hoc · selective reporting · float substituted for a rational · Liouvillian relabeled "`G⁰` abelian" without group evidence · no-Liouvillian relabeled chaos · target monodromy relabeled `G_diff` · source data recomputed per cell · Burau promoted · `n=4..6` added · result resealed after changing a predicate · NOT_FALSIFIED promoted to SUFFICIENT · nonabelian `G⁰` converted into a nonintegrability claim. The validator also binds the preregistration to its commit blob (post-hoc grid edits are detected), rebuilds every cell record from the digest-bound provider log, and recomputes the adjudication.

## Positive controls

frozen `SOURCE_SIGNATURE` exact across all cells ✓ · target normalization replays exactly ✓ · provider K-matrix 10/10 ✓ · direct `(0,0)` derivation ✓ · provider outputs independently checked: c1 (direct derivation), c2/c4 (Riccati + conjugate, exact), c3 (exact ODE verification of `√x` and RU), c7 (rational Riccati solution independent of the provider), c5/c6/c8 (sympy case-1 exclusion; case-4 itself rests on the provider's qualification).

## Limitations and claim ceiling

- The **FALSE** verdicts rest on the qualified provider's completeness (Kovacic cases 1–3 exhausted). The independent check excludes case 1 only; cases 2–3 are not independently excluded here. A second exact implementation would strengthen these cells.
- The provider's own *second* solutions in c2/c4/c7 (reduction-of-order integrals) were not re-verified; the rules do not use them.
- Morales-Ruiz 1999 is unavailable; consequently nothing here involves monodromy or Zariski closure, and the Lamé classification carries no authority in this package.
- Statement scope: the frozen family only. Absence of a counterexample would not have established sufficiency; presence of one establishes insufficiency for this family.

## Reproduce

```bash
python -m msk_formal_discovery.topological_galois.bridge_finalize --check     # replays preregistration, rebuilds cells from the saved log, recomputes adjudication, runs 16 hostile fixtures
python -m pytest tests/test_hamiltonian_variational_bridge_01a.py
# re-running the provider (needs nix): see bridge_runner.provider_qualification / run_cells
```
