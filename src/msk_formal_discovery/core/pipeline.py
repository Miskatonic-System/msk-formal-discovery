"""Core discovery pipeline definition and stage sequence freezing (WO-MATH-FORMAL-DISCOVERY-01A)."""
from __future__ import annotations

from enum import Enum
from typing import List, Tuple

class PipelineStage(str, Enum):
    """Canonical frozen stages of the formal discovery architecture."""
    SOURCE_CORPUS = "SOURCE_CORPUS"
    SOURCE_GRAPH = "SOURCE_GRAPH"
    BLUEPRINT_OR_PROBLEM = "BLUEPRINT_OR_PROBLEM"
    SEARCH = "SEARCH"
    REASONING_BACKEND = "REASONING_BACKEND"
    EXECUTION_TRACE = "EXECUTION_TRACE"
    ABSTRACTION_MINING = "ABSTRACTION_MINING"
    CANDIDATE_LIBRARY = "CANDIDATE_LIBRARY"
    REPLAY = "REPLAY"
    QUALIFICATION = "QUALIFICATION"


CANONICAL_PIPELINE_SEQUENCE: Tuple[PipelineStage, ...] = (
    PipelineStage.SOURCE_CORPUS,
    PipelineStage.SOURCE_GRAPH,
    PipelineStage.BLUEPRINT_OR_PROBLEM,
    PipelineStage.SEARCH,
    PipelineStage.REASONING_BACKEND,
    PipelineStage.EXECUTION_TRACE,
    PipelineStage.ABSTRACTION_MINING,
    PipelineStage.CANDIDATE_LIBRARY,
    PipelineStage.REPLAY,
    PipelineStage.QUALIFICATION,
)


def verify_pipeline_sequence(stages: List[PipelineStage]) -> bool:
    """Verify that a sequence of pipeline stages preserves the canonical progression."""
    if not stages:
        return False
    expected_indices = [CANONICAL_PIPELINE_SEQUENCE.index(st) for st in stages]
    return expected_indices == sorted(expected_indices)
