"""Execution trace IR implementation and validator (WO-MATH-FORMAL-DISCOVERY-01A-R1)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import jsonschema

from msk_formal_discovery.core.exceptions import AuthorityViolationError, ReceiptValidationError, TraceValidationError
from msk_formal_discovery.trace.events import EventOrigin, ExecutionTraceEvent, TraceEventType


@dataclass
class ExecutionTrace:
    """Canonical backend-neutral execution trace IR."""
    trace_id: str
    problem_id: str
    backend_id: str
    backend_version: str
    logical_authority_class: str
    created_at: str
    execution_origin: str = "SYNTHETIC_FIXTURE"
    problem_digest: str = ""
    execution_receipt: Optional[Dict[str, Any]] = None
    events: List[ExecutionTraceEvent] = field(default_factory=list)
    terminal_verdict: str = "INCOMPLETE"
    wall_time_ms: float = 0.0

    def __post_init__(self) -> None:
        # Enforce Section 8: Universal Non-NONE Authority Rule
        # Simulation or Synthetic Fixture NEVER grants non-NONE authority
        if self.execution_origin in ("SYNTHETIC_FIXTURE", "SIMULATED"):
            if self.logical_authority_class not in ("NONE", "SYNTHETIC_FIXTURE_ONLY"):
                raise AuthorityViolationError(
                    f"SYNTHETIC_CANNOT_CLAIM_AUTHORITY: Synthetic fixture or simulated trace cannot assert {self.logical_authority_class}"
                )

        # Real execution traces carrying non-NONE authority require a valid execution receipt
        if self.execution_origin in ("EXECUTED_NATIVE", "EXECUTED_CONTAINERIZED", "CERTIFIED_REPLAY"):
            if self.logical_authority_class not in ("NONE", "SYNTHETIC_FIXTURE_ONLY"):
                if not self.execution_receipt:
                    raise AuthorityViolationError(
                        f"RECEIPT_REQUIRED_FOR_NON_NONE_AUTHORITY: Real execution trace claiming '{self.logical_authority_class}' requires validated execution receipt"
                    )

                # Section 7: Trace / Receipt Cross-Consistency
                receipt_dict = self.execution_receipt if isinstance(self.execution_receipt, dict) else self.execution_receipt.to_dict()
                if receipt_dict.get("exit_code") != 0 or receipt_dict.get("timeout_status") is True:
                    raise AuthorityViolationError(
                        "UNSUCCESSFUL_EXECUTION_CANNOT_CLAIM_AUTHORITY: Execution receipt must attest exit_code == 0 and timeout_status == False"
                    )
                if receipt_dict.get("backend_id") != self.backend_id:
                    raise AuthorityViolationError(
                        f"RECEIPT_TRACE_MISMATCH: backend_id mismatch: trace '{self.backend_id}' vs receipt '{receipt_dict.get('backend_id')}'"
                    )
                if receipt_dict.get("execution_origin") != self.execution_origin:
                    raise AuthorityViolationError(
                        f"RECEIPT_TRACE_MISMATCH: execution_origin mismatch: trace '{self.execution_origin}' vs receipt '{receipt_dict.get('execution_origin')}'"
                    )
                if receipt_dict.get("logical_authority_class") != self.logical_authority_class:
                    raise AuthorityViolationError(
                        f"RECEIPT_TRACE_MISMATCH: logical_authority_class mismatch: trace '{self.logical_authority_class}' vs receipt '{receipt_dict.get('logical_authority_class')}'"
                    )
                if receipt_dict.get("terminal_classification") != self.terminal_verdict:
                    raise AuthorityViolationError(
                        f"RECEIPT_TRACE_MISMATCH: terminal mismatch: trace terminal_verdict '{self.terminal_verdict}' vs receipt terminal_classification '{receipt_dict.get('terminal_classification')}'"
                    )
                if self.problem_digest and receipt_dict.get("input_digest") and self.problem_digest != receipt_dict.get("input_digest"):
                    raise AuthorityViolationError(
                        f"RECEIPT_TRACE_MISMATCH: input_digest mismatch: trace '{self.problem_digest}' vs receipt '{receipt_dict.get('input_digest')}'"
                    )

    def add_event(
        self,
        event_type: TraceEventType,
        operation: str,
        state_digest: str,
        result_digest: str,
        parent_event_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        provenance: Optional[Dict[str, Any]] = None,
        logical_authority_class: Optional[str] = None,
        event_origin: Optional[EventOrigin] = None,
        evidence_ref: Optional[str] = None,
        evidence_digest: Optional[str] = None,
        typed_extension: Optional[Dict[str, Any]] = None,
    ) -> ExecutionTraceEvent:
        seq = len(self.events)
        ev_id = f"{self.trace_id}-ev-{seq:04d}"
        if provenance is None:
            provenance = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "origin": self.backend_id,
            }
        if event_origin is None:
            event_origin = (
                EventOrigin.SYNTHETIC_FIXTURE
                if self.execution_origin in ("SYNTHETIC_FIXTURE", "SIMULATED")
                else EventOrigin.BACKEND_OBSERVED
            )
        ev = ExecutionTraceEvent(
            event_id=ev_id,
            sequence=seq,
            event_type=event_type,
            backend_id=self.backend_id,
            backend_version=self.backend_version,
            parent_event_id=parent_event_id,
            state_digest=state_digest,
            operation=operation,
            result_digest=result_digest,
            provenance=provenance,
            logical_authority_class=logical_authority_class or self.logical_authority_class,
            event_origin=event_origin,
            evidence_ref=evidence_ref,
            evidence_digest=evidence_digest,
            payload=payload or {},
            typed_extension=typed_extension,
        )
        self.events.append(ev)
        return ev

    def validate(self, schema_path: Optional[Path] = None) -> None:
        """Validate trace invariants and schema compliance."""
        if not self.events:
            raise TraceValidationError("Execution trace must contain at least one event")

        event_ids = set()
        for idx, ev in enumerate(self.events):
            if ev.sequence != idx:
                raise TraceValidationError(
                    f"Non-monotonic event sequence: event {ev.event_id} has seq {ev.sequence}, expected {idx}"
                )
            if ev.event_id in event_ids:
                raise TraceValidationError(f"Duplicate event_id detected: {ev.event_id}")
            event_ids.add(ev.event_id)

            if ev.parent_event_id and ev.parent_event_id not in event_ids:
                raise TraceValidationError(
                    f"Parent event '{ev.parent_event_id}' not found in preceding trace history for event {ev.event_id}"
                )

            # Check untyped field leakage: raw payload must not contain arbitrary un-namespaced backend internals
            # without being wrapped in typed_extension or standard payload keys
            for key in ev.payload:
                if key.startswith("_raw_") or key.startswith("internal_backend_"):
                    if not ev.typed_extension:
                        raise TraceValidationError(
                            f"BACKEND_LEAK_WITHOUT_TYPED_EXTENSION: Untyped backend field '{key}' leaked into canonical event payload"
                        )

        # Validate against JSON schema if schema_path provided
        if schema_path and schema_path.exists():
            schema_data = json.loads(schema_path.read_text(encoding="utf-8"))
            jsonschema.validate(self.to_dict(), schema_data)

    def to_dict(self) -> Dict[str, Any]:
        branch_count = sum(1 for e in self.events if e.event_type == TraceEventType.BRANCH)
        data: Dict[str, Any] = {
            "schema_version": "miskatonic.execution-trace.v0.1",
            "trace_id": self.trace_id,
            "problem_id": self.problem_id,
            "backend_id": self.backend_id,
            "backend_version": self.backend_version,
            "execution_origin": self.execution_origin,
            "logical_authority_class": self.logical_authority_class,
            "created_at": self.created_at,
            "events": [e.to_dict() for e in self.events],
            "terminal_verdict": self.terminal_verdict,
            "metrics": {
                "event_count": len(self.events),
                "branch_count": branch_count,
                "wall_time_ms": self.wall_time_ms,
            },
        }
        if self.problem_digest:
            data["problem_digest"] = self.problem_digest
        if self.execution_receipt:
            data["execution_receipt"] = self.execution_receipt
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExecutionTrace:
        events = [ExecutionTraceEvent.from_dict(ed) for ed in data.get("events", [])]
        metrics = data.get("metrics", {})
        return cls(
            trace_id=data["trace_id"],
            problem_id=data["problem_id"],
            backend_id=data["backend_id"],
            backend_version=data["backend_version"],
            execution_origin=data.get("execution_origin", "SYNTHETIC_FIXTURE"),
            problem_digest=data.get("problem_digest", ""),
            execution_receipt=data.get("execution_receipt"),
            logical_authority_class=data["logical_authority_class"],
            created_at=data["created_at"],
            events=events,
            terminal_verdict=data.get("terminal_verdict", "INCOMPLETE"),
            wall_time_ms=metrics.get("wall_time_ms", 0.0),
        )
