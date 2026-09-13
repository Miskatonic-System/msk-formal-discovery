# G-Action Equivariance and Non-Commutative Formal Discovery Roadmap

**Status:** `FUTURE_RESEARCH_ONLY`
**Authority:** `NONE`
**Current scientific dependency:** `WO-MATH-FORMAL-DISCOVERY-01C` and its custody closure
**Canonical-library mutation:** `PROHIBITED`

## 1. Motivation

The representation-orbit work exposed a more general research question than hard-coded permutation invariance: given an explicit transformation system `G` acting on a representation space `X`, which transformations does a discovered abstraction actually respect?

The primitive object for future work is therefore a governed action contract, not universal permutation symmetry and not universal irrep decomposition.

For an abstraction `F : X -> Y`, the core contract is a witnessed equivariance relation of the form

`F(g · x) ≃ rho(g) · F(x)`

where `g` is a certified transformation, `rho` is an optional induced action on the abstraction space, and `≃` is backed by an explicitly scoped verifier. Exact equality, semantic equivalence, path equality, or categorical coherence must remain distinct authority classes.

## 2. Architecture Layers

Future non-commutative discovery work should separate five responsibilities:

1. **Generative Search**
   - proposes directed transformation trajectories;
   - has zero authority to declare algebraic equality or coherence.

2. **Group / Groupoid Action Layer**
   - owns generators, relations, action composition, orbit membership, and stabilizer queries;
   - treats an explicit `G`-action or presented action as primitive;
   - does not assume semisimplicity or a complete irrep decomposition.

3. **Algebraic Normalization Layer**
   - future planned backend family: `ALGEBRAIC_NORMALIZER`;
   - target capabilities include free-associative-algebra reduction, critical-pair analysis, bounded non-commutative Gröbner completion, joinability checks, and normal-form computation;
   - candidate providers to evaluate include GAP/GBNP and Sage/Singular letterplace-style non-commutative Gröbner machinery;
   - `NORMAL_FORM_UNDER_FROZEN_BASIS != GLOBAL_CONFLUENCE_PROVEN`.

4. **Solver Certification Layer**
   - Z3 remains a fast SAT/UNSAT and counterexample oracle for decidable side conditions;
   - cvc5 is the first parked SMT backend to prioritize for qualification because proof-producing SMT can support durable, independently checkable side-condition evidence;
   - Yices 2 and Bitwuzla remain secondary differential or domain-specific solver candidates rather than the primary non-commutative algebra kernel.

5. **Proof / Coherence Kernel**
   - Lean 4 is the preferred first kernel for governed group actions, representation-theoretic constructions, algebraic invariants, and monoidal/braided coherence;
   - Rocq remains useful as an independent proof-system replication lane once qualified for the required authority surface;
   - Agda/Cubical Agda is reserved as a distinct research lane for path-level, HIT, groupoid, and higher-coherence experiments rather than as a redundant checker.

## 3. Optional Representation-Theory Refinement

Irrep projection, steerable latent spaces, and Clebsch-Gordan decomposition are optional capabilities when the chosen category supports them. They must not be treated as the universal representation contract for arbitrary non-commutative transformation systems.

Future schemas should therefore separate:

- `action_specification`
- `representation_specification`
- `decomposition_capability`
- `decomposition_evidence`

A system may have a valid explicit action while `decomposition_capability = NOT_AVAILABLE` or `NOT_ESTABLISHED`.

## 4. Non-Commutative Rewrite Contract

A future algebraic normalizer should expose governed operations such as:

- `REDUCE_WORD`
- `NORMAL_FORM`
- `ENUMERATE_CRITICAL_PAIRS`
- `CHECK_JOINABILITY`
- `GROEBNER_BASIS_BOUNDED`
- `VERIFY_RELATION_PRESERVATION`

Every result must bind:

- presentation / relation-set digest;
- monomial or word ordering;
- algorithm/provider identity and version;
- resource bounds and termination status;
- input/output normal forms;
- unresolved ambiguities;
- exact authority class.

Undecidable or non-terminating cases must fail closed or return bounded/unknown status rather than being silently promoted.

## 5. Invariant and Obstruction Tracking

Future search guidance may track commutators, lower-central/derived-series position, Casimir values, or analogous invariants. Search loss and formal authority must remain separate:

`CASIMIR_LOSS_MINIMIZED != CASIMIR_INVARIANT_CERTIFIED`

`COMMUTATOR_SMALL != EQUIVARIANCE_PROVEN`

Exact invariant claims require algebraic, solver, or proof-kernel certification appropriate to the claim.

## 6. Stabilizer-Oriented Measurement

The representation-orbit result motivates measuring a scoped stabilizer of an abstraction rather than forcing a binary universal invariance claim:

`Stab_G(F) = { g in G | F ∘ g ≃ rho(g) ∘ F }`

Future experiments should preserve per-generator/per-relation outcomes so that a candidate may earn a bounded symmetry profile even when global invariance is not supported.

The existing 01C scientific outcome remains scoped to its tested orbit and must not be retroactively reinterpreted as a general group-action result.

## 7. Planned Qualification Order

No implementation authority is granted by this roadmap. After 01C custody is canonicalized, a sensible sequence is:

1. Freeze a generic `GActionSpec` / presented-action contract and reproduce the existing representation-orbit experiment through that contract without changing the scientific disposition.
2. Qualify cvc5 as a proof-producing SMT side-condition backend.
3. Prototype `ALGEBRAIC_NORMALIZER` behind a provider-neutral contract using a bounded non-commutative algebra engine.
4. Formalize a small non-commutative action and coherence contract in Lean 4.
5. Test a minimal genuinely non-commutative presentation, such as a small braid/Yang-Baxter relation, before attempting broad Lie-theoretic or neural-irrep machinery.
6. Only then evaluate Cubical Agda/HIT-style computational path semantics as a distinct higher-structure hypothesis.

## 8. Research Firewalls

- `GENERATIVE_PROPOSAL != ALGEBRAIC_EQUALITY`
- `SMT_UNSAT != PROOF_ASSISTANT_THEOREM` unless an independently checked proof artifact bridges the authority boundary.
- `NORMAL_FORM_EQUALITY != UNIVERSAL_CONFLUENCE`.
- `REPRESENTATION_INVARIANCE_WITHIN_ORBIT != UNIVERSAL_EQUIVARIANCE`.
- `IRREP_DECOMPOSITION_AVAILABLE != IRREP_DECOMPOSITION_UNIVERSAL`.
- `QUOTIENTING_ALIAS_EQUIVALENCE != KERNEL_COMPLETE_FORMAL_EQUIVALENCE`.

This document preserves a future research architecture only. It makes no new scientific or mathematical claim.