# Miskatonic Formal Discovery Engine (`msk-formal-discovery`)

**Work Order**: `WO-MATH-FORMAL-DISCOVERY-01A`  
**Repository**: `Miskatonic-System/msk-formal-discovery`  
**Architecture Owner**: `Miskatonic-System/miskatonic-systems`  
**Upstream Sources**: `Miskatonic-System/msk-corpus-intake`, `Miskatonic-System/msk-epistemic-engine`  
**Evaluation Owner**: `Miskatonic-System/msk-onto`  
**Work Type**: `PLATFORM_BOOTSTRAP_AND_ABSTRACTION_KERNEL`  
**Authority**: `NONE` (Zero theorem proof or mathematical claim authority)  
**Earned Disposition**: `FORMAL_DISCOVERY_SPINE_READY`

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
2. **Backend Authority Firewall**:
   - SMT solvers (e.g. Z3, cvc5) produce `SOLVER_SAT_OR_UNSAT`, never `DEDUCTIVE_PROOF_AUTHORITY`.
   - Model checkers (e.g. TLA+, Alloy) produce `BOUNDED_EXHAUSTIVE_VERDICT`, never proof assistant verdicts.
   - Proof assistants (e.g. Lean 4, Rocq) produce `DEDUCTIVE_PROOF_AUTHORITY` solely within their verified kernels.
3. **Search Policy Exploration Firewall**: Search policies (Frontier, Beam, A*, MCTS) propose exploration candidates; they possess `authority: "NONE"`. Specifically:
   $$\text{CORPUS\_GUIDED\_MCTS} \neq \text{CORPUS\_AUTHORITY}$$
4. **Candidate vs Accepted Abstraction**: An abstraction candidate is never accepted into canonical libraries automatically. In 01A:
   $$\text{canonical\_library\_mutated} = \text{false}$$
5. **Strict Held-Out Separation**:
   $$\text{DISCOVERY\_SET} \cap \text{QUALIFICATION\_SET} = \emptyset$$
   Any overlap immediately raises `HeldOutDataLeakageError`.

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
- [`msk_formal_discovery.backend`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/backend): Heterogeneous backend contract, authority boundaries, adapter registry, and reference adapters (`Z3Adapter`, `Lean4Adapter`, `RocqAdapter`).
- [`msk_formal_discovery.trace`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/trace): Backend-neutral Execution Trace IR, 19 canonical event types, and successful-path normalizer/slicer.
- [`msk_formal_discovery.search`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/search): Search policy contract (`authority: "NONE"`), Frontier, Beam, A*, and Corpus-Guided MCTS.
- [`msk_formal_discovery.abstraction`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/abstraction): Subtrace miner, deterministic structural anti-unification kernel (Least General Generalization), candidate lifecycle, prospective value metrics, and held-out replay engine.
- [`msk_formal_discovery.onto`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/onto): Evaluation evidence exporter package for `Miskatonic-System/msk-onto`.
- [`msk_formal_discovery.refactoring`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/refactoring): Non-authoritative refactoring proposal generator with `canonical_library_mutated: false`.
- [`fixtures`](file:///home/kowen9024/repos/msk-formal-discovery/fixtures): 8 preregistered deterministic fixture cases (Section 14).

---

## 4. Schemas (Draft 2020-12)

All data exchange conforms strictly to JSON Schema Draft 2020-12 specifications:

1. [`schemas/reasoning-backend.v0.1.schema.json`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/reasoning-backend.v0.1.schema.json): Adapter capabilities, backend families, and logical authority classes.
2. [`schemas/execution-trace.v0.1.schema.json`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/execution-trace.v0.1.schema.json): Monotonic sequence, parent-child event DAG, and typed extensions.
3. [`schemas/search-run.v0.1.schema.json`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/search-run.v0.1.schema.json): Search policy metrics, corpus guidance disclaimers, and node expansions.
4. [`schemas/abstraction-candidate.v0.1.schema.json`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/abstraction-candidate.v0.1.schema.json): LGG representation, substitution witnesses, and held-out metrics.
5. [`schemas/refactoring-proposal.v0.1.schema.json`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/refactoring-proposal.v0.1.schema.json): Non-mutating refactoring transformations and replay plans.

---

## 5. Quickstart & Verification

### Running the Test Suite

```bash
cd /home/kowen9024/repos/msk-formal-discovery
python3 -m pytest
```

The test suite runs 46 deterministic tests verifying:
- Backend registry, adapters, and authority boundaries (`test_reasoning_backends.py`)
- Execution Trace IR sequence invariants and normalization (`test_execution_trace_ir.py`)
- Search policies (Frontier, Beam, A*, MCTS) (`test_search_policies.py`)
- Structural anti-unification and reconstruction invariants (`test_anti_unification.py`)
- All 8 preregistered fixture matrix cases (`test_fixture_matrix.py`)
- End-to-end multi-trace discovery and qualification flow (`test_end_to_end_demonstration.py`)
- All 10 hostile rejection and authority escalation invariant tests (`test_hostile_invariants.py`)

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
