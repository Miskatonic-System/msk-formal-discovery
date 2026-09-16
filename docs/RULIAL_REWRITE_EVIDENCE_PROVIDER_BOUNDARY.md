# Rulial Rewrite Evidence Provider Boundary v0.1

**Status:** `FUTURE_RESEARCH_ONLY`  
**Authority:** `NONE`  
**Scientific execution:** `NONE`

## Purpose

Preserve a future theorem/evidence custody seam between `msk-ruliology` and `msk-formal-discovery` for exact rewrite-system properties.

`msk-ruliology` owns bounded rule generation and executable multiway traces. `msk-formal-discovery` may later own or custody independently qualified evidence about rewrite-theoretic properties.

Formal Discovery does not become the generator of rulial atlases merely by providing certificates.

## Evidence families

Suggested future record types:

```text
REWRITE_RULESET_IDENTITY
CRITICAL_PAIR_RECORD
BOUNDED_JOINABILITY_RECORD
LOCAL_CONFLUENCE_CERTIFICATE
GLOBAL_CONFLUENCE_CERTIFICATE
TERMINATION_CERTIFICATE
COMPLETION_CERTIFICATE
REWRITE_EQUIVALENCE_CERTIFICATE
STATE_EQUIVALENCE_CERTIFICATE
EVENT_CAUSAL_COMPARISON_RECORD
```

The last record is intentionally a comparison record, not a classical rewriting theorem.

## Bounded search semantics

A finite search that finds a join may certify only the declared bounded witness.

A finite search that fails to find one may not prove non-joinability in a general system.

Permanent:

```text
BOUNDED_JOIN_FOUND
=>
EXPLICIT_JOIN_WITNESS_WITHIN_BOUND
```

but:

```text
BOUNDED_NO_JOIN_FOUND
!=
NONCONFLUENT_PROOF
```

Required status vocabulary should include at least:

```text
PASS
FAIL
UNKNOWN
NOT_APPLICABLE
```

with `FAIL` reserved for independently sufficient negative authority, not search exhaustion.

## Confluence envelope

A future confluence record should preserve separately:

```text
rule_family_digest
representation
state_equivalence_policy
one_step_peak_definition
local_confluence_status
global_confluence_status
termination_status
critical_pair_scope
joinability_scope
proof_or_certificate_ref
authority_class
assumptions
failure_state
```

Permanent:

```text
ONE_STEP_DIAMOND
!=
LOCAL_CONFLUENCE
```

```text
LOCAL_CONFLUENCE
!=
GLOBAL_CONFLUENCE
```

and Newman's-lemma style promotion requires exact termination/theorem hypotheses.

## Causal-invariance firewall

Wolfram-style event causal invariance is not relabeled classical confluence.

Keep separate:

```text
CLASSICAL_CONFLUENCE_EVIDENCE
EVENT_CAUSAL_INVARIANCE_MEASUREMENT
CAUSAL_GRAPH_ISOMORPHISM_EVIDENCE
```

Formal Discovery may custody a theorem relating these only if a qualified source/proof establishes that relationship under exact semantics.

Permanent:

```text
CONFLUENCE_CERTIFICATE
!=
CAUSAL_INVARIANCE_CERTIFICATE
```

## State-equivalence custody

Multiway semantics depend on when states are considered equivalent.

A future evidence record should bind:

```text
state_equivalence_policy_id
policy_version
canonicalization_function_ref
proof_or_test_authority
collision / false-equivalence tests
```

Permanent:

```text
STATE_EQUIVALENCE_CHANGE
!=
SEMANTICS_PRESERVING_MIGRATION
```

unless separately proved.

## Provider-to-Ruliology contract

A sealed evidence package should contain at minimum:

```text
provider
source digest
rule-family digest
representation
state-equivalence digest
claim type
scope
assumptions
authority
certificate / witness digest
failure state
```

Ruliology may attach such evidence to atlas records but may not strengthen it.

```text
RULIAL_ATLAS_RECURRENCE
!=
REWRITE_THEOREM_PROOF
```

## Exact proof / solver hierarchy

Where applicable retain existing Formal Discovery authority vocabulary, including distinctions among:

```text
SOURCE_PARSED
FORMULA_CHECKED
NUMERICALLY_VERIFIED
SOLVER_CERTIFIED
PROOF_ASSISTANT_VERIFIED
KERNEL_VERIFIED
THEOREM_SCOPED_EXTERNAL_AUTHORITY
UNVERIFIED_HYPOTHESIS
```

A CUDA parity test does not become a confluence proof.

## Formal-system seam

`msk-ftt-nhe` may later provide exact categorical or formal interpretations of selected multiway constructions.

Such interpretations remain optional and provider-scoped.

Permanent:

```text
HIGHER_CATEGORY_MODEL_AVAILABLE
!=
RULIAL_SEMANTICS_REDEFINED
```

## Future qualification ladder

```text
RWP0  rule/state-equivalence custody
RWP1  critical-pair fixtures
RWP2  bounded joinability positive/unknown controls
RWP3  terminating confluence controls
RWP4  nonterminating / undecidable-boundary negatives
RWP5  independent causal-invariance comparison records
RWP6  expose sealed evidence to Ruliology and ONTO
```

No phase is authorized here.

## Nonclaims

This document does not establish that:

- Formal Discovery proves any new confluence theorem;
- every Ruliology rule family is terminating;
- bounded search decides confluence;
- classical confluence equals Wolfram causal invariance;
- rewrite evidence implies physical-law authority;
- any current Formal Discovery experiment is changed.
