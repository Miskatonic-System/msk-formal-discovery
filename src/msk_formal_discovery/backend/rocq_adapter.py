"""Rocq (Coq) Proof Assistant Adapter (WO-MATH-FORMAL-DISCOVERY-01A-R1)."""
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


class RocqAdapter(ReasoningBackend):
    """Rocq structural proof assistant adapter enforcing real-vs-simulated boundaries."""

    def __init__(
        self,
        backend_id: str = "rocq",
        backend_version: Optional[str] = None,
        rocq_binary: Optional[str] = None,
    ) -> None:
        self.rocq_binary = rocq_binary or shutil.which("rocq") or shutil.which("coqc")
        detected_version = backend_version
        if not detected_version and self.rocq_binary:
            try:
                proc = subprocess.run([self.rocq_binary, "--version"], capture_output=True, text=True, timeout=5)
                if proc.returncode == 0:
                    detected_version = proc.stdout.strip().split("\n")[0]
            except Exception:
                pass
        version = detected_version or "unqualified-runtime"

        super().__init__(
            backend_id=backend_id,
            backend_family=BackendFamily.PROOF_ASSISTANT,
            backend_version=version,
            logical_authority_class=LogicalAuthorityClass.DEDUCTIVE_PROOF_AUTHORITY,
        )

    def supported_operations(self) -> List[str]:
        return [
            "intros",
            "apply",
            "rewrite",
            "reflexivity",
            "simpl",
            "destruct",
            "induction",
            "auto",
        ]

    def _get_executable_sha256(self) -> str:
        if not self.rocq_binary or not os.path.exists(self.rocq_binary):
            return "UNAVAILABLE: BINARY_NOT_FOUND"
        try:
            with open(self.rocq_binary, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            return f"UNAVAILABLE: {type(e).__name__}"

    def run_proof(
        self,
        problem_id: str,
        theorem_name: str,
        code: str,
        tactics: Optional[List[str]] = None,
        execution_mode: str = "AUTO",
        simulate: bool = False,
    ) -> ExecutionTrace:
        """Convenience method to execute a Rocq proof."""
        if simulate:
            execution_mode = "SYNTHETIC"
        prob = ProblemDefinition(
            problem_id=problem_id,
            formal_syntax=code,
            context={
                "theorem_name": theorem_name,
                "tactics": tactics or ["intros", "reflexivity"],
                "execution_mode": execution_mode,
            },
            goals=[f"prove {theorem_name}"],
            assumptions=[],
        )
        return self.solve(prob)

    def solve(self, problem: ProblemDefinition) -> ExecutionTrace:
        start_time = time.time()
        start_iso = datetime.now(timezone.utc).isoformat()
        mode = problem.context.get("execution_mode", "AUTO")
        if mode == "AUTO":
            mode = "REAL" if self.rocq_binary else "SYNTHETIC"

        input_bytes = problem.formal_syntax.encode("utf-8")
        input_hash = hashlib.sha256(input_bytes).hexdigest()

        if mode == "REAL":
            if not self.rocq_binary or not os.path.exists(self.rocq_binary):
                raise BackendUnavailableError(
                    f"ROCQ_BINARY_UNAVAILABLE: Cannot execute real Rocq proof without executable binary"
                )

            # In a real environment, invoke rocq/coqc
            cmd = [self.rocq_binary, "-"]
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
                stderr_text = f"Subprocess invocation error: {e}"
                exit_code = -1

            elapsed = (time.time() - start_time) * 1000
            end_iso = datetime.now(timezone.utc).isoformat()
            stdout_hash = hashlib.sha256(stdout_text.encode("utf-8")).hexdigest()
            stderr_hash = hashlib.sha256(stderr_text.encode("utf-8")).hexdigest()

            terminal_verdict = "PROVEN" if (exit_code == 0 and not timeout_status) else "FAILED"

            receipt = BackendExecutionReceipt(
                receipt_id=f"rcpt-rocq-{problem.problem_id}-{int(start_time)}",
                backend_id=self.backend_id,
                backend_family=self.backend_family,
                execution_origin=ExecutionOrigin.EXECUTED_NATIVE,
                executable_path=self.rocq_binary,
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
                terminal_classification=terminal_verdict,
                logical_authority_class=(
                    LogicalAuthorityClass.DEDUCTIVE_PROOF_AUTHORITY
                    if (terminal_verdict == "PROVEN" and exit_code == 0 and not timeout_status)
                    else LogicalAuthorityClass.NONE
                ),
            )

            authority = derive_authority(
                self.backend_family,
                ExecutionOrigin.EXECUTED_NATIVE,
                receipt,
                terminal_verdict,
            )
            if authority != receipt.logical_authority_class:
                receipt.logical_authority_class = authority

            trace = ExecutionTrace(
                trace_id=f"trace-{problem.problem_id}-rocq-real",
                problem_id=problem.problem_id,
                problem_digest=input_hash,
                backend_id=self.backend_id,
                backend_version=self.backend_version,
                execution_origin=ExecutionOrigin.EXECUTED_NATIVE.value,
                execution_receipt=receipt.to_dict(),
                logical_authority_class=authority.value,
                created_at=start_iso,
                terminal_verdict=terminal_verdict,
                wall_time_ms=elapsed,
            )

            ev_init = trace.add_event(
                event_type=TraceEventType.INITIAL_PROBLEM,
                operation="start_lemma",
                state_digest=input_hash,
                result_digest=input_hash,
                event_origin=EventOrigin.CLIENT_DECLARED,
                payload={"formal_syntax": problem.formal_syntax, "goals": problem.goals},
            )
            last_ev_id = ev_init.event_id
            tactics = problem.context.get("tactics", [])
            curr_state = input_hash
            for i, tac in enumerate(tactics):
                tac_hash = hashlib.sha256(f"{curr_state}:{tac}".encode("utf-8")).hexdigest()
                ev_tac = trace.add_event(
                    event_type=TraceEventType.TACTIC_APPLICATION,
                    operation=f"tactic_step_{i}",
                    state_digest=curr_state,
                    result_digest=tac_hash,
                    parent_event_id=last_ev_id,
                    event_origin=EventOrigin.CLIENT_DECLARED,
                    payload={"tactic": tac, "expression": tac, "caller_hint": True},
                )
                last_ev_id = ev_tac.event_id
                curr_state = tac_hash

            trace.add_event(
                event_type=TraceEventType.TERMINAL_VERDICT,
                operation="qed" if terminal_verdict == "PROVEN" else "proof_failed",
                state_digest=curr_state,
                result_digest=stdout_hash,
                parent_event_id=last_ev_id,
                event_origin=EventOrigin.BACKEND_OBSERVED,
                payload={"verdict": terminal_verdict, "proof_complete": (terminal_verdict == "PROVEN")},
            )
            return trace

        else:
            # Mode A: Synthetic Fixture Mode
            elapsed = (time.time() - start_time) * 1000
            end_iso = datetime.now(timezone.utc).isoformat()
            terminal_verdict = "SYNTHETIC_SUCCESS"

            receipt = BackendExecutionReceipt(
                receipt_id=f"rcpt-rocq-syn-{problem.problem_id}-{int(start_time)}",
                backend_id=self.backend_id,
                backend_family=self.backend_family,
                execution_origin=ExecutionOrigin.SYNTHETIC_FIXTURE,
                executable_path="synthetic://internal/rocq_simulator",
                executable_version=self.backend_version,
                executable_sha256="UNAVAILABLE: SYNTHETIC_FIXTURE",
                command=["synthetic_simulation"],
                input_digest=input_hash,
                started_at=start_iso,
                completed_at=end_iso,
                exit_code=0,
                timeout_status=False,
                stdout_digest="0" * 64,
                stderr_digest="0" * 64,
                terminal_classification=terminal_verdict,
                logical_authority_class=LogicalAuthorityClass.NONE,
                execution_metadata={"mode": "SYNTHETIC_FIXTURE"},
            )

            trace = ExecutionTrace(
                trace_id=f"trace-{problem.problem_id}-rocq-syn",
                problem_id=problem.problem_id,
                problem_digest=input_hash,
                backend_id=self.backend_id,
                backend_version=self.backend_version,
                execution_origin=ExecutionOrigin.SYNTHETIC_FIXTURE.value,
                execution_receipt=receipt.to_dict(),
                logical_authority_class=LogicalAuthorityClass.NONE.value,
                created_at=start_iso,
                terminal_verdict=terminal_verdict,
                wall_time_ms=elapsed,
            )

            ev_init = trace.add_event(
                event_type=TraceEventType.INITIAL_PROBLEM,
                operation="start_lemma",
                state_digest=input_hash,
                result_digest=input_hash,
                event_origin=EventOrigin.CLIENT_DECLARED,
                payload={"formal_syntax": problem.formal_syntax, "goals": problem.goals},
            )
            last_ev_id = ev_init.event_id
            tactics = problem.context.get("tactics", [])
            curr_state = input_hash
            for i, tac in enumerate(tactics):
                tac_hash = hashlib.sha256(f"{curr_state}:{tac}".encode("utf-8")).hexdigest()
                ev_tac = trace.add_event(
                    event_type=TraceEventType.TACTIC_APPLICATION,
                    operation=f"tactic_step_{i}",
                    state_digest=curr_state,
                    result_digest=tac_hash,
                    parent_event_id=last_ev_id,
                    event_origin=EventOrigin.CLIENT_DECLARED,
                    payload={"tactic": tac, "expression": tac, "caller_hint": True},
                )
                last_ev_id = ev_tac.event_id
                curr_state = tac_hash

            trace.add_event(
                event_type=TraceEventType.TERMINAL_VERDICT,
                operation="synthetic_verdict",
                state_digest=curr_state,
                result_digest=hashlib.sha256(b"synthetic_receipt").hexdigest(),
                parent_event_id=last_ev_id,
                event_origin=EventOrigin.BACKEND_OBSERVED,
                payload={"verdict": terminal_verdict, "proof_complete": "NOT_ESTABLISHED"},
            )
            return trace
