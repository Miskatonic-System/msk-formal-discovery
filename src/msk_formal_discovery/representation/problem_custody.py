"""Problem-level representation custody receipt and whole-problem semantic certification (WO-MATH-FORMAL-DISCOVERY-01C-R1 Finding F-FD-01C-03)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import jsonschema

from msk_formal_discovery.backend.contract import LogicalAuthorityClass
from msk_formal_discovery.backend.z3_adapter import Z3Adapter
from msk_formal_discovery.core.exceptions import (
    BackendUnavailableError,
    ReceiptValidationError,
)
from msk_formal_discovery.experiments.rewrite_control import RewriteProblem, term_to_smtlib
from msk_formal_discovery.representation.transform import (
    RepresentationStratum,
    get_transform_implementation_digest,
)
from msk_formal_discovery.trace.ir import ExecutionTrace

RECEIPT_V0_2_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "schemas" / "representation-problem-custody-receipt.v0.2.schema.json"
)


def get_problem_custody_implementation_digest() -> str:
    """SHA-256 digest of problem_custody.py source code."""
    path = Path(__file__).resolve()
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class RepresentationProblemCustodyReceipt:
    """Attested receipt binding complete problem semantics (initial + goal) under representation transformation."""
    receipt_id: str
    family_id: str
    representation_stratum: str
    source_problem_id: str
    source_problem_digest: str
    transformed_problem_id: str
    transformed_problem_digest: str
    source_initial_expression: str
    source_initial_expression_digest: str
    transformed_initial_expression: str
    transformed_initial_expression_digest: str
    source_goal_expression: str
    source_goal_digest: str
    transformed_goal_expression: str
    transformed_goal_digest: str
    variable_bijection: Dict[str, str]
    transform_parameters: Dict[str, Any]
    transform_implementation_digest: str
    original_v0_1_transform_receipt_ref: str
    original_v0_1_transform_receipt_digest: str
    original_initial_semantics_smt_ref: str
    original_initial_semantics_smt_digest: str
    whole_problem_semantics_smt_ref: str
    whole_problem_semantics_smt_digest: str
    authority: str = "NONE"
    schema_version: str = "miskatonic.representation-problem-custody-receipt.v0.2"
    receipt_digest: str = ""

    def __post_init__(self) -> None:
        if not self.receipt_digest:
            self.receipt_digest = self.compute_digest()

    def compute_digest(self) -> str:
        d = {k: v for k, v in self.to_dict().items() if k != "receipt_digest"}
        serialized = json.dumps(d, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "family_id": self.family_id,
            "representation_stratum": self.representation_stratum,
            "source_problem_id": self.source_problem_id,
            "source_problem_digest": self.source_problem_digest,
            "transformed_problem_id": self.transformed_problem_id,
            "transformed_problem_digest": self.transformed_problem_digest,
            "source_initial_expression": self.source_initial_expression,
            "source_initial_expression_digest": self.source_initial_expression_digest,
            "transformed_initial_expression": self.transformed_initial_expression,
            "transformed_initial_expression_digest": self.transformed_initial_expression_digest,
            "source_goal_expression": self.source_goal_expression,
            "source_goal_digest": self.source_goal_digest,
            "transformed_goal_expression": self.transformed_goal_expression,
            "transformed_goal_digest": self.transformed_goal_digest,
            "variable_bijection": dict(self.variable_bijection),
            "transform_parameters": dict(self.transform_parameters),
            "transform_implementation_digest": self.transform_implementation_digest,
            "original_v0_1_transform_receipt_ref": self.original_v0_1_transform_receipt_ref,
            "original_v0_1_transform_receipt_digest": self.original_v0_1_transform_receipt_digest,
            "original_initial_semantics_smt_ref": self.original_initial_semantics_smt_ref,
            "original_initial_semantics_smt_digest": self.original_initial_semantics_smt_digest,
            "whole_problem_semantics_smt_ref": self.whole_problem_semantics_smt_ref,
            "whole_problem_semantics_smt_digest": self.whole_problem_semantics_smt_digest,
            "authority": self.authority,
            "receipt_digest": self.receipt_digest,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RepresentationProblemCustodyReceipt:
        return cls(
            schema_version=data.get("schema_version", "miskatonic.representation-problem-custody-receipt.v0.2"),
            receipt_id=data["receipt_id"],
            family_id=data["family_id"],
            representation_stratum=data["representation_stratum"],
            source_problem_id=data["source_problem_id"],
            source_problem_digest=data["source_problem_digest"],
            transformed_problem_id=data["transformed_problem_id"],
            transformed_problem_digest=data["transformed_problem_digest"],
            source_initial_expression=data["source_initial_expression"],
            source_initial_expression_digest=data["source_initial_expression_digest"],
            transformed_initial_expression=data["transformed_initial_expression"],
            transformed_initial_expression_digest=data["transformed_initial_expression_digest"],
            source_goal_expression=data["source_goal_expression"],
            source_goal_digest=data["source_goal_digest"],
            transformed_goal_expression=data["transformed_goal_expression"],
            transformed_goal_digest=data["transformed_goal_digest"],
            variable_bijection=dict(data.get("variable_bijection", {})),
            transform_parameters=dict(data.get("transform_parameters", {})),
            transform_implementation_digest=data["transform_implementation_digest"],
            original_v0_1_transform_receipt_ref=data["original_v0_1_transform_receipt_ref"],
            original_v0_1_transform_receipt_digest=data["original_v0_1_transform_receipt_digest"],
            original_initial_semantics_smt_ref=data["original_initial_semantics_smt_ref"],
            original_initial_semantics_smt_digest=data["original_initial_semantics_smt_digest"],
            whole_problem_semantics_smt_ref=data["whole_problem_semantics_smt_ref"],
            whole_problem_semantics_smt_digest=data["whole_problem_semantics_smt_digest"],
            authority=data.get("authority", "NONE"),
            receipt_digest=data.get("receipt_digest", ""),
        )

    def validate(self, schema_path: Optional[Path] = None) -> None:
        if self.authority != "NONE":
            raise ReceiptValidationError(f"AUTHORITY_VIOLATION: authority must be 'NONE', got '{self.authority}'")
        
        target_schema = schema_path or RECEIPT_V0_2_SCHEMA_PATH
        if target_schema.is_file():
            schema_data = json.loads(target_schema.read_text(encoding="utf-8"))
            try:
                jsonschema.validate(self.to_dict(), schema_data)
            except jsonschema.exceptions.ValidationError as e:
                raise ReceiptValidationError(f"V0_2_RECEIPT_SCHEMA_ERROR: {e.message}") from e

        computed = self.compute_digest()
        if self.receipt_digest != computed:
            raise ReceiptValidationError(
                f"V0_2_RECEIPT_DIGEST_MISMATCH: Stored {self.receipt_digest} != computed {computed}"
            )


def certify_whole_problem_equivalence(
    r0_problem: RewriteProblem,
    rk_problem: RewriteProblem,
    stratum: RepresentationStratum,
    variable_bijection: Dict[str, str],
    family_id: str,
    orig_v0_1_receipt_ref: str,
    orig_v0_1_receipt_digest: str,
    orig_initial_smt_ref: str,
    orig_initial_smt_digest: str,
    receipts_rel_dir: str = "experiments/formal-discovery-01c-r1/receipts",
    adapter: Optional[Z3Adapter] = None,
) -> Tuple[bool, ExecutionTrace, RepresentationProblemCustodyReceipt]:
    """Perform native-Z3 certification proving both initial and goal semantic equivalence.
    
    Refutes:
    (initial_source != initial_transformed) OR (goal_source != goal_transformed)
    under the alpha-bijection constraints.
    Required verdict: UNSAT_REFUTED.
    """
    z3 = adapter or Z3Adapter()
    if not z3.z3_binary:
        raise BackendUnavailableError("Z3_UNAVAILABLE: Native Z3 binary not found on system path")

    s_name = stratum.value if isinstance(stratum, RepresentationStratum) else str(stratum)
    t0_init = r0_problem.initial_expression
    tk_init = rk_problem.initial_expression
    t0_goal = r0_problem.goal_expression
    tk_goal = rk_problem.goal_expression

    all_vars = sorted(list(t0_init.free_vars() | tk_init.free_vars() | t0_goal.free_vars() | tk_goal.free_vars()))
    smt_lines = [
        f"; Whole-Problem Semantic Certification (WO-MATH-FORMAL-DISCOVERY-01C-R1)",
        f"; Family: {family_id}, Stratum: {s_name}",
        f"; Problem: {rk_problem.problem_id}",
    ]
    for v in all_vars:
        smt_lines.append(f"(declare-const {v} Int)")

    # Assert variable bijection mappings
    for orig_var, renamed_var in variable_bijection.items():
        if orig_var != renamed_var:
            smt_lines.append(f"(assert (= {orig_var} {renamed_var}))")

    s0_i = term_to_smtlib(t0_init)
    sk_i = term_to_smtlib(tk_init)
    s0_g = term_to_smtlib(t0_goal)
    sk_g = term_to_smtlib(tk_goal)

    # Hostile refutation: Prove NOT (init_diff OR goal_diff) is UNSAT
    smt_lines.append(f"(assert (or (not (= {s0_i} {sk_i})) (not (= {s0_g} {sk_g}))))")
    smt_lines.append("(check-sat)")
    smt_script = "\n".join(smt_lines) + "\n"

    trace_id = f"smt-whole-problem-{family_id}-{s_name}"
    trace = z3.run_smt(
        problem_id=trace_id,
        smtlib_script=smt_script,
        execution_mode="REAL",
    )

    if trace.execution_origin != "EXECUTED_NATIVE":
        raise ReceiptValidationError(
            f"SMT_NON_NATIVE_EXECUTION: origin '{trace.execution_origin}', simulated fallback prohibited"
        )
    if trace.logical_authority_class != LogicalAuthorityClass.SOLVER_SAT_OR_UNSAT:
        raise ReceiptValidationError(
            f"SMT_INVALID_AUTHORITY: {trace.logical_authority_class}"
        )
    if trace.terminal_verdict != "UNSAT_REFUTED":
        raise ReceiptValidationError(
            f"WHOLE_PROBLEM_SEMANTIC_EQUIVALENCE_FAILED: Problem {rk_problem.problem_id} failed whole-problem equivalence with verdict '{trace.terminal_verdict}'"
        )

    smt_rec_ref = f"{receipts_rel_dir}/{trace_id}.json"
    smt_rec_digest = trace.digest()

    receipt_id = f"problem-custody-{family_id}-{s_name}"
    receipt = RepresentationProblemCustodyReceipt(
        receipt_id=receipt_id,
        family_id=family_id,
        representation_stratum=s_name,
        source_problem_id=r0_problem.problem_id,
        source_problem_digest=r0_problem.problem_digest,
        transformed_problem_id=rk_problem.problem_id,
        transformed_problem_digest=rk_problem.problem_digest,
        source_initial_expression=t0_init.canonical_repr(),
        source_initial_expression_digest=t0_init.digest(),
        transformed_initial_expression=tk_init.canonical_repr(),
        transformed_initial_expression_digest=tk_init.digest(),
        source_goal_expression=t0_goal.canonical_repr(),
        source_goal_digest=t0_goal.digest(),
        transformed_goal_expression=tk_goal.canonical_repr(),
        transformed_goal_digest=tk_goal.digest(),
        variable_bijection=dict(variable_bijection),
        transform_parameters={"stratum": s_name},
        transform_implementation_digest=get_transform_implementation_digest(),
        original_v0_1_transform_receipt_ref=orig_v0_1_receipt_ref,
        original_v0_1_transform_receipt_digest=orig_v0_1_receipt_digest,
        original_initial_semantics_smt_ref=orig_initial_smt_ref,
        original_initial_semantics_smt_digest=orig_initial_smt_digest,
        whole_problem_semantics_smt_ref=smt_rec_ref,
        whole_problem_semantics_smt_digest=smt_rec_digest,
        authority="NONE",
    )
    receipt.validate()

    return True, trace, receipt
