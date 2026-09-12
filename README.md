# Miskatonic Formal Discovery Engine (`msk-formal-discovery`)

**Work Order**: `WO-MATH-FORMAL-DISCOVERY-01B`
**Repository**: `Miskatonic-System/msk-formal-discovery`
**Architecture Owner**: `Miskatonic-System/miskatonic-systems`
**Upstream Sources**: `Miskatonic-System/msk-corpus-intake`, `Miskatonic-System/msk-epistemic-engine`
**Evaluation Owner**: `Miskatonic-System/msk-onto`
**Work Type**: `PROSPECTIVE_CANDIDATE_APPLICATION_EXPERIMENT`
**Claim Ceiling**: `ENGINEERING_ABSTRACTION_EFFECT_ONLY`
**Authority**: `NONE` (Zero theorem proof or mathematical claim authority; canonical library mutation prohibited; MCTS scientific claims prohibited)
**Canonical Predecessor**: `288af1a06fa1d98bd9cf8dd48a9ef6902c36b9f9` (`FORMAL_DISCOVERY_SPINE_ACCEPTED`)
**Canonical Predecessor Tree**: `2e7ccb2cb5750ad2a09ec8feae684a3e8ed5409a`
**Acceptance Review**: `5188100687`

---

## 0. WO-MATH-FORMAL-DISCOVERY-01B: Governed Candidate Application & Prospective Replay

`WO-MATH-FORMAL-DISCOVERY-01B` implements the governed candidate application subsystem and runs the first prospective held-out search experiment to answer whether an abstraction candidate derived from primitive discovery traces can improve search performance on held-out problems without compromising semantic equivalence or negative-control selectivity.

### Two-Phase Governance Freeze
1. **Commit A (`APPLICATION_AND_PREREG_FREEZE`)**:
   - Commit SHA: `0f7b699779b9fc6a702bc3d675ddb555a2c2213a`
   - Tree SHA: `aa49f6dbe3a7bd3f6a7efbefad1cb798030132f3`
   - Schema: [`candidate-application-receipt.v0.1.schema.json`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/candidate-application-receipt.v0.1.schema.json) certifying candidate artifact digest, applicator implementation digest, problem digest, input state digest, substitution witness, primitive expansion digest, pre/post action surface digests, macro action digest, output state digest, and status.
   - Subsystem: [`CandidateApplicator`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/application/applicator.py) performing step-by-step primitive expansion matching, macro action construction, application equivalence witness checking (`macro_output_state_digest == primitive_output_state_digest`), and action surface replacement.
   - Integration: [`SearchExecutor`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/search/executor.py) binds `CandidateApplicator` and derives `candidate_application_status = APPLIED` exclusively via attested receipts; caller-minted `APPLIED` is strictly rejected with `AuthorityViolationError`.
   - Environment: [`RewriteSearchEnvironment`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/experiments/rewrite_control.py) implementing primitive term rewriting over an integer algebra ruleset (`MUL_ONE_LEFT`, `MUL_ONE_RIGHT`, `ADD_ZERO_LEFT`, `ADD_ZERO_RIGHT`, `DOUBLE_NEG`).
   - SMT Control: Native Z3 SMT-LIB2 semantic equivalence checking (`UNSAT_REFUTED` via `/home/linuxbrew/.linuxbrew/bin/z3`).
   - Frozen Manifests:
     - `discovery-manifest.json` (8 discovery problems, `seed=42`)
     - `qualification-manifest.json` (8 positive held-out problems, `seed=1337`; 4 negative control problems, `seed=2026`)
     - `preregistration.json` (frozen candidate selection rule, search budget, metric thresholds, adjudication criteria)
   - Commit A Freeze: Established application subsystem without recording any held-out outcomes.
