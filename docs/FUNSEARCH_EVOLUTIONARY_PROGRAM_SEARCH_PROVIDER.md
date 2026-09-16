# FunSearch-Style Evolutionary Program Search Provider Lane

**Status:** `PARKED_EXTERNAL_PROVIDER_LANE`  
**Repository:** `Miskatonic-System/msk-formal-discovery`  
**Authority:** `NONE`  
**Implementation authorization:** `NOT_AUTHORIZED`  
**Primary external reference:** `google-deepmind/funsearch@cc53f274237d7ab05c19df939edbc1f9616a7c19`  
**Conceptual successor reference:** `google-deepmind/alphaevolve_repository_of_problems@8f447457957deac61e28bf1676746f0753b3b2f8`

## 1. Purpose

Register FunSearch-style evolutionary program search as a future proposal-generation provider for `msk-formal-discovery` without collapsing evaluator score, executable success, or evolutionary survival into mathematical truth or scientific authority.

The intended role is narrow:

```text
problem / executable objective
        |
        v
candidate population
        |
        v
LLM proposal / mutation / recombination
        |
        v
sandboxed deterministic evaluation
        |
        v
scored + provenance-bound candidate
        |
        v
diversity-preserving population update
        |
        +--------------------------+
        |                          |
        +--> next proposal cycle <-+
```

FunSearch is treated as an external research method and reference implementation, not as an architectural authority.

## 2. Why the fit is strong

The existing Formal Discovery program already implements a proposal-and-evidence lifecycle around search traces, abstraction mining, held-out replay, candidate qualification, and non-authoritative refactoring proposals.

FunSearch adds a complementary search policy family in which the object under search is executable program text and the feedback signal is an objective evaluator.

The two mechanisms are adjacent but not identical:

```text
CURRENT FORMAL DISCOVERY
search trace -> repeated structure -> abstraction candidate -> held-out replay

FUNSEARCH-STYLE LANE
program population -> LLM mutation -> executable score -> evolutionary selection
```

Both remain candidate generators.

Neither owns theorem authority.

## 3. Upstream FunSearch mechanics retained as reference

The open FunSearch repository exposes a single-threaded reference pipeline built around:

- a `ProgramsDatabase`;
- multiple evolutionary islands;
- score-signature clustering;
- prompt construction from prior programs;
- LLM sampling;
- sandboxed evaluation;
- program registration;
- periodic weaker-island reset/reseeding;
- bias toward shorter programs within equivalent score clusters.

The open implementation deliberately omits the production language model, untrusted-code sandbox, and distributed execution infrastructure.

Therefore:

```text
OPEN_FUNSEARCH_REPOSITORY
!=
TURNKEY_FUNSEARCH_RUNTIME
```

Any Miskatonic reproduction must supply its own governed provider, sandbox, budget, receipt, and provenance surfaces.

## 4. Core provider contract direction

A future provider should expose a bounded interface conceptually equivalent to:

```text
EvolutionaryProgramSearchRequest
  - problem_id
  - specification_digest
  - evaluator_digest
  - initial_program_digest
  - model_provider_ref
  - model_configuration_digest
  - sandbox_profile_ref
  - resource_budget_digest
  - campaign_seed
  - population/island configuration
  - stopping contract

EvolutionaryProgramSearchCandidate
  - candidate_id
  - parent_candidate_ids[]
  - generation
  - island_id
  - source_code_digest
  - source_code_ref
  - proposal_provider_trace
  - evaluator_receipt_ref
  - score_vector
  - reduced_score
  - resource_observation
  - candidate_status

EvolutionaryProgramSearchRunReceipt
  - campaign identity
  - exact execution source SHA
  - upstream provider identity
  - evaluator identity
  - sandbox identity
  - budget declared / observed
  - seed / determinism class
  - candidate lineage root
  - terminal population digest
  - best-candidate refs
  - execution disposition
```

This is a future contract direction only.

No schema is authorized by this document.

## 5. Existing Miskatonic components to reuse rather than duplicate

### 5.1 Model / LLM provider adapter

`Miskatonic-System/msk-engine` already owns a provider-neutral inference fabric with:

- `InferenceProvider` abstractions;
- local and remote model execution classes;
- model/runtime provenance;
- provider/model digests;
- deterministic fallback semantics;
- structured output validation;
- token, latency, memory, and accelerator budgets.

The FunSearch lane should consume a qualified inference-provider contract rather than embed vendor-specific LLM API logic into Formal Discovery.

```text
FUNSEARCH_PROVIDER_LANE != NEW_LLM_RUNTIME
```

A future adapter may use local or remote providers, but provider choice does not change search-result authority.

### 5.2 Sandboxed execution

Miskatonic already contains multiple containment precedents:

- `miskatonic-systems` disposable sandbox execution permits / receipts;
- `miskatonic-agent-os` governed scientific workload admission and resource-constrained execution envelopes;
- project-local hardened sandboxes such as SSX multi-file workspace isolation.

