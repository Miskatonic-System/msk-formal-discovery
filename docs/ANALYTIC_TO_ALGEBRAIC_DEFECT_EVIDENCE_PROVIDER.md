# Analytic-to-Algebraic Defect Evidence Provider Boundary

**Status:** `FUTURE_RESEARCH_ONLY`  
**Authority:** `NONE`  
**Scientific execution:** `NONE`

## 1. Purpose

Preserve a future provider/evidence seam for mathematical artifacts that certify scoped transitions from analytic, variational, gauge-theoretic, Higgs, microlocal, or derived data into rigid geometric outputs.

`msk-formal-discovery` may eventually normalize, custody, and validate evidence records supplied by qualified mathematical/proof backends. It does not become the proving authority merely by storing those records.

ONTO remains the comparative observer of recurrence across independently supplied defect-engine profiles.

## 2. Provider Boundary

Formal Discovery may own future machine-readable custody for records such as:

- line-bundle / Chern-class realization records;
- positive-current certification records;
- calibration records;
- HYM bubbling-cycle records;
- Taubes-style curve records in theorem-scoped settings;
- Higgs spectral-support records;
- holonomic characteristic-cycle records;
- conormal-component records;
- derived-intersection / obstruction-theory records;
- virtual-class records where separately qualified.

It SHALL NOT infer global Hodge-conjecture conclusions from any local record.

## 3. Common Evidence Envelope

A future provider-neutral record should retain at minimum:

```text
record_id
record_version
provider_id
provider_version
engine_family
source_object_digest
ambient_space_digest
input_assumptions
coefficient_scope
dimension_scope
codimension_scope
rigidity_condition
output_object_digest
output_object_type
authority_class
theorem_or_certificate_ref
failure_state
provenance_receipt
```

Optional fields may include:

```text
mass
energy
rank
chern_character
c1
c2
spectral_degree
singular_support_components
conormal_components
virtual_dimension
orientation_ref
compactness_ref
regularity_ref
```

Unknown fields must not silently upgrade evidence authority.

## 4. Evidence Families

Suggested future evidence classes:

```text
LEFSCHETZ_11_REALIZATION
KING_POSITIVE_CURRENT_CERTIFICATE
KAHLER_CALIBRATION_CERTIFICATE
TAUBES_SW_GR_CURVE_CERTIFICATE
HYM_BUBBLING_CYCLE_CERTIFICATE
HIGGS_SPECTRAL_SCHEME_CERTIFICATE
HOLONOMIC_CHARACTERISTIC_CYCLE_CERTIFICATE
CONORMAL_LAGRANGIAN_CERTIFICATE
DERIVED_LAGRANGIAN_INTERSECTION_CERTIFICATE
VIRTUAL_CLASS_CERTIFICATE
LOCALIZED_CHERN_CHARACTER_CERTIFICATE
```

These labels describe evidence types, not universal theorem authority.

## 5. Authority Classes

Suggested authority vocabulary:

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

Each record must preserve the exact scope of the authority.

Permanent firewall:

```text
CERTIFICATE_STORED
!=
THEOREM_PROVED_BY_FORMAL_DISCOVERY
```

## 6. Current / Calibration Evidence

A positive-current record should preserve separately:

```text
closedness_status
rectifiability_status
positivity_status
integrality_status
mass_minimizing_status
calibration_form_ref
calibration_status
complex_tangent_status
analytic_cycle_status
algebraic_cycle_status
```

Never infer:

```text
MASS_MINIMIZING -> CALIBRATED
```

or:

```text
HODGE_CLASS -> POSITIVE_CURRENT
```

without an explicit upstream certificate.

## 7. Gauge-Theoretic Evidence

A gauge-defect record should preserve:

```text
gauge_group
bundle_rank
connection_family_id
PDE_system_id
compactness_theorem_ref
energy_measure_digest
defect_dimension
holomorphicity_authority
integrable_complex_structure_ref
algebraicity_authority
```

Taubes-style evidence must retain its dimensional and symplectic/integrable scope.

HYM bubbling evidence must retain its codimension-2 scope unless a stronger theorem explicitly says otherwise.

Permanent firewalls:

```text
TAUBES_CURVE_CERTIFICATE
!=
ARBITRARY_CODIMENSION_CERTIFICATE
```

```text
HYM_BUBBLING_CERTIFICATE
!=
ARBITRARY_HODGE_CLASS_CERTIFICATE
```

## 8. Higgs / Spectral Evidence

