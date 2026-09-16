# Finite-Reduction and Descent Evidence Provider Boundary

**Status:** `FUTURE_RESEARCH_ONLY`  
**Authority:** `NONE`  
**Scientific execution:** `NONE`

## 1. Purpose

Preserve a future evidence/custody seam for local-to-global constructions in which hard local analysis or geometry is reduced to bounded local data, explicit obstructions, overlap/boundary compatibility, and separately qualified gluing or descent authority.

`msk-formal-discovery` may normalize and custody such records. It does not become the proving authority merely by storing them.

ONTO remains the comparative observer of recurrence across independently qualified records.

## 2. Evidence Families

Suggested future record types:

```text
LOCAL_REDUCTION_CERTIFICATE
OBSTRUCTION_OBJECT_RECORD
LOCAL_COMPACTNESS_CERTIFICATE
LOCAL_REGULARITY_CERTIFICATE
ORIENTATION_CERTIFICATE
OVERLAP_COMPATIBILITY_RECORD
BOUNDARY_STRATUM_RECORD
GLUING_WITNESS
DESCENT_WITNESS
GLOBAL_COMPARISON_WITNESS
OUTPUT_SEMANTICS_RECORD
VIRTUAL_OBJECT_CERTIFICATE
```

These labels are provider/custody types, not theorem claims.

## 3. Local-Reduction Envelope

A future `LOCAL_REDUCTION_CERTIFICATE` should retain at minimum:

```text
record_id
record_version
provider_id
provider_version
source_problem_id
local_model_id
local_domain_digest
operator_or_equation_id
finite_reduction_id
local_dimension
index_status
kernel_status
cokernel_or_obstruction_status
compactness_status
regularity_status
orientation_status
assumptions_digest
authority_class
theorem_or_certificate_ref
output_digest
failure_state
provenance_receipt
```

Unknown fields must stay unknown.

Permanent:

```text
LOCAL_REDUCTION_CERTIFIED
!=
GLOBAL_TRANSVERSALITY_CERTIFIED
```

## 4. Obstruction Custody

Obstruction data must be recorded explicitly rather than collapsed into a generic failure flag.

Suggested fields:

```text
obstruction_object_id
obstruction_kind
rank_or_dimension
kernel_cokernel_relation
locality_scope
transport_status
overlap_status
gluing_status
retained_or_eliminated_status
authority_ref
```

Permanent firewalls:

```text
OBSTRUCTION_DATA_PRESENT
!=
OBSTRUCTION_RESOLVED
```

```text
OBSTRUCTION_SPACE_FINITE_DIMENSIONAL
!=
GLOBAL_VIRTUAL_CLASS_EXISTS
```

## 5. Overlap / Boundary Compatibility

An overlap record should preserve:

```text
left_local_object
right_local_object
overlap_object
restriction_or_corestriction_maps
compatibility_condition
compatibility_status
higher_coherence_required
higher_coherence_status
boundary_stratum_ref
compactification_ref
assumptions
source_authority
```

Pairwise compatibility may not be silently upgraded into higher coherence.

```text
PAIRWISE_COMPATIBILITY
!=
DESCENT
```

## 6. Gluing Witness

A future `GLUING_WITNESS` should retain:

```text
gluing_provider
gluing_theorem_ref
input_local_objects
input_obstruction_objects
input_overlap_data
boundary_or_neck_parameters
orientation_compatibility
glued_output_id
scope
assumptions
authority_class
failure_state
```

Formal Discovery may validate record integrity and replayable certificates where available. It must not infer a gluing theorem from local data alone.

## 7. Descent Witness

A future `DESCENT_WITNESS` should preserve:

```text
ambient_object_id
cover_or_sectorization_id
local_object_refs
intersection_object_refs
restriction_corestriction_refs
higher_coherence_refs
assembly_operator
homotopy_colimit_or_pushout_ref
independent_global_object_ref
comparison_map_ref
equivalence_criterion
disposition
authority_class
```

Canonical dispositions may include:

```text
DESCENT_UNTESTED
DESCENT_COVER_VALID
DESCENT_DATA_INCOMPLETE
DESCENT_COMPARISON_NOT_EQUIVALENT
DESCENT_COMPARISON_EQUIVALENT
DESCENT_NOT_APPLICABLE
```

Permanent:

```text
LOCAL_OBJECTS_PRESENT
!=
DESCENT_DATA_COMPLETE
```

## 8. Weakest-Sufficient-Structure Metadata

Each provider record should state the strongest structure actually required by the source theorem or certificate and separately record stronger structure that happens to be available.

Suggested fields:

```text
required_structure_level
available_structure_level
minimality_authority
stronger_structure_unused
```

Permanent:

```text
AVAILABLE_SMOOTH_STRUCTURE
!=
SMOOTH_STRUCTURE_REQUIRED
```

and:

```text
STRONGER_CERTIFICATE
!=
STRONGER_CLAIM_NECESSARY
```

