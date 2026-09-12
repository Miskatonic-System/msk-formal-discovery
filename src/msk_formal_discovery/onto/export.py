"""ONTO evaluation evidence exporter (WO-MATH-FORMAL-DISCOVERY-01A-R1)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Union

from msk_formal_discovery.abstraction.candidate import AbstractionCandidate


@dataclass
class OntoEvaluationPackage:
    """Export package for Miskatonic-System/msk-onto structural evaluation.
    
    Contains observed evidence states, not invented conclusions (Section 16).
    """
    package_id: str
    candidate_id: str
    recurrence_count: int
    representation_invariance: Union[bool, str]
    cross_search_policy_recurrence: Union[bool, str]
    cross_formal_system_recurrence: Union[bool, str]
    functional_search_benefit: Union[bool, str]
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
    """Exports abstraction candidate evidence for external ONTO evaluation without pre-answering research questions."""

    @staticmethod
    def export(
        candidate: AbstractionCandidate,
        representation_evidence: Optional[bool] = None,
        cross_policy_evidence: Optional[bool] = None,
        cross_formal_system_evidence: Optional[bool] = None,
        functional_evidence: Optional[bool] = None,
    ) -> OntoEvaluationPackage:
        fp = hashlib.sha256(
            json.dumps(candidate.formal_specification, sort_keys=True).encode("utf-8")
        ).hexdigest()

        # Fail-closed evidence state: do not invent positive answers
        rep_inv: Union[bool, str] = (
            representation_evidence if representation_evidence is not None else "UNKNOWN"
        )
        cross_pol: Union[bool, str] = (
            cross_policy_evidence if cross_policy_evidence is not None else "UNKNOWN"
        )
        cross_formal: Union[bool, str] = (
            cross_formal_system_evidence if cross_formal_system_evidence is not None else "UNKNOWN"
        )

        if functional_evidence is not None:
            func_benefit: Union[bool, str] = functional_evidence
        else:
            func_benefit = "UNKNOWN"
            if candidate.held_out_evaluation:
                mode = candidate.held_out_evaluation.get("replay_mode")
                if mode == "EXECUTED_HELD_OUT_REPLAY":
                    # Real executed benefit
                    comp = candidate.held_out_evaluation.get("structural_compression_ratio", 1.0)
                    eval_red = candidate.held_out_evaluation.get("candidate_evaluation_reduction", 0.0)
                    branch_red = candidate.held_out_evaluation.get("proof_branch_reduction", 0.0)
                    func_benefit = (comp > 1.0 or eval_red > 0.0 or branch_red > 0.0)
                elif mode == "SYNTHETIC_REPLAY_FIXTURE":
                    func_benefit = "UNTESTED"

        return OntoEvaluationPackage(
            package_id=f"onto-eval-{candidate.candidate_id}",
            candidate_id=candidate.candidate_id,
            recurrence_count=len(candidate.discovery_set_trace_ids),
            representation_invariance=rep_inv,
            cross_search_policy_recurrence=cross_pol,
            cross_formal_system_recurrence=cross_formal,
            functional_search_benefit=func_benefit,
            source_traces=candidate.discovery_set_trace_ids,
            structural_fingerprint=fp,
            authority="NONE",
        )
