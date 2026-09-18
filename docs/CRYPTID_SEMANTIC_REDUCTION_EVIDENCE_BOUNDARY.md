# Cryptid Semantic-Reduction Evidence Boundary

**Status:** `FUTURE_RESEARCH_ONLY`  
**Authority:** `NONE`  
**Scientific execution:** `NONE`

## Purpose

Preserve a future provider/custody seam for exact reductions from low-level computational systems to compact mathematical dynamics while keeping the transported target decision predicate separate from representation quality.

The core distinction is:

```text
EXACT_SEMANTIC_REDUCTION
!=
TARGET_DECISION_PROOF
```

## Evidence types

Future records may include:

```text
MACHINE_MACRO_SEMANTIC_REDUCTION_CERTIFICATE
HALTING_PREDICATE_TRANSPORT_WITNESS
MACRO_TRANSITION_CERTIFICATE
MACRO_RECURRENCE_INVARIANT
DECIDER_CERTIFICATE
DECIDER_UNKNOWN_RECORD
PROOF_OBLIGATION_RECORD
AXIOM_SCOPE_RECORD
REPRESENTATION_ACCESSIBILITY_RECORD
DECISION_ACCESSIBILITY_RECORD
```

Record labels do not create theorem authority.

## Semantic-reduction certificate

A `MACHINE_MACRO_SEMANTIC_REDUCTION_CERTIFICATE` should bind at least:

```text
source_machine_digest
source_semantics
configuration_encoding
macro_state_encoding
phi_map
macro_transition
micro_steps_per_macro_step
commuting_relation
domain_of_validity
initial_condition
exception_set
proof_or_certificate_ref
authority_class
failure_state
```

Unknown domains or exceptions must remain explicit.

## Target-predicate transport

A separate `HALTING_PREDICATE_TRANSPORT_WITNESS` should state exactly how the source-machine target is represented in the macro system.

Examples:

```text
machine halts
iff
macro trajectory reaches predicate P
```

or a one-way implication if that is all that has been established.

Permanent:

```text
DYNAMICS_EQUIVALENCE
!=
HALTING_EQUIVALENCE_UNLESS_PREDICATE_TRANSPORT_IS_PROVED
```

## Accessibility separation

This seam composes conceptually with the existing Representation–Information Accessibility program.

Track independently:

```text
MECHANISM_ACCESSIBILITY
DECISION_ACCESSIBILITY
PROOF_ACCESSIBILITY
SIMULATION_ACCESSIBILITY
```

A compact transition law may make mechanism accessibility high while the global decision predicate remains unresolved.

Permanent:

```text
HIGH_MECHANISM_ACCESSIBILITY
!=
HIGH_DECISION_ACCESSIBILITY
```

This is a classical-dynamics analogue of the broader information-versus-extraction distinction already preserved by REGB-RIA.

## Decider authority

For every decider:

```text
HALT
NONHALT
UNKNOWN
```

must remain distinct.

Permanent:

```text
DECIDER_UNKNOWN
!=
NONHALT
```

```text
BOUNDED_SIMULATION_TIMEOUT
!=
NONHALT
```

```text
HEURISTIC_PREDICTION
!=
PROOF_CERTIFICATE
```

## Formal proof systems

Rocq, Lean, or another proof assistant may:

- encode the machine semantics;
- verify semantic reductions;
- check recurrence lemmas;
- verify exhaustive classification certificates;
- validate a discovered proof.

The presence of a proof assistant does not imply the missing invariant or theorem has been discovered.

```text
PROOF_CHECKER_AVAILABLE
!=
PROOF_EXISTS
```

and:

```text
PROOF_SEARCH_AUTOMATION
!=
TARGET_THEOREM_RESOLVED
```

## Positive and negative controls

Future calibration should include:

- trivial halters;
- cyclers and translated cyclers;
- machines decided by established automated deciders;
- BB(5) difficult but externally solved machines;
- formerly unresolved machines whose later resolution is known;
- malformed reductions that match finite traces but fail globally;
- reductions that preserve dynamics but fail to transport the target predicate;
- current Cryptids retained as unsolved, unscored stress cases.

## Axiomatic scope

Formal independence requires its own certificate and theory scope.

Permanent:

```text
OPEN_PROBLEM
!=
INDEPENDENT_STATEMENT
```

```text
BUSY_BEAVER_EVENTUALLY_EXCEEDS_PROOF_SYSTEMS
!=
BB6_INDEPENDENT
```

## Cross-repository contract

- Mathematics owns source/status truth.
- Ruliology owns bounded machine/rule-space experiments and atlas artifacts.
- Formal Discovery owns exact semantic-reduction and proof-evidence custody.
- ONTO compares representation transitions without upgrading proof authority.

## Nonclaims

This boundary does not establish that:

- any BB(6) holdout has been decided;
- Antihydra has been formally reduced here;
- Cryptid macro-dynamics are automatically simple to prove;
- semantic compression predicts formal independence;
- Formal Discovery can infer nonhalting from failure of known deciders.
