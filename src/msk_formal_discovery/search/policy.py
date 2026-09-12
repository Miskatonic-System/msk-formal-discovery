"""Search policy interfaces and firewalls (Sections 4 & 5)."""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SearchPolicyKind(str, Enum):
    """Canonical search policies."""
    DETERMINISTIC_FRONTIER = "DETERMINISTIC_FRONTIER"
    BOUNDED_BEAM_SEARCH = "BOUNDED_BEAM_SEARCH"
    A_STAR = "A_STAR"
    MCTS = "MCTS"
    EVOLUTIONARY = "EVOLUTIONARY"
    NOVELTY_SEARCH = "NOVELTY_SEARCH"
    LEARNED_HEURISTIC = "LEARNED_HEURISTIC"
    NEURAL_PREMISE_GUIDANCE = "NEURAL_PREMISE_GUIDANCE"
    RL = "RL"
    HYBRID_LATENT = "HYBRID_LATENT"


@dataclass
class SearchState:
    """State node within the search space."""
    state_id: str
    goal: str
    depth: int
    parent_id: Optional[str] = None
    path_cost: float = 0.0
    heuristic_value: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)
    is_terminal: bool = False
    is_solved: bool = False


@dataclass
class SearchAction:
    """An action / rule / tactic proposed by a search policy."""
    action_id: str
    operation: str
    payload: Dict[str, Any] = field(default_factory=dict)
    prior_probability: float = 1.0
    estimated_cost: float = 1.0


class SearchPolicy(abc.ABC):
    """Provider-neutral search policy interface."""

    def __init__(self, policy_kind: SearchPolicyKind, config: Optional[Dict[str, Any]] = None) -> None:
        self.policy_kind = policy_kind
        self.config = config or {}

    @property
    def authority(self) -> str:
        """Search policy MUST NOT grant proof authority."""
        return "NONE"

    @abc.abstractmethod
    def propose_actions(self, state: SearchState) -> List[SearchAction]:
        """Propose exploration actions for the given state.
        
        Search policy MAY propose exploration; it MUST NOT grant proof authority.
        """

    @abc.abstractmethod
    def select_next(self, candidates: List[SearchState]) -> Optional[SearchState]:
        """Select the next state to explore according to the policy."""


import re
from msk_formal_discovery.core.exceptions import ReceiptValidationError

HEX_64_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass
class SearchRun:
    """Record of a search execution run."""
    run_id: str
    problem_id: str
    search_policy: SearchPolicyKind
    policy_configuration: Dict[str, Any]
    problem_digest: str = ""
    nodes_expanded: int = 0
    nodes_evaluated: int = 0
    max_depth_reached: int = 0
    branching_factor_effective: float = 1.0
    total_wall_time_ms: float = 0.0
    terminal_status: str = "EXHAUSTED"
    resulting_trace_id: Optional[str] = None
    corpus_guidance: Optional[Dict[str, Any]] = None
    execution_trace_refs: List[str] = field(default_factory=list)
    execution_trace_digests: List[str] = field(default_factory=list)
    search_execution_receipt: Optional[Dict[str, Any]] = None
    replay_mode: Optional[str] = None

    def __post_init__(self) -> None:
        if self.problem_digest and not HEX_64_PATTERN.match(self.problem_digest):
            raise ValueError(
                f"INVALID_PROBLEM_DIGEST: problem_digest '{self.problem_digest}' is not a 64-char lowercase hex SHA-256"
            )
        if self.replay_mode == "EXECUTED_SEARCH_RUN":
            if not self.search_execution_receipt:
                raise ReceiptValidationError(
                    "EXECUTED_SEARCH_RUN_REQUIRES_RECEIPT: SearchRun claiming EXECUTED_SEARCH_RUN requires valid search_execution_receipt"
                )
            if self.execution_trace_refs or self.execution_trace_digests:
                if len(self.execution_trace_refs) != len(self.execution_trace_digests):
                    raise ReceiptValidationError(
                        f"TRACE_REF_DIGEST_COUNT_MISMATCH: {len(self.execution_trace_refs)} refs != {len(self.execution_trace_digests)} digests"
                    )

    @property
    def authority(self) -> str:
        return "NONE"

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "schema_version": "miskatonic.search-run.v0.1",
            "run_id": self.run_id,
            "problem_id": self.problem_id,
            "search_policy": self.search_policy.value,
            "policy_configuration": self.policy_configuration,
            "corpus_guidance": self.corpus_guidance,
            "resulting_trace_id": self.resulting_trace_id,
            "metrics": {
                "nodes_expanded": self.nodes_expanded,
                "nodes_evaluated": self.nodes_evaluated,
                "max_depth_reached": self.max_depth_reached,
                "branching_factor_effective": self.branching_factor_effective,
                "total_wall_time_ms": self.total_wall_time_ms,
            },
            "terminal_status": self.terminal_status,
            "authority": self.authority,
        }
        if self.problem_digest:
            d["problem_digest"] = self.problem_digest
        if self.replay_mode:
            d["replay_mode"] = self.replay_mode
        if self.search_execution_receipt is not None:
            d["search_execution_receipt"] = self.search_execution_receipt
        if self.execution_trace_refs:
            d["execution_trace_refs"] = list(self.execution_trace_refs)
        if self.execution_trace_digests:
            d["execution_trace_digests"] = list(self.execution_trace_digests)
        return d


def is_successful_terminal(terminal_status: str) -> bool:
    """Canonical predicate for successful search run terminal status (WO-MATH-FORMAL-DISCOVERY-01A-R4 Section 8)."""
    return terminal_status in ("SUCCESS", "SOLVED")

