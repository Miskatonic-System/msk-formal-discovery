# Heterogeneous Reasoning Backend Contract & Adapters

**Work Order**: `WO-MATH-FORMAL-DISCOVERY-01A-R1`  
**Module**: `msk-formal-discovery/docs/BACKEND_MODEL.md`

---

## 1. Provider-Neutral Architecture

The reasoning backend layer decouples formal discovery logic from concrete underlying theorem provers, SMT solvers, and model checkers.

Each backend adapter implements the abstract base class [`ReasoningBackend`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/backend/contract.py):
- `solve(problem: ProblemDefinition) -> ExecutionTrace`
- `supported_operations() -> List[str]`
- `to_descriptor() -> Dict[str, Any]`

---

## 2. Backend Families, Origins & Logical Authority Classification

### 2.1 Backend Families

| Backend Family | Default Authority Class | Authority Scope | Examples |
| :--- | :--- | :--- | :--- |
| **`SMT_SOLVER`** | `SOLVER_SAT_OR_UNSAT` | First-order satisfiability/unsat refutation without certified proof tree. | Z3, cvc5, Yices 2, Bitwuzla |
| **`MODEL_CHECKER`** | `BOUNDED_EXHAUSTIVE_VERDICT` | Exhaustive state exploration within bounded horizon. | TLA+, Alloy |
| **`PROOF_ASSISTANT`** | `DEDUCTIVE_PROOF_AUTHORITY` | Formally verified proof kernel certificates. | Lean 4, Rocq, Isabelle/HOL, Agda |
| **`SYMBOLIC_ORACLE`** | `SYMBOLIC_IDENTITY` | Algebraic rewriting and exact symbolic canonicalization. | SymPy, Mathematica |
| **`EXECUTABLE_ORACLE`** | `EMPIRICAL_EXECUTION` | Direct computational evaluation and testing. | Python, Julia |

### 2.2 Execution Origin Classes

Every trace event and receipt is tagged with its exact `ExecutionOrigin`:
- **`EXECUTED_NATIVE`**: Executed directly against a verified local binary runtime.
- **`EXECUTED_CONTAINERIZED`**: Executed within an attested isolated container environment.
- **`CERTIFIED_REPLAY`**: Replayed and verified against an immutable cryptographic trace record.
- **`SYNTHETIC_FIXTURE`**: Static test fixture with zero runtime backend invocation.
- **`SIMULATED`**: Algorithmic or heuristic emulation of backend behavior.

---

## 3. Authority Escalation Firewalls & Execution Receipts

### 3.1 Strict Receipt Requirement
To claim non-zero logical authority (`DEDUCTIVE_PROOF_AUTHORITY`, `SOLVER_SAT_OR_UNSAT`, `BOUNDED_EXHAUSTIVE_VERDICT`), traces **must** include an attested [`BackendExecutionReceipt`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/backend-execution-receipt.v0.1.schema.json) certifying:
- Verified executable path and version
- SHA-256 digest of executable binary (or runtime indicator)
- Exact process invocation arguments (`command`)
- SHA-256 digest of source input syntax
- Capturing of process exit code (`exit_code == 0`)
- `timeout_status == False`
- SHA-256 digests of captured stdout and stderr

### 3.2 Authority Derivation Rules
Under `derive_authority(...)`:
1. If `execution_origin in ("SYNTHETIC_FIXTURE", "SIMULATED")`:
   $$\text{Authority} \equiv \text{NONE}$$
2. If `receipt is None`, or `exit_code != 0`, or `timeout_status == True`:
   $$\text{Authority} \equiv \text{NONE}$$
3. Any attempt by a synthetic trace to assert `DEDUCTIVE_PROOF_AUTHORITY` or `SOLVER_SAT_OR_UNSAT` raises `AuthorityViolationError`.

---

## 4. Reference Adapters

### 4.1 Z3 SMT Adapter (`Z3Adapter`)
- **Backend ID**: `z3`
- **Family**: `SMT_SOLVER`
- **Real Execution**: Invokes native `z3 -in -smt2`. Produces `SOLVER_SAT_OR_UNSAT` and terminal verdicts `UNSAT_REFUTED` or `SAT_VERIFIED` with attested execution receipts.
- **Synthetic Simulation**: Emits `SYNTHETIC_SAT` or `SYNTHETIC_UNSAT` with authority `NONE`. Heuristic string matching cannot produce solver authority.
- **Fail-Closed**: If `z3` binary is missing in real mode, raises `BackendUnavailableError`.

### 4.2 Lean 4 Adapter (`Lean4Adapter`)
- **Backend ID**: `lean4`
- **Family**: `PROOF_ASSISTANT`
- **Real Execution**: Invokes `lean -D warningAsError=true --stdin`. Emits `DEDUCTIVE_PROOF_AUTHORITY` and `PROVEN` only upon clean exit code 0.
- **Synthetic Fixture**: Emits `SYNTHETIC_SUCCESS`, authority `NONE`, and `proof_complete: NOT_ESTABLISHED`.
- **Fail-Closed**: If `lean` binary is missing in real mode, raises `BackendUnavailableError`.

### 4.3 Rocq Adapter (`RocqAdapter`)
- **Backend ID**: `rocq`
- **Family**: `PROOF_ASSISTANT`
- **Real Execution**: Invokes `rocq` / `coqc` with attested source and exit semantics.
- **Synthetic Fixture**: Emits `SYNTHETIC_SUCCESS` with authority `NONE` and `proof_complete: NOT_ESTABLISHED`.
- **Fail-Closed**: If `rocq`/`coqc` binary is missing in real mode, raises `BackendUnavailableError`.

---

## 5. Planned Backend Descriptors

The [`BackendRegistry`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/backend/registry.py) maintains validated registration descriptors for planned extensions conforming to `schemas/reasoning-backend.v0.1.schema.json`:
- `cvc5` (SMT_SOLVER)
- `yices2` (SMT_SOLVER)
- `bitwuzla` (SMT_SOLVER)
- `alloy` (MODEL_CHECKER)
- `tlaplus` (MODEL_CHECKER)
- `isabelle` (PROOF_ASSISTANT)
- `agda` (PROOF_ASSISTANT)
