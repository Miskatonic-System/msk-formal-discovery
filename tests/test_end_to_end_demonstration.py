"""End-to-end demonstration of the formal discovery engine (Section 15).

Demonstrates:
  Execution traces -> Subtrace mining -> Anti-unification -> Abstraction candidate
  -> Held-out replay qualification -> Search-space reduction measurement
  -> ONTO export package -> Non-authoritative refactoring proposal.
"""
from pathlib import Path
import json
import hashlib
import pytest
import jsonschema

from fixtures.fixture_matrix import make_sample_trace
from msk_formal_discovery.abstraction.anti_unification import (
    AdmissibilityStatus,
    StructuralAntiUnifier,
)
from msk_formal_discovery.abstraction.candidate import (
    AbstractionCandidate,
    AbstractionKind,
    CandidateFactory,
    CandidateStatus,
)
from msk_formal_discovery.abstraction.replay import (
    HeldOutReplayEngine,
    PairedReplayContract,
    ReplayRunReceipt,
)
from msk_formal_discovery.abstraction.subtrace_miner import SubtraceMiner
from msk_formal_discovery.backend.registry import BackendRegistry
from msk_formal_discovery.core.pipeline import CANONICAL_PIPELINE_SEQUENCE, verify_pipeline_sequence
from msk_formal_discovery.onto.export import OntoEvidenceRef, OntoExporter
from msk_formal_discovery.refactoring.proposal import (
    RefactoringKind,
    RefactoringProposalGenerator,
)
from msk_formal_discovery.search.mcts import MCTSSearch
from msk_formal_discovery.search.policy import SearchPolicyKind, SearchRun


SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"
BACKEND_SCHEMA = json.loads((SCHEMAS_DIR / "reasoning-backend.v0.1.schema.json").read_text())
TRACE_SCHEMA = json.loads((SCHEMAS_DIR / "execution-trace.v0.1.schema.json").read_text())
SEARCH_SCHEMA = json.loads((SCHEMAS_DIR / "search-run.v0.1.schema.json").read_text())
CANDIDATE_SCHEMA = json.loads((SCHEMAS_DIR / "abstraction-candidate.v0.1.schema.json").read_text())
REFACTOR_SCHEMA = json.loads((SCHEMAS_DIR / "refactoring-proposal.v0.1.schema.json").read_text())
SEARCH_EXECUTION_RECEIPT_SCHEMA = json.loads((SCHEMAS_DIR / "search-execution-receipt.v0.1.schema.json").read_text())


