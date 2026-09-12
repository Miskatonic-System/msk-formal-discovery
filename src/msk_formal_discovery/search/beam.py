"""Bounded beam search policy (Section 4)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from msk_formal_discovery.search.policy import (
    SearchAction,
    SearchPolicy,
    SearchPolicyKind,
    SearchState,
)


class BoundedBeamSearch(SearchPolicy):
    """Bounded beam search maintaining top-k candidate states."""

    def __init__(self, beam_width: int = 5, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        cfg["beam_width"] = beam_width
        super().__init__(SearchPolicyKind.BOUNDED_BEAM_SEARCH, cfg)
        self.beam_width = beam_width
        self.rules = self.config.get("available_rules", ["rule_0", "rule_1", "rule_2"])

    def propose_actions(self, state: SearchState) -> List[SearchAction]:
        actions = []
        for r in self.rules:
            actions.append(
                SearchAction(
                    action_id=f"act-{state.state_id}-{r}",
                    operation=r,
                    payload={"rule": r, "target_goal": state.goal},
                    prior_probability=1.0 / len(self.rules),
                    estimated_cost=1.0,
                )
            )
        return actions

    def prune_to_beam(self, candidates: List[SearchState]) -> List[SearchState]:
        """Prune candidates to top beam_width elements according to heuristic_value."""
        sorted_candidates = sorted(candidates, key=lambda s: s.heuristic_value, reverse=True)
        return sorted_candidates[: self.beam_width]

    def select_next(self, candidates: List[SearchState]) -> Optional[SearchState]:
        if not candidates:
            return None
        beam = self.prune_to_beam(candidates)
        return beam[0] if beam else None
