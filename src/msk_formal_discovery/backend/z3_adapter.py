"""Z3 SMT Solver Reference Adapter (WO-MATH-FORMAL-DISCOVERY-01A-R1)."""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from msk_formal_discovery.backend.contract import (
    BackendExecutionReceipt,
    BackendFamily,
    ExecutionOrigin,
    LogicalAuthorityClass,
    ProblemDefinition,
    ReasoningBackend,
    derive_authority,
)
from msk_formal_discovery.core.exceptions import BackendUnavailableError
from msk_formal_discovery.trace.events import EventOrigin, TraceEventType
from msk_formal_discovery.trace.ir import ExecutionTrace


class Z3Adapter(ReasoningBackend):
    """Z3 SMT solver reference adapter enforcing real-vs-simulated solver boundaries."""

    def __init__(
        self,
        backend_id: str = "z3",
        backend_version: Optional[str] = None,
        z3_binary: Optional[str] = None,
    ) -> None:
        self.z3_binary = z3_binary or shutil.which("z3")
        detected_version = backend_version
        if not detected_version and self.z3_binary:
            try:
                proc = subprocess.run([self.z3_binary, "--version"], capture_output=True, text=True, timeout=5)
                if proc.returncode == 0:
                    detected_version = proc.stdout.strip().split("\n")[0]
            except Exception:
                pass
        version = detected_version or "5.1.0-unqualified"

        super().__init__(
            backend_id=backend_id,
            backend_family=BackendFamily.SMT_SOLVER,
            backend_version=version,
            logical_authority_class=LogicalAuthorityClass.SOLVER_SAT_OR_UNSAT,
        )

    def supported_operations(self) -> List[str]:
        return [
            "assert",
            "check_sat",
            "get_model",
            "get_unsat_core",
            "push",
            "pop",
            "reset",
        ]

    def _get_executable_sha256(self) -> str:
        if not self.z3_binary or not os.path.exists(self.z3_binary):
            return "UNAVAILABLE: BINARY_NOT_FOUND"
        try:
            with open(self.z3_binary, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            return f"UNAVAILABLE: {type(e).__name__}"

    def run_smt(
        self,
        problem_id: str,
        smtlib_script: str,
        assumptions: Optional[List[str]] = None,
        execution_mode: str = "AUTO",
        simulate: bool = False,
    ) -> ExecutionTrace:
        """Convenience method to execute an SMT problem."""
        if simulate:
            execution_mode = "SYNTHETIC"
        prob = ProblemDefinition(
            problem_id=problem_id,
            formal_syntax=smtlib_script,
            context={"execution_mode": execution_mode},
            goals=["check-sat"],
            assumptions=assumptions or [],
        )
        return self.solve(prob)

    def solve(self, problem: ProblemDefinition) -> ExecutionTrace:
        start_time = time.time()
        start_iso = datetime.now(timezone.utc).isoformat()
        mode = problem.context.get("execution_mode", "AUTO")
        if mode == "AUTO":
            mode = "REAL" if (self.z3_binary and problem.formal_syntax.strip().startswith("(")) else "SIMULATED"

        input_bytes = problem.formal_syntax.encode("utf-8")
        input_hash = hashlib.sha256(input_bytes).hexdigest()

        if mode == "REAL":
            if not self.z3_binary or not os.path.exists(self.z3_binary):
                raise BackendUnavailableError(
                    "Z3_BINARY_UNAVAILABLE: Cannot execute real SMT check without executable Z3 binary"
                )

            cmd = [self.z3_binary, "-in"]
            timeout_status = False
            stdout_text = ""
            stderr_text = ""
            exit_code: Optional[int] = None

            try:
                proc = subprocess.run(
                    cmd,
                    input=problem.formal_syntax,
                    text=True,
                    capture_output=True,
                    timeout=problem.timeout_seconds,
                )
                exit_code = proc.returncode
                stdout_text = proc.stdout
                stderr_text = proc.stderr
            except subprocess.TimeoutExpired as e:
                timeout_status = True
                stdout_text = e.stdout.decode("utf-8") if isinstance(e.stdout, bytes) else (e.stdout or "")
                stderr_text = e.stderr.decode("utf-8") if isinstance(e.stderr, bytes) else (e.stderr or "")
            except Exception as e:
                stderr_text = f"Subprocess error: {e}"
                exit_code = -1

            elapsed = (time.time() - start_time) * 1000
            end_iso = datetime.now(timezone.utc).isoformat()
            stdout_hash = hashlib.sha256(stdout_text.encode("utf-8")).hexdigest()
            stderr_hash = hashlib.sha256(stderr_text.encode("utf-8")).hexdigest()

            output_lines = [l.strip() for l in stdout_text.splitlines() if l.strip() and not l.strip().startswith(";")]
            has_error = any(l.lower().startswith("(error ") for l in output_lines) or (exit_code != 0)
            verdict_lines = [l.lower() for l in output_lines if l.lower() in ("sat", "unsat", "unknown")]

            if timeout_status:
                verdict = "TIMEOUT"
            elif has_error or len(verdict_lines) != 1:
                verdict = "FAILED"
            else:
                raw_v = verdict_lines[0]
                if raw_v == "sat":
                    verdict = "REFUTED_SAT"
                elif raw_v == "unsat":
                    verdict = "UNSAT_REFUTED"
                elif raw_v == "unknown":
                    verdict = "UNKNOWN"
                else:
                    verdict = "FAILED"

            authority_if_valid = (
                LogicalAuthorityClass.SOLVER_SAT_OR_UNSAT
                if (verdict in ("REFUTED_SAT", "UNSAT_REFUTED") and exit_code == 0 and not timeout_status)
                else LogicalAuthorityClass.NONE
            )

            receipt = BackendExecutionReceipt(
                receipt_id=f"rcpt-z3-{problem.problem_id}-{int(start_time)}",
                backend_id=self.backend_id,
                backend_family=self.backend_family,
                execution_origin=ExecutionOrigin.EXECUTED_NATIVE,
                executable_path=self.z3_binary,
                executable_version=self.backend_version,
                executable_sha256=self._get_executable_sha256(),
                command=cmd,
                input_digest=input_hash,
                started_at=start_iso,
                completed_at=end_iso,
                exit_code=exit_code,
                timeout_status=timeout_status,
                stdout_digest=stdout_hash,
                stderr_digest=stderr_hash,
                terminal_classification=verdict,
                logical_authority_class=authority_if_valid,
                execution_metadata={"raw_output_snippet": stdout_text[:200]},
            )

            authority = derive_authority(
                self.backend_family,
                ExecutionOrigin.EXECUTED_NATIVE,
                receipt,
                verdict,
            )
            if authority != receipt.logical_authority_class:
                receipt.logical_authority_class = authority

            trace = ExecutionTrace(
                trace_id=f"trace-{problem.problem_id}-z3-real",
                problem_id=problem.problem_id,
                problem_digest=input_hash,
                backend_id=self.backend_id,
                backend_version=self.backend_version,
                execution_origin=ExecutionOrigin.EXECUTED_NATIVE.value,
                execution_receipt=receipt.to_dict(),
                logical_authority_class=authority.value,
                created_at=start_iso,
                terminal_verdict=verdict,
                wall_time_ms=elapsed,
            )

            ev_init = trace.add_event(
                event_type=TraceEventType.INITIAL_PROBLEM,
                operation="load_problem",
                state_digest=input_hash,
                result_digest=input_hash,
                event_origin=EventOrigin.CLIENT_DECLARED,
                payload={"formal_syntax": problem.formal_syntax, "goals": problem.goals},
            )
            last_ev_id = ev_init.event_id

            # Section 13: Emit SAT_MODEL only if get-model was requested and parsed
            if verdict == "REFUTED_SAT" and "(get-model)" in problem.formal_syntax:
                model_lines = [l for l in stdout_text.splitlines() if "(model" in l or "define-fun" in l]
                if model_lines:
                    ev_model = trace.add_event(
                        event_type=TraceEventType.SAT_MODEL,
                        operation="get_model",
                        state_digest=input_hash,
                        result_digest=stdout_hash,
                        parent_event_id=last_ev_id,
                        event_origin=EventOrigin.BACKEND_OBSERVED,
                        payload={"raw_output": stdout_text.strip()},
                    )
                    last_ev_id = ev_model.event_id

            # Emit UNSAT_CORE only if get-unsat-core was requested and parsed
            if verdict == "UNSAT_REFUTED" and "(get-unsat-core)" in problem.formal_syntax:
                core_lines = [l for l in stdout_text.splitlines() if l.strip().startswith("(") and "error" not in l]
                if core_lines:
                    ev_core = trace.add_event(
                        event_type=TraceEventType.UNSAT_CORE,
                        operation="get_unsat_core",
                        state_digest=input_hash,
                        result_digest=stdout_hash,
                        parent_event_id=last_ev_id,
                        event_origin=EventOrigin.BACKEND_OBSERVED,
                        payload={"raw_output": stdout_text.strip()},
                    )
                    last_ev_id = ev_core.event_id

            trace.add_event(
                event_type=TraceEventType.TERMINAL_VERDICT,
                operation="check_sat",
                state_digest=input_hash,
                result_digest=stdout_hash,
                parent_event_id=last_ev_id,
                event_origin=EventOrigin.BACKEND_OBSERVED,
                payload={"verdict": verdict},
            )
            return trace

        else:
            # Simulation mode (Section 6)
            # Produces SYNTHETIC_SAT or SYNTHETIC_UNSAT with authority NONE.
            elapsed = (time.time() - start_time) * 1000
            end_iso = datetime.now(timezone.utc).isoformat()
            syntax_lower = problem.formal_syntax.lower()
            if "unsat" in syntax_lower or "assert false" in syntax_lower or "< x 0" in syntax_lower:
                verdict = "SYNTHETIC_UNSAT"
            else:
                verdict = "SYNTHETIC_SAT"

            receipt = BackendExecutionReceipt(
                receipt_id=f"rcpt-z3-sim-{problem.problem_id}-{int(start_time)}",
                backend_id=self.backend_id,
                backend_family=self.backend_family,
                execution_origin=ExecutionOrigin.SIMULATED,
                executable_path="synthetic://internal/z3_simulator",
                executable_version=self.backend_version,
                executable_sha256="UNAVAILABLE: SIMULATED",
                command=["simulated_smt_solver"],
                input_digest=input_hash,
                started_at=start_iso,
                completed_at=end_iso,
                exit_code=0,
                timeout_status=False,
                stdout_digest="0" * 64,
                stderr_digest="0" * 64,
                terminal_classification=verdict,
                logical_authority_class=LogicalAuthorityClass.NONE,
                execution_metadata={"mode": "SIMULATED"},
            )

            trace = ExecutionTrace(
                trace_id=f"trace-{problem.problem_id}-z3-sim",
                problem_id=problem.problem_id,
                problem_digest=input_hash,
                backend_id=self.backend_id,
                backend_version=self.backend_version,
                execution_origin=ExecutionOrigin.SIMULATED.value,
                execution_receipt=receipt.to_dict(),
                logical_authority_class=LogicalAuthorityClass.NONE.value,
                created_at=start_iso,
                terminal_verdict=verdict,
                wall_time_ms=elapsed,
            )

            ev_init = trace.add_event(
                event_type=TraceEventType.INITIAL_PROBLEM,
                operation="load_problem",
                state_digest=input_hash,
                result_digest=input_hash,
                event_origin=EventOrigin.SYNTHETIC_FIXTURE,
                payload={"formal_syntax": problem.formal_syntax, "goals": problem.goals},
            )
            last_ev_id = ev_init.event_id

            # Do NOT emit authoritative UNSAT_CORE or SAT_MODEL as if from Z3
            trace.add_event(
                event_type=TraceEventType.TERMINAL_VERDICT,
                operation="synthetic_verdict",
                state_digest=input_hash,
                result_digest=hashlib.sha256(b"simulated_verdict").hexdigest(),
                parent_event_id=last_ev_id,
                event_origin=EventOrigin.SYNTHETIC_FIXTURE,
                payload={"verdict": verdict, "simulated": True},
            )
            return trace
