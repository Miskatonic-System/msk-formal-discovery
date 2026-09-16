# ELH / BBP-ORD Dual-Track Provider Seam

**Status:** `PARKED_PROVIDER_SEAM`  
**Authority:** `NONE`  
**Execution:** `NOT_AUTHORIZED`  
**Mathematical owner:** `Miskatonic-System/miskatonic-mathematics`  
**Upstream direction:** `docs/research-directions/ELH_BBP_DUAL_TRACK_RESEARCH_DIRECTION_V0_1.md`  
**Bound ELH-R1 source SHA-256:** `d97b4355a8db6d9199cdc2f8fbe18a9457f1af81f4f4bfcfbf72dd0671476334`

## Purpose

Register Formal Discovery's future execution/search role for two distinct research tracks sharing a BBP/radix substrate:

```text
TRACK A  ELH-pi
         pi-specific single-orbit normality program

TRACK B  BBP-ORD
         generic BBP Orbit and Radix Dynamics program
```

Formal Discovery does not own either theorem claim. It may provide exact/certified execution surfaces, search transformations, discrepancy measurements, candidate arithmetic abstractions, and non-authoritative lemma/proof proposals.

```text
PROVIDER_OUTPUT != MATHEMATICAL_AUTHORITY
SHARED_PROVIDER != SHARED_CLAIM
```

## Track identity

Every future provider invocation, receipt, trace, candidate, and exported metric MUST bind:

```text
track_id
problem_id
source_formula_digest
base
perturbation_identity
representation_identity
precision_or_exactness_contract
execution_source_sha
```

Recommended initial track IDs:

```text
ELH_PI
BBP_ORD
```

No output may silently migrate between tracks.

## Shared exact-orbit provider family

Candidate provider roles:

```text
DIRECT_BBP_MODULAR
EXACT_RATIONAL_RECURRENCE
CERTIFIED_ARBITRARY_PRECISION
```

Before downstream statistics are interpreted, bounded parity studies SHOULD compare all qualified available representations.

```text
EXACT_MODULAR_NUMERATOR + FLOAT_DIVISION != EXACT_STATE
FLOAT64_PSEUDO_ORBIT != EXACT_BAILEY_CRANDALL_ORBIT
REPRESENTATION_AGREEMENT_ON_BOUND != GLOBAL_THEOREM
```

The ELH-R1 Python implementation remains a prototype because it uses binary floating-point division and floating-point tail evaluation. It must not be registered as an exact-state provider without repair.

## ELH-pi provider lane

Formal Discovery MAY eventually support:

- exact symbolic simplification of the pi perturbation;
- verification of the exact rational identity for `r_n`;
- global rational/asymptotic bounds;
- direct BBP versus recurrence parity;
- van der Corput shifted-phase identities;
- residual-error bounding for fixed shifts;
- multiplicative-order / resonance feature extraction;
- amplified-frequency Weyl-sum evaluation;
- candidate nonresonance lemmas;
- candidate quantitative correlation bounds;
- held-out comparison of alternative arithmetic transformations.

Permanent firewall:

```text
ENSEMBLE_DENSITY_MIXING != SINGLE_ORBIT_EQUIDISTRIBUTION
VAN_DER_CORPUT_FREQUENCY_AMPLIFICATION != WEYL_CANCELLATION
LARGE_MULTIPLICATIVE_ORDER != WEYL_CANCELLATION
```

The current critical theorem interface is:

```text
NONRESONANCE_EVIDENCE
    -> QUANTITATIVE_CORRELATION_CANCELLATION
    -> WEYL_CANCELLATION
```

Formal Discovery may propose candidates for this bridge but cannot mark it established.

## BBP-ORD provider lane

The generic track MAY eventually support a registry/corpus of BBP perturbation families with explicit structural descriptors:

```text
formula identity
base
p(n), q(n)
degree gap
decay class
leading coefficient
summability class
denominator family
factorization statistics
multiplicative-order statistics
known normality status
source/literature status
```

Candidate first-order decay classes:

```text
BBP-d1 ~ c/n
BBP-d2 ~ c/n^2
BBP-d3 ~ c/n^3
...
```

These labels are structural observations, not normality classes.

```text
SAME_DECAY_CLASS != SAME_ORBIT_BEHAVIOR
SAME_DECAY_CLASS != SAME_NORMALITY_STATUS
```

## Multiplicative-order research firewall

Future source bindings must distinguish direct fixed-base multiplicative-order results from broader modular-period literature.

Do not encode the R1 reciprocal-divisor double sum as evidence:

```text
sum_d sum_{D | (16^d - 1)} 1/D^2
```

diverges because fixed divisors recur for infinitely many `d`.

Also:

```text
sum_{D in E} 1/D^2 < infinity
```

is true for every subset of positive integers and cannot by itself establish dynamical negligibility.

```text
RECIPROCAL_SQUARE_SUMMABILITY != QUANTITATIVE_RESONANCE_SUPPRESSION
PRIME_DENOMINATOR_EXCEPTION_BOUND != COMPOSITE_DENOMINATOR_CONTROL
```

## Formalization boundary

Suggested proof-object decomposition for future exported candidates:

```text
A  VDC correlation hypothesis -> bcSeq Weyl cancellation
B  bcSeq <-> {16^n pi} tracking/equivalence
C  {16^n pi} Weyl cancellation -> base-16 normality
```

```text
BCSEQ_WEYL_CANCELLATION != PI_NORMALITY
SORRY_PRESENT != VERIFIED_PROOF
FORMAL_SKELETON != FORMAL_THEOREM
```

## Metrics

Use an explicit convention for cancellation-rate fields.

Recommended:

```text
|S_N| ~ N^-delta
```

with square-root-like cancellation represented as `delta >= 1/2`.

If a log-slope metric is also emitted, use a distinct field such as `gamma_log_slope`.

```text
DELTA_CONVENTION != GAMMA_CONVENTION
```

## Evidence and receipts

Future executions SHOULD reuse Formal Discovery's existing receipt and provenance architecture rather than invent an ungoverned side channel.

Minimum future bindings include:

```text
source digest
executor/provider identity
runtime identity
exactness/precision contract
budget
seed if stochastic
input range
harmonic/shift parameters
stdout/result digest
track identity
claim ceiling
```

Empirical results remain bounded observations.

```text
FINITE_NUMERICAL_EQUIDISTRIBUTION != NORMALITY_PROOF
NO_SQRT_CANCELLATION != NOT_NORMAL
```

## Activation boundary

No implementation or empirical campaign is authorized by this document.

Preferred future sequence:

```text
DUAL-00  source/literature custody
DUAL-01  shared exact-orbit provider qualification

then separate ELH_PI and BBP_ORD preregistrations
```

A future shared implementation repository is not yet justified.

```text
TRACK_SPLIT = YES
REPOSITORY_SPLIT = NOT_YET_EARNED
```
