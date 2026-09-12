# Search Policy Interfaces & Guidance Firewalls

**Work Order**: `WO-MATH-FORMAL-DISCOVERY-01A-R4`
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

## 5. Search Execution Provenance Receipts & Runtime Witness

Real search executions via [`SearchExecutor`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/search/executor.py) emit attested [`SearchExecutionReceipt`](file:///home/kowen9024/repos/msk-formal-discovery/schemas/search-execution-receipt.v0.1.schema.json) records bundled in a [`SearchExecutionBundle`](file:///home/kowen9024/repos/msk-formal-discovery/src/msk_formal_discovery/search/executor.py).

### 5.1 Factory-Bound Witness Security
Under `WO-MATH-FORMAL-DISCOVERY-01A-R4`:
- A cryptographic `SearchExecutionWitness` is generated inside `SearchExecutor.execute(...)` signed with a runtime HMAC secret.
- Caller-constructed replay receipts without witness cannot confer executed qualification capability (`CALLER_CONSTRUCTED_REPLAY_RECEIPT != EXECUTED_REPLAY_EVIDENCE`).
- `SearchExecutionBundle.validate()` validates the witness, receipt schema, trace ID/digest cross-matching, and search run consistency.

### 5.2 R4 Provenance Fields
Receipts enforce comprehensive identity binding:
- `receipt_id`, `run_id`, `problem_id`, `problem_digest` (canonical 64-char hex)
- `search_policy_digest`, `search_policy_implementation_digest`
- `environment_digest`, `backend_digest`
- `initial_state_digest`, `transition_model_id`, `transition_model_digest`
- `candidate_application_status` (`DISABLED`, `REQUESTED_NOT_APPLIED`, `APPLIED`) and optional `candidate_application_digest`
- `execution_start_time` (ISO 8601 UTC) and `execution_wall_time_ms`
- `terminal_status` (`SUCCESS`, `EXHAUSTED`, `TIMEOUT`, `BUDGET_REACHED`, `FAILED`), normalized with canonical `is_successful_terminal(status)`
- `resulting_trace_id` and `resulting_trace_digest` (verified against actual trace)
- `executor_implementation_digest`: Bound to the actual file bytes of `search/executor.py` (`test_executor_implementation_digest_equals_actual_file_bytes`).