These are capability references and design precedents, not an assertion that any existing sandbox is already qualified for arbitrary generated Python.

A FunSearch execution sandbox must be independently qualified for generated-code execution before use.

Minimum expected properties include:

```text
HOST_FILESYSTEM_ESCAPE = DENIED
AMBIENT_CREDENTIAL_ACCESS = DENIED
NETWORK_ACCESS = DENIED_BY_DEFAULT
PROCESS_SPAWN = DENIED_OR_EXPLICITLY_BOUNDED
CPU_BUDGET = FINITE
MEMORY_BUDGET = FINITE
WALLCLOCK_BUDGET = FINITE
OUTPUT_BYTES = BOUNDED
CLEANUP = VERIFIED
PRODUCTION_EFFECT = FALSE
```

### 5.3 Execution receipts

Formal Discovery already has native evidence surfaces including:

- `BackendExecutionReceipt`;
- `SearchExecutionReceipt`;
- `ReplayRunReceipt`;
- `AdmissibilityReceipt`;
- exact source / runtime / output digests.

The evolutionary lane should extend or compose these concepts rather than create an incompatible parallel receipt universe.

### 5.4 Resource budgets

The organization already has reusable budget semantics in multiple layers:

- Formal Discovery search budget digests;
- `msk-engine` inference budgets;
- Agent OS cgroup / execution-envelope resource limits;
- organization-wide Empirical Assurance EA-07 / EA-08 declared-versus-observed execution-budget controls;
- `msk-ecology` deterministic finite resource-ledger precedent for bounded evolutionary simulations.

The future FunSearch lane must preregister and observe exact campaign budgets.

A campaign budget may include:

```text
model_calls
sampled_candidates
sandbox_executions
cpu_seconds
wallclock_seconds
memory_mb
accelerator_seconds
tokens_in
tokens_out
candidate_bytes
```

No dynamic budget expansion is allowed merely because a candidate improves.

### 5.5 Deterministic evaluation wrapper

Formal Discovery should own the lane-specific deterministic evaluator wrapper.

A candidate score is meaningful only if the evaluator binds at least:

```text
evaluator_source_digest
objective_definition_digest
input_fixture_digest
input_order
seed_or_rng_contract
sandbox_profile_digest
timeout
resource_caps
score_vector
score_reduction_rule
candidate_source_digest
runtime_identity
```

The evaluation wrapper should emit immutable evidence before the candidate is admitted to the population database.

```text
EVALUATOR_SCORE_WITHOUT_EVALUATOR_IDENTITY = NONAUTHORITATIVE
```

### 5.6 Artifact identity / provenance

`msk-steward` already defines portable artifact passports and content-addressed state identity.

A future evolutionary lane may reuse Steward identity primitives for persisted candidate artifacts, population snapshots, or external source material when useful.

Formal Discovery remains responsible for search semantics; Steward remains responsible for artifact identity/custody mechanics.

### 5.7 Empirical campaign assurance

A real FunSearch reproduction is a `SEARCH_OR_OPTIMIZATION_CAMPAIGN` and should conform to:

```text
STD-MSK-EMPIRICAL-ASSURANCE-01
```

In particular:

- exact source identity;
- immutable preregistration;
- execution-source sealing;
- environment provenance;
- declared and observed budgets;
- partial-execution fail-closed semantics;
- immutable result receipts;
- explicit claim ceiling.

## 6. Required invariants

The provider lane permanently preserves:

```text
LLM_PROPOSAL != ADMISSION
PROGRAM_EXECUTES != PROGRAM_IS_CORRECT
EVALUATOR_PASS != SPECIFICATION_CORRECT
HIGH_SCORE != MATHEMATICAL_TRUTH
HIGH_SCORE != SCIENTIFIC_IMPORTANCE
EVOLUTIONARY_SURVIVAL != VALIDITY
ISLAND_SURVIVAL != CANONICALIZATION
SHORTER_PROGRAM != BETTER_EXPLANATION
SHORTER_PROGRAM != BETTER_MATHEMATICS
DIVERSITY != VALIDITY
CANDIDATE_IMPROVEMENT != GENERALIZATION
TRAINING_OR_PROMPT_CONTAMINATION != INDEPENDENT_DISCOVERY
SANDBOX_SUCCESS != PRODUCTION_SAFETY
SEARCH_RESULT != EXECUTION_AUTHORITY
SEARCH_RESULT != DEPLOYMENT_AUTHORITY
SEARCH_RESULT != CLAIM_PROMOTION
```

The existing Formal Discovery authority ceiling remains `NONE`.

## 7. Diversity upstream, compression downstream

FunSearch's island model suggests a useful organization-level principle:

```text
DISCOVERY
  preserve competing candidates and local basins
        |
        v
REFEREEING / VALIDATION
  apply adversarial survival pressure
        |
        v
DIGESTION / CANONICALIZATION
  compress only after evidence survives
```

This aligns with Mathematical Metabolism.

Premature deduplication or canonicalization during discovery may destroy useful alternative solution families.

