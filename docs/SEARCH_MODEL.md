# Search Policy Interfaces & Guidance Firewalls

**Work Order**: `WO-MATH-FORMAL-DISCOVERY-01A-R4-R1`
**Module**: `msk-formal-discovery/docs/SEARCH_MODEL.md`
**Final Disposition**: `FORMAL_DISCOVERY_SPINE_ACCEPTED`

---

## 1. Search Policy Contract

Search policies govern the exploration of formal proof trees, tactic states, and goal decompositions.

Every policy implements [`SearchPolicy`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/search/policy.py):
- `propose_actions(state: SearchState) -> List[SearchAction]`
- `select_next(candidates: List[SearchState]) -> Optional[SearchState]`
- `authority: str = "NONE"`

### Strict Invariant: Exploration $\neq$ Proof Truth
Search policies propose paths of mathematical exploration. They possess zero deductive authority. A high heuristic score or deep MCTS visit count does not constitute a proof:
$$\text{SearchPolicy.authority} \equiv \text{NONE}$$

---

## 2. Core Search Implementations

### 2.1 Deterministic Frontier Search (`DeterministicFrontierSearch`)
- **Strategy**: Breadth-first / FIFO deterministic queue.
- **Ordering**: Prioritizes lowest depth, resolving ties deterministically by `state_id`.
- **Use Case**: Exhaustive baseline search over small discrete proof graphs.

### 2.2 Bounded Beam Search (`BoundedBeamSearch`)
- **Strategy**: Maintains the top $K$ candidate states according to `heuristic_value`.
- **Parameter**: `beam_width` (default $K = 5$).
- **Use Case**: Memory-bounded heuristic proof search in wide branching spaces.

### 2.3 A* Search (`AStarSearch`)
- **Strategy**: Priority queue minimizing total estimated cost:
  $$f(n) = g(n) + h(n)$$
  where $g(n) = \text{path\_cost}$ and $h(n) = \text{heuristic\_value}$.
- **Use Case**: Optimal pathfinding when admissible heuristic estimators are available.

### 2.4 Monte Carlo Tree Search (`MCTSSearch`)
- **Strategy**: 4-stage exploration cycle:
  1. **Selection**: Traverses tree using Upper Confidence bounds for Trees (UCT):
     $$\text{UCT}(n) = Q(n) + c \cdot P(n) \cdot \sqrt{\frac{\ln N(\text{parent})}{1 + N(n)}}$$
  2. **Expansion**: Proposes actions for unexplored leaf states.
  3. **Simulation / Rollout**: Evaluates candidate rollout reward.
  4. **Backpropagation**: Updates visit counts and cumulative values along ancestry path.
- **Rollout Evaluator Capability Boundary**:
  Rollout evaluations are explicitly typed as **`SYNTHETIC_PRIOR_ROLLOUT`** (or `UNBOUNDED_ESTIMATE`). They carry **zero** formal proof authority:
  $$\text{MCTS\_SIMULATION\_METRICS} \not\to \text{DEDUCTIVE\_PROOF\_AUTHORITY}$$

---

## 3. Corpus-Guided MCTS & Epistemic Guidance Firewall

When coupled with upstream epistemic graphs (`Miskatonic-System/msk-epistemic-engine`), MCTS utilizes prior probabilities derived from corpus co-occurrence and concept graphs.

### Invariant: Corpus Guidance $\neq$ Corpus Authority
$$\text{CORPUS\_GUIDED\_MCTS} \neq \text{CORPUS\_AUTHORITY}$$

The corpus guidance interface:
- **May**: Adjust prior probabilities $P(a)$ to guide tactic selection toward historically fruitful paths.
- **May**: Suggest premise retrieval hints.
- **Must Not**: Bypass formal verification or claim proof authority.
- **Required Disclaimer**: Every search run utilizing corpus hints must record:
  ```json
  "authority_disclaimer": "CORPUS_GUIDED_MCTS_DOES_NOT_CONFER_CORPUS_AUTHORITY"
  ```

---

## 4. Search Run Record Specification

