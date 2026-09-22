# Coupling-Conditioned Degree-Ladder Residual Test — BO-3 (01C)

**Work order:** `WO-FORMAL-HAMILTONIAN-VARIATIONAL-BRIDGE-01C`  
**Proposed disposition:** `BO3_DEGREE_CONDITIONED_VARIATION_OBSERVED` (lanes A, C split; lanes B, D partial; all `n = 6` cells unresolved by provider timeout) — R1 applied (degree-ladder authority scope: LOCAL_DERIVED vs IDENTIFIED_UNBOUND; no scientific change) — `PROPOSED_BY_EXECUTING_AGENT_PENDING_INDEPENDENT_REVIEW`  
**Canonical start:** `d4a71a72b36a68fca60dfffb53737846c3cde41d` (01B + R1 merged) · **Preregistration commit:** `24e0408caf2a8cdcaabcab7e5b70384c793e1da1` (before any provider run) · **Package:** `experiments/hamiltonian-variational-bridge-01c/` · **Code:** `bridge_01c.py`, `bridge_01c_finalize.py`

BO-2 (source topology alone → target predicate) is canonically refuted and is **not reopened**. 01B showed that the target coupling pair `(λ, μ)` is the coordinate the source-only bridge omitted. The residual question of this work order is conditional: **once `(λ, μ)` is held exactly fixed, does the controlled background degree `n` still change `ABELIAN_IDENTITY_COMPONENT(G_diff)`?**

## Result in one paragraph

On the controlled centred unit-spacing family (`E = −1`, `n = 3, 4, 5, 6`) with four frozen coupling lanes, the target predicate **changes with the background at fixed `(λ, μ)`**: on lane A (`λ = 1, μ = 0`) and lane C (`λ = 3/8, μ = 0`) the consumed `n = 3` anchors are TRUE while the new `n = 4` and `n = 5` cells are FALSE (Kovacic case 4 on both forms, independent case-1 exclusion consistent) — same coupling signature, different background signature, different predicate. So `COUPLING_PAIR_ALONE_INSUFFICIENT_ACROSS_DEGREE_LADDER` holds for lanes A and C of this family (falsifier F1), which does **not** contradict 01B (a statement about one frozen `n = 3` background). Lanes B (`λ = 2, μ = 0`) and D (`λ = 3/8, μ = ½`) are FALSE at `n = 3, 4, 5`. All eight `n = 6` provider scripts hit the preregistered 1800 s timeout, so every `n = 6` cell is `UNRESOLVED` (no retry, by policy): lanes B and D are `LANE_PARTIAL`, and the `5→6` transition is unresolved on every lane. Across the `4→5` source group-solvability transition (solvable `S_4` → nonsolvable `S_5`, established here by exact finite-group computation) **no** target-predicate change was observed on any lane (F2 on all four); F3 is not adjudicable. No causal statement is made about any transition, no `DEGREE_IRRELEVANT`, no universal sufficiency.

## Gate 0

