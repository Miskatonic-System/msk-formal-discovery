# Map Bridge Evidence Provider Boundary

**Status:** `FUTURE_RESEARCH_ONLY`  
**Authority:** `NONE`  
**Scientific execution:** `NONE`

## Purpose

Preserve a provider/custody seam for explicit bridges among heterogeneous Problem Maps.

The central rule is:

```text
MAP_RELATIONSHIP
!=
QUALIFIED_BRIDGE
```

A bridge becomes composable only when its direction, scope, preserved predicates, information loss, and authority are explicit.

## Bridge evidence classes

Suggested future record types:

```text
EXACT_EQUIVALENCE_CERTIFICATE
BIIMPLICATION_CERTIFICATE
SOUND_REDUCTION_CERTIFICATE
COMPLETE_REDUCTION_CERTIFICATE
SIMULATION_CERTIFICATE
ABSTRACTION_CERTIFICATE
QUOTIENT_CERTIFICATE
CONSERVATIVE_EXTENSION_CERTIFICATE
FUNCTORIAL_TRANSLATION_CERTIFICATE
DESCENT_WITNESS
APPROXIMATE_EMBEDDING_RECORD
EMPIRICAL_CORRESPONDENCE_RECORD
HEURISTIC_ANALOGY_RECORD
TARGET_PREDICATE_TRANSPORT_WITNESS
MAP_COMPOSITION_RECEIPT
```

## Bridge record

A future `MAP_BRIDGE_RECORD` should retain:

```text
bridge_id
source_map_id
target_map_id
source_type
target_type
bridge_class
direction
domain_of_validity
assumptions
preserved_objects
preserved_predicates
lost_information
counterexamples
proof_or_evidence_ref
authority_class
failure_state
provenance
```

Unknown preservation obligations remain unknown.

## Parameter-type gate

Formal Discovery must reject composition when maps share only a numeral or label.

```text
NUMERICAL_EQUALITY
!=
TYPE_COMPATIBILITY
```

A qualified conversion between parameter types requires its own bridge.

## Predicate-transport gate

If a composition claims to resolve target predicate `P`, every bridge on the active path must declare the exact relationship to `P`.

Possible statuses:

```text
PRESERVES_IFF
PRESERVES_FORWARD
PRESERVES_BACKWARD
PRESERVES_WITNESS_ONLY
PRESERVES_COUNTEREXAMPLE_ONLY
DOES_NOT_PRESERVE
UNKNOWN
```

No stronger status may be inferred.

## Information-loss gate

Lossy maps are allowed. They must declare what is forgotten.

```text
LOSSY_MAP
!=
INVALID_MAP
```

But:

```text
LOST_INFORMATION_CONTAINING_TARGET_WITNESS
->
TARGET_CLAIM_NOT_TRANSPORTABLE
```

unless a separate theorem recovers it.

## Composition receipt

For:

```text
M1 --B12--> M2 --B23--> ... --B(k-1,k)--> Mk
```

a `MAP_COMPOSITION_RECEIPT` should bind:

- ordered map IDs;
- ordered bridge IDs;
- common target obligation;
- cumulative assumptions;
- cumulative information loss;
- predicate-preservation chain;
- weakest authority on the path;
- unresolved intermediate obligations;
- final allowable claim.

Permanent:

```text
COMPOSITE_CLAIM
<=
WEAKEST_RELEVANT_BRIDGE
```

## Reviewer protocol support

Formal Discovery may supply evidence for a `PROBLEM_ATLAS_REVIEWER` to evaluate:

```text
TYPE_COMPATIBILITY
SCOPE_COMPATIBILITY
BRIDGE_AUTHORITY
PREDICATE_TRANSPORT
INFORMATION_LOSS
CIRCULARITY
CONCLUSION_LEAKAGE
OVERLAP_CONSISTENCY
CONTRADICTIONS
COVERAGE
CLAIM_CEILING
```

The reviewer itself does not become theorem authority.

## Independence and evidence reuse

Two maps derived from the same source corpus are not automatically independent confirmations.

```text
TWO_MAPS
!=
TWO_INDEPENDENT_EVIDENCE_EVENTS
```

Provider records should retain shared ancestry and source digests.

## Busy Beaver positive control

Busy Beaver provides a natural composition-positive control:

```text
enumeration
+ normalization
+ specialized deciders
+ macro reductions
+ sporadic proofs
+ proof checking
+ exhaustive coverage
```

The whole result depends on coverage and bridge integrity across multiple methods.

## Cryptid bridge control

A machine-to-macro semantic reduction with correct target-predicate transport can be a valid bridge even when the macro problem remains open.

```text
VALID_BRIDGE
!=
TARGET_SOLVED
```

## HEX-666 false-consilience control

A set of mathematically legitimate maps sharing the integer six but lacking typed bridge authority should be classified:

```text
ANALOGY_ONLY
```

or:

```text
NO_QUALIFIED_BRIDGE
```

not as a shared mechanism.

This fixture tests whether bridge validation resists seductive shared metadata.

## Circularity

The provider must reject atlases in which a downstream map is used to justify the upstream assumption that generated it.

```text
CIRCULAR_MAP_GRAPH
!=
INDEPENDENT_COMPOSITION
```

## Nonclaims

This boundary does not establish that every bridge can be formalized, every useful analogy should be rejected, a map-composition receipt proves the source theorems, automated bridge review replaces mathematical judgment, or Formal Discovery owns domain-specific maps.


## Specialized bridge family: Squeeze Bridge

The generic bridge registry now recognizes a theorem-scoped order/sandwich specialization documented in:

```text
docs/SQUEEZE_BRIDGE_EVIDENCE_PROVIDER_BOUNDARY.md
```

Additional admissible bridge/evidence classes include:

```text
ORDER_BOUNDED_BRIDGE
STOCHASTIC_DOMINATION_BRIDGE
COUPLING_SANDWICH_CERTIFICATE
COMPARISON_PRINCIPLE_CERTIFICATE
MONOTONICITY_WITNESS
SQUEEZE_TRANSFER_RECEIPT
```

Permanent:

```text
SQUEEZE_BRIDGE
!=
MODEL_EQUIVALENCE
```

A Squeeze Bridge may discharge a target obligation through order-compatible property transfer without establishing a bidirectional representation map.
