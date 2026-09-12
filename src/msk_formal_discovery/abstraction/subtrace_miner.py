"""Repeated subtrace mining and pattern extraction (Section 6)."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from msk_formal_discovery.abstraction.anti_unification import (
    AntiUnificationResult,
    StructuralAntiUnifier,
)
from msk_formal_discovery.core.terms import Term
from msk_formal_discovery.trace.events import ExecutionTraceEvent, TraceEventType
from msk_formal_discovery.trace.ir import ExecutionTrace
from msk_formal_discovery.trace.normalizer import TraceNormalizer


@dataclass
class RecurringSubtracePattern:
    """A discovered pattern occurring across multiple traces."""
    pattern_id: str
    operations: Tuple[str, ...]
    occurrences: List[Tuple[str, int]]  # (trace_id, start_index)
    frequency: int
    extracted_terms: Dict[str, Term]  # trace_id -> Term
    anti_unification_result: Optional[AntiUnificationResult] = None


class SubtraceMiner:
    """Discovers repeated subtrace patterns across execution traces."""

    def __init__(self, min_length: int = 2, min_support: int = 2) -> None:
        self.min_length = min_length
        self.min_support = min_support
        self.anti_unifier = StructuralAntiUnifier()

    def mine_traces(self, traces: Sequence[ExecutionTrace]) -> List[RecurringSubtracePattern]:
        """Mine successful traces for recurring subtrace patterns."""
        # 1. Slicing successful paths
        sliced_traces: Dict[str, List[ExecutionTraceEvent]] = {}
        for tr in traces:
            spine = TraceNormalizer.slice_successful_path(tr)
            tactical_events = [
                e for e in spine
                if e.event_type not in (
                    TraceEventType.INITIAL_PROBLEM,
                    TraceEventType.TERMINAL_VERDICT,
                    TraceEventType.RESOURCE_OBSERVATION,
                )
            ]
            if tactical_events:
                sliced_traces[tr.trace_id] = tactical_events

        if len(sliced_traces) < self.min_support:
            return []

        # 2. Extract n-gram subtrace sequences
        # Map: operations_tuple -> list of (trace_id, start_idx, extracted_term)
        patterns_map: Dict[Tuple[str, ...], List[Tuple[str, int, Term]]] = defaultdict(list)

        for trace_id, events in sliced_traces.items():
            ops = [e.operation for e in events]
            n = len(ops)
            for length in range(self.min_length, min(n + 1, self.min_length + 4)):
                for start in range(n - length + 1):
                    sub_ops = tuple(ops[start : start + length])
                    # Construct composite term representation for this subtrace
                    sub_events = events[start : start + length]
                    expr_terms = []
                    for ev in sub_events:
                        val = (
                            ev.payload.get("expression")
                            or ev.payload.get("tactic")
                            or ev.payload.get("assertion")
                            or ev.operation
                        )
                        try:
                            term_obj = Term.parse(str(val))
                        except Exception:
                            # Fallback to atomic Const
                            from msk_formal_discovery.core.terms import Const
                            term_obj = Const(str(val))
                        expr_terms.append(term_obj)

                    # Wrap in composite sequence application
                    from msk_formal_discovery.core.terms import App
                    composite_term = App("seq", tuple(expr_terms))
                    patterns_map[sub_ops].append((trace_id, start, composite_term))

        # 3. Filter by min_support (must appear in distinct traces)
        discovered: List[RecurringSubtracePattern] = []
        pat_counter = 0

        for sub_ops, occurrences in patterns_map.items():
            distinct_traces = {occ[0] for occ in occurrences}
            if len(distinct_traces) >= self.min_support:
                pat_counter += 1
                # Gather one representative term per distinct trace
                trace_term_map: Dict[str, Term] = {}
                occ_list: List[Tuple[str, int]] = []
                for tid, s_idx, t_obj in occurrences:
                    occ_list.append((tid, s_idx))
                    if tid not in trace_term_map:
                        trace_term_map[tid] = t_obj

                # Anti-unify terms across participating traces
                au_res: Optional[AntiUnificationResult] = None
                try:
                    pairs = list(trace_term_map.items())
                    au_res = self.anti_unifier.anti_unify(pairs)
                except Exception:
                    au_res = None

                pattern = RecurringSubtracePattern(
                    pattern_id=f"pattern-{pat_counter:03d}",
                    operations=sub_ops,
                    occurrences=occ_list,
                    frequency=len(distinct_traces),
                    extracted_terms=trace_term_map,
                    anti_unification_result=au_res,
                )
                discovered.append(pattern)

        # Sort by frequency and length descending
        discovered.sort(key=lambda p: (p.frequency, len(p.operations)), reverse=True)
        return discovered