Formal Discovery main `d4a71a72` (= origin/main, merge of PR #26); Mathematics main `2337c7d7`. Replayed: 01A (`bridge_validate`, 21/21 hostile), 01B (`bridge_01b_finalize --check`, 19/19 hostile), TG-01A qualification result (digest bound in the preregistration). Predecessor identities: `BO2 = CANONICALLY_REFUTED_NOT_REOPENED`; 01B verdict `LAME_PARAMETER_MAP_ESTABLISHED + LAMBDA_ALONE_INSUFFICIENT`; `pooled_cell_count = 18`; `distinct_lambda_count = 6`; `universal_half_integer_only_claim = false` — all checked live by the validator. Provider identity: Maxima 5.49.0, `kovacicODE.mac` SHA-256 `ab7f476a…` observed inside the nix shell before the run — identical to the 01A qualification, **no requalification needed**.

## Phase A — controlled background family (`CONTROLLED_BACKGROUND_FAMILY != UNIVERSAL_DEGREE_MODEL`)

`r_{n,j} = j − (n+1)/2`, `E = −1`, `R_n = ∏(q − r_{n,j})`, `P_n = −1 + R_n`, `f_n = 2(E − P_n) = −2R_n`.

| `n` | roots | `P_n` | `f_n` | `disc f_n` | class |
|---|---|---|---|---|---|
| 3 | `−1, 0, 1` | `q³ − q − 1` | `−2q³ + 2q` | 64 | `CANONICAL_N3_LAME_MEMBER` |
| 4 | `−3/2, −1/2, 1/2, 3/2` | `q⁴ − 5q²/2 − 7/16` | `−2q⁴ + 5q² − 9/8` | 9216 | `ALGEBRAIC_NVE_4` |
| 5 | `−2, −1, 0, 1, 2` | `q⁵ − 5q³ + 4q − 1` | `−2q⁵ + 10q³ − 8q` | 21233664 | `ALGEBRAIC_NVE_5` |
| 6 | `−5/2, …, 5/2` | `q⁶ − 35q⁴/4 + 259q²/16 − 289/64` | `−2q⁶ + 35q⁴/2 − 259q²/8 + 225/32` | 1223059046400 | `ALGEBRAIC_NVE_6` |

Checked for every `n`: `deg P_n = n`, `roots(f_n)` = the frozen positions, simple, `disc ≠ 0`, centre 0, adjacent spacing 1. **PC1:** the generated `n = 3` member equals the canonical 01A/01B member (`P_3 = q³ − q − 1`, `E = −1`, `f = −2q³ + 2q`) and, on all four lanes, `target_equation_n(3, μ, λ)` is dict-identical to the 01A `bx.target_equation(μ, λ)`.

Target equation for every `(n, λ, μ)`: `f_n y'' + (f_n'/2) y' + (μ + λq) y = 0`, normalised with the accepted algebraic gauge `y = f_n^{−1/4} z` into `z'' = r_{n,λ,μ}(q) z` (identity component unchanged; AMW Prop 6.2/6.3, bound). All coefficients exact in `Q(q)`; no floats. `n ≥ 4` equations are `ALGEBRAIC_NVE_n` — never "Lamé" (`N3_LAME_MAP != ALL_DEGREES_ARE_LAME`).

## Phase B — source degree / background signatures

Per `n`: ordered roots, discriminant digest, `B_n` identity, and the TG-01A certificate digests consumed read-only — `π_perm: B_n → S_n` (`s1`, image `n!`), Artin action (`s2`), Hurwitz action (`n3_generic`, `n4_involutions_00A`, `n5_generic`, `n6_generic`; the `n = 4` certificate is on the 00A involution tuple, recorded as such). `BACKGROUND_SIGNATURE_n = digest(n, E, P_n, f_n, roots, certificate digests)`; four distinct values.

Degree-ladder authority matrix (R1, `degree_ladder_authority()`, recomputed by the validator on every canonical surface):

| status | items | basis |
|---|---|---|
| **LOCAL_DERIVED** | `S_n` derived-series orders `[6,3,1]`, `[24,12,4,1]`, `[120,60]`, `[720,360]`; `S_3`, `S_4` solvable = TRUE; `S_5`, `S_6` solvable = FALSE; `A_5`, `A_6` perfect = TRUE | exact finite-group computation (`sympy.combinatorics`) |
| **IDENTIFIED_UNBOUND** | generic-polynomial radical-solvability interpretation; `A_5` simplicity; exceptional outer automorphism of `S_6` | no theorem source bound in any consumed ledger, no local witness — labels only |

`PERFECT` is not promoted to `SIMPLE`; the `S_4 → S_5` **group-solvability transition** is not promoted to a radical-solvability theorem statement; `Out(S_6)` is `IDENTIFIED_UNBOUND`, not witnessed, not load-bearing (`DEGREE_EQUALS_6 != OUT_S6_THEOREM_CERTIFICATE`). The Mathematics candidate freeze's `degree_ladder_firewall` is consumed read-only (blob `e0c5d462…`); the control document it names (`docs/TOPOLOGICAL_GALOIS_DEGREE_LADDER_CONTROL.md`) is `ABSENT_AT_PIN` and nothing was rederived to replace it. The `degree_ladder` labels embedded in the frozen preregistration (`24e0408c`) used the pre-R1 wording ("radical-solvability cliff", "perfect/simple core", "exceptional Out(S_6) layer present", "EXTERNAL_ESTABLISHED"); that document is retained byte-identically for replay, its labels were never load-bearing, and they are superseded by this matrix. No target predicate rests on any of these labels: `DEGREE_SIGNATURE != TARGET_GALOIS_PREDICATE`, `DEGREE_LADDER_ASSOCIATION != CAUSATION_BY_GROUP_THEOREM`.

## Phase C — four frozen coupling lanes and consumed anchors

| lane | `λ` | `μ` | `COUPLING_SIGNATURE` | `n = 3` anchor (consumed) | design |
|---|---|---|---|---|---|
| A | 1 | 0 | `0dbf3111…` | 01A `c3` → **TRUE** | accepted abelian integer-Lamé point |
| B | 2 | 0 | `96dd27cd…` | 01A `c5` → **FALSE** | accepted nonabelian non-half-integer point |
| C | 3/8 | 0 | `c9ac1de7…` | 01B `d7` → **TRUE** | half-integer BHC finite point (`ℓ = ½`, `B = 0`) |
| D | 3/8 | 1/2 | `46ed9706…` | 01B `d8` → **FALSE** | same `λ`, accessory parameter off the finite point |

Anchors carry the canonical record digest and the package log digest; they are never rerun (validator recomputes `consume_anchor` against the canonical packages). One coupling signature per lane, identical on `n = 3, 4, 5, 6` (validator-enforced). `SAME_COUPLING != SAME_TARGET_EQUATION` — `f_n` changes with `n`.

## Phase D — preregistration and provider policy

12 new cells `n{4,5,6}_{A,B,C,D}` preregistered at `24e0408c` with `n, E, P_n, f_n`, roots, background signature, `λ, μ`, exact original and reduced equations, digests, both provider input strings and the authority ceiling. No target-predicate expectations were recorded. One Maxima script per (cell, form) — 24 scripts, each digest-bound to its own log; 1800 s per script, no retries, 6 workers; a timeout is `PROVIDER_TIMEOUT` for that form and the cell is `UNRESOLVED` unless a provider-independent exact rule resolves it. Rules R4 / R2L / RU / RD exactly as in 01A/01B; nothing weakened.

## Panel results (16 cells: 4 consumed anchors + 12 new)

| lane | `(λ, μ)` | `n = 3` (anchor) | `n = 4` | `n = 5` | `n = 6` |
|---|---|---|---|---|---|
| A | (1, 0) | **TRUE** (01A c3, RU) | FALSE (R4) | FALSE (R4) | UNRESOLVED (timeout) |
| B | (2, 0) | **FALSE** (01A c5, R4) | FALSE (R4) | FALSE (R4) | UNRESOLVED (timeout) |
| C | (3/8, 0) | **TRUE** (01B d7, R2L) | FALSE (R4) | FALSE (R4) | UNRESOLVED (timeout) |
| D | (3/8, 1/2) | **FALSE** (01B d8, R4) | FALSE (R4) | FALSE (R4) | UNRESOLVED (timeout) |

Every `n = 4, 5` cell: provider `nil` on both the original and the reduced form with clean logs (no input rejection, no Lisp error), the independent sympy rational-Riccati test excludes case 1 on the reduced form, hence R4 → `G = SL₂(C)`, `G⁰` nonabelian → FALSE. The `n = 4` runs took about a minute per form, the `n = 5` runs a few minutes; every `n = 6` form ran to the 1800 s ceiling and was killed (process group), the sentinel is in the bound log, the verdict is `PROVIDER_TIMEOUT` and the predicate `UNRESOLVED`. The provider-independent RU case-1 path did not resolve any `n = 6` cell either (no rational Riccati solution). Nothing was rerun.

## BO-3 adjudication

| lane | `TARGET_SEQUENCE` | lane result | witness |
|---|---|---|---|
| A | `{3: TRUE, 4: FALSE, 5: FALSE, 6: UNRESOLVED}` | `DEGREE_CONDITIONED_TARGET_VARIATION_OBSERVED` → `COUPLING_PAIR_ALONE_INSUFFICIENT_ACROSS_DEGREE_LADDER` | TRUE at `n = 3` (anchor) vs FALSE at `n = 4` (`n4_A`) |
| B | `{3: FALSE, 4: FALSE, 5: FALSE, 6: UNRESOLVED}` | `LANE_PARTIAL` | — |
| C | `{3: TRUE, 4: FALSE, 5: FALSE, 6: UNRESOLVED}` | `DEGREE_CONDITIONED_TARGET_VARIATION_OBSERVED` → `COUPLING_PAIR_ALONE_INSUFFICIENT_ACROSS_DEGREE_LADDER` | TRUE at `n = 3` (anchor) vs FALSE at `n = 4` (`n4_C`) |
| D | `{3: FALSE, 4: FALSE, 5: FALSE, 6: UNRESOLVED}` | `LANE_PARTIAL` | — |

**Verdict: `BO3_DEGREE_CONDITIONED_VARIATION_OBSERVED`.** The primary question — does a `TARGET_SEQUENCE` contain both TRUE and FALSE while the coupling signature is fixed — is answered YES on lanes A and C. Lanes B and D are not adjudicated as no-effect lanes: with `n = 6` unresolved they are partial, and even a fully resolved constant lane would only earn `NO_DEGREE_EFFECT_OBSERVED_ON_FROZEN_LANE`, never `DEGREE_IRRELEVANT`. `COUPLING_PAIR_UNIVERSALLY_SUFFICIENT` is not emitted (it could never be, from a finite panel).

Reading of the split (evidence-scoped): both split lanes are the two lanes whose `n = 3` anchor was TRUE *for Lamé-specific reasons* on the elliptic member (`ℓ = 1` Lamé–Hermite; `ℓ = ½, B = 0` Brioschi–Halphen–Crawford finite point). On the degree-4 and degree-5 backgrounds the same `(λ, μ)` gives case-4 equations. That is an observation about this family; it is not a theorem that "the Lamé structure is what made `n = 3` abelian", and it is not a statement about any other background family.

## Transition table (`TRANSITION_ALIGNMENT != CAUSAL_TRANSPORT`)

| transition | source-side label | A | B | C | D |
|---|---|---|---|---|---|
| 3→4 | `S_3 → S_4` (both solvable) | CHANGES | NO_CHANGE | CHANGES | NO_CHANGE |
| 4→5 | `S_4 → S_5` GROUP-SOLVABILITY TRANSITION (LOCAL_DERIVED: `S_4` solvable = TRUE, `S_5` solvable = FALSE, `A_5` perfect = TRUE) | NO_CHANGE | NO_CHANGE | NO_CHANGE | NO_CHANGE |
| 5→6 | `S_5 → S_6`; classical `Out(S_6)` exceptional-layer label is IDENTIFIED_UNBOUND in this WO | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED |

Exact statements (as recorded in `result.v0.1.json#/transitions` and `#/cliff_statements`, `causal_attribution = NONE` on every entry):

- **3→4:** "A target-predicate change coincided with the 3→4 transition on lane A (coincidence recorded; no causal attribution)." Same for lane C. No change on lanes B, D. Both `S_3` and `S_4` are solvable, so the only observed changes sit where *no* source solvability layer changes — which is itself a reason not to read the ladder labels causally.
- **4→5 (group-solvability transition):** "No target-predicate change was observed across the 4→5 source group-solvability transition (solvable S_4 to nonsolvable S_5, LOCAL_DERIVED) on lane A." Identically on B, C, D. This is the meaningful negative result F2 on all four lanes: on the frozen lanes the target predicate remains FALSE from `n = 4` to `n = 5` even though the exact source group changes from solvable `S_4` to nonsolvable `S_5`, so that **source-group** solvability transition **does not force** a target-predicate transition on those lanes. This is not a radical-solvability theorem result. *Does not force ≠ has no mathematical relation.*
- **5→6 (`Out(S_6)` label):** "The target predicate is unresolved across the 5→6 transition carrying the IDENTIFIED_UNBOUND `Out(S_6)` label" on every lane. F3 is **not adjudicable**. Nothing is said about `Out(S_6)`; the boolean `n == 6` is not evidence for the theorem.

Forbidden and not said: "the `S_5` solvability transition caused the target Galois change" (there was no 4→5 change to attribute); "the 3→4 change was caused by …"; "`Out(S_6)` caused/forces …"; "degree never matters".

## Falsifiers

| falsifier | A | B | C | D |
|---|---|---|---|---|
| F1 coupling-pair sufficiency | `FULL_COUPLING_PAIR_ALONE_INSUFFICIENT_ACROSS_BACKGROUND` | not adjudicable (unresolved `n = 6`) | `FULL_COUPLING_PAIR_ALONE_INSUFFICIENT_ACROSS_BACKGROUND` | not adjudicable |
| F2 source group-solvability-transition determinism (4→5) | `S4_TO_S5_GROUP_SOLVABILITY_TRANSITION_DOES_NOT_FORCE_TARGET_PREDICATE_CHANGE` | same | same | same |
| F3 `S_6`-exception determinism (5→6) | not adjudicable | not adjudicable | not adjudicable | not adjudicable |

F1 on lanes A/C does not contradict 01B: 01B established that `ORIGINAL + (λ, μ)` separated the 18 sampled cells on **one** frozen `n = 3` background; 01C shows that across backgrounds the pair is not enough.

## Firewalls

BO-2 `CANONICALLY_REFUTED_NOT_REOPENED`; BO-1 `NOT_EXECUTED` (no target-monodromy tuple needed; the unavailable Morales-Ruiz custody does not block BO-3); Morales-Ramis `NOT_APPLIED` — a nonabelian `G⁰` is recorded as `TARGET_VARIATIONAL_GALOIS_PREDICATE = NONABELIAN` and nothing more; no integrability, nonintegrability or chaos claim; FTT `NOT_REQUIRED`; Burau `CONTROL_ONLY`; Lamé `N3_ONLY`.

## Hostile controls (28, all rejected by `bridge_01c_finalize.validate`)

C01 coupling changed inside a lane · C02 root spacing changed · C03 `E` changed for one degree · C04 anchor recomputed instead of consumed · C05 provider drift · C06 provider script differs from the preregistered equation · C07 background signature resealed after the result · C08 predicate coerced · C09 4→5 change attributed to `S_5` nonsolvability · C10 no-change promoted to `DEGREE_IRRELEVANT` · C11 5→6 attributed to `Out(S_6)` · C12 `n = 5` relabelled Lamé · C13 BO-2 reopened · C14 Morales-Ramis applied · C15 lane added post hoc · C16 one degree dropped from a lane · C17 `COUPLING_PAIR_UNIVERSALLY_SUFFICIENT` · C18 source-theorem label substituted for the target computation · C19 anchor resealed in the adjudication · C20 causal transition statement · C21 Lamé authority extended to `n ≥ 4` · C22 provider log swapped between cells · **R1:** C23 canonical result says "radical-solvability cliff" with no bound theorem · C24 "A_5 simple" on local perfectness only · C25 `Out(S_6)` promoted to BOUND/WITNESSED/LOCAL_DERIVED · C26 F2 renamed back to the solvability-cliff claim · C27 authority matrix deleted · C28 preregistration-time `EXTERNAL_ESTABLISHED` copied onto the ledger.

## Positive controls

PC1 generated `n = 3` member identical to canonical (member and all four lane equations) · PC2 every `f_n` has `n` simple rational roots at the frozen positions · PC3 one exact coupling signature per lane across `n = 3..6` · PC4 anchors reproduce the accepted 01A/01B predicates without rerunning · PC5 provider identity exact · PC6 original/reduced normalisation exact on every new cell (same gauge code path as 01A, dict-identical at `n = 3`) · PC7 every reconstructed record equals the digest-bound logs.

## Limitations and claim ceiling

- **`n = 6` is entirely unresolved.** All eight `n = 6` scripts exceeded the preregistered 1800 s ceiling; by policy there were no retries and no reruns. Lanes B and D are therefore partial, and the 5→6 transition / F3 are not adjudicated. A successor would need a preregistered larger budget or a different qualified provider; nothing here says what `n = 6` would give.
- The family is one controlled choice (centred, unit spacing, `E = −1`). `CONTROLLED_BACKGROUND_FAMILY != UNIVERSAL_DEGREE_MODEL`: no statement is made about other root geometries, other energies, or "degree" in general.
- FALSE cells rest on the provider's completeness for Kovacic case 4 (qualified in 01A, K-matrix 10/10) plus an independent case-1 exclusion; TRUE anchors rest on the exact 01A/01B Picard–Vessiot rules. `TARGET_VARIATIONAL_GALOIS_PREDICATE = NONABELIAN` is all that is recorded for FALSE cells — Morales-Ramis not applied, no integrability/chaos claim.
- Degree-ladder authority is split: `S_n` solvability and `A_n` perfectness are LOCAL_DERIVED (exact finite-group computation); the generic radical-solvability interpretation, `A_5` simplicity and `Out(S_6)` are IDENTIFIED_UNBOUND (no source bound, no local witness); the Mathematics degree-ladder control document named in the candidate freeze is ABSENT_AT_PIN. None of these is load-bearing.
- `n = 6` timeouts: no `RESULT` return was emitted before the 1800 s kill on any form; the repeated intermediate Maxima line "No Liouvillian solutions exist" is printed inside the search and is **not** a verdict (`PARTIAL_PROVIDER_PROGRESS != PROVIDER_VERDICT`).
- `n ≥ 4` equations are `ALGEBRAIC_NVE_n`; whether `n = 4` (a genus-1 phase curve) admits a Lamé normal form was **not** derived and is not claimed.
- Claim ceiling: per-lane statements on this family only; `COUPLING_PAIR_ALONE_INSUFFICIENT_ACROSS_DEGREE_LADDER` only on lanes A and C; F2 only on the four lanes as observed; no `DEGREE_IRRELEVANT`, no `COUPLING_PAIR_UNIVERSALLY_SUFFICIENT`, no causal transport from any group-theoretic transition.

## Reproduce

```bash
python -m msk_formal_discovery.topological_galois.bridge_01c_finalize --check
python -m pytest tests/test_hamiltonian_variational_bridge_01c.py
```
