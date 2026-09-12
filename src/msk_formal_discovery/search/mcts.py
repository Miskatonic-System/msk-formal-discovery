"""Monte Carlo Tree Search (MCTS) policy and corpus-guidance interface (Section 5)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from msk_formal_discovery.search.policy import (
    SearchAction,
    SearchPolicy,
    SearchPolicyKind,
    SearchState,
)


@dataclass
class MCTSNode:
    """MCTS search tree node."""
    node_id: str
    state: SearchState
    parent: Optional[MCTSNode] = None
    action_from_parent: Optional[SearchAction] = None
    children: List[MCTSNode] = field(default_factory=list)
    visit_count: int = 0
    total_value: float = 0.0
    prior: float = 1.0

    @property
    def mean_value(self) -> float:
        return self.total_value / self.visit_count if self.visit_count > 0 else 0.0

    def uct_score(self, c_param: float = 1.414) -> float:
        if not self.parent or self.parent.visit_count == 0:
            return self.mean_value
        exploration = c_param * self.prior * math.sqrt(math.log(self.parent.visit_count) / (1 + self.visit_count))
        return self.mean_value + exploration


class MCTSSearch(SearchPolicy):
    """Monte Carlo Tree Search with optional corpus guidance.
    
    Authority Invariants:
    - CORPUS_GUIDED_MCTS != CORPUS_AUTHORITY
    - MCTS score is exploration guidance, NOT proof truth.
    """

    def __init__(
        self,
        c_param: float = 1.414,
        max_rollouts: int = 50,
        corpus_guidance: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        cfg = config or {}
        cfg["c_param"] = c_param
        cfg["max_rollouts"] = max_rollouts
        super().__init__(SearchPolicyKind.MCTS, cfg)
        self.c_param = c_param
        self.max_rollouts = max_rollouts
        self.corpus_guidance = corpus_guidance or {}
        self.rules = self.config.get("available_rules", ["rule_0", "rule_1", "rule_2"])

    def propose_actions(self, state: SearchState) -> List[SearchAction]:
        actions = []
        priors = self.corpus_guidance.get("prior_probabilities", {})
        for r in self.rules:
            prior = priors.get(r, 1.0 / len(self.rules))
            actions.append(
                SearchAction(
                    action_id=f"act-mcts-{state.state_id}-{r}",
                    operation=r,
                    payload={"rule": r, "target_goal": state.goal},
                    prior_probability=prior,
                    estimated_cost=1.0,
                )
            )
        return actions

    def select_next(self, candidates: List[SearchState]) -> Optional[SearchState]:
        if not candidates:
            return None
        # In MCTS, the best candidate is selected based on mean value / UCT
        return max(candidates, key=lambda s: (s.heuristic_value, s.state_id))

    def run_mcts_cycle(self, root: MCTSNode) -> MCTSNode:
        """Execute standard 4-stage MCTS cycle: Selection, Expansion, Simulation, Backpropagation."""
        for _ in range(self.max_rollouts):
            # 1. Selection
            leaf = self._select_leaf(root)

            # 2. Expansion
            if not leaf.state.is_terminal and not leaf.children:
                self._expand(leaf)
                if leaf.children:
                    leaf = leaf.children[0]

            # 3. Simulation
            reward = self._simulate(leaf)

            # 4. Backpropagation
            self._backpropagate(leaf, reward)

        # Return child with highest visit count
        if root.children:
            return max(root.children, key=lambda c: (c.visit_count, c.node_id))
        return root

    def _select_leaf(self, node: MCTSNode) -> MCTSNode:
        curr = node
        while curr.children:
            curr = max(curr.children, key=lambda c: c.uct_score(self.c_param))
        return curr

    def _expand(self, node: MCTSNode) -> None:
        actions = self.propose_actions(node.state)
        for act in actions:
            child_state = SearchState(
                state_id=f"{node.state.state_id}_{act.operation}",
                goal=f"{node.state.goal}_{act.operation}",
                depth=node.state.depth + 1,
                parent_id=node.state.state_id,
                path_cost=node.state.path_cost + act.estimated_cost,
                heuristic_value=act.prior_probability,
            )
            child_node = MCTSNode(
                node_id=f"node_{child_state.state_id}",
                state=child_state,
                parent=node,
                action_from_parent=act,
                prior=act.prior_probability,
            )
            node.children.append(child_node)

    def _simulate(self, node: MCTSNode) -> float:
        # Default rollout evaluation: prior-weighted simulation score
        return min(1.0, max(0.0, node.prior))

    def _backpropagate(self, node: Optional[MCTSNode], reward: float) -> None:
        curr = node
        while curr is not None:
            curr.visit_count += 1
            curr.total_value += reward
            curr = curr.parent
