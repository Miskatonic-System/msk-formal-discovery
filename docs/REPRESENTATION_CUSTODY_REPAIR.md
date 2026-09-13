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

---

# WO-MATH-FORMAL-DISCOVERY-01C-R1-R1: Exact Replay Application-Receipt Custody & Applied-Count Parity Repair

## 1. Scope and Invariants
This work order repairs the deterministic-replay custody seam identified in blocking source review 5188829114:
- Historical evidence namespaces `experiments/formal-discovery-01c/**` and `experiments/formal-discovery-01c-r1/**` are strictly immutable.
- All new artifacts are isolated under `experiments/formal-discovery-01c-r1-r1/**`.
- Scientific status remains identical and unchanged:
  - `R0_CANONICAL_CONTROL`: `REPRESENTATION_STRATUM_INVARIANT`
  - `R1_ALPHA_RENAMED`: `REPRESENTATION_STRATUM_INVARIANT`
  - `R2_ASSOCIATIVE_REGROUPED`: `REPRESENTATION_STRATUM_INVARIANT`
  - `R3_COMMUTATIVE_MIRROR`: `REPRESENTATION_STRATUM_SENSITIVE`
  - `GLOBAL`: `REPRESENTATION_INVARIANCE_NOT_SUPPORTED`
- Claim Ceiling: `ENGINEERING_ABSTRACTION_EFFECT_ONLY`, Authority: `NONE`.

## 2. Custody Findings and Remedies

### F-FD-01C-R1-01: Exact Replay Application-Receipt Body Custody
- **Defect**: The R1 replay persisted 13-field summary records rather than full `miskatonic.candidate-application-receipt.v0.1` instances.
- **Remedy**: Full `CandidateApplicationReceipt` instances produced by the replay search engine are validated and persisted in complete v0.1 format at occurrence-addressed filenames (`application-replay-<problem-id>-<ordinal:04d>-<digest[:16]>.json`). Across all 48 replay runs, exactly 528 receipts are verified and dereferenced.
- **Durable Custody Statement**:
  - `ORIGINAL_ATTEMPT_BODY_CUSTODY = PARTIAL_AND_EXPLICIT` (169 original bodies preserved, 359 unresolvable due to historical in-place overwriting in 01C Commit B).
  - `DETERMINISTIC_REPLAY_ATTEMPT_BODY_CUSTODY = COMPLETE` (528 collision-free application receipts deterministically re-executed, verified, and sealed).

### F-FD-01C-R1-02: 4-Way Applied-Count Parity Verification
- **Defect**: Replay previously verified candidate application status matching without validating numeric parity between paired manifest counts and actual attempt bodies.
- **Remedy**: Enforces strict 4-way equality:
  `ORIGINAL_MANIFEST_APPLIED_COUNT == ORIGINAL_APPLICATION_ID_APPLIED_COUNT == REPLAY_RECEIPT_BODY_APPLIED_COUNT == REPLAY_APPLICATION_ID_APPLIED_COUNT`.
  Fails closed if aggregate status matches but applied counts diverge.

### F-FD-01C-R1-03: Frozen Search-Budget Identity & Replay Search Receipts
- **Defect**: Replay previously used `max_nodes: 100` rather than the preregistered `max_expansions: 100`.
- **Remedy**: Search budget pinned to exact preregistration dictionary `{"max_expansions": 100}` with canonical SHA-256 digest `33e3063843806441f4193971b31f4c3093393af722d83f8f95cc11ff669f9635`. Replay persists all 48 full `SearchExecutionReceipt` bodies (`search-replay-<problem-id>.json`), validating search budget parity and metric parity across all runs.

