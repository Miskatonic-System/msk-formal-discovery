"""Tests for Execution Trace IR, events, normalizer, and schema compliance."""
from pathlib import Path
import json
import pytest
import jsonschema

from msk_formal_discovery.core.exceptions import TraceValidationError
from msk_formal_discovery.trace.events import ExecutionTraceEvent, TraceEventType
from msk_formal_discovery.trace.ir import ExecutionTrace
from msk_formal_discovery.trace.normalizer import TraceNormalizer
from fixtures.fixture_matrix import make_sample_trace


SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"
TRACE_SCHEMA_PATH = SCHEMAS_DIR / "execution-trace.v0.1.schema.json"


@pytest.fixture
def trace_schema():
    with open(TRACE_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_execution_trace_schema_validation(trace_schema):
    """Verify standard sample traces conform to execution-trace JSON schema."""
    trace = make_sample_trace(
        "trace-schema-001",
        "prob-lean-001",
        [("step_intro", "intro(h)"), ("step_exact", "exact(h)")],
        verdict="PROVEN",
    )
    data = trace.to_dict()
    jsonschema.validate(instance=data, schema=trace_schema)
    trace.validate(TRACE_SCHEMA_PATH)


def test_roundtrip_serialization():
    trace = make_sample_trace(
        "trace-rt-001",
        "prob-rt-001",
        [("step1", "tac1(a)"), ("step2", "tac2(b)")],
        verdict="PROVEN",
    )
    d = trace.to_dict()
    reloaded = ExecutionTrace.from_dict(d)
    assert reloaded.trace_id == trace.trace_id
    assert len(reloaded.events) == len(trace.events)
    assert reloaded.events[1].operation == "step1"


def test_trace_sequence_monotonicity_enforcement():
    trace = make_sample_trace("trace-seq-001", "prob-seq", [("s1", "e1")])
    # Deliberately corrupt sequence number
    trace.events[1].sequence = 99
    with pytest.raises(TraceValidationError) as excinfo:
        trace.validate()
    assert "Non-monotonic event sequence" in str(excinfo.value)


def test_trace_dangling_parent_id_enforcement():
    trace = make_sample_trace("trace-dangle-001", "prob-dangle", [("s1", "e1")])
    trace.events[1].parent_event_id = "non-existent-parent-ev"
    with pytest.raises(TraceValidationError) as excinfo:
        trace.validate()
    assert "Parent event 'non-existent-parent-ev' not found" in str(excinfo.value)


def test_untyped_backend_leak_enforcement():
    trace = make_sample_trace("trace-leak-001", "prob-leak", [("s1", "e1")])
    trace.events[1].payload["_raw_backend_state"] = "untyped_pointer_0x7fff"
    with pytest.raises(TraceValidationError) as excinfo:
        trace.validate()
    assert "BACKEND_LEAK_WITHOUT_TYPED_EXTENSION" in str(excinfo.value)


def test_successful_path_slicing_eliminates_backtracks():
    trace = ExecutionTrace(
        trace_id="trace-branching-001",
        problem_id="prob-branching",
        backend_id="lean4",
        backend_version="4.25.0",
        logical_authority_class="NONE",
        created_at="2026-09-12T10:00:00Z",
        execution_origin="SYNTHETIC_FIXTURE",
        terminal_verdict="SYNTHETIC_SUCCESS",
    )
    ev0 = trace.add_event(TraceEventType.INITIAL_PROBLEM, "init", "d0", "d0")
    # Failed branch
    ev1_fail = trace.add_event(TraceEventType.BRANCH, "try_bad", "d0", "d1", parent_event_id=ev0.event_id)
    ev1_bt = trace.add_event(TraceEventType.BACKTRACK, "backtrack", "d1", "d0", parent_event_id=ev1_fail.event_id)
    # Successful branch
    ev2_good = trace.add_event(TraceEventType.BRANCH, "try_good", "d0", "d2", parent_event_id=ev0.event_id)
    ev3_step = trace.add_event(TraceEventType.TACTIC_APPLICATION, "step", "d2", "d3", parent_event_id=ev2_good.event_id)
    ev4_term = trace.add_event(TraceEventType.TERMINAL_VERDICT, "qed", "d3", "d4", parent_event_id=ev3_step.event_id)

    spine = TraceNormalizer.slice_successful_path(trace)
    spine_ops = [e.operation for e in spine]
    assert "try_bad" not in spine_ops
    assert "backtrack" not in spine_ops
    assert spine_ops == ["init", "try_good", "step", "qed"]


def test_all_canonical_trace_event_types_present():
    expected_event_types = {
        "INITIAL_PROBLEM",
        "FORMAL_CONTEXT",
        "GOAL_STATE",
        "SUBGOAL_STATE",
        "CONSTRAINTS",
        "SELECTED_ACTION",
        "RULE_APPLICATION",
        "TACTIC_APPLICATION",
        "GENERATED_SUBGOALS",
        "SOLVER_ASSERTION",
        "SAT_MODEL",
        "UNSAT_CORE",
        "REWRITE",
        "LEMMA_INVOCATION",
        "FAILURE",
        "BACKTRACK",
        "BRANCH",
        "TERMINAL_VERDICT",
        "RESOURCE_OBSERVATION",
    }
    actual_event_types = {e.value for e in TraceEventType}
    assert expected_event_types == actual_event_types
