"""Abstraction candidate prospective value metrics (Section 10)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class AbstractionValueReport:
    """Prospective evaluation report for an abstraction candidate.
    
    Invariant: A shorter proof alone is insufficient. Multi-metric benefit required.
    """
    candidate_id: str
    supporting_trace_count: int
    structural_compression_ratio: float
    proof_branch_reduction: float
    candidate_evaluation_reduction: float
    held_out_success_rate_delta: float
    wall_time_delta_pct: float
    portability_across_instances: float
    portability_across_formal_systems: float
    human_inspectable_representation_size: int
    is_held_out_disjoint_from_discovery: bool = True
    replay_mode: str = "SYNTHETIC_REPLAY_FIXTURE"

    def is_qualified_for_promotion(
        self,
        min_support: int = 2,
        min_compression: float = 1.05,
        min_branch_reduction: float = 0.0,
    ) -> bool:
        """Determine if candidate qualifies for non-authoritative promotion proposal.
        
        Requires:
        - at least min_support traces
        - real executed paired replay (NOT synthetic replay)
        - measurable compression or branch reduction
        - non-negative held-out success delta
        """
        # Synthetic replay CANNOT qualify candidates per Section 11 & 14
        if self.replay_mode != "EXECUTED_HELD_OUT_REPLAY":
            return False

        if self.supporting_trace_count < min_support:
            return False
        if self.held_out_success_rate_delta < 0.0:
            return False
        # Cannot qualify solely on proof length without search or compression benefit
        has_benefit = (
            self.structural_compression_ratio >= min_compression
            or self.proof_branch_reduction > min_branch_reduction
            or self.candidate_evaluation_reduction > 0.0
        )
        return has_benefit

    def to_dict(self) -> Dict[str, Any]:
        return {
            "replay_mode": self.replay_mode,
            "is_held_out_disjoint_from_discovery": self.is_held_out_disjoint_from_discovery,
            "supporting_trace_count": self.supporting_trace_count,
            "structural_compression_ratio": round(self.structural_compression_ratio, 4),
            "proof_branch_reduction": round(self.proof_branch_reduction, 4),
            "candidate_evaluation_reduction": round(self.candidate_evaluation_reduction, 4),
            "held_out_success_rate_delta": round(self.held_out_success_rate_delta, 4),
            "wall_time_delta_pct": round(self.wall_time_delta_pct, 4),
            "portability_across_instances": round(self.portability_across_instances, 4),
            "portability_across_formal_systems": round(self.portability_across_formal_systems, 4),
            "human_inspectable_representation_size": self.human_inspectable_representation_size,
        }


def compute_compression_ratio(before_ast_size: int, after_ast_size: int) -> float:
    """Compute structural compression ratio: before / max(1, after)."""
    if after_ast_size <= 0:
        return 1.0
    return before_ast_size / after_ast_size