def test_end_to_end_discovery_pipeline_demonstration():
    # 1. Pipeline sequence invariant verification
    assert verify_pipeline_sequence(list(CANONICAL_PIPELINE_SEQUENCE))

    # 2. Reasoning Backend registry validation
    reg = BackendRegistry.create_default()
    lean4_backend = reg.get("lean4")
    assert lean4_backend is not None
    jsonschema.validate(lean4_backend.to_descriptor(), BACKEND_SCHEMA)

    # 3. Search run recording
    search_prob_digest = hashlib.sha256(b"prob-e2e-group").hexdigest()
    search_run = SearchRun(
        run_id="search-run-e2e-001",
        problem_id="prob-e2e-group",
        problem_digest=search_prob_digest,
        search_policy=SearchPolicyKind.MCTS,
        policy_configuration={"c_param": 1.414, "max_rollouts": 20},
        nodes_expanded=20,
        nodes_evaluated=35,
        max_depth_reached=3,
        branching_factor_effective=1.75,
        total_wall_time_ms=45.0,
        terminal_status="SUCCESS",
        resulting_trace_id="trace-disc-1",
        corpus_guidance={
            "source_graph_ref": "msk://corpus/e2e/graph",
            "retrieval_hints": ["comm", "assoc"],
            "prior_probabilities": {"step_comm": 0.6, "step_assoc": 0.4},
            "authority_disclaimer": "CORPUS_GUIDED_MCTS_DOES_NOT_CONFER_CORPUS_AUTHORITY",
        },
    )
    assert search_run.authority == "NONE"
    jsonschema.validate(search_run.to_dict(), SEARCH_SCHEMA)

    # 4. Input execution traces: 2 discovery traces, 2 strictly held-out qualification traces
    d1_digest = hashlib.sha256(b"prob-algebra-1").hexdigest()
    d2_digest = hashlib.sha256(b"prob-algebra-2").hexdigest()
    q1_digest = hashlib.sha256(b"prob-algebra-3").hexdigest()
    q2_digest = hashlib.sha256(b"prob-algebra-4").hexdigest()

    trace_d1 = make_sample_trace(
        "trace-disc-1",
        "prob-algebra-1",
        [("step_expand", "mul_add(a, b, c)"), ("step_assoc", "add_assoc(a, b, c)")],
        verdict="PROVEN",
        problem_digest=d1_digest,
    )
    trace_d2 = make_sample_trace(
        "trace-disc-2",
        "prob-algebra-2",
        [("step_expand", "mul_add(x, y, z)"), ("step_assoc", "add_assoc(x, y, z)")],
        verdict="PROVEN",
        problem_digest=d2_digest,
    )

    trace_q1 = make_sample_trace(
        "trace-qual-1",
        "prob-algebra-3",
        [("step_expand", "mul_add(p, q, r)"), ("step_assoc", "add_assoc(p, q, r)")],
        verdict="PROVEN",
        problem_digest=q1_digest,
    )
    trace_q2 = make_sample_trace(
        "trace-qual-2",
        "prob-algebra-4",
        [("step_expand", "mul_add(u, v, w)"), ("step_assoc", "add_assoc(u, v, w)")],
        verdict="PROVEN",
        problem_digest=q2_digest,
    )

    for tr in [trace_d1, trace_d2, trace_q1, trace_q2]:
        jsonschema.validate(tr.to_dict(), TRACE_SCHEMA)

    # 5. Subtrace mining across discovery set (synthetic_algorithm_test_mode=True for fixture traces)
    miner = SubtraceMiner(min_length=2, min_support=2, synthetic_algorithm_test_mode=True)
    patterns = miner.mine_traces([trace_d1, trace_d2])
    assert len(patterns) > 0

    top_pattern = patterns[0]
    assert top_pattern.frequency == 2
    assert top_pattern.operations == ("step_expand", "step_assoc")
    assert top_pattern.anti_unification_result is not None

    au_result = top_pattern.anti_unification_result
    assert str(au_result.lgg_term) == "seq(mul_add(V1, V2, V3), add_assoc(V1, V2, V3))"
    assert len(au_result.substitution_witnesses) == 2

    # 6. Synthesize Abstraction Candidate via governed synthesis path (Section 27)
    candidate = CandidateFactory.from_pattern(
        top_pattern,
        candidate_kind=AbstractionKind.LEMMA,
        candidate_id="cand-macro-algebraic-01",
        discovery_problem_digests=[d1_digest, d2_digest],
        blueprint_family="MICRO_LEMMA",
    )
    assert candidate.authority == "NONE"
    assert candidate.admissibility_status == AdmissibilityStatus.ADMISSIBLE
    assert candidate.admissibility_receipt is not None
    assert candidate.discovery_origin == "SYNTHETIC_FIXTURE"
    jsonschema.validate(candidate.to_dict(), CANDIDATE_SCHEMA)

    # 7. Held-Out Replay Qualification (enforcing disjointness and genuine measurement)
    contracts = [
        PairedReplayContract(
            problem_id="prob-algebra-3",
            problem_digest=q1_digest,
            backend_id="lean4",
            search_policy_kind="MCTS",
            search_budget={"max_expansions": 50, "timeout_ms": 1000},
            random_seed=42,
            corpus_context={"context_id": "ctx-algebra"},
            baseline_configuration={"enable_candidate": False},
            abstracted_configuration={"enable_candidate": True, "candidate_id": candidate.candidate_id},
            candidate_id=candidate.candidate_id,
            candidate_enabled_in_abstracted=True,
        ),
        PairedReplayContract(
            problem_id="prob-algebra-4",
            problem_digest=q2_digest,
            backend_id="lean4",
            search_policy_kind="MCTS",
            search_budget={"max_expansions": 50, "timeout_ms": 1000},
            random_seed=42,
            corpus_context={"context_id": "ctx-algebra"},
            baseline_configuration={"enable_candidate": False},
            abstracted_configuration={"enable_candidate": True, "candidate_id": candidate.candidate_id},
            candidate_id=candidate.candidate_id,
            candidate_enabled_in_abstracted=True,
        ),
    ]

    def runner_fn(contract: PairedReplayContract, arm: str) -> ReplayRunReceipt:
        t_ref = "trace-qual-1" if contract.problem_id == "prob-algebra-3" else "trace-qual-2"
        return ReplayRunReceipt(
            receipt_id=f"run-{arm.lower()}-{contract.problem_id}",
            arm=arm,
            problem_id=contract.problem_id,
            problem_digest=contract.problem_digest,
            paired_contract_digest=contract.contract_digest(),
            backend_id=contract.backend_id,
            search_policy_kind=contract.search_policy_kind,
            candidate_id=contract.candidate_id,
            candidate_enabled=(arm == "ABSTRACTED"),
            random_seed=contract.random_seed,
            search_budget_digest=hashlib.sha256(json.dumps(contract.search_budget, sort_keys=True).encode("utf-8")).hexdigest(),
            corpus_context_digest=hashlib.sha256(json.dumps(contract.corpus_context, sort_keys=True).encode("utf-8")).hexdigest(),
            nodes_expanded=50 if arm == "BASELINE" else 30,
            nodes_evaluated=70 if arm == "BASELINE" else 40,
            branch_count=10 if arm == "BASELINE" else 6,
            solved=True,
            wall_time_ms=100.0 if arm == "BASELINE" else 65.0,
            execution_trace_refs=[t_ref],
            execution_trace_digests=["0" * 64],
            evidence_origin="SYNTHETIC_FIXTURE",
        )

    replay_engine = HeldOutReplayEngine()
    value_report = replay_engine.execute_paired_replay(
        candidate=candidate,
        contracts=contracts,
        runner_fn=runner_fn,
    )

    # Search space reduction measurement
    assert value_report.structural_compression_ratio > 1.0
    assert value_report.candidate_evaluation_reduction > 0.0
    assert value_report.wall_time_delta_pct < 0.0
    # Section 15 & 24: synthetic discovery leaves candidate at CANDIDATE_ONLY
    assert candidate.status == CandidateStatus.CANDIDATE_ONLY
    assert candidate.qualification_problem_ids == ["prob-algebra-3", "prob-algebra-4"]
    assert candidate.qualification_problem_digests == [q1_digest, q2_digest]
    jsonschema.validate(candidate.to_dict(), CANDIDATE_SCHEMA)

    # 8. ONTO structural evaluation export (Section 31 & 32: no naked booleans)
    onto_pkg = OntoExporter.export(candidate)
    assert onto_pkg.authority == "NONE"
    assert onto_pkg.recurrence_count == 2
    assert onto_pkg.functional_search_benefit in ("UNTESTED", "UNKNOWN")

    # Providing verified OntoEvidenceRef
    art_ref = "run-abs-trace-qual-1"
    art_dig = hashlib.sha256(b"replay_artifact").hexdigest()
    OntoExporter.register_evidence_artifact(art_ref, art_dig)
    ev_ref = OntoEvidenceRef(
        evidence_kind="HELD_OUT_REPLAY",
        artifact_ref=art_ref,
        artifact_digest=art_dig,
        evidence_status="SUPPORTED",
        source_experimental_units=[q1_digest, q2_digest],
    )
    onto_pkg_with_ref = OntoExporter.export(candidate, functional_evidence=ev_ref)
    assert onto_pkg_with_ref.functional_search_benefit == "SUPPORTED"

    # 9. Non-authoritative Refactoring Proposal Generation
    proposal = RefactoringProposalGenerator.generate(
        candidate=candidate,
        refactoring_kind=RefactoringKind.EXTRACTED_HELPER_LEMMA,
    )
    assert proposal.canonical_library_mutated is False
    assert proposal.authority == "NONE"
    assert proposal.candidate_id == candidate.candidate_id
    assert len(proposal.affected_traces) == 4
    jsonschema.validate(proposal.to_dict(), REFACTOR_SCHEMA)
    proposal.validate(SCHEMAS_DIR / "refactoring-proposal.v0.1.schema.json")

    from msk_formal_discovery.backend.contract import ProblemDefinition
    from msk_formal_discovery.search.executor import SearchExecutor
    from msk_formal_discovery.search.policy import SearchState
    exec_prob_digest = hashlib.sha256(b"prob-executed-mcts").hexdigest()
    exec_prob = ProblemDefinition(
        problem_id="prob-executed-mcts",
        formal_syntax="eval(True)",
        context={},
        goals=["True"],
        assumptions=[],
    )
    mcts_policy = MCTSSearch({"max_rollouts": 5})
    init_state = SearchState(state_id="init_0", goal="True", depth=0)
    executor = SearchExecutor()
    bundle = executor.execute(
        policy=mcts_policy,
        problem=exec_prob,
        initial_state=init_state,
        budget={"max_nodes": 10, "max_depth": 5},
        random_seed=42,
        corpus_context={},
    )
    assert bundle.search_run.replay_mode == "EXECUTED_SEARCH_RUN"
    bundle.receipt.validate()
    jsonschema.validate(bundle.receipt.to_dict(), SEARCH_EXECUTION_RECEIPT_SCHEMA)
    assert bundle.search_run.search_execution_receipt is not None

    # Prove that EXECUTED_SEARCH_RUN cannot be manually forged without SearchExecutionReceipt
    from msk_formal_discovery.core.exceptions import ReceiptValidationError
    with pytest.raises(ReceiptValidationError):
        ReplayRunReceipt(
            receipt_id="r-forged",
            arm="BASELINE",
            problem_id="prob-executed-mcts",
            problem_digest=exec_prob_digest,
            paired_contract_digest="c" * 64,
            backend_id="lean4",
            search_policy_kind="MCTS",
            evidence_origin="EXECUTED_SEARCH_RUN",
        ).validate()
