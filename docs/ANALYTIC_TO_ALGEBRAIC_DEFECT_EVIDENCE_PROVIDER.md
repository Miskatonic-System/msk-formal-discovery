# Analytic-to-Algebraic Defect Evidence Provider Boundary

**Revision:** `v0.2`  
**Status:** `FUTURE_RESEARCH_ONLY`  
**Authority:** `NONE`  
**Scientific execution:** `NONE`

## 1. Purpose

Preserve a future provider/evidence seam for mathematical artifacts that certify scoped transitions from analytic, variational, gauge-theoretic, Higgs, microlocal, or derived data into rigid geometric outputs.

`msk-formal-discovery` may eventually normalize, custody, and validate evidence records supplied by qualified mathematical/proof backends. It does not become the proving authority merely by storing those records.

ONTO remains the comparative observer of recurrence across independently supplied defect-engine profiles.

## 2. v0.2 Evidence Model

Do not encode one universal rule of the form:

```text
INTEGRALITY + POSITIVITY + MONOTONICITY -> ALGEBRAICITY
```

Different engines rely on different combinations of discrete charge, positivity/stability, integrability, compactness, finiteness, complex-type certification, and terminal algebraization theorems.

The provider contract SHALL expose those distinctions explicitly.

## 3. Rigidity Signature Custody

A future provider-neutral defect record should support the signature:

```text
R(E) = (Q, P, I, M, F, C, A, T)
```

where:

- `Q` = quantization / integrality / discrete charge;
- `P` = positivity / calibration / stability;
- `I` = integrability / involutivity / closedness;
- `M` = monotonicity / compactness / concentration control;
- `F` = finiteness / constructibility / rectifiability / perfectness;
- `C` = complex-geometric type certification;
- `A` = terminal algebraization / rigidification authority;
- `T` = target-class fidelity.

Every coordinate should carry:

```text
status
provider
assumptions
scope
authority_class
certificate_ref
failure_state
```

Missing coordinates SHALL remain missing/unknown rather than being synthesized as PASS.

## 4. Staged Evidence Envelope

A future record should preserve the stage boundaries:

```text
S0 SOURCE ENCODING
S1 RIGIDITY / INTEGRABILITY
S2 COMPACTNESS / DEFECT EXTRACTION
S3 COMPLEX-TYPE CERTIFICATION
S4 ALGEBRAIZATION / RIGIDIFICATION
S5 TARGET-CLASS FIDELITY
```

