"""Preregistered deterministic fixture matrix (Section 14)."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from msk_formal_discovery.core.terms import Term
from msk_formal_discovery.trace.events import TraceEventType
from msk_formal_discovery.trace.ir import ExecutionTrace


@dataclass
class FixtureCase:
    name: str
    description: str
    traces: List[ExecutionTrace]
    expected_outcome: Dict[str, Any]


def make_sample_trace(
    trace_id: str,
    problem_id: str,
    operations: List[Tuple[str, str]],  # (op_name, expression)
    verdict: str = "SYNTHETIC_SUCCESS",
    branch_count: int = 0,
    execution_origin: str = "SYNTHETIC_FIXTURE",
    backend_id: str = "synthetic-fixture",
    logical_authority_class: str = "NONE",
    problem_digest: Optional[str] = None,
) -> ExecutionTrace:
    p_digest = problem_digest or hashlib.sha256(problem_id.encode("utf-8")).hexdigest()
    tr = ExecutionTrace(
        trace_id=trace_id,
        problem_id=problem_id,
        problem_digest=p_digest,
        backend_id=backend_id,
        backend_version="1.0.0-fixture",
        execution_origin=execution_origin,
        logical_authority_class=logical_authority_class,
        created_at="2026-09-12T10:00:00Z",
        terminal_verdict=verdict,
        wall_time_ms=15.0,
    )
    init_ev = tr.add_event(
        event_type=TraceEventType.INITIAL_PROBLEM,
        operation="init",
        state_digest="0" * 64,
        result_digest="0" * 64,
        payload={"problem": problem_id},
    )
    last_id = init_ev.event_id
    for idx, (op, expr) in enumerate(operations):
        ev = tr.add_event(
            event_type=TraceEventType.TACTIC_APPLICATION,
            operation=op,
            state_digest="0" * 64,
            result_digest="1" * 64,
            parent_event_id=last_id,
            payload={"operation": op, "expression": expr, "tactic": expr},
        )
        last_id = ev.event_id

    tr.add_event(
        event_type=TraceEventType.TERMINAL_VERDICT,
        operation="qed",
        state_digest="1" * 64,
        result_digest="2" * 64,
        parent_event_id=last_id,
        payload={"verdict": verdict, "proof_complete": "NOT_ESTABLISHED"},
    )
    return tr


def get_preregistered_fixtures() -> Dict[str, FixtureCase]:
    """Return all 8 preregistered fixture cases per Section 14."""
    fixtures: Dict[str, FixtureCase] = {}

    # 1. Repeated Identical
    t1_ident = make_sample_trace(
        "trace-ident-1", "prob-1",
        [("step_intro", "intro(h)"), ("step_comm", "apply(add_comm)"), ("step_exact", "exact(h)")]
    )
    t2_ident = make_sample_trace(
        "trace-ident-2", "prob-2",
        [("step_intro", "intro(h)"), ("step_comm", "apply(add_comm)"), ("step_exact", "exact(h)")]
    )
    fixtures["REPEATED_IDENTICAL"] = FixtureCase(
        name="repeated_identical_proof_fragments",
        description="Identical proof fragments across distinct problem traces",
        traces=[t1_ident, t2_ident],
        expected_outcome={
            "subtrace_found": True,
            "mined_pattern_length": 3,
            "free_variable_count": 0,
        },
    )

    # 2. Alpha-Renamed
    t1_alpha = make_sample_trace(
        "trace-alpha-1", "prob-3",
        [("step_trans", "le_trans(x, y)"), ("step_finish", "finish(x)")]
    )
    t2_alpha = make_sample_trace(
        "trace-alpha-2", "prob-4",
        [("step_trans", "le_trans(a, b)"), ("step_finish", "finish(a)")]
    )
    fixtures["ALPHA_RENAMED"] = FixtureCase(
        name="alpha_renamed_equivalent_fragments",
        description="Equivalence under variable alpha-renaming",
        traces=[t1_alpha, t2_alpha],
        expected_outcome={
            "subtrace_found": True,
            "mined_pattern_length": 2,
            "free_variable_count": 2,
        },
    )

    # 3. Structurally Generalizable
    t1_struct = make_sample_trace(
        "trace-struct-1", "prob-5",
        [("step_eval", "f(a, g(x))"), ("step_done", "done(a)")]
    )
    t2_struct = make_sample_trace(
        "trace-struct-2", "prob-6",
        [("step_eval", "f(b, g(y))"), ("step_done", "done(b)")]
    )
    fixtures["STRUCTURALLY_GENERALIZABLE"] = FixtureCase(
        name="structurally_generalizable_fragments",
        description="Nonlinear structural generalization f(V1, g(V2))",
        traces=[t1_struct, t2_struct],
        expected_outcome={
            "subtrace_found": True,
            "lgg_representation": "seq(f(V1, g(V2)), done(V1))",
            "witness_count": 2,
        },
    )

    # 4. Superficially Similar but Semantically Distinct
    t1_distinct = make_sample_trace(
        "trace-dist-1", "prob-7",
        [("step_op", "int_plus(a, b)")]
    )
    t2_distinct = make_sample_trace(
        "trace-dist-2", "prob-8",
        [("step_op", "bool_xor(a, b)")]
    )
    fixtures["SEMANTICALLY_DISTINCT"] = FixtureCase(
        name="superficially_similar_semantically_distinct",
        description="Matching arity but distinct semantic domains",
        traces=[t1_distinct, t2_distinct],
        expected_outcome={
            "functor_match": False,
            "shared_direct_functor": False,
        },
    )

    # 5. Repeated UNSAT-Core Patterns
    t1_unsat = make_sample_trace(
        "trace-unsat-1", "prob-9",
        [("assert_c1", "assert(c1)"), ("assert_c2", "assert(c2)"), ("assert_c3", "assert(c3)")],
        verdict="SYNTHETIC_UNSAT"
    )
    t2_unsat = make_sample_trace(
        "trace-unsat-2", "prob-10",
        [("assert_c1", "assert(c1)"), ("assert_other", "assert(c4)"), ("assert_c3", "assert(c3)")],
        verdict="SYNTHETIC_UNSAT"
    )
    fixtures["REPEATED_UNSAT_CORE"] = FixtureCase(
        name="repeated_unsat_core_patterns",
        description="Solver traces with recurring conflicting assertion subset",
        traces=[t1_unsat, t2_unsat],
        expected_outcome={
            "core_overlap": ["c1", "c3"],
            "conflict_mined": True,
        },
    )

    # 6. Shared Lemma Chains
    t1_chain = make_sample_trace(
        "trace-chain-1", "prob-11",
        [("step_simp", "simp(h1)"), ("step_rw", "rewrite(h2)"), ("step_exact", "exact(h3)")]
    )
    t2_chain = make_sample_trace(
        "trace-chain-2", "prob-12",
        [("step_simp", "simp(h1)"), ("step_rw", "rewrite(h2)"), ("step_exact", "exact(h3)")]
    )
    fixtures["SHARED_LEMMA_CHAINS"] = FixtureCase(
        name="shared_lemma_chains",
        description="Chained lemma applications across multiple problems",
        traces=[t1_chain, t2_chain],
        expected_outcome={
            "chain_length": 3,
            "candidate_macro_eligible": True,
        },
    )

    # 7. Misleading Common Prefixes
    t1_pref = make_sample_trace(
        "trace-pref-1", "prob-13",
        [("setup_1", "intro(x)"), ("setup_2", "intro(y)"), ("diverge_1", "ring_solve(x)")]
    )
    t2_pref = make_sample_trace(
        "trace-pref-2", "prob-14",
        [("setup_1", "intro(x)"), ("setup_2", "intro(y)"), ("diverge_2", "omega_solve(y)")]
    )
    fixtures["MISLEADING_COMMON_PREFIX"] = FixtureCase(
        name="misleading_common_prefixes",
        description="Identical setup prefix with divergent terminal strategies",
        traces=[t1_pref, t2_pref],
        expected_outcome={
            "common_prefix_length": 2,
            "terminal_identical": False,
            "global_completion_lemma_generated": False,
        },
    )

    # 8. Branch-Local Patterns
    t1_branch = make_sample_trace(
        "trace-branch-1", "prob-15",
        [("case_neg", "assume(neg)"), ("sub_1", "scale(x)"), ("sub_2", "bound(x)")],
        branch_count=2
    )
    t2_branch = make_sample_trace(
        "trace-branch-2", "prob-16",
        [("case_pos", "assume(pos)"), ("other_1", "invert(x)"), ("other_2", "bound(x)")],
        branch_count=2
    )
    fixtures["BRANCH_LOCAL_PATTERN"] = FixtureCase(
        name="branch_local_patterns",
        description="Patterns local to conditional branch cases that must not globalize",
        traces=[t1_branch, t2_branch],
        expected_outcome={
            "globalizes_without_precondition": False,
            "requires_branch_guard": True,
        },
    )

    return fixtures