2. **Commit B (`FROZEN_EXPERIMENT_EXECUTION`)**:
   - Executes the frozen discovery and paired replay experiment across all 12 held-out units.
   - Verified 8/8 discovery traces generated and mined top candidate `macro_mul_one_add_zero` (`43eeb2651b87d6da5e39e0cba39fbe59c55da1d1af52bfb6167057e96ba36108`).
   - Measured prospective search reduction:
     - Positive held-out: 318 baseline nodes -> 142 abstracted nodes (**55.35% node reduction**, threshold $\ge 20\%$).
     - Negative control: 15 baseline nodes == 15 abstracted nodes (**0 node delta**, exact parity, 0 applications).
   - Real native Z3 SMT semantic equivalence control: 12/12 verified `UNSAT_REFUTED`.
   - Promoted candidate status to `QUALIFIED_HELD_OUT`.
   - Emitted non-authoritative ONTO package (`functional_search_benefit = SUPPORTED`) and `RefactoringProposal` (`canonical_library_mutated = false`, `authority = NONE`).
   - Adjudication Verdict: **`ABSTRACTION_SEARCH_BENEFIT_SUPPORTED`**.

### Executed Prospective Experiment Results Summary

| Metric Dimension | Baseline Arm (`DISABLED`) | Abstracted Arm (`APPLIED` / `REQUESTED`) | Observed Effect / Parity | Gate Threshold | Gate Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Discovery Traces** | N/A | 8 traces (`seed=42`) | Top pattern support 8/8 (100%) | 8 traces | **PASS** |
| **Candidate Admissibility** | N/A | `ADMISSIBLE` (`macro_mul_one_add_zero`) | Validated receipt & LGG | Admissible | **PASS** |
| **Positive Problems Solved** | 8 / 8 (100%) | 8 / 8 (100%) | $\Delta = 0.0$ (Zero regressions) | $\ge 0.0$ | **PASS** |
| **Positive Nodes Expanded** | 318 nodes | 142 nodes | **-55.35% reduction** (176 nodes saved) | $\ge 20.0\%$ | **PASS** |
| **Positive Macro Applications**| 0 | 8 applied | 100% application on positive motifs | $\ge 6$ | **PASS** |
| **Negative Problems Solved** | 4 / 4 (100%) | 4 / 4 (100%) | $\Delta = 0.0$ (Zero regressions) | $\ge 0.0$ | **PASS** |
| **Negative Nodes Expanded** | 15 nodes | 15 nodes | **$\Delta = 0$ nodes** (Exact parity) | $\Delta = 0$ | **PASS** |
| **Negative Macro Applications**| 0 | 0 applied (4 `NOT_APPLICABLE`) | Exact selectivity (Zero false triggers)| 0 applications | **PASS** |
| **SMT Semantic Control (Z3)** | N/A | 12 / 12 `UNSAT_REFUTED` | Real native Z3 integer arithmetic | 12 / 12 UNSAT | **PASS** |
| **Candidate Lifecycle** | `PROPOSED` | `QUALIFIED_HELD_OUT` | Promoted via executed replay | Qualified | **PASS** |
| **ONTO Export** | `UNTESTED` | `SUPPORTED` | Validated `OntoEvidenceRef` bound | Supported | **PASS** |
| **Refactoring Proposal** | N/A | Emitted (`mutated=false`, `auth=NONE`)| Non-authoritative proposal | Non-mutating | **PASS** |

The earned adjudication disposition is:
$$\text{ABSTRACTION\_SEARCH\_BENEFIT\_SUPPORTED}$$

---

## Historical Disposition & R4-R1 Ratification Record

1. **01A Prototype Baseline**: Root commit `8d80e82d5936fb0df36afc95ff7bffb7d4915768` established the initial formal discovery prototype. `FORMAL_DISCOVERY_SPINE_READY` was withheld due to simulated backends, missing process receipts, and formula-based qualification.
2. **01A-R1 Authority Repair**: Head commit `96587f8fa379aa972922b7f5e689728e36238f50` established execution-authority separation and paired replay contracts.
3. **01A-R2 Evidence Chain & Trace Semantics**: Head commit `5a641eee2022d8ba54b20aef8708c6b380f3f987` resolved initial evidence-chain defects across 79 deterministic tests.
4. **01A-R3 Final Execution Evidence Closure**: Head commit `17724487c3e127ff0f6df07e2ad15824712078b4` sealed evidence custody seams across 99 deterministic tests.
5. **01A-R4 Production Bridge Final Repair**: Head commit `6d80eb75c7949358597022a69eb7536faeafe59d` sealed production bridges across 115 deterministic tests.
6. **01A-R4-R1 Candidate-Application Authority Closure & Spine Ratification**: Candidate application authority was formally closed and sealed, earning `FORMAL_DISCOVERY_SPINE_ACCEPTED` across 124 deterministic tests.


