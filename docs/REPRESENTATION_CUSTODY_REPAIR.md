# WO-MATH-FORMAL-DISCOVERY-01C-R1: Representation Custody Repair Architecture

## 1. Scope and Scientific Boundary
This work order repairs evidence custody for `WO-MATH-FORMAL-DISCOVERY-01C`.
The underlying scientific result remains prospectively earned, unchanged, and immutable:
- `R0_CANONICAL_CONTROL`: `REPRESENTATION_STRATUM_INVARIANT`
- `R1_ALPHA_RENAMED`: `REPRESENTATION_STRATUM_INVARIANT`
- `R2_ASSOCIATIVE_REGROUPED`: `REPRESENTATION_STRATUM_INVARIANT`
- `R3_COMMUTATIVE_MIRROR`: `REPRESENTATION_STRATUM_SENSITIVE`
- `global_disposition`: `REPRESENTATION_INVARIANCE_NOT_SUPPORTED`

Claim Ceiling: `ENGINEERING_ABSTRACTION_EFFECT_ONLY`
Authority: `NONE`
Candidate Mutation: `PROHIBITED`

Deterministic replay is conducted strictly for evidence custody reconstruction and validation (`EVIDENCE_REPLAY != SCIENTIFIC_REPLICATION`).

## 2. Findings and Remedies

### F-FD-01C-01: Receipt Body Integrity Verification
- **Defect**: Resolver previously verified only `raw["receipt_digest"] == manifest_digest`.
- **Remedy**: Every historical transform receipt (48) and search execution receipt (96) is independently reconstructed, validated against its schema, has its digest recomputed from the serialized body, and has all semantic field invariants cross-checked.

### F-FD-01C-02: Application-Attempt Custody & Deterministic Replay
- **Defect**: Original Commit B persistence keyed application receipt files only by `application_id`, causing repeated state visits to overwrite earlier attempt bodies on disk.
- **Audit**:
  - `TOTAL_ORIGINAL_APPLICATION_ATTEMPT_REFS`: 528
  - `TOTAL_ORIGINAL_APPLICATION_ATTEMPT_DIGESTS`: 528
  - `UNIQUE_APPLICATION_IDS`: 169
  - `DUPLICATED_APPLICATION_IDS`: 100
  - `EXACT_ORIGINAL_APPLICATION_ATTEMPTS_RESOLVED`: 169
  - `OVERWRITTEN_OR_UNRESOLVABLE_APPLICATION_ATTEMPTS`: 359
- **Remedy**: All 169 resolvable artifacts are validated and verified. The 359 overwritten attempts are explicitly recorded as `ORIGINAL_APPLICATION_ATTEMPT_BODY_UNRESOLVED`. A deterministic search replay reconstructs all 528 application attempts, proving exact application-ID sequence parity, metric parity, candidate application status parity, applied count parity, and terminal status parity across all 48 abstracted searches. Replay receipts are persisted collision-free using occurrence-addressed filenames (`application-replay-<problem-id>-<ordinal>-<receipt-digest>.json`).

### F-FD-01C-03: Whole-Problem Transform Binding & Certification
- **Defect**: v0.1 transform receipts bound only initial expression transformations, omitting explicit goal expression binding.
- **Remedy**: Minted `miskatonic.representation-problem-custody-receipt.v0.2` binding initial and goal expressions, variable bijections, and original receipt references. Native-Z3 whole-problem semantic certification refutes `(initial_source != initial_transformed) OR (goal_source != goal_transformed)` under variable bijection constraints, yielding `UNSAT_REFUTED` across all 48 problems.

### F-FD-01C-04: Hardened Custody Verification & Fail-Closed Status
- **Defect**: Broken or incomplete evidence could hypothetically be conflated with scientific sensitivity.
- **Remedy**: The custody verifier fails closed with `REPRESENTATION_CUSTODY_REPAIR_FAILED` if any evidence check fails. Scientific sensitivity (`R3_COMMUTATIVE_MIRROR = REPRESENTATION_STRATUM_SENSITIVE`) is certified only after all prerequisite semantic and execution verifications succeed. Negative-control abstracted arms must strictly report `REQUESTED_NOT_APPLIED`.

### F-FD-01C-05: Exact Result Artifact Binding & Superseding Closure
- **Defect**: Historical result resolution was existence-only.
- **Remedy**: `result.json` is parsed and independently validated by exact file SHA-256 (`1455687bb385b75a01fb9c8c29158b3de6151878e0124c1af7c8a5faab7f68a8`), verifying all fields, candidate identity, and manifest/ONTO references. All historical frozen artifacts are bound by exact SHA-256 in the superseding closure manifest.