Suggested common fields:

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
rigidity_signature
source_encoding_status
rigidity_condition
compactness_ref
defect_object_digest
defect_object_type
complex_type_authority
algebraization_authority
target_class_ref
output_class_ref
class_comparison_ref
target_class_fidelity_status
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
higher_chern_data
spectral_degree
singular_support_components
conormal_components
virtual_dimension
orientation_ref
regularity_ref
monotonicity_ref
multiplicity_data
```

Unknown fields must not silently upgrade authority.

## 5. Evidence Families

Suggested future evidence classes:

```text
LEFSCHETZ_11_REALIZATION
KING_POSITIVE_CURRENT_CERTIFICATE
KAHLER_CALIBRATION_CERTIFICATE
TAUBES_SW_GR_CURVE_CERTIFICATE
HYM_BUBBLING_CYCLE_CERTIFICATE
STATIONARY_YM_MONOTONICITY_CERTIFICATE
HIGHER_CODIMENSION_DEFECT_CERTIFICATE
HIGGS_SPECTRAL_SCHEME_CERTIFICATE
CONSTRUCTIBLE_MICROSUPPORT_CERTIFICATE
HOLONOMIC_CHARACTERISTIC_CYCLE_CERTIFICATE
CONORMAL_LAGRANGIAN_CERTIFICATE
DERIVED_LAGRANGIAN_INTERSECTION_CERTIFICATE
PERFECT_OBSTRUCTION_THEORY_CERTIFICATE
VIRTUAL_CLASS_CERTIFICATE
LOCALIZED_CHERN_CHARACTER_CERTIFICATE
TARGET_CLASS_FIDELITY_CERTIFICATE
```

These labels describe evidence types, not universal theorem authority.

## 6. Authority Classes

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

Every record preserves exact scope.

```text
CERTIFICATE_STORED
!=
THEOREM_PROVED_BY_FORMAL_DISCOVERY
```

## 7. Lefschetz (1,1) Evidence

A codimension-one control record must distinguish:

```text
INTEGRAL_(1,1)_CLASS_REALIZATION
```

from:

```text
POSITIVE_LINE_BUNDLE_EFFECTIVITY
```

Required principle:

```text
LINE_BUNDLE_EXISTS
!=
EFFECTIVE_SECTION_EXISTS
```

A provider record should preserve:

```text
integral_class_ref
hodge_type_authority
line_bundle_ref
c1_comparison_ref
divisor_class_ref
positivity_status
effective_section_status
```

Positivity is optional for the basic `(1,1)` theorem and must not be fabricated as a universal requirement.

## 8. Current / Calibration Evidence

A positive-current record should preserve separately:

```text
closedness_status
rectifiability_status
positivity_status
integrality_status
lelong_or_monotonicity_ref
mass_minimizing_status
calibration_form_ref
calibration_status
complex_tangent_status
analytic_cycle_status
algebraic_cycle_status
target_class_fidelity_status
```

Never infer:

```text
MASS_MINIMIZING -> CALIBRATED
```

or:

```text
SIU_LEVEL_SET_ANALYTICITY -> CURRENT_IS_PURE_CYCLE
```

without the required rectifiability/integer-multiplicity authority.

## 9. Gauge-Theoretic Evidence

A gauge-defect record should preserve:

```text
gauge_group
bundle_rank
connection_family_id
PDE_system_id
energy_functional_id
scaling_exponent
monotonicity_ref
compactness_theorem_ref
energy_measure_digest
defect_dimension
bubbling_cycle_ref
residual_singular_set_ref
holomorphicity_authority
integrable_complex_structure_ref
algebraicity_authority
topological_charge_ref
target_class_fidelity_status
```

### Yang-Mills scaling correction

Provider semantics must preserve:

```text
L2_YANG_MILLS_CONFORMAL_INVARIANCE_DIMENSION = 4
```

without inferring:

```text
DIMENSION_GT_4 -> NO_MONOTONICITY
```

For stationary Yang-Mills, a qualified monotonicity record may bind the scale-corrected quantity schematically:

```text
r^(4-m) * integral_{B_r} |F|^2
```

The natural quadratic-energy defect scale is real codimension four, which in Kähler settings aligns with complex codimension two.

Permanent firewalls:

```text
HYM_BUBBLING_CERTIFICATE
!=
ARBITRARY_CODIMENSION_CERTIFICATE
```

```text
BUBBLING_CYCLE
!=
RESIDUAL_SINGULAR_SET
```

## 10. Higher-Codimension Defect Evidence

A future arbitrary-codimension record may be accepted only if a provider independently certifies the required stages.

Suggested fields:

```text
requested_complex_codimension
topological_charge_degree
variational_system_id
natural_defect_dimension
quantization_status
compactness_status
integer_rectifiability_status
closedness_status
positivity_or_complex_type_status
king_compatibility_status
output_cycle_ref
target_class_ref
target_class_fidelity_status
```

Formal Discovery SHALL NOT require higher-gauge theory specifically.

Permitted future provider families may include higher-order curvature functionals, `p`-Yang-Mills-type theories, Chern-Weil-driven systems, calibrated gauge equations, Donaldson-Thomas-type systems, special-holonomy instantons, or higher-form/higher-gauge systems.

```text
HIGHER_CODIMENSION_RESEARCH
!=
HIGHER_GAUGE_THEORY_REQUIREMENT
```

## 11. Higgs / Spectral Evidence

A spectral record should preserve:

```text
higgs_bundle_id
holomorphic_structure_ref
stability_status
chern_class_constraints
harmonic_metric_ref
flat_connection_ref
nonabelian_hodge_scope
integrability_status
spectral_sheaf_digest
spectral_support_digest
spectral_support_dimension
finite_over_base_status
nilpotence_status
conical_status
lagrangian_status
target_class_fidelity_status
```

Do not infer a map from arbitrary `(p,p)` Hodge classes into this record type.

Preserve the two stages:

```text
FLAT / HARMONIC ANALYTIC DATA -> HOLomorphic HIGGS OBJECT
```

and:

```text
HOLomorphic HIGGS OBJECT -> SPECTRAL SUPPORT
```

```text
HIGGS_BUNDLE_CERTIFICATE
!=
HODGE_CLASS_ORIGIN_CERTIFICATE
```

## 12. Microlocal Evidence

Separate sheaf-side constructibility from `D`-module holonomicity.

A record may preserve:

```text
constructible_sheaf_id
constructibility_status
microsupport_digest
involutivity_authority
D_module_id
holonomicity_status
riemann_hilbert_comparison_ref
characteristic_cycle_digest
multiplicity_data
conormal_component_refs
zero_section_intersection_data
index_theorem_scope
```

Never infer:

```text
FINITE_DIMENSIONAL_STALKS -> HOLONOMIC_D_MODULE
```

and do not treat cotangent projection as a generic Chow pushforward.

## 13. Derived Evidence

A derived record should preserve separately:

```text
derived_stack_or_scheme_id
shifted_structure_degree
shifted_symplectic_status
quasi_smooth_status
perfectness_status
orientation_status
perfect_obstruction_theory_status
virtual_class_status
virtual_dimension
localized_chern_character_status
target_class_fidelity_status
```

No field may be synthesized merely because a derived enhancement exists.

```text
SHIFTED_SYMPLECTIC
!=
VIRTUAL_CLASS_CERTIFICATE
```

```text
VIRTUAL_CLASS_CERTIFICATE
!=
TARGET_CLASS_FIDELITY_CERTIFICATE
```

## 14. Cotangent-Lift Custody

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

Fixed Lagrangian dimension upstairs does not erase codimension information downstairs.

## 15. Target-Class Fidelity Evidence

Every future algebraization record must state whether the produced object represents the requested class.

Required fields:

```text
target_class_ref
output_class_ref
coefficient_scope
comparison_map_ref
class_equality_authority
fidelity_status
```

Suggested statuses:

```text
SUPPORTED
NOT_SUPPORTED
UNKNOWN
INCONCLUSIVE_EVIDENCE_FAILURE
```

Permanent:

```text
ALGEBRAIC_OBJECT_CERTIFICATE
!=
TARGET_CLASS_FIDELITY_CERTIFICATE
```

## 16. Hypothesis Records

Strong speculative claims such as a universal spectral-Higgs origin for rational Hodge classes may be stored only as hypotheses.

Required metadata:

```text
status: UNVERIFIED_HYPOTHESIS
authority: NONE
classical_hodge_equivalence: NOT_ESTABLISHED
```

Hypothesis records may not satisfy proof or candidate-promotion gates.

## 17. Provider-to-ONTO Contract

If this seam is ever activated, ONTO should consume only sealed provider records containing:

```text
provider
scope
authority
assumptions
source digest
rigidity signature
defect/output digest
comparison maps
target-class fidelity
failure state
```

ONTO may measure recurrence across records but may not strengthen their authority.

```text
ONTO_RECURRENCE
!=
UPSTREAM_PROOF_UPGRADE
```

## 18. Calibration Sequence v0.2

A reasonable future provider-qualification sequence is:

```text
P0  Lefschetz-(1,1) fixture custody
P1  positive-current / holomorphic-chain fixtures
P2  codim-2 HYM bubbling fixtures
P3  Higgs spectral-support fixtures
P4  characteristic-cycle / conormal fixtures
P5  derived-intersection fixtures with known virtual data
P6  Rigidity Signature schema/authority calibration
P7  target-class fidelity positive/negative controls
P8  malformed / authority-mismatch negative controls
P9  only then expose records to ONTO comparative experiments
```

No phase is authorized by this document.

## 19. Negative Controls

Future validators should fail closed on cases such as:

```text
universal triad asserted from incomplete engine evidence
mass minimizer without calibration evidence
Siu analytic level sets relabeled pure cycle without rectifiability authority
pseudoholomorphic curve without integrable/projective algebraicity authority
HYM defect relabeled arbitrary codimension
higher-dimensional Yang-Mills relabeled no-monotonicity merely because m>4
higher-codimension proposal relabeled higher-gauge requirement
Higgs spectral support relabeled conormal cycle
constructible sheaf relabeled holonomic D-module without bridge authority
nonproper projection relabeled Chow pushforward
shifted symplectic object relabeled virtual cycle
algebraic defect relabeled requested target class without comparison evidence
hypothesis relabeled theorem
```

## 20. Relation to Existing Formal Discovery Work

This seam complements:

- `G_ACTION_EQUIVARIANCE_ROADMAP.md`;
- `NONCOMMUTATIVE_EGRAPH_HORIZON.md`;
- `MOTIVIC_REALIZATION_EVIDENCE_PROVIDER_BOUNDARY.md` where present;
- existing representation-custody and exact-replay machinery.

Formal Discovery remains responsible for custody and provider-scoped evidence semantics, not universal mathematical interpretation.

## 21. Nonclaims

This document does not establish that:

- one universal rigidity triad exists;
- any analytic-to-algebraic defect engine has been implemented here;
- Formal Discovery proves King, Taubes, HYM compactness, Simpson correspondence, Kashiwara theory, or shifted-derived results;
- arbitrary Hodge classes are generated by any listed engine;
- higher gauge theory is necessary for arbitrary codimension;
- any generated algebraic cycle represents a requested Hodge class without explicit fidelity evidence;
- ONTO may infer algebraicity from structural recurrence;
- EXP-007 is modified or activated;
- any current experiment or candidate is changed.