Conversely, indefinite population diversity downstream of validation creates unnecessary epistemic redundancy.

## 8. Mathematical Metabolism boundary

FunSearch-style search occupies the discovery/generation side only.

```text
EVOLUTIONARY PROGRAM SEARCH
        |
        v
DISCOVERY ARTIFACT
        |
        v
PROOF / RESULT CLEANUP
        |
        v
REFEREEING / VALIDATION
        |
        v
DIGESTION / CANONICALIZATION
        |
        v
USEFUL SYNTHESIS
        |
        v
EXPOSITION / REUSE
```

The evolved program may itself become the object of digestion.

Potential future questions include:

- What invariant or mathematical idea does the program encode?
- Can the program be simplified without changing the evaluator-observed behavior?
- Does the idea transfer to held-out instances or neighboring problem families?
- Can its structure be converted into a reusable lemma, algorithm, or construction?
- Does independent implementation reproduce the result?

## 9. AlphaEvolve reference posture

AlphaEvolve is tracked as a conceptual successor showing that evolutionary code search can scale beyond one evolved function toward larger programs and scientific/algorithmic optimization tasks.

The public DeepMind problem repository is useful as an external problem/evaluator/reference-result corpus, but it does not contain the AlphaEvolve runtime.

Therefore:

```text
ALPHAEVOLVE_REFERENCE != ALPHAEVOLVE_IMPLEMENTATION_DEPENDENCY
```

Miskatonic's long-horizon scope is broader than code evolution alone.

Machine-originated candidates may include programs, algorithms, formal objects, hypotheses, experiment designs, architectures, models, and governance recommendations under their respective domain authorities.

The broader cross-repository ownership is governed by `miskatonic-systems`, not by this provider lane.

## 10. Proposed future experiment sequence

No experiment is authorized by this document.

When resources permit, preferred sequence:

### FS-00 — Open Reference Custody / Static Reproduction

- pin FunSearch source at the frozen upstream SHA;
- run upstream unit/static tests that do not require missing LLM/sandbox components;
- reproduce known notebook artifacts where deterministic and practical;
- establish source and license custody.

### FS-01 — Bounded Closed-Loop Reproduction

Use one small published objective such as cap-set or admissible-set construction.

Provide:

- one qualified LLM provider;
- one qualified generated-code sandbox;
- frozen evaluator;
- finite campaign budget;
- deterministic campaign seed where applicable;
- exact candidate lineage receipts.

Target is method reproduction, not discovery novelty.

### FS-02 — Matched Search Comparison

Under equal budget and evaluator:

```text
A: independent LLM sampling
B: FunSearch-style evolutionary program search
C: existing Formal Discovery search policy / abstraction-assisted lane where semantically applicable
```

Measure at minimum:

- best objective;
- samples consumed;
- evaluator executions;
- wall-clock;
- candidate diversity;
- program length;
- held-out generalization;
- candidate lineage depth;
- reproducibility.

### FS-03 — Mathematical Metabolism Pilot

Take a high-performing evolved program and produce separate artifacts for:

```text
RAW_EVOLVED_PROGRAM
CLEANED_PROGRAM
REFEREE_REPORT
DIGESTED_CONCEPTUAL_STRUCTURE
HUMAN_EXPOSITION
```

Then test whether cleanup/digestion improves reuse or transfer without falsifying the original performance claim.

## 11. No new repository yet

Do not create `msk-funsearch`, `msk-evolution`, or another generic evolutionary-search repository merely because this lane exists.

A shared implementation repository may be justified later only if at least two independent domain programs demonstrate repeated need for the same load-bearing machinery, for example:

- candidate population storage;
- island scheduling / migration;
- provider-neutral proposal generation;
- evaluator contracts;
- campaign budgeting;
- sandbox adapters;
- population checkpoints;
- candidate lineage / replay;
- shared campaign receipts.

Until that duplication is demonstrated:

```text
FORMAL_DISCOVERY_OWNS_THE_PILOT
SYSTEMS_OWNS_THE_CROSS_DOMAIN_ARCHITECTURE
DOMAIN_REPOS_OWN_DOMAIN_EVALUATORS
```

## 12. Activation boundary

This lane remains parked.

Activation requires a separate Work Order with:

1. frozen upstream source reference;
2. qualified LLM provider;
3. qualified generated-code sandbox;
4. deterministic evaluator contract;
5. exact empirical-assurance profile;
6. finite preregistered resource budget;
7. source/proposal/evaluation provenance;
8. no production or claim authority;
9. explicit positive and negative controls;
10. matched baseline search strategy.

Current disposition:

```text
FUNSEARCH_PROVIDER_LANE = PARKED
FUNSEARCH_LOCAL_REPRODUCTION = NOT_STARTED
ALPHAEVOLVE_RUNTIME = NOT_DEPENDENCY
EXECUTION_AUTHORITY = NONE
CLAIM_AUTHORITY = NONE
CANONICAL_LIBRARY_MUTATION = FALSE
```