---

## 1. Executive Summary

`msk-formal-discovery` establishes the missing execution layer of the Miskatonic mathematical discovery architecture.

In traditional automated theorem proving and formal methods pipelines, success is defined narrowly as `solve(problem)`. This engine enforces an explicit, cumulative engineering requirement:

```text
solve(problem)
  -> retain execution trace
  -> discover repeated structure
  -> generate reusable lemma candidate
  -> replay against held-out instances
  -> measure search-space reduction
  -> propose non-authoritative refactoring
```

By coupling heterogeneous solver backends (SMT, interactive proof assistants, model checkers) through a canonical **Execution Trace IR**, a deterministic **Anti-Unification Kernel**, and a strict **Held-Out Replay Engine**, the system discovers, qualifies, and proposes reusable lemmas, tactics, and normalization rules across independent mathematical problems.

---

## 2. Authority & Governance Boundaries

> [!CAUTION]
> **Claim Ceiling: NONE**
> `msk-formal-discovery` is strictly an orchestration, search, trace-capture, anti-unification, and refactoring-proposal engine. It possesses **zero** mathematical theorem proving authority.

1. **No Scientific Claims**: No mathematical conjectures, theorems, or lemmas are asserted or proven by this repository.
2. **Backend Execution-Authority Separation**:
   - `SYNTHETIC_FIXTURE` and `SIMULATED` traces carry **zero** authority (`NONE`).
   - SMT solvers (e.g. Z3) produce `SOLVER_SAT_OR_UNSAT` only with attested native execution receipts under zero exit code. Heuristic string simulations emit `SYNTHETIC_SAT` / `SYNTHETIC_UNSAT` with authority `NONE`.
   - Proof assistants (e.g. Lean 4, Rocq) produce `DEDUCTIVE_PROOF_AUTHORITY` only when the native checker executes successfully (`lean -D warningAsError=true --stdin`, exit code 0) and records an attested execution receipt. Synthetic simulations emit `SYNTHETIC_SUCCESS` with authority `NONE` and `proof_complete: NOT_ESTABLISHED`.
3. **Execution Receipt Requirement**:
   Authoritative verdicts require an attested [`BackendExecutionReceipt`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/backend-execution-receipt.v0.1.schema.json) capturing executable path, sha256 digest, command invocation, source input digest, stdout/stderr digests, exit code, and timeout status. All authority transitions MUST flow through `derive_authority(...)`.
4. **Trace Event Origin Taxonomy**:
   - `CLIENT_DECLARED`: Tactical instructions, caller-supplied hypotheses, and exploration hints. Strictly excluded from abstraction mining.
   - `BACKEND_OBSERVED`: Structural verdicts and state changes verified and reported by the backend checker or solver.
5. **Backend Qualification Declarations**:
   - `LEAN_CHECKER_VERDICT_EXECUTION: QUALIFIED` (Lean 4.25.0 verified locally)
   - `LEAN_PROOF_STEP_TRACE_EXTRACTION: NOT_YET_QUALIFIED`
   - `ROCQ_CHECKER_VERDICT_EXECUTION: NOT_QUALIFIED` (Fail-closed due to environment absence)
   - `ROCQ_PROOF_STEP_TRACE_EXTRACTION: NOT_YET_QUALIFIED`
6. **Term IR Status**:
   Current Term IR is strictly an **`UNTYPED FIRST_ORDER_STRUCTURAL_AST`**. It does **not** claim higher-order logic, dependent type theory, or lambda calculus with subtyping.
