"""Execution trace IR event types and data structures."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Dict, Optional


class TraceEventType(str, Enum):
    """Canonical event types supported by execution trace IR."""
    INITIAL_PROBLEM = "INITIAL_PROBLEM"
    FORMAL_CONTEXT = "FORMAL_CONTEXT"
    GOAL_STATE = "GOAL_STATE"
    SUBGOAL_STATE = "SUBGOAL_STATE"
    CONSTRAINTS = "CONSTRAINTS"
    SELECTED_ACTION = "SELECTED_ACTION"
    RULE_APPLICATION = "RULE_APPLICATION"
    TACTIC_APPLICATION = "TACTIC_APPLICATION"
    GENERATED_SUBGOALS = "GENERATED_SUBGOALS"
    SOLVER_ASSERTION = "SOLVER_ASSERTION"
    SAT_MODEL = "SAT_MODEL"
    UNSAT_CORE = "UNSAT_CORE"
    REWRITE = "REWRITE"
    LEMMA_INVOCATION = "LEMMA_INVOCATION"
    FAILURE = "FAILURE"
    BACKTRACK = "BACKTRACK"
    BRANCH = "BRANCH"
    TERMINAL_VERDICT = "TERMINAL_VERDICT"
    RESOURCE_OBSERVATION = "RESOURCE_OBSERVATION"


class EventOrigin(str, Enum):
    """Exact origin classification of execution trace events (WO-MATH-FORMAL-DISCOVERY-01A-R2)."""
    BACKEND_OBSERVED = "BACKEND_OBSERVED"
    CLIENT_DECLARED = "CLIENT_DECLARED"
    DERIVED_NORMALIZATION = "DERIVED_NORMALIZATION"
    SYNTHETIC_FIXTURE = "SYNTHETIC_FIXTURE"


@dataclass
class ExecutionTraceEvent:
    """A discrete, typed step within an execution trace."""
    event_id: str
    sequence: int
    event_type: TraceEventType
    backend_id: str
    backend_version: str
    parent_event_id: Optional[str]
    state_digest: str
    operation: str
    result_digest: str
    provenance: Dict[str, Any]
    logical_authority_class: str
    event_origin: EventOrigin = EventOrigin.BACKEND_OBSERVED
    evidence_ref: Optional[str] = None
    evidence_digest: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    typed_extension: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "event_id": self.event_id,
            "sequence": self.sequence,
            "event_type": self.event_type.value if isinstance(self.event_type, TraceEventType) else str(self.event_type),
            "backend_id": self.backend_id,
            "backend_version": self.backend_version,
            "parent_event_id": self.parent_event_id,
            "state_digest": self.state_digest,
            "operation": self.operation,
            "result_digest": self.result_digest,
            "provenance": self.provenance,
            "logical_authority_class": self.logical_authority_class,
            "event_origin": self.event_origin.value if isinstance(self.event_origin, EventOrigin) else str(self.event_origin),
        }
        if self.evidence_ref is not None:
            data["evidence_ref"] = self.evidence_ref
        if self.evidence_digest is not None:
            data["evidence_digest"] = self.evidence_digest
        if self.payload:
            data["payload"] = self.payload
        if self.typed_extension:
            data["typed_extension"] = self.typed_extension
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExecutionTraceEvent:
        event_type_str = data["event_type"]
        ev_type = TraceEventType(event_type_str) if event_type_str in TraceEventType.__members__ else TraceEventType(event_type_str)
        origin_str = data.get("event_origin", EventOrigin.BACKEND_OBSERVED.value)
        ev_origin = EventOrigin(origin_str) if origin_str in EventOrigin.__members__ else EventOrigin(origin_str)
        return cls(
            event_id=data["event_id"],
            sequence=data["sequence"],
            event_type=ev_type,
            backend_id=data["backend_id"],
            backend_version=data["backend_version"],
            parent_event_id=data.get("parent_event_id"),
            state_digest=data["state_digest"],
            operation=data["operation"],
            result_digest=data["result_digest"],
            provenance=data["provenance"],
            logical_authority_class=data["logical_authority_class"],
            event_origin=ev_origin,
            evidence_ref=data.get("evidence_ref"),
            evidence_digest=data.get("evidence_digest"),
            payload=data.get("payload", {}),
            typed_extension=data.get("typed_extension"),
        )
