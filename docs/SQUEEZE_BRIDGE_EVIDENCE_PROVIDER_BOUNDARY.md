# Squeeze Bridge Evidence Provider Boundary

**Status:** `FUTURE_RESEARCH_ONLY`  
**Authority:** `NONE`  
**Scientific execution:** `NONE`

## Purpose

Register a first-class Map Bridge family for arguments that bound a hard target object between tractable lower and upper comparison objects and transfer only predicates compatible with the declared order relation.

Canonical shape:

```text
LOWER MAP
    <=
TARGET MAP
    <=
UPPER MAP
```

plus an explicit predicate-transfer rule.

The target need not be equivalent to either bound.

## Bridge classes

Future provider records may include:

```text
ORDER_BOUNDED_BRIDGE
STOCHASTIC_DOMINATION_BRIDGE
COUPLING_SANDWICH_CERTIFICATE
COMPARISON_PRINCIPLE_CERTIFICATE
LOWER_BOUND_MAP
UPPER_BOUND_MAP
MONOTONICITY_WITNESS
TYPICAL_SET_CERTIFICATE
EXCEPTION_MASS_BOUND
SQUEEZE_TRANSFER_RECEIPT
```

These labels do not themselves establish the underlying theorem.

## Squeeze Bridge record

A future `SQUEEZE_BRIDGE_RECORD` should retain:

```text
bridge_id
problem_id
lower_map_id
target_map_id
upper_map_id

order_relation
lower_relation_authority
upper_relation_authority

common_space_or_coupling
coupling_authority
success_probability

parameter_alignment
asymptotic_scope
finite_scope

target_predicate
predicate_monotonicity
transfer_direction

lower_predicate_authority
upper_predicate_authority

exception_set
exception_mass_bound
information_loss
counterexamples
source_theorem_ref
failure_state
provenance
```

Unknown fields remain unknown.

## Predicate monotonicity

Monotonicity belongs to the **predicate**, not merely to a named statistic.

Canonical values:

```text
MONOTONE_INCREASING
MONOTONE_DECREASING
NONMONOTONE
UNKNOWN
NOT_APPLICABLE
```

For a lower/target/upper order:

```text
L <= T <= U
```

a monotone-increasing predicate may transfer:

```text
P(L) => P(T)
```

while a monotone-decreasing predicate may transfer:

```text
P(U) => P(T)
```

under the bridge's exact semantics.

Permanent:

```text
ORDER_BOUNDS
!=
UNRESTRICTED_PROPERTY_TRANSFER
```

```text
PARAMETER_MONOTONICITY
!=
PREDICATE_MONOTONICITY
```

## Property-direction receipt

A `SQUEEZE_TRANSFER_RECEIPT` should bind:

```text
target_obligation
predicate
monotonicity
required_bound = LOWER | UPPER | BOTH
source_map
source_claim
bridge_record
transferred_target_claim
authority_ceiling
failure_state
```

A reviewer should be able to identify when one half of a sandwich is sufficient and when neither half applies.

## Probabilistic squeeze

A squeeze may hold only on a high-probability event.

Required fields then include:

```text
probability_space
coupling
sandwich_event
success_probability
asymptotic_limit
exception_event
exception_mass
```

Permanent:

```text
WITH_HIGH_PROBABILITY
!=
FINITE_INSTANCE_CERTAINTY
```

```text
PROBABILISTIC_ORDER_BRIDGE
!=
DETERMINISTIC_ORDER_BRIDGE
```

## Typical-set authority

A theorem may require control only over a sufficiently typical region rather than every possible configuration.

Future records may express:

```text
TYPICAL_SET_CERTIFICATE
+
EXCEPTION_MASS_BOUND
```

Permanent:

```text
HIGH_PROBABILITY_CONTROL
!=
UNIVERSAL_CONTROL
```

and:

```text
UNCONTROLLED_RARE_SET
!=
THEOREM_FAILURE
```

when the theorem's declared authority is probabilistic and the rare-set mass is already within scope.

## Positive control: Kim–Vu sandwich theorem

The Behague–Il'kovič–Montgomery proof of the Kim–Vu sandwich conjecture is the canonical initial theorem-scoped positive control.

It supplies:

```text
G_* subseteq G_d(n) subseteq G^*
```

with high probability in a common coupling, where the outer models are binomial random graphs and the target is a uniformly random regular graph.

The control tests whether the provider can preserve all of the following simultaneously:

- model-type distinction;
- common probability-space authority;
- order direction;
- asymptotic parameter alignment;
- high-probability rather than deterministic authority;
- property monotonicity;
- transfer direction.

## Negative controls

Future validators should reject at least:

```text
sandwich relation relabeled model equivalence
nonmonotone property transferred without extra theorem
monotonicity direction reversed
high-probability coupling relabeled deterministic identity
lower-bound theorem used for a decreasing predicate
upper-bound theorem used for an increasing predicate
exception mass silently discarded
parameter regimes mismatched
```

## Relationship to Problem Atlas Composition

The existing `MAP_BRIDGE_RECORD` remains the generic bridge envelope.

A Squeeze Bridge is a specialized bridge family with:

```text
two ordered comparison maps
+
target map
+
property-transfer semantics
```

It may discharge a target obligation without constructing a full representation equivalence.

## Relationship to ELH

Kim–Vu is a positive control for **what an earned ensemble transfer looks like**.

It does not provide the missing ELH bridge.

Permanent:

```text
KIM_VU_COUPLING
!=
ELH_SINGLE_ORBIT_ARITHMETIC_BRIDGE
```

The ELH ensemble-control lane remains separate until its own target-predicate bridge is qualified.

## Nonclaims

This boundary does not establish that every difficult target admits useful upper/lower maps, every order relation supports theorem transfer, all probabilistic bridges can be certified mechanically, or the Kim–Vu theorem applies outside its random-graph domain.