This prevents evidence packages from overclaiming merely because a provider emitted richer data than the downstream theorem consumes.

## 9. Output Semantics

Every global-output record must include an exact output type.

Suggested vocabulary:

```text
ACTUAL_GEOMETRIC_OBJECT
ANALYTIC_SUBVARIETY
ALGEBRAIC_CYCLE
VIRTUAL_FUNDAMENTAL_CLASS
VIRTUAL_FUNDAMENTAL_CHAIN
K_THEORY_CLASS
HOMOLOGY_CLASS
COHOMOLOGY_CLASS
CATEGORY_OR_HIGHER_CATEGORY
SHEAF_OR_COSHEAF_OBJECT
NUMERICAL_INVARIANT
COMBINATORIAL_INVARIANT
OTHER_TYPED_OUTPUT
```

Permanent firewalls:

```text
VIRTUAL_FUNDAMENTAL_CLASS
!=
ALGEBRAIC_CYCLE
```

```text
VIRTUAL_STRUCTURE_SHEAF
!=
VIRTUAL_FUNDAMENTAL_CLASS
```

```text
K_THEORY_CLASS
!=
CHOW_CLASS_WITHOUT_QUALIFIED_TRANSFORMATION
```

```text
CATEGORY_EQUIVALENCE
!=
GEOMETRIC_OBJECT_IDENTITY
```

Provider adapters must reject output-type promotion without an explicit qualified map or theorem.

## 10. Provenance / Rigidity Separation

These records may be consumed by the existing Algebraicity Provenance and Rigidity Signature programs, but the axes remain independent.

A record may legitimately encode:

```text
C1_ANALYTIC_INPUT
    -> C2_ANALYTICALLY_PRODUCED_RIGID_OBJECT
    -> VIRTUAL_FUNDAMENTAL_CLASS
```

without any algebraic-cycle authority.

Permanent:

```text
GENUINE_EXTRACTION
!=
ALGEBRAIC_OUTPUT_REQUIRED
```

and:

```text
CLEAN_PROVENANCE
!=
OUTPUT_TYPE_PROMOTION
```

## 11. Derived / Non-Derived Custody

Derived structure is a possible representation, not a mandatory authority source.

Suggested fields:

```text
derived_representation_present
derived_model_id
shifted_structure_status
perfectness_or_quasi_smoothness_status
orientation_status
virtual_class_authority_ref
nonderived_construction_ref
```

Permanent:

```text
DERIVED_REPRESENTATION_PRESENT
!=
VIRTUAL_CLASS_CERTIFIED
```

```text
NONDERIVED_CONSTRUCTION
!=
LOWER_AUTHORITY_BY_DEFAULT
```

## 12. Theorem-Scoped Positive Controls

Future provider qualification may use source-bound controls for:

- implicit-atlas virtual fundamental cycles;
- contact-homology virtual cycle packages;
- covariantly functorial wrapped Floer theory on Liouville sectors;
- sectorial descent for wrapped Fukaya categories;
- microlocal Morse equivalences under their exact hypotheses;
- simpler finite-dimensional descent/gluing examples with independently known ground truth.

The source theorem's exact domain, coefficient scope, compactness assumptions, orientation assumptions, and output semantics must be retained.

No theorem may be generalized by record-label similarity.

## 13. Negative Controls

Future validators should fail closed on at least:

```text
local reductions relabeled global transversality
obstruction record relabeled obstruction resolution
pairwise overlap relabeled full descent
missing higher coherence relabeled equivalence
gluing narrative without theorem/provider authority
virtual class relabeled algebraic cycle
K-theory output relabeled Chow cycle without map
derived enhancement relabeled VFC
strong local structure relabeled necessary structure
provider package relabeled theorem proved by Formal Discovery
```

## 14. Provider-to-ONTO Contract

ONTO should consume only sealed records containing:

```text
provider
scope
authority
assumptions
source digest
local reduction digest
obstruction digest
overlap/gluing/descent digest
output semantics
failure state
comparison maps
```

ONTO may compare recurrence across records but may not strengthen authority.

```text
ONTO_RECURRENCE
!=
UPSTREAM_PROOF_UPGRADE
```

## 15. Future Qualification Ladder

```text
FRP0  schema and authority vocabulary
FRP1  finite-dimensional local-reduction fixtures
FRP2  obstruction-retention fixtures
FRP3  overlap and failed-gluing negatives
FRP4  known descent positive controls
FRP5  output-semantics promotion negatives
FRP6  blind custody/replay validation
FRP7  expose sealed records to ONTO
```

No phase is authorized by this document.

## 16. Nonclaims

This document does not establish that:

- every hard analytical problem has a finite reduction;
- every obstruction admits gluing;
- every local cover satisfies descent;
- Formal Discovery proves implicit-atlas, Floer, Fukaya, microlocal, or virtual-cycle theorems;
- virtual outputs are algebraic outputs;
- derived geometry is necessary or sufficient;
- any current experiment or candidate is changed.
