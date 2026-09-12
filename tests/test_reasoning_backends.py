"""Tests for reasoning backends, registry, adapters, and authority contracts."""
from pathlib import Path
import json
import pytest
import jsonschema

from msk_formal_discovery.backend.contract import (
    BackendFamily,
    LogicalAuthorityClass,
    ReasoningBackend,
)
from msk_formal_discovery.backend.registry import BackendRegistry
from msk_formal_discovery.backend.z3_adapter import Z3Adapter
from msk_formal_discovery.backend.lean4_adapter import Lean4Adapter
from msk_formal_discovery.backend.rocq_adapter import RocqAdapter
from msk_formal_discovery.core.exceptions import AuthorityViolationError


SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"
BACKEND_SCHEMA_PATH = SCHEMAS_DIR / "reasoning-backend.v0.1.schema.json"


@pytest.fixture
def backend_schema():
    with open(BACKEND_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_backend_schema_validation(backend_schema):
    """Verify backend descriptors conform to JSON schema."""
    registry = BackendRegistry.create_default(schema_path=BACKEND_SCHEMA_PATH)
    for backend_id, desc in registry.all_descriptors().items():
        jsonschema.validate(instance=desc, schema=backend_schema)


def test_default_registry_contains_expected_backends():
    registry = BackendRegistry.create_default()
    assert "z3" in registry
    assert "lean4" in registry
    assert "rocq" in registry
    assert "cvc5" in registry
    assert "tlaplus" in registry

    assert registry.get("z3").backend_family == BackendFamily.SMT_SOLVER
    assert registry.get("lean4").backend_family == BackendFamily.PROOF_ASSISTANT
    assert registry.get("rocq").backend_family == BackendFamily.PROOF_ASSISTANT


def test_authority_enforcement_on_instantiation():
    """Verify that an SMT solver cannot claim deductive proof authority upon initialization."""
    class DummySMT(ReasoningBackend):
        def solve(self, problem): pass
        def supported_operations(self): return ["assert"]

    with pytest.raises(AuthorityViolationError) as excinfo:
        DummySMT(
            backend_id="fake_smt",
            backend_family=BackendFamily.SMT_SOLVER,
            backend_version="1.0.0",
            logical_authority_class=LogicalAuthorityClass.DEDUCTIVE_PROOF_AUTHORITY,
        )
    assert "SOLVER_SAT_RESULT_CANNOT_CLAIM_PROOF_AUTHORITY" in str(excinfo.value)


def test_authority_enforcement_on_model_checker():
    """Verify that a model checker cannot claim deductive proof authority upon initialization."""
    class DummyMC(ReasoningBackend):
        def solve(self, problem): pass
        def supported_operations(self): return ["check"]

    with pytest.raises(AuthorityViolationError) as excinfo:
        DummyMC(
            backend_id="fake_mc",
            backend_family=BackendFamily.MODEL_CHECKER,
            backend_version="1.0.0",
            logical_authority_class=LogicalAuthorityClass.DEDUCTIVE_PROOF_AUTHORITY,
        )
    assert "MODEL_CHECKER_MISLABELED_AS_PROOF_ASSISTANT" in str(excinfo.value)


def test_z3_adapter_simulated():
    adapter = Z3Adapter()
    trace = adapter.run_smt(
        problem_id="prob-smt-001",
        smtlib_script="(assert (> x 0))\n(assert (< x 0))\n(check-sat)",
        simulate=True,
    )
    assert trace.backend_id == "z3"
    assert trace.execution_origin == "SIMULATED"
    assert trace.logical_authority_class == "NONE"
    assert trace.terminal_verdict in ("SYNTHETIC_SAT", "SYNTHETIC_UNSAT")
    assert len(trace.events) >= 2


def test_lean4_adapter_simulated():
    adapter = Lean4Adapter()
    code = "theorem test_thm (p : Prop) (h : p) : p := by\n  exact h\n"
    trace = adapter.run_proof(
        problem_id="prob-lean-001",
        theorem_name="test_thm",
        code=code,
        simulate=True,
    )
    assert trace.backend_id == "lean4"
    assert trace.execution_origin == "SYNTHETIC_FIXTURE"
    assert trace.logical_authority_class == "NONE"
    assert trace.terminal_verdict == "SYNTHETIC_SUCCESS"
    assert len(trace.events) >= 2


def test_rocq_adapter_simulated():
    adapter = RocqAdapter()
    code = "Lemma test_lem : forall p : Prop, p -> p.\nProof.\n  intros p H.\n  exact H.\nQed."
    trace = adapter.run_proof(
        problem_id="prob-rocq-001",
        theorem_name="test_lem",
        code=code,
        simulate=True,
    )
    assert trace.backend_id == "rocq"
    assert trace.execution_origin == "SYNTHETIC_FIXTURE"
    assert trace.logical_authority_class == "NONE"
    assert trace.terminal_verdict == "SYNTHETIC_SUCCESS"
    assert len(trace.events) >= 2


def test_z3_adapter_real_execution():
    adapter = Z3Adapter()
    if not adapter.z3_binary:
        pytest.skip("z3 binary not available")
    trace = adapter.run_smt(
        problem_id="prob-smt-real-001",
        smtlib_script="(declare-const x Int)\n(assert (> x 0))\n(assert (< x 0))\n(check-sat)\n",
        execution_mode="REAL",
    )
    assert trace.backend_id == "z3"
    assert trace.execution_origin == "EXECUTED_NATIVE"
    assert trace.logical_authority_class == "SOLVER_SAT_OR_UNSAT"
    assert trace.terminal_verdict == "UNSAT_REFUTED"
    assert trace.execution_receipt is not None
    assert trace.execution_receipt["exit_code"] == 0


def test_lean4_adapter_real_execution():
    adapter = Lean4Adapter()
    if not adapter.lean_binary:
        pytest.skip("lean binary not available")
    code = "theorem test_real (p : Prop) (h : p) : p := by\n  exact h\n"
    trace = adapter.run_proof(
        problem_id="prob-lean-real-001",
        theorem_name="test_real",
        code=code,
        execution_mode="REAL",
    )
    assert trace.backend_id == "lean4"
    assert trace.execution_origin == "EXECUTED_NATIVE"
    assert trace.logical_authority_class == "DEDUCTIVE_PROOF_AUTHORITY"
    assert trace.terminal_verdict == "PROVEN"
    assert trace.execution_receipt is not None
    assert trace.execution_receipt["exit_code"] == 0

