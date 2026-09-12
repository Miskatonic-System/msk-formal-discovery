"""Execution trace IR implementation and validator."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import jsonschema

from msk_formal_discovery.core.exceptions import TraceValidationError
from msk_formal_discovery.trace.events import ExecutionTraceEvent, TraceEventType


@dataclass
class ExecutionTrace:
    """Canonical backend-neutral execution trace IR."""
    trace_id: str
    problem_id: str
    backend_id: str
    backend_version: str
    logical_authority_class: str
    created_at: str
    events: List[ExecutionTraceEvent] = field(default_factory=list)
    terminal_verdict: str = "INCOMPLETE"
    wall_time_ms: float = 0.0

    def add_event(
        self,
        event_type: TraceEventType,
        operation: str,
        state_digest: str,
        result_digest: str,
        parent_event_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        provenance: Optional[Dict[str, Any]] = None,
        typed_extension: Optional[Dict[str, Any]] = None,
    ) -> ExecutionTraceEvent:
        seq = len(self.events)
        ev_id = f"{self.trace_id}-ev-{seq:04d}"
        if provenance is None:
            provenance = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "origin": self.backend_id,
            }
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
            logical_authority_class=self.logical_authority_class,
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
        return {
            "schema_version": "miskatonic.execution-trace.v0.1",
            "trace_id": self.trace_id,
            "problem_id": self.problem_id,
            "backend_id": self.backend_id,
            "backend_version": self.backend_version,
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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExecutionTrace:
        events = [ExecutionTraceEvent.from_dict(ed) for ed in data.get("events", [])]
        metrics = data.get("metrics", {})
        return cls(
            trace_id=data["trace_id"],
            problem_id=data["problem_id"],
            backend_id=data["backend_id"],
            backend_version=data["backend_version"],
            logical_authority_class=data["logical_authority_class"],
            created_at=data["created_at"],
            events=events,
            terminal_verdict=data.get("terminal_verdict", "INCOMPLETE"),
            wall_time_ms=metrics.get("wall_time_ms", 0.0),
        )