7. **Search Policy Exploration Firewall**: Search policies (Frontier, Beam, A*, MCTS) propose exploration candidates; they possess `authority: "NONE"`. MCTS rollout evaluation is labeled `SYNTHETIC_PRIOR_ROLLOUT` and carries no formal proof authority.
8. **Canonical Experimental-Unit Identity & Replay Non-Fabrication**:
   - Canonical identity is strictly bound to `problem_digest` ($\text{DISCOVERY\_SET} \cap \text{QUALIFICATION\_SET} = \emptyset$).
   - Predetermined benefit formulas (`* 0.7`) are prohibited. Qualification requires genuine observed search reduction from `EXECUTED_HELD_OUT_REPLAY` governed by a cryptographic [`PairedReplayContract`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/abstraction/replay.py) and validated against [`ReplayRunReceipt`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/replay-run-receipt.v0.1.schema.json).
   - `SYNTHETIC_REPLAY_FIXTURE` leaves candidates at `CANDIDATE_ONLY`.
9. **Candidate Admissibility Default**:
   Candidates default to `admissibility_status: "UNASSESSED"` until formally evaluated via an [`AdmissibilityReceipt`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/abstraction/anti_unification.py). Vacuous wrapper patterns like `seq(V1)` are rejected.
10. **Evidence-Referenced ONTO Export**:
    Naked booleans and unsupported positive strings are prohibited (`NAKED_BOOLEAN_PROHIBITED`). All positive exports require structured `OntoEvidenceRef` referencing executed receipts.
11. **Candidate vs Accepted Abstraction**: An abstraction candidate is never accepted into canonical libraries automatically:
    $$\text{canonical\_library\_mutated} = \text{false}$$

---

## 3. Core Architecture

The system implements the frozen 10-stage canonical pipeline:

```mermaid
flowchart LR
    S1[1. Source Corpus] --> S2[2. Source Graph]
    S2 --> S3[3. Blueprint / Problem]
    S3 --> S4[4. Search Policy]
    S4 --> S5[5. Reasoning Backend]
    S5 --> S6[6. Execution Trace IR]
    S6 --> S7[7. Abstraction Mining]
    S7 --> S8[8. Candidate Library]
    S8 --> S9[9. Held-Out Replay]
    S9 --> S10[10. Qualification & Proposal]
```

### Module Organization

