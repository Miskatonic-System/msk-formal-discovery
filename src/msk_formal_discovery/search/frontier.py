"""Deterministic frontier search policy (Section 4)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from msk_formal_discovery.search.policy import (
    SearchAction,
    SearchPolicy,
    SearchPolicyKind,
    SearchState,
)


class DeterministicFrontierSearch(SearchPolicy):
    """Breadth-first / deterministic frontier expansion."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(SearchPolicyKind.DETERMINISTIC_FRONTIER, config)
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

    def select_next(self, candidates: List[SearchState]) -> Optional[SearchState]:
        if not candidates:
            return None
        # Deterministic FIFO order (by depth, then state_id)
        return sorted(candidates, key=lambda s: (s.depth, s.state_id))[0]
