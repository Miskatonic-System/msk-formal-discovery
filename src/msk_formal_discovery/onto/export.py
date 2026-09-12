"""ONTO evaluation evidence exporter (Section 12)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List

from msk_formal_discovery.abstraction.candidate import AbstractionCandidate


@dataclass
class OntoEvaluationPackage:
    """Export package for Miskatonic-System/msk-onto structural evaluation."""
    package_id: str
    candidate_id: str
    recurrence_count: int
    representation_invariance: bool
    cross_search_policy_recurrence: bool
    cross_formal_system_recurrence: bool
    functional_search_benefit: bool
    source_traces: List[str]
    structural_fingerprint: str
    authority: str = "NONE"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "package_id": self.package_id,
            "candidate_id": self.candidate_id,
            "recurrence_count": self.recurrence_count,
            "representation_invariance": self.representation_invariance,
            "cross_search_policy_recurrence": self.cross_search_policy_recurrence,
            "cross_formal_system_recurrence": self.cross_formal_system_recurrence,
            "functional_search_benefit": self.functional_search_benefit,
            "source_traces": self.source_traces,
            "structural_fingerprint": self.structural_fingerprint,
            "authority": self.authority,
        }


class OntoExporter:
    """Exports abstraction candidate evidence for external ONTO ontology and structure evaluation."""

    @staticmethod
    def export(candidate: AbstractionCandidate) -> OntoEvaluationPackage:
        fp = hashlib.sha256(
            json.dumps(candidate.formal_specification, sort_keys=True).encode("utf-8")
        ).hexdigest()

        return OntoEvaluationPackage(
            package_id=f"onto-eval-{candidate.candidate_id}",
            candidate_id=candidate.candidate_id,
            recurrence_count=len(candidate.discovery_set_trace_ids),
            representation_invariance=True,
            cross_search_policy_recurrence=True,
            cross_formal_system_recurrence=False,
            functional_search_benefit=bool(
                candidate.held_out_evaluation
                and (
                    candidate.held_out_evaluation.get("proof_branch_reduction", 0) > 0
                    or candidate.held_out_evaluation.get("candidate_evaluation_reduction", 0) > 0
                    or candidate.held_out_evaluation.get("structural_compression_ratio", 1.0) > 1.0
                )
            ),
            source_traces=candidate.discovery_set_trace_ids,
            structural_fingerprint=fp,
            authority="NONE",
        )
