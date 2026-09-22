# Topological Galois Bridge Evidence Boundary

**Status:** `FUTURE_RESEARCH_ONLY`  
**Authority:** `NONE`  
**Scientific execution:** `NONE`

## Purpose

Preserve theorem/evidence custody for the degree-ladder map chain connecting polynomial coefficient space, root configurations, braid groups, permutation monodromy, Galois/solvability data, and exact projective representations.

## Bridge classes

Future records may include:

```text
DISCRIMINANT_COMPLEMENT_TO_ROOT_CONFIGURATION_CERTIFICATE
CONFIGURATION_PI1_TO_BRAID_GROUP_CERTIFICATE
BRAID_TO_PERMUTATION_QUOTIENT_CERTIFICATE
MONODROMY_TO_GALOIS_STATEMENT_ALIGNMENT
DERIVED_SERIES_CERTIFICATE
RADICAL_SOLVABILITY_CERTIFICATE
OUTER_AUTOMORPHISM_CERTIFICATE
PROJECTIVE_REPRESENTATION_CERTIFICATE
VALENTINER_A6_FIXTURE_CERTIFICATE
```

## Degree-ladder ground truth

Required controls:

```text
S3 -> A3 -> 1
S4 -> A4 -> V4 -> 1
S5 -> A5 -> A5
S6 -> A6 -> A6
```

and:

```text
generic degree <= 4: solvable by radicals
generic degree >= 5: not solvable by radicals
Out(S6) ~= C2
```

The 4->5 and 5->6 changes are separate target predicates.

## Bridge integrity

Permanent:

```text
BRAID_MONODROMY
!=
GALOIS_GROUP_WITHOUT_STATEMENT_ALIGNMENT
```

```text
OUTER_AUTOMORPHISM_OF_S6
!=
ABEL_RUFFINI_OBSTRUCTION
```

```text
PROJECTIVE_REPRESENTATION
!=
SOLUTION_BY_RADICALS
```

## FTT contract

FTT-NHE may emit exact braid/representation artifacts and replay receipts.

Formal Discovery retains the statement alignment that says what those artifacts certify in the polynomial/Galois problem.

```text
FTT_ARTIFACT_VALID
!=
TOPOLOGICAL_GALOIS_THEOREM_ESTABLISHED
```

## Ruliology contract

Ruliology may emit commutator-witness or degree-ladder graph artifacts.

```text
GRAPH_PATTERN
!=
DERIVED_SERIES_PROOF
```

Formal Discovery may certify exact finite-group calculations where authorized.

## Problem Atlas composition

The intended chain should be represented as ordered map/bridge records rather than one prose equivalence.

A composition receipt should identify:

- exact source map;
- exact target map;
- preserved predicate;
- weakest bridge authority;
- information loss;
- unresolved arrows.

## Nonclaims

No new theorem, arbitrary-n claim, Hamiltonian bridge, or G60 connection is established here.


## Executed qualification: source representation (01A)

`WO-FORMAL-TOPOLOGICAL-GALOIS-SOURCE-REPRESENTATION-01A` qualified the exact
source package for the frozen Hamiltonian bridge candidate CAND-1:

```text
docs/TOPOLOGICAL_GALOIS_SOURCE_REPRESENTATION_01A.md
experiments/topological-galois-source-representation-01a/
```

Minimal package: `B_n -> S_n` and the Artin/Hurwitz action of `B_n` on `F_n`
are `LOAD_BEARING`; the Burau representation is `CONTROL_ONLY`.

Permanent:

```text
B_n != F_n
SOURCE_GROUP_ACTION != TARGET_MONODROMY_REPRESENTATION
GROUP_ACTION != REPRESENTATION_VALUE
```

No theorem, no differential Galois group and no bridge execution are
established there.

## Parallel intake: M23 inverse-Galois / Hurwitz method transfer

A 2026 external inverse-Galois result for `M23` motivates a future method-transfer qualification. This intake is not mathematical authority and does not alter the executed Hamiltonian bridge program.

See:

```text
docs/M23_HURWITZ_AI_METHOD_TRANSFER_00A.md
experiments/m23-hurwitz-ai-method-transfer-00a/
```

Candidate object kinds include:

```text
CONJUGACY_CLASS_TUPLE
NIELSEN_CLASS
BRAID_ORBIT
HURWITZ_SPACE
ARITHMETIC_GALOIS_ACTION
FIELD_OF_MODULI
FIELD_OF_DEFINITION
BELYI_MAP
EXACT_ALGEBRAIC_RECONSTRUCTION
GROUP_ACTION_FIXED_POINT
```

Permanent intake firewalls:

```text
INVERSE_GALOIS != DIFFERENTIAL_GALOIS
BRAID_ACTION != ABSOLUTE_GALOIS_ACTION
BRAID_ORBIT != ARITHMETIC_GALOIS_ORBIT
FIELD_OF_MODULI != FIELD_OF_DEFINITION
NUMERICAL_APPROXIMATION != EXACT_COVER
AI_PROPOSAL != MATHEMATICAL_AUTHORITY
EXCEPTIONAL_FIXED_POINT != CONCEPTUAL_EXPLANATION
```

The intended reusable discovery pattern is to make the group action explicit and search for exceptional stabilizers, fixed points, and unexpectedly small orbits rather than treating "symmetry" as an untyped prose observation.

No M23 theorem or arithmetic-Galois conclusion is imported by this document.

