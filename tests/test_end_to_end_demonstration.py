"""End-to-end demonstration of the formal discovery engine (Section 15).

Demonstrates:
  Execution traces -> Subtrace mining -> Anti-unification -> Abstraction candidate
  -> Held-out replay qualification -> Search-space reduction measurement
  -> ONTO export package -> Non-authoritative refactoring proposal.
"""
from pathlib import Path
import json
import pytest
import jsonschema

from fixtures.fixture_matrix import make_sample_trace
from msk_formal_discovery.abstraction.anti_unification import StructuralAntiUnifier
from msk_formal_discovery.abstraction.candidate import (
    AbstractionCandidate,
    AbstractionKind,
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
from msk_formal_discovery.onto.export import OntoExporter
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


def test_end_to_end_discovery_pipeline_demonstration():
    # 1. Pipeline sequence invariant verification
    assert verify_pipeline_sequence(list(CANONICAL_PIPELINE_SEQUENCE))

    # 2. Reasoning Backend registry validation
    reg = BackendRegistry.create_default()
    lean4_backend = reg.get("lean4")
    assert lean4_backend is not None
    jsonschema.validate(lean4_backend.to_descriptor(), BACKEND_SCHEMA)

    # 3. Search run recording
    search_run = SearchRun(
        run_id="search-run-e2e-001",
        problem_id="prob-e2e-group",
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
    trace_d1 = make_sample_trace(
        "trace-disc-1",
        "prob-algebra-1",
        [("step_expand", "mul_add(a, b, c)"), ("step_assoc", "add_assoc(a, b, c)")],
        verdict="PROVEN",
    )
    trace_d2 = make_sample_trace(
        "trace-disc-2",
        "prob-algebra-2",
        [("step_expand", "mul_add(x, y, z)"), ("step_assoc", "add_assoc(x, y, z)")],
        verdict="PROVEN",
    )

    trace_q1 = make_sample_trace(
        "trace-qual-1",
        "prob-algebra-3",
        [("step_expand", "mul_add(p, q, r)"), ("step_assoc", "add_assoc(p, q, r)")],
        verdict="PROVEN",
    )
    trace_q2 = make_sample_trace(
        "trace-qual-2",
        "prob-algebra-4",
        [("step_expand", "mul_add(u, v, w)"), ("step_assoc", "add_assoc(u, v, w)")],
        verdict="PROVEN",
    )

    for tr in [trace_d1, trace_d2, trace_q1, trace_q2]:
        jsonschema.validate(tr.to_dict(), TRACE_SCHEMA)

    # 5. Subtrace mining across discovery set
    miner = SubtraceMiner(min_length=2, min_support=2)
    patterns = miner.mine_traces([trace_d1, trace_d2])
    assert len(patterns) > 0

    top_pattern = patterns[0]
    assert top_pattern.frequency == 2
    assert top_pattern.operations == ("step_expand", "step_assoc")
    assert top_pattern.anti_unification_result is not None

    au_result = top_pattern.anti_unification_result
    assert str(au_result.lgg_term) == "seq(mul_add(V1, V2, V3), add_assoc(V1, V2, V3))"
    assert len(au_result.substitution_witnesses) == 2

    # 6. Synthesize Abstraction Candidate
    candidate = AbstractionCandidate(
        candidate_id="cand-macro-algebraic-01",
        candidate_kind=AbstractionKind.LEMMA,
        formal_specification={
            "name": "distrib_assoc_bridge",
            "statement": "forall V1 V2 V3, mul_add(V1, V2, V3) /\\ add_assoc(V1, V2, V3)",
            "canonical_representation": str(au_result.lgg_term),
        },
        anti_unification_evidence=au_result,
        discovery_set_trace_ids=["trace-disc-1", "trace-disc-2"],
        status=CandidateStatus.PROPOSED,
        blueprint_family="MICRO_LEMMA",
    )
    assert candidate.authority == "NONE"
    jsonschema.validate(candidate.to_dict(), CANDIDATE_SCHEMA)

    # 7. Held-Out Replay Qualification (enforcing disjointness and genuine measurement)
    contracts = [
        PairedReplayContract(
            problem_id="trace-qual-1",
            problem_digest="sha256_qual_1",
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
            problem_id="trace-qual-2",
            problem_digest="sha256_qual_2",
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
        if arm == "BASELINE":
            return ReplayRunReceipt(
                run_id=f"run-base-{contract.problem_id}",
                arm="BASELINE",
                problem_id=contract.problem_id,
                nodes_expanded=50,
                nodes_evaluated=70,
                branch_count=10,
                solved=True,
                wall_time_ms=100.0,
            )
        else:
            return ReplayRunReceipt(
                run_id=f"run-abs-{contract.problem_id}",
                arm="ABSTRACTED",
                problem_id=contract.problem_id,
                nodes_expanded=30,
                nodes_evaluated=40,
                branch_count=6,
                solved=True,
                wall_time_ms=65.0,
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
    assert candidate.status == CandidateStatus.QUALIFIED_HELD_OUT
    assert candidate.qualification_trace_ids == ["trace-qual-1", "trace-qual-2"]
    jsonschema.validate(candidate.to_dict(), CANDIDATE_SCHEMA)

    # 8. ONTO structural evaluation export
    onto_pkg = OntoExporter.export(candidate, functional_evidence=True)
    assert onto_pkg.authority == "NONE"
    assert onto_pkg.recurrence_count == 2
    assert onto_pkg.functional_search_benefit is True

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