- [`msk_formal_discovery.core`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/core): Exceptions, first-order Term AST (`Const`, `Var`, `App`), and frozen pipeline sequence.
- [`msk_formal_discovery.backend`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/backend): Heterogeneous backend contract, execution receipts (`BackendExecutionReceipt`), execution origins, authority boundaries, adapter registry, and reference adapters (`Z3Adapter`, `Lean4Adapter`, `RocqAdapter`).
- [`msk_formal_discovery.trace`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/trace): Backend-neutral Execution Trace IR, execution origin binding, event origins (`CLIENT_DECLARED`, `BACKEND_OBSERVED`), 19 canonical event types, and successful-path normalizer/slicer.
- [`msk_formal_discovery.search`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/search): Search policy contract (`authority: "NONE"`), Frontier, Beam, A*, and Corpus-Guided MCTS (`SYNTHETIC_PRIOR_ROLLOUT`).
- [`msk_formal_discovery.abstraction`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/abstraction): Subtrace miner (excluding client-declared hints), deterministic structural anti-unification kernel (Least General Generalization), admissibility receipts & guards (`STRUCTURAL_GENERALIZATION_TRIVIAL`, `TRIVIAL_OR_SEMANTICALLY_INCOMPATIBLE_GENERALIZATION`, `REQUIRES_BRANCH_GUARD`), candidate lifecycle (`UNASSESSED` default), prospective value metrics, and held-out paired replay engine with cryptographic contract digests.
- [`msk_formal_discovery.onto`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/onto): Fail-closed evaluation evidence exporter package with `OntoEvidenceRef` enforcement for `Miskatonic-System/msk-onto`.
- [`msk_formal_discovery.refactoring`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/refactoring): Non-authoritative refactoring proposal generator with `canonical_library_mutated: false`.
- [`fixtures`](file:///home/kowen9024/repos/msk-formal-discovery/fixtures): 8 preregistered deterministic fixture cases (Section 14).

---

## 4. Schemas (Draft 2020-12)

All data exchange conforms strictly to JSON Schema Draft 2020-12 specifications:

1. [`schemas/reasoning-backend.v0.1.schema.json`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/reasoning-backend.v0.1.schema.json): Adapter capabilities, backend families, and logical authority classes.
2. [`schemas/backend-execution-receipt.v0.1.schema.json`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/backend-execution-receipt.v0.1.schema.json): Exact executable path, sha256, command, source input digest, stdout/stderr digests, exit code, timeout status, and authority class.
3. [`schemas/search-execution-receipt.v0.1.schema.json`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/search-execution-receipt.v0.1.schema.json): Attested search execution receipt tracking executor ID/version/digest, problem digest, policy configuration, search budget digest, trace refs/digests, and receipt digest.
4. [`schemas/replay-run-receipt.v0.1.schema.json`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/replay-run-receipt.v0.1.schema.json): Paired replay run receipt capturing contract digest, arm parity, observed metrics, embedded search execution receipt, and replay execution mode.
5. [`schemas/admissibility-receipt.v0.1.schema.json`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/admissibility-receipt.v0.1.schema.json): Attested admissibility receipt recording LGG digest, term digests, branch guards, meaningful shared constructor count, and admissibility status.
6. [`schemas/execution-trace.v0.1.schema.json`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/execution-trace.v0.1.schema.json): Monotonic sequence, parent-child event DAG, execution origin, event origins (`CLIENT_DECLARED`, `BACKEND_OBSERVED`), receipts, and problem digest.
7. [`schemas/search-run.v0.1.schema.json`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/search-run.v0.1.schema.json): Search policy metrics, corpus guidance disclaimers, problem digest, replay mode, and node expansions.
8. [`schemas/abstraction-candidate.v0.1.schema.json`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/abstraction-candidate.v0.1.schema.json): LGG representation, discovery origin, admissibility status (`UNASSESSED` default), admissibility receipt, substitution witnesses, and held-out problem digests.
9. [`schemas/refactoring-proposal.v0.1.schema.json`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/refactoring-proposal.v0.1.schema.json): Non-mutating refactoring transformations and replay plans.

---

## 5. Quickstart & Verification

### Running the Test Suite

```bash
cd /home/kowen9024/repos/msk-formal-discovery
python3 -m pytest -v
```

The test suite runs 99 deterministic tests verifying:
- Backend registry, adapters, real native execution, line-by-line parsing, and authority boundaries (`test_reasoning_backends.py`, 9 tests)
- Execution Trace IR sequence invariants, problem digests, event origins, and normalization (`test_execution_trace_ir.py`, 6 tests)
- Search policies (Frontier, Beam, A*, MCTS) (`test_search_policies.py`, 5 tests)
- Structural anti-unification, LGG, admissibility receipts, and wrapper guards (`test_anti_unification.py`, 9 tests)
- All 8 preregistered fixture matrix cases (`test_fixture_matrix.py`, 8 tests)
- End-to-end multi-trace discovery and paired replay qualification flow with SearchExecutor (`test_end_to_end_demonstration.py`, 1 test)
- All 61 hostile rejection, positive control, authority escalation, and qualification de-fabrication invariant tests (`test_hostile_invariants.py`, 61 tests)

---

## 6. Blueprint Object Families & Canonical Sequence

The engine integrates with the canonical 8 Blueprint Object Families:
- `MICRO_LEMMA`
- `HIDDEN_PRECONDITION`
- `TYPECLASS_REQUIREMENT`
- `NORMALIZATION_LEMMA`
- `LIBRARY_BRIDGE`
- `FORMAL_DEPENDENCY`
- `AMBIGUITY`
- `UNRESOLVED_SYMBOL`

And supports the canonical track sequence:
`MATH-00A` -> `MATH-00B` -> `MATH-01A` -> `MATH-02A` -> `MATH-03A` -> `MATH-04A` -> `MATH-05A`.
