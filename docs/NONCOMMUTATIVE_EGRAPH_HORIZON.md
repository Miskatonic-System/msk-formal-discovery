# Noncommutative E-Graph Research Horizon

**Status:** `PROPOSED_RESEARCH_HORIZON`

**Authority:** `NONE`

**Primary owner:** `Miskatonic-System/msk-formal-discovery`

**Potential representation provider:** `Miskatonic-System/msk-rcir`

This document preserves a future research lane. It does not modify the current formal-discovery experiment, its preregistration, its claim ceiling, or any accepted abstraction result.

## Why this belongs here

Equality saturation, rewrite-space exploration, representation sensitivity, extraction cost models, and stabilizer/equivariance experiments are search questions. They belong in Formal Discovery rather than in RCIR's canonical semantic storage or MSK ISA's machine-facing lowering layer.

A future data-oriented RCIR execution representation may provide an efficient ordered term DAG or packed word projection, but that projection does not grant rewrite authority.

```text
RCIR canonical term
      |
      | deterministic projection
      v
ordered term DAG / packed word view
      |
      v
noncommutative e-graph experiment
      |
      +--> rewrite exploration
      +--> group/groupoid action orbit
      +--> extraction cost model
      +--> representation-sensitivity measurement
      |
      v
candidate only
      |
      v
native checker / proof-engineering validation when applicable
```

## Permanent firewalls

```text
EGRAPH_EQUIVALENCE != GLOBAL_CONFLUENCE_PROVEN
EQUALITY_SATURATION != DIAMOND_LEMMA_COMPLETION
REWRITE_REACHABILITY != THEOREM_PROVEN
LOW_EXTRACTION_COST != SEMANTIC_OPTIMALITY
SMALL_ECLASS != MATHEMATICAL_CANONICAL_FORM
```

Equality saturation should be treated as a way to retain and search many represented equivalent forms without committing prematurely to a single rewrite orientation.

Confluence, termination, completion, noncommutative Groebner bases, or Diamond-Lemma results require their own independent evidence.

## Noncommutative representation rule

Order is semantic unless explicitly quotiented by an earned law.

A packed word or flattened associative representation may normalize parenthesization while preserving symbol order.

```text
ASSOCIATIVE_PACKING != COMMUTATIVE_QUOTIENT
```

For example, an ordered word representation may identify the storage structure for `(a*b)*c` and `a*(b*c)` if associativity is explicitly in scope, while still preserving:

```text
[a,b,c] != [b,a,c]
```

unless a separate rule establishes the commutative relation.

This horizon should therefore align with the existing representation-orbit and G/groupoid-action roadmap rather than silently broadening it.

## Candidate data-oriented representation

A research implementation may use dense handles and packed arrays rather than pointer-rich symbolic nodes.

Illustrative shape:

```rust
#[repr(transparent)]
struct EClassId(u32);

#[repr(transparent)]
struct ENodeId(u32);

struct ENode {
    op: OpId,
    child_start: u32,
    child_len: u16,
}

struct PackedEGraph {
    nodes: Vec<ENode>,
    children: Vec<EClassId>,
    classes: Vec<EClassMeta>,
    union_parent: Vec<EClassId>,
}
```

This is an implementation hypothesis, not a frozen schema.

The point of a data-oriented experiment is to measure whether dense IDs and contiguous storage reduce allocation, pointer chasing, memory footprint, or rewrite traversal cost under a fixed semantic workload.

## Suggested experimental sequence

### Stage A: representation-only benchmark

Compare a pointer/tree baseline with a packed ordered-term representation while holding rewrite semantics fixed.

Measure:

- allocations;
- bytes per represented term;
- peak RSS;
- term traversal throughput;
- hashcons/intern throughput;
- deterministic replay parity.

### Stage B: bounded equality saturation

Add a small preregistered noncommutative rewrite system with positive and negative controls.

Freeze:

- rewrite rules;
- orientation metadata;
- search budget;
- extraction cost function;
- input term corpus;
- representation variant;
- random seeds if any.

Measure:

- e-nodes/e-classes created;
- rebuild/union counts;
- saturation status;
- budget exhaustion;
- extraction cost;
- wall-clock and memory;
- representation sensitivity.

### Stage C: orbit/stabilizer integration

Only after Stages A/B close, combine equality saturation with explicit group/groupoid action experiments.

Questions may include:

- which representation transforms preserve abstraction benefit;
- whether orbit-aware indexing reduces redundant search;
- whether known stabilizers reduce e-graph growth;
- whether noncommutative mirror/order transforms remain outside the supported stabilizer.

No positive result may be generalized beyond the tested action family.

## Confluence/completion lane stays separate

If the research goal changes from equality-space exploration to deterministic normal-form computation, create a separate experiment around explicit completion machinery such as:

- critical-pair analysis;
- Diamond-Lemma conditions;
- noncommutative Groebner-style bases;
- termination/order proofs or bounded evidence;
- rewrite-normal-form parity.

Do not use e-graph saturation as evidence that these properties hold.

## RCIR boundary

Formal Discovery may consume an RCIR projection only if the projection contract is deterministic and versioned.

The research layer must not depend on execution-local `NodeId` values as durable identities. Stable experimental identity should remain content-derived.

```text
RCIR_NODE_ID != FORMAL_DISCOVERY_EXPERIMENT_IDENTITY
```

Any RCIR arena implementation remains RCIR-owned; Formal Discovery owns only the experimental projection/consumer and the evidence generated from its search behavior.

## MSK Proof Engineering boundary

If an extracted rewrite, equivalence, or normalization candidate is later translated into a proof-bearing system, `msk-proof-engineering` may provide checker and proof-package custody.

Checker acceptance does not retroactively convert the e-graph search process into proof authority.

## Graduation rule

Do not create a dedicated e-graph repository yet.

Keep the lane internal to Formal Discovery until one of the following is earned:

1. a second independent repository requires the exact same e-graph runtime through a stable API;
2. the e-graph runtime develops a lifecycle independent of Formal Discovery experiments;
3. cross-language/provider requirements make in-repo ownership materially harmful.

Until then:

```text
ONE_RESEARCH_OWNER -> INTERNAL_CAPABILITY
MULTIPLE_INDEPENDENT_CONSUMERS -> REEVALUATE_GRADUATION
```

## Non-goals

This horizon does not authorize:

- changing current formal-discovery adjudications;
- declaring representation invariance;
- adding canonical-library mutation;
- asserting global confluence;
- replacing anti-unification;
- importing RCIR semantic authority;
- modifying FTT domain compiler authority;
- creating a shared repository before independent reuse exists.
