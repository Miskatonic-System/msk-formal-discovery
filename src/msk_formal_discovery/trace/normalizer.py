"""Trace normalization and successful-trace slicing (Section 6)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from msk_formal_discovery.trace.events import ExecutionTraceEvent, TraceEventType
from msk_formal_discovery.trace.ir import ExecutionTrace


@dataclass(frozen=True)
class NormalizedStep:
    """A normalized, deterministic operation step."""
    event_type: str
    operation: str
    normalized_expression: str
    depth: int


class TraceNormalizer:
    """Normalizes execution traces for pattern mining and anti-unification."""

    @staticmethod
    def slice_successful_path(trace: ExecutionTrace) -> List[ExecutionTraceEvent]:
        """Filter trace events to only those contributing to the successful goal resolution.
        
        Backtracks and failed branches are eliminated, leaving the direct proof / derivation spine.
        """
        # If trace is empty or failed, return empty
        if trace.terminal_verdict not in (
            "PROVEN",
            "UNSAT_REFUTED",
            "REFUTED_SAT",
            "SUCCESS",
            "SYNTHETIC_SUCCESS",
            "SYNTHETIC_SAT",
            "SYNTHETIC_UNSAT",
        ):
            return []

        # Start from terminal event and trace backwards along parent_event_id links
        events_by_id = {e.event_id: e for e in trace.events}
        if not trace.events:
            return []

        terminal_event = trace.events[-1]
        spine: List[ExecutionTraceEvent] = []
        curr: Optional[ExecutionTraceEvent] = terminal_event

        visited = set()
        while curr and curr.event_id not in visited:
            visited.add(curr.event_id)
            spine.append(curr)
            if curr.parent_event_id and curr.parent_event_id in events_by_id:
                curr = events_by_id[curr.parent_event_id]
            else:
                break

        # Reverse spine to restore forward order
        spine.reverse()
        # Filter out explicit failure and backtrack events
        filtered = [
            e for e in spine
            if e.event_type not in (TraceEventType.FAILURE, TraceEventType.BACKTRACK)
        ]
        return filtered

    @classmethod
    def normalize_step_sequence(cls, events: Sequence[ExecutionTraceEvent]) -> List[NormalizedStep]:
        """Convert events to a sequence of normalized steps suitable for subtrace mining."""
        steps: List[NormalizedStep] = []
        depth = 0
        for ev in events:
            if ev.event_type in (TraceEventType.BRANCH, TraceEventType.GENERATED_SUBGOALS):
                depth += 1
            op = ev.operation
            # Extract expression from payload
            expr = (
                ev.payload.get("expression")
                or ev.payload.get("tactic")
                or ev.payload.get("assertion")
                or ev.payload.get("rule")
                or ev.operation
            )
            norm_expr = cls.alpha_normalize(str(expr))
            steps.append(
                NormalizedStep(
                    event_type=ev.event_type.value,
                    operation=op,
                    normalized_expression=norm_expr,
                    depth=depth,
                )
            )
        return steps

    @staticmethod
    def alpha_normalize(text: str) -> str:
        """Deterministically re-index local identifiers while preserving structure."""
        # Simple whitespace collapse
        text = re.sub(r"\s+", " ", text.strip())
        return text
