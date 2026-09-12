"""Repeated subtrace mining and pattern extraction (Section 6)."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from msk_formal_discovery.abstraction.anti_unification import (
    AntiUnificationResult,
    StructuralAntiUnifier,
)
from msk_formal_discovery.core.terms import Term
from msk_formal_discovery.trace.events import EventOrigin, ExecutionTraceEvent, TraceEventType
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
    branch_guards: List[str] = field(default_factory=list)
    discovery_origin: str = "EXECUTED_OBSERVED"
    trace_problem_digests: Dict[str, str] = field(default_factory=dict)
    trace_digests: Dict[str, str] = field(default_factory=dict)


class SubtraceMiner:
    """Discovers repeated subtrace patterns across execution traces (Section 6 & WO-MATH-FORMAL-DISCOVERY-01A-R3 Section 14)."""

    def __init__(
        self,
        min_length: int = 2,
        min_support: int = 2,
        synthetic_algorithm_test_mode: bool = False,
    ) -> None:
        self.min_length = min_length
        self.min_support = min_support
        self.synthetic_algorithm_test_mode = synthetic_algorithm_test_mode
        self.anti_unifier = StructuralAntiUnifier()

    def mine_traces(self, traces: Sequence[ExecutionTrace]) -> List[RecurringSubtracePattern]:
        """Mine successful traces for recurring subtrace patterns."""
        import json
        import hashlib

        # Map trace problem digests and trace content digests
        trace_pdigests: Dict[str, str] = {tr.trace_id: tr.problem_digest for tr in traces if tr.problem_digest}
        trace_digs: Dict[str, str] = {
            tr.trace_id: hashlib.sha256(json.dumps(tr.to_dict(), sort_keys=True).encode("utf-8")).hexdigest()
            for tr in traces
        }

        # Determine overall discovery origin
        if self.synthetic_algorithm_test_mode:
            discovery_origin = "SYNTHETIC_FIXTURE"
        elif all(tr.execution_origin in ("EXECUTED_NATIVE", "EXECUTED_CONTAINERIZED") for tr in traces):
            discovery_origin = "EXECUTED_OBSERVED"
        elif all(tr.execution_origin == "CERTIFIED_REPLAY" for tr in traces):
            discovery_origin = "CERTIFIED_REPLAY"
        else:
            discovery_origin = "SYNTHETIC_FIXTURE"

        # 1. Slicing successful paths
        sliced_traces: Dict[str, List[ExecutionTraceEvent]] = {}
        trace_branch_guards: Dict[str, List[str]] = defaultdict(list)

        for tr in traces:
            spine = TraceNormalizer.slice_successful_path(tr)
            # Collect trace-level branch guards
            for ev in spine:
                if ev.event_type == TraceEventType.BRANCH and (ev.payload.get("guard") or ev.payload.get("branch_guard") or ev.payload.get("branch_condition")):
                    g = ev.payload.get("guard") or ev.payload.get("branch_guard") or ev.payload.get("branch_condition")
                    trace_branch_guards[tr.trace_id].append(str(g))
                elif ev.payload.get("branch_guard") or ev.payload.get("branch_condition") or ev.payload.get("guard"):
                    g = ev.payload.get("branch_guard") or ev.payload.get("branch_condition") or ev.payload.get("guard")
                    trace_branch_guards[tr.trace_id].append(str(g))

            # Section 14: Discovery Event Eligibility Rule
            # In production, only BACKEND_OBSERVED and DERIVED_NORMALIZATION are eligible.
            # CLIENT_DECLARED and SYNTHETIC_FIXTURE are excluded unless synthetic_algorithm_test_mode is active.
            if self.synthetic_algorithm_test_mode:
                allowed_origins = {EventOrigin.BACKEND_OBSERVED, EventOrigin.DERIVED_NORMALIZATION, EventOrigin.SYNTHETIC_FIXTURE}
            else:
                allowed_origins = {EventOrigin.BACKEND_OBSERVED, EventOrigin.DERIVED_NORMALIZATION}

            tactical_events = [
                e for e in spine
                if e.event_type not in (
                    TraceEventType.INITIAL_PROBLEM,
                    TraceEventType.TERMINAL_VERDICT,
                    TraceEventType.RESOURCE_OBSERVATION,
                )
                and e.event_origin in allowed_origins
            ]
            if tactical_events:
                sliced_traces[tr.trace_id] = tactical_events

        if len(sliced_traces) < self.min_support:
            return []

        # 2. Extract n-gram subtrace sequences
        patterns_map: Dict[Tuple[str, ...], List[Tuple[str, int, Term, List[str]]]] = defaultdict(list)

        for trace_id, events in sliced_traces.items():
            ops = [e.operation for e in events]
            n = len(ops)
            for length in range(self.min_length, min(n + 1, self.min_length + 4)):
                for start in range(n - length + 1):
                    sub_ops = tuple(ops[start : start + length])
                    sub_events = events[start : start + length]
                    expr_terms = []
                    sub_guards = list(trace_branch_guards.get(trace_id, []))
                    for ev in sub_events:
                        g = ev.payload.get("guard") or ev.payload.get("branch_guard") or ev.payload.get("branch_condition")
                        if g and str(g) not in sub_guards:
                            sub_guards.append(str(g))
                        val = (
                            ev.payload.get("expression")
                            or ev.payload.get("tactic")
                            or ev.payload.get("assertion")
                            or ev.operation
                        )
                        try:
                            term_obj = Term.parse(str(val))
                        except Exception:
                            from msk_formal_discovery.core.terms import Const
                            term_obj = Const(str(val))
                        expr_terms.append(term_obj)

                    from msk_formal_discovery.core.terms import App
                    composite_term = App("seq", tuple(expr_terms))
                    patterns_map[sub_ops].append((trace_id, start, composite_term, sub_guards))

        # 3. Filter by min_support (must appear in distinct traces)
        discovered: List[RecurringSubtracePattern] = []
        pat_counter = 0

        for sub_ops, occurrences in patterns_map.items():
            distinct_traces = {occ[0] for occ in occurrences}
            if len(distinct_traces) >= self.min_support:
                pat_counter += 1
                trace_term_map: Dict[str, Term] = {}
                occ_list: List[Tuple[str, int]] = []
                pat_guards: List[str] = []
                for tid, s_idx, t_obj, g_list in occurrences:
                    occ_list.append((tid, s_idx))
                    if tid not in trace_term_map:
                        trace_term_map[tid] = t_obj
                    for g in g_list:
                        if g not in pat_guards:
                            pat_guards.append(g)

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
                    branch_guards=pat_guards,
                    discovery_origin=discovery_origin,
                    trace_problem_digests=trace_pdigests,
                    trace_digests=trace_digs,
                )
                discovered.append(pattern)

        # Sort by frequency and length descending
        discovered.sort(key=lambda p: (p.frequency, len(p.operations)), reverse=True)
        return discovered
