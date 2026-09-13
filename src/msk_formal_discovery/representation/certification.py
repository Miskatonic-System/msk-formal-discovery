"""Automated Reasoning SMT Certification for Representation Equivalence (WO-MATH-FORMAL-DISCOVERY-01C)."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Optional, Tuple

from msk_formal_discovery.backend.contract import LogicalAuthorityClass
from msk_formal_discovery.backend.z3_adapter import Z3Adapter
from msk_formal_discovery.core.exceptions import (
    BackendUnavailableError,
    ReceiptValidationError,
)
from msk_formal_discovery.experiments.rewrite_control import RewriteProblem, term_to_smtlib
from msk_formal_discovery.representation.receipt import RepresentationTransformReceipt
from msk_formal_discovery.representation.transform import (
    RepresentationStratum,
    get_transform_implementation_digest,
)
from msk_formal_discovery.trace.ir import ExecutionTrace


def get_certification_implementation_digest() -> str:
    """SHA-256 digest of certification.py source bytes."""
    path = Path(__file__).resolve()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def certify_representation_equivalence(
    r0_problem: RewriteProblem,
    rk_problem: RewriteProblem,
    stratum: RepresentationStratum,
    variable_bijection: Dict[str, str],
    family_id: str,
    adapter: Optional[Z3Adapter] = None,
    receipts_rel_dir: str = "experiments/formal-discovery-01c/receipts",
) -> Tuple[bool, ExecutionTrace, RepresentationTransformReceipt]:
    """Verify semantic equivalence of canonical R0 representation vs transformed Rk representation via native Z3 SMT check.
    
    Query structure:
    (declare-const v Int) for all variables
    (assert (= v v_renamed)) for variable bijection pairs
    (assert (not (= smt(r0) smt(rk))))
    (check-sat)
    
    Expected: UNSAT_REFUTED (UNSAT) -> expressions are equivalent under bijection for all integer assignments.
    """
    z3 = adapter or Z3Adapter()
    if not z3.z3_binary:
        raise BackendUnavailableError("Z3_UNAVAILABLE: Native Z3 binary not found on system path")

    s_name = stratum.value if isinstance(stratum, RepresentationStratum) else str(stratum)
    t0 = r0_problem.initial_expression
    tk = rk_problem.initial_expression

    free_vars = sorted(list(t0.free_vars().union(tk.free_vars())))
    smt_lines = [
        f"; SMT Representation Equivalence Certificate (WO-MATH-FORMAL-DISCOVERY-01C)",
        f"; Family: {family_id}, Stratum: {s_name}",
    ]
    for v in free_vars:
        smt_lines.append(f"(declare-const {v} Int)")

    # Assert variable bijection mappings
    for orig_var, renamed_var in variable_bijection.items():
        if orig_var != renamed_var:
            smt_lines.append(f"(assert (= {orig_var} {renamed_var}))")

    smt0 = term_to_smtlib(t0)
    smtk = term_to_smtlib(tk)
    smt_lines.append(f"(assert (not (= {smt0} {smtk})))")
    smt_lines.append("(check-sat)")
    smt_script = "\n".join(smt_lines) + "\n"

    trace_id = f"smt-transform-{family_id}-{s_name}"
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
            f"SEMANTIC_EQUIVALENCE_FAILED: Representation {s_name} of family {family_id} failed equivalence proof with verdict '{trace.terminal_verdict}'"
        )

    smt_rec_ref = f"{receipts_rel_dir}/{trace_id}.json"
    smt_rec_digest = trace.digest()

    receipt_id = f"transform-{family_id}-{s_name}"
    receipt = RepresentationTransformReceipt(
        receipt_id=receipt_id,
        family_id=family_id,
        stratum=s_name,
        source_expression=t0.canonical_repr(),
        transformed_expression=tk.canonical_repr(),
        source_expression_digest=t0.digest(),
        transformed_expression_digest=tk.digest(),
        variable_bijection=dict(variable_bijection),
        transform_implementation_digest=get_transform_implementation_digest(),
        smt_certificate_ref=smt_rec_ref,
        smt_certificate_digest=smt_rec_digest,
        smt_verdict=trace.terminal_verdict,
        semantic_equivalence_certified=True,
        authority="NONE",
    )
    receipt.validate()

    return True, trace, receipt