Search runs are persisted and validated against `schemas/search-run.v0.1.schema.json`:
- `run_id`, `problem_id`, `problem_digest` (canonical experimental-unit identity, 64-char lowercase hex)
- `search_policy` and `policy_configuration`
- `replay_mode`: Explicitly records `EXECUTED_SEARCH_RUN`, `CERTIFIED_SEARCH_REPLAY`, or `SYNTHETIC_REPLAY_FIXTURE`
- `paired_contract_ref`: Optional reference to the binding `PairedReplayContract`
- `corpus_guidance` (if present)
- `resulting_trace_id`
- Metrics: `nodes_expanded`, `nodes_evaluated`, `max_depth_reached`, `branching_factor_effective`, `total_wall_time_ms`
- `terminal_status`: `SUCCESS`, `EXHAUSTED`, `TIMEOUT`, `BUDGET_REACHED`, `FAILED`
- Invariant: `authority: "NONE"`

---

## 5. Search Execution Provenance, Candidate Application Closure, & Runtime Witness

Real search executions via [`SearchExecutor`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/search/executor.py) emit attested [`SearchExecutionReceipt`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/search-execution-receipt.v0.1.schema.json) records bundled in a [`SearchExecutionBundle`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/search/executor.py).

### 5.1 Factory-Bound Witness Security & Trust Boundary
Under `WO-MATH-FORMAL-DISCOVERY-01A-R4-R1`:
- A cryptographic `SearchExecutionWitness` is generated inside `SearchExecutor.execute(...)` signed with a runtime HMAC secret.
- Caller-constructed replay receipts without witness cannot confer executed qualification capability (`CALLER_CONSTRUCTED_REPLAY_RECEIPT != EXECUTED_REPLAY_EVIDENCE`).
- `SearchExecutionBundle.validate()` validates the witness, receipt schema, trace ID/digest cross-matching, and search run consistency.
- **Process-Local Witness Trust Note (Section 16)**:
  `SearchExecutionWitness` is a process-local provenance and anti-construction mechanism, NOT a cryptographic security boundary against arbitrary code executing inside the same Python interpreter:
  $$\text{PROCESS\_LOCAL\_PROVENANCE\_WITNESS} \neq \text{HOSTILE\_CODE\_ISOLATION}$$

### 5.2 Candidate Application Closure & State Freeze (Sections 2-6)
- **Removal of Caller APPLIED Control**: `SearchExecutor.execute(...)` derives application status itself:
  - `candidate_enabled = False` $\implies$ `DISABLED`
  - `candidate_enabled = True` $\implies$ `REQUESTED_NOT_APPLIED`
- **Caller Requests for APPLIED Rejected**: Any caller attempt to set `candidate_application_status = "APPLIED"` raises `AuthorityViolationError`.
- **Reserved State for 01B**: `APPLIED` is frozen as a reserved future state requiring a governed `CandidateApplicator` and `CandidateApplicationReceipt`.
- **Action-Generator Parity**: `action_generator` receives identical inputs in baseline and candidate-requested arms; candidate ID is never passed into the action generator.

### 5.3 Candidate Digests & Invariants (Sections 12 & 13)
- **Candidate Artifact Digest**: Binds `candidate_id`, `candidate_kind`, `formal_specification`, `lgg_digest`, and `admissibility_receipt_digest`.
- **Candidate Application Digest**: Binds status, requested candidate ID, and candidate artifact digest, enforcing:
  $$\text{REQUEST\_DIGEST} \neq \text{APPLICATION\_PROOF}$$

### 5.4 Candidate Application Subsystem (`CandidateApplicator`)
Under `WO-MATH-FORMAL-DISCOVERY-01B`:
- `CandidateApplicator` executes candidate application at search expansion time.
- Emits attested `CandidateApplicationReceipt` binding:
  - candidate artifact digest
  - applicator implementation digest
  - input search state digest
  - output/transformed search state or action surface digest
  - application semantics and execution outcome (`APPLIED`, `NOT_APPLICABLE`, `REJECTED`)
  - exact experimental unit
- `SearchExecutionReceipt` records:
  - `candidate_application_receipt_refs`: List of references to emitted application receipts
  - `candidate_application_receipt_digests`: List of digests of emitted application receipts
- Only valid `CandidateApplicationReceipt(status="APPLIED")` records permit `SearchExecutor` to derive `candidate_application_status = APPLIED`. Attempts by callers to pass `APPLIED` directly continue to be strictly rejected.
- **Executed Prospective Results**:
  - Positive held-out units (8 instances): Search space reduced from 318 nodes (baseline) to 142 nodes (abstracted), establishing a **55.35% node expansion reduction** ($\Delta = 176$ nodes saved) with 100% solve rate maintained.
  - Negative control units (4 instances): Search space remained exactly 15 nodes (baseline) vs 15 nodes (abstracted) with 0 candidate applications (**$\Delta = 0$ node delta**), maintaining exact selectivity parity.