A spectral record should preserve:

```text
higgs_bundle_id
stability_status
chern_class_constraints
harmonic_metric_ref
flat_connection_ref
integrability_status
spectral_sheaf_digest
spectral_support_digest
spectral_support_dimension
finite_over_base_status
nilpotence_status
conical_status
lagrangian_status
```

Do not infer a map from an arbitrary `(p,p)` Hodge class into this record type.

Permanent firewall:

```text
HIGGS_BUNDLE_CERTIFICATE
!=
HODGE_CLASS_ORIGIN_CERTIFICATE
```

## 9. Microlocal Evidence

A characteristic-cycle record should preserve:

```text
D_module_or_sheaf_id
holonomicity_status
singular_support_digest
characteristic_cycle_digest
multiplicity_data
conormal_component_refs
zero_section_intersection_data
index_theorem_scope
```

Do not treat cotangent projection as a generic Chow pushforward.

```text
CHARACTERISTIC_CYCLE
!=
AUTOMATIC_BASE_ALGEBRAIC_CYCLE
```

## 10. Derived Evidence

A derived record should preserve separately:

```text
derived_stack_or_scheme_id
shifted_structure_degree
shifted_symplectic_status
orientation_status
perfect_obstruction_theory_status
virtual_class_status
virtual_dimension
localized_chern_character_status
```

No field may be synthesized merely because a derived enhancement exists.

Permanent firewall:

```text
DERIVED_ENHANCEMENT
!=
VIRTUAL_CLASS_CERTIFICATE
```

## 11. Cotangent-Lift Custody

Where evidence is expressed in `T*X`, retain both base and cotangent identities:

```text
base_space_digest
cotangent_space_digest
support_projection_digest
conormal_or_spectral_type
fiber_dimension_profile
properness_status
projection_authority
```

This prevents accidental claims that fixed Lagrangian dimension upstairs erases codimension information downstairs.

## 12. Hypothesis Records

Strong speculative claims may be stored only as hypotheses, for example:

```text
SPECTRAL_HODGE_HYPOTHESIS
```

with required metadata:

```text
status: UNVERIFIED_HYPOTHESIS
authority: NONE
classical_hodge_implication: UNPROVED
classical_hodge_equivalence: NOT_ESTABLISHED
```

Hypothesis records may not satisfy proof or candidate-promotion gates.

## 13. Provider-to-ONTO Contract

If this seam is ever activated, ONTO should consume only sealed provider records containing:

```text
provider
scope
authority
assumptions
source digest
output digest
comparison map
failure state
```

ONTO may measure recurrence across records but may not strengthen their authority.

```text
ONTO_RECURRENCE
!=
UPSTREAM_PROOF_UPGRADE
```

## 14. Calibration Sequence

A reasonable future provider-qualification sequence is:

```text
P0  Lefschetz-(1,1) fixture custody
P1  positive-current / holomorphic-chain fixtures
P2  codim-2 HYM bubbling fixtures
P3  Higgs spectral-support fixtures
P4  characteristic-cycle / conormal fixtures
P5  derived-intersection fixtures with known virtual data
P6  malformed / authority-mismatch negative controls
P7  only then expose records to ONTO comparative experiments
```

No phase is authorized by this document.

## 15. Negative Controls

Future validators should fail closed on cases such as:

```text
mass minimizer without calibration evidence
pseudoholomorphic curve without integrable/projective algebraicity authority
HYM defect relabeled arbitrary codimension
Higgs spectral support relabeled conormal cycle
nonproper projection relabeled Chow pushforward
shifted symplectic object relabeled virtual cycle
hypothesis relabeled theorem
```

## 16. Relation to Existing Formal Discovery Work

This seam complements:

- `G_ACTION_EQUIVARIANCE_ROADMAP.md`;
- `NONCOMMUTATIVE_EGRAPH_HORIZON.md`;
- existing representation-custody and exact-replay machinery.

Formal Discovery remains responsible for custody and provider-scoped evidence semantics, not for universal mathematical interpretation.

## 17. Nonclaims

This document does not establish that:

- any analytic-to-algebraic defect engine has been implemented here;
- Formal Discovery proves King, Taubes, HYM compactness, Simpson correspondence, Kashiwara theory, or PTVV-style derived results;
- arbitrary Hodge classes are generated by any listed engine;
- a spectral Hodge construction exists for all classes;
- ONTO may infer algebraicity from structural recurrence;
- any current experiment or candidate is changed.
