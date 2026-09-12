# Heterogeneous Reasoning Backend Contract & Adapters

**Work Order**: `WO-MATH-FORMAL-DISCOVERY-01A`  
**Module**: `msk-formal-discovery/docs/BACKEND_MODEL.md`

---

## 1. Provider-Neutral Architecture

The reasoning backend layer decouples formal discovery logic from concrete underlying theorem provers, SMT solvers, and model checkers.

Each backend adapter implements the abstract base class [`ReasoningBackend`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/backend/contract.py):
- `solve(problem: ProblemDefinition) -> ExecutionTrace`
- `supported_operations() -> List[str]`
- `to_descriptor() -> Dict[str, Any]`

---

## 2. Backend Families & Logical Authority Classification

To prevent conflating solver refutations with deductive proofs, every backend is categorized into a `BackendFamily` and mapped to its canonical `LogicalAuthorityClass`:

| Backend Family | Default Authority Class | Authority Scope | Examples |
| :--- | :--- | :--- | :--- |
| **`SMT_SOLVER`** | `SOLVER_SAT_OR_UNSAT` | First-order satisfiability/unsat refutation without certified proof tree. | Z3, cvc5, Yices 2, Bitwuzla |
| **`MODEL_CHECKER`** | `BOUNDED_EXHAUSTIVE_VERDICT` | Exhaustive state exploration within bounded horizon. | TLA+, Alloy |
| **`PROOF_ASSISTANT`** | `DEDUCTIVE_PROOF_AUTHORITY` | Formally verified proof kernel certificates. | Lean 4, Rocq, Isabelle/HOL, Agda |
| **`SYMBOLIC_ORACLE`** | `SYMBOLIC_IDENTITY` | Algebraic rewriting and exact symbolic canonicalization. | SymPy, Mathematica |
| **`EXECUTABLE_ORACLE`** | `EMPIRICAL_EXECUTION` | Direct computational evaluation and testing. | Python, Julia |

---

## 3. Authority Escalation Firewalls

Backends must not claim higher authority than their fundamental logical model permits:

1. **SMT Solver Firewall**:
   An SMT solver cannot declare `DEDUCTIVE_PROOF_AUTHORITY`. Instantiating an SMT solver with proof authority immediately raises `AuthorityViolationError`:
   $$\text{SMT\_SOLVER} \not\to \text{DEDUCTIVE\_PROOF\_AUTHORITY}$$

2. **Model Checker Firewall**:
   A model checker cannot label bounded state enumeration as an interactive proof assistant certificate.
   $$\text{MODEL\_CHECKER} \not\to \text{DEDUCTIVE\_PROOF\_AUTHORITY}$$

3. **Untyped Internals Firewall**:
   Execution traces must not leak raw, unnamespaced solver pointers or backend memory structures into event payloads without explicit `typed_extension` wrapping.

---

## 4. Reference Adapters

### 4.1 Z3 SMT Adapter (`Z3Adapter`)
- **Backend ID**: `z3` (v5.1.0)
- **Family**: `SMT_SOLVER`
- **Authority**: `SOLVER_SAT_OR_UNSAT`
- **Features**: SMT-LIB2 command execution, `assert`, `check-sat`, model synthesis (`SAT_MODEL`), and conflict subset extraction (`UNSAT_CORE`).

### 4.2 Lean 4 Adapter (`Lean4Adapter`)
- **Backend ID**: `lean4` (v4.25.0)
- **Family**: `PROOF_ASSISTANT`
- **Authority**: `DEDUCTIVE_PROOF_AUTHORITY`
- **Features**: Elaboration of theorems, tactic sequence stepping (`TACTIC_APPLICATION`), goal state tracking, and closed proof verification.

### 4.3 Rocq Adapter (`RocqAdapter`)
- **Backend ID**: `rocq` (v9.0.0)
- **Family**: `PROOF_ASSISTANT`
- **Authority**: `DEDUCTIVE_PROOF_AUTHORITY`
- **Features**: Gallina / Ltac tactic stepping, reflexivity, structural induction, and Qed verification.

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
