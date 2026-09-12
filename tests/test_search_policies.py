"""Tests for search policy interfaces, implementations, and authority firewalls."""
from pathlib import Path
import json
import pytest
import jsonschema

from msk_formal_discovery.search.astar import AStarSearch
from msk_formal_discovery.search.beam import BoundedBeamSearch
from msk_formal_discovery.search.frontier import DeterministicFrontierSearch
from msk_formal_discovery.search.mcts import MCTSNode, MCTSSearch
from msk_formal_discovery.search.policy import (
    SearchAction,
    SearchPolicyKind,
    SearchRun,
    SearchState,
)


SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"
SEARCH_RUN_SCHEMA_PATH = SCHEMAS_DIR / "search-run.v0.1.schema.json"


@pytest.fixture
def search_run_schema():
    with open(SEARCH_RUN_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_deterministic_frontier_search():
    search = DeterministicFrontierSearch({"available_rules": ["r1", "r2"]})
    assert search.authority == "NONE"

    s0 = SearchState("s0", "goal0", depth=0)
    actions = search.propose_actions(s0)
    assert len(actions) == 2
    assert actions[0].operation == "r1"

    candidates = [
        SearchState("s2", "goal2", depth=2),
        SearchState("s1_b", "goal1_b", depth=1),
        SearchState("s1_a", "goal1_a", depth=1),
    ]
    next_st = search.select_next(candidates)
    assert next_st is not None
    assert next_st.state_id == "s1_a"


def test_bounded_beam_search():
    search = BoundedBeamSearch(beam_width=2)
    assert search.authority == "NONE"

    candidates = [
        SearchState("s1", "g1", depth=1, heuristic_value=0.2),
        SearchState("s2", "g2", depth=1, heuristic_value=0.9),
        SearchState("s3", "g3", depth=1, heuristic_value=0.5),
        SearchState("s4", "g4", depth=1, heuristic_value=0.1),
    ]
    beam = search.prune_to_beam(candidates)
    assert len(beam) == 2
    assert [s.state_id for s in beam] == ["s2", "s3"]

    selected = search.select_next(candidates)
    assert selected is not None
    assert selected.state_id == "s2"


def test_astar_search():
    search = AStarSearch()
    assert search.authority == "NONE"

    candidates = [
        SearchState("s1", "g1", depth=1, path_cost=2.0, heuristic_value=3.0),  # f = 5.0
        SearchState("s2", "g2", depth=2, path_cost=1.0, heuristic_value=2.0),  # f = 3.0
        SearchState("s3", "g3", depth=1, path_cost=3.0, heuristic_value=1.5),  # f = 4.5
    ]
    selected = search.select_next(candidates)
    assert selected is not None
    assert selected.state_id == "s2"


def test_mcts_search_cycle_and_corpus_guidance():
    guidance = {
        "source_graph_ref": "graph://onto/v1",
        "retrieval_hints": ["lemma_comm", "lemma_assoc"],
        "prior_probabilities": {"r1": 0.8, "r2": 0.2},
        "authority_disclaimer": "CORPUS_GUIDED_MCTS_DOES_NOT_CONFER_CORPUS_AUTHORITY",
    }
    mcts = MCTSSearch(c_param=1.414, max_rollouts=10, corpus_guidance=guidance, config={"available_rules": ["r1", "r2"]})
    assert mcts.authority == "NONE"

    root_state = SearchState("root", "initial_goal", depth=0)
    root_node = MCTSNode(node_id="n_root", state=root_state)

    best_child = mcts.run_mcts_cycle(root_node)
    assert root_node.visit_count == 10
    assert best_child is not None
    assert len(root_node.children) == 2


def test_search_run_schema_validation(search_run_schema):
    run = SearchRun(
        run_id="run-001",
        problem_id="prob-001",
        search_policy=SearchPolicyKind.MCTS,
        policy_configuration={"c_param": 1.414, "max_rollouts": 50},
        nodes_expanded=50,
        nodes_evaluated=75,
        max_depth_reached=4,
        branching_factor_effective=2.1,
        total_wall_time_ms=125.4,
        terminal_status="SUCCESS",
        resulting_trace_id="trace-001",
        corpus_guidance={
            "source_graph_ref": "msk://corpus/math/01",
            "retrieval_hints": ["hint1"],
            "prior_probabilities": {"step1": 0.7},
            "authority_disclaimer": "CORPUS_GUIDED_MCTS_DOES_NOT_CONFER_CORPUS_AUTHORITY",
        },
    )
    assert run.authority == "NONE"
    data = run.to_dict()
    jsonschema.validate(instance=data, schema=search_run_schema)
