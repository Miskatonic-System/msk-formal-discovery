"""Automated refactoring proposal generator (Section 9)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import jsonschema

from msk_formal_discovery.abstraction.candidate import AbstractionCandidate
from msk_formal_discovery.core.exceptions import RefactoringError


class RefactoringKind(str, Enum):
    """Kinds of refactoring transformations."""
    EXTRACTED_HELPER_LEMMA = "EXTRACTED_HELPER_LEMMA"
    COMMON_PROOF_COMBINATOR = "COMMON_PROOF_COMBINATOR"
    MODULE_EXTRACTION = "MODULE_EXTRACTION"
    API_SIGNATURE = "API_SIGNATURE"
    REPEATED_CONSTRAINT_HELPER = "REPEATED_CONSTRAINT_HELPER"
    REPEATED_TACTIC_SEQUENCE = "REPEATED_TACTIC_SEQUENCE"


@dataclass
class RefactoringProposal:
    """Non-authoritative proposal to refactor formal proof or library structure."""
    proposal_id: str
    candidate_id: str
    refactoring_kind: RefactoringKind
    before_state: Dict[str, Any]
    proposed_after_state: Dict[str, Any]
    semantic_obligations: List[str]
    affected_traces: List[str]
    expected_compression: float
    replay_plan: Dict[str, Any]
    canonical_library_mutated: bool = False
    authority: str = "NONE"

    def __post_init__(self) -> None:
        if self.canonical_library_mutated:
            raise RefactoringError("CANONICAL_LIBRARY_MUTATION_PROHIBITED: Refactoring proposal cannot mutate canonical libraries")
        if self.authority != "NONE":
            raise RefactoringError("REFACTORING_AUTHORITY_INVALID: Refactoring proposal authority must be NONE")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "miskatonic.refactoring-proposal.v0.1",
            "proposal_id": self.proposal_id,
            "candidate_id": self.candidate_id,
            "refactoring_kind": self.refactoring_kind.value,
            "before_state": self.before_state,
            "proposed_after_state": self.proposed_after_state,
            "semantic_obligations": self.semantic_obligations,
            "affected_traces": self.affected_traces,
            "expected_compression": self.expected_compression,
            "replay_plan": self.replay_plan,
            "canonical_library_mutated": self.canonical_library_mutated,
            "authority": self.authority,
        }

    def validate(self, schema_path: Optional[Path] = None) -> None:
        if self.canonical_library_mutated:
            raise RefactoringError("Refactoring cannot declare canonical_library_mutated=True")
        if schema_path and schema_path.exists():
            s = json.loads(schema_path.read_text(encoding="utf-8"))
            jsonschema.validate(self.to_dict(), s)


class RefactoringProposalGenerator:
    """Synthesizes non-authoritative refactoring proposals from qualified candidates."""

    @staticmethod
    def generate(
        candidate: AbstractionCandidate,
        refactoring_kind: RefactoringKind = RefactoringKind.EXTRACTED_HELPER_LEMMA,
    ) -> RefactoringProposal:
        before_text = f"// Inlined steps across traces: {candidate.discovery_set_trace_ids}"
        after_text = f"lemma {candidate.formal_specification.get('name', 'helper_lemma')} : {candidate.formal_specification.get('canonical_representation', '')}"

        return RefactoringProposal(
            proposal_id=f"prop-refactor-{candidate.candidate_id}",
            candidate_id=candidate.candidate_id,
            refactoring_kind=refactoring_kind,
            before_state={
                "representation": before_text,
                "token_or_ast_size": len(before_text.split()),
            },
            proposed_after_state={
                "representation": after_text,
                "token_or_ast_size": len(after_text.split()),
            },
            semantic_obligations=[
                f"Prove auxiliary lemma: {candidate.formal_specification.get('name')}",
                "Verify equivalence of inlined subtraces with auxiliary lemma application",
            ],
            affected_traces=candidate.discovery_set_trace_ids + candidate.qualification_trace_ids,
            expected_compression=candidate.held_out_evaluation.get("structural_compression_ratio", 1.2) if candidate.held_out_evaluation else 1.2,
            replay_plan={
                "replay_target_traces": candidate.qualification_trace_ids,
                "verification_backend": "lean4",
            },
            canonical_library_mutated=False,
            authority="NONE",
        )
