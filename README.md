# Miskatonic Formal Discovery Engine (`msk-formal-discovery`)

**Work Order**: `WO-MATH-FORMAL-DISCOVERY-01A-R1`  
**Repository**: `Miskatonic-System/msk-formal-discovery`  
**Architecture Owner**: `Miskatonic-System/miskatonic-systems`  
**Upstream Sources**: `Miskatonic-System/msk-corpus-intake`, `Miskatonic-System/msk-epistemic-engine`  
**Evaluation Owner**: `Miskatonic-System/msk-onto`  
**Work Type**: `PLATFORM_AUTHORITY_AND_MEASUREMENT_REPAIR`  
**Authority**: `NONE` (Zero theorem proof or mathematical claim authority)  
**Historical 01A Predecessor**: `8d80e82d5936fb0df36afc95ff7bffb7d4915768` (`FORMAL_DISCOVERY_PROTOTYPE_SPINE_ESTABLISHED`)  
**Earned Repaired Disposition**: `FORMAL_DISCOVERY_SPINE_READY`

---

## Historical 01A Disposition Record

Root commit `8d80e82d5936fb0df36afc95ff7bffb7d4915768` established a prototype architecture for formal discovery. However, `FORMAL_DISCOVERY_SPINE_READY` was not yet earned at 01A because backend execution was simulated, solver refutations lacked verified process receipts, and held-out qualification metrics relied on predetermined formulas (`baseline * 0.7`).

The canonical repaired interpretation of `8d80e82` is:
$$\text{FORMAL\_DISCOVERY\_PROTOTYPE\_SPINE\_ESTABLISHED}$$

Under `WO-MATH-FORMAL-DISCOVERY-01A-R1`, all execution-authority firewalls, real backend receipts, paired replay contracts, admissibility guards, and fail-closed evaluation defaults have been implemented and verified across 56 tests, earning:
$$\text{FORMAL\_DISCOVERY\_SPINE\_READY}$$

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
   - SMT solvers (e.g. Z3) produce `SOLVER_SAT_OR_UNSAT` only with attested native execution receipts. Heuristic string simulations emit `SYNTHETIC_SAT` / `SYNTHETIC_UNSAT` with authority `NONE`.
   - Proof assistants (e.g. Lean 4, Rocq) produce `DEDUCTIVE_PROOF_AUTHORITY` only when the native checker executes successfully (`lean -D warningAsError=true --stdin`, exit code 0) and records an attested execution receipt. Synthetic simulations emit `SYNTHETIC_SUCCESS` with authority `NONE` and `proof_complete: NOT_ESTABLISHED`.
3. **Execution Receipt Requirement**:
   Authoritative verdicts require an attested [`BackendExecutionReceipt`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/backend-execution-receipt.v0.1.schema.json) capturing executable path, sha256 digest, command invocation, source input digest, stdout/stderr digests, exit code, and timeout status.
4. **Term IR Status**:
   Current Term IR is strictly an **`UNTYPED FIRST_ORDER_STRUCTURAL_AST`**. It does **not** claim higher-order logic, dependent type theory, or lambda calculus with subtyping.
5. **Search Policy Exploration Firewall**: Search policies (Frontier, Beam, A*, MCTS) propose exploration candidates; they possess `authority: "NONE"`. MCTS rollout evaluation is labeled `SYNTHETIC_PRIOR_ROLLOUT` and carries no formal proof authority.
6. **Held-Out Replay Non-Fabrication**:
   Predetermined benefit formulas (`* 0.7`) are prohibited. Qualification requires genuine observed search reduction from `EXECUTED_HELD_OUT_REPLAY` governed by a [`PairedReplayContract`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/abstraction/replay.py). `SYNTHETIC_REPLAY_FIXTURE` leaves candidates at `CANDIDATE_ONLY`.
7. **Strict Held-Out Separation**:
   $$\text{DISCOVERY\_SET} \cap \text{QUALIFICATION\_SET} = \emptyset$$
   Any overlap immediately raises `HeldOutDataLeakageError`.
8. **Candidate vs Accepted Abstraction**: An abstraction candidate is never accepted into canonical libraries automatically:
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
- [`msk_formal_discovery.trace`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/trace): Backend-neutral Execution Trace IR, execution origin binding, 19 canonical event types, and successful-path normalizer/slicer.
- [`msk_formal_discovery.search`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/search): Search policy contract (`authority: "NONE"`), Frontier, Beam, A*, and Corpus-Guided MCTS (`SYNTHETIC_PRIOR_ROLLOUT`).
- [`msk_formal_discovery.abstraction`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/abstraction): Subtrace miner, deterministic structural anti-unification kernel (Least General Generalization), admissibility guards (`STRUCTURAL_GENERALIZATION_TRIVIAL`, `TRIVIAL_OR_SEMANTICALLY_INCOMPATIBLE_GENERALIZATION`, `REQUIRES_BRANCH_GUARD`), candidate lifecycle, prospective value metrics, and held-out paired replay engine.
- [`msk_formal_discovery.onto`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/onto): Fail-closed evaluation evidence exporter package for `Miskatonic-System/msk-onto`.
- [`msk_formal_discovery.refactoring`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/refactoring): Non-authoritative refactoring proposal generator with `canonical_library_mutated: false`.
- [`fixtures`](file:///home/kowen9024/repos/msk-formal-discovery/fixtures): 8 preregistered deterministic fixture cases (Section 14).

---

## 4. Schemas (Draft 2020-12)

All data exchange conforms strictly to JSON Schema Draft 2020-12 specifications:

1. [`schemas/reasoning-backend.v0.1.schema.json`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/reasoning-backend.v0.1.schema.json): Adapter capabilities, backend families, and logical authority classes.
2. [`schemas/backend-execution-receipt.v0.1.schema.json`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/backend-execution-receipt.v0.1.schema.json): Exact executable path, sha256, command, source input digest, stdout/stderr digests, exit code, timeout status, and authority class.
3. [`schemas/execution-trace.v0.1.schema.json`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/execution-trace.v0.1.schema.json): Monotonic sequence, parent-child event DAG, execution origin, receipts, and typed extensions.
4. [`schemas/search-run.v0.1.schema.json`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/search-run.v0.1.schema.json): Search policy metrics, corpus guidance disclaimers, replay mode, and node expansions.
5. [`schemas/abstraction-candidate.v0.1.schema.json`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/abstraction-candidate.v0.1.schema.json): LGG representation, admissibility status, substitution witnesses, and held-out metrics.
6. [`schemas/refactoring-proposal.v0.1.schema.json`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/refactoring-proposal.v0.1.schema.json): Non-mutating refactoring transformations and replay plans.

---

## 5. Quickstart & Verification

### Running the Test Suite

```bash
cd /home/kowen9024/repos/msk-formal-discovery
python3 -m pytest
```

The test suite runs 56 deterministic tests verifying:
- Backend registry, adapters, real native execution, and authority boundaries (`test_reasoning_backends.py`)
- Execution Trace IR sequence invariants and normalization (`test_execution_trace_ir.py`)
- Search policies (Frontier, Beam, A*, MCTS) (`test_search_policies.py`)
- Structural anti-unification, LGG, and admissibility guards (`test_anti_unification.py`)
- All 8 preregistered fixture matrix cases (`test_fixture_matrix.py`)
- End-to-end multi-trace discovery and paired replay qualification flow (`test_end_to_end_demonstration.py`)
- All 18 hostile rejection and authority escalation invariant tests (`test_hostile_invariants.py`)

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
