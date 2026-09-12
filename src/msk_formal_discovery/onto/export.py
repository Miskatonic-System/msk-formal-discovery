"""ONTO evaluation evidence exporter (WO-MATH-FORMAL-DISCOVERY-01A-R2)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from msk_formal_discovery.abstraction.candidate import AbstractionCandidate


@dataclass(frozen=True)
class OntoEvidenceRef:
    """Evidence reference binding an artifact to an ONTO dimension (Section 31)."""
    evidence_kind: str
    artifact_ref: str
    artifact_digest: str
    evidence_status: str  # "SUPPORTED", "NOT_SUPPORTED", "UNTESTED", "UNKNOWN"
    source_experimental_units: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_kind": self.evidence_kind,
            "artifact_ref": self.artifact_ref,
            "artifact_digest": self.artifact_digest,
            "evidence_status": self.evidence_status,
            "source_experimental_units": self.source_experimental_units,
        }


@dataclass
class OntoEvaluationPackage:
    """Export package for Miskatonic-System/msk-onto structural evaluation.
    
    Contains observed evidence states, not invented conclusions (Sections 31-33).
    """
    package_id: str
    candidate_id: str
    recurrence_count: int
    representation_invariance: str
    cross_search_policy_recurrence: str
    cross_formal_system_recurrence: str
    functional_search_benefit: str
    source_traces: List[str]
    structural_fingerprint: str
    evidence_refs: List[OntoEvidenceRef] = field(default_factory=list)
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
            "evidence_refs": [ref.to_dict() for ref in self.evidence_refs],
            "authority": self.authority,
        }


class OntoExporter:
    """Exports abstraction candidate evidence for external ONTO evaluation without pre-answering research questions."""

    @staticmethod
    def export(
        candidate: AbstractionCandidate,
        representation_evidence: Optional[Union[OntoEvidenceRef, str]] = None,
        cross_policy_evidence: Optional[Union[OntoEvidenceRef, str]] = None,
        cross_formal_system_evidence: Optional[Union[OntoEvidenceRef, str]] = None,
        functional_evidence: Optional[Union[OntoEvidenceRef, str]] = None,
    ) -> OntoEvaluationPackage:
        # Reject naked booleans per Section 31
        for name, val in [
            ("representation_evidence", representation_evidence),
            ("cross_policy_evidence", cross_policy_evidence),
            ("cross_formal_system_evidence", cross_formal_system_evidence),
            ("functional_evidence", functional_evidence),
        ]:
            if isinstance(val, bool):
                raise ValueError(
                    f"NAKED_BOOLEAN_PROHIBITED: Naked boolean '{name}={val}' is prohibited; provide OntoEvidenceRef or let exporter derive from replay evidence"
                )
            if isinstance(val, str) and val in ("SUPPORTED", "TRUE", "POSITIVE", "CONFIRMED"):
                raise ValueError(
                    f"NAKED_BOOLEAN_PROHIBITED: Naked positive claim '{name}={val}' is prohibited without OntoEvidenceRef"
                )

        fp = hashlib.sha256(
            json.dumps(candidate.formal_specification, sort_keys=True).encode("utf-8")
        ).hexdigest()

        evidence_refs: List[OntoEvidenceRef] = []

        if isinstance(representation_evidence, OntoEvidenceRef):
            evidence_refs.append(representation_evidence)
            rep_inv = representation_evidence.evidence_status
        else:
            rep_inv = representation_evidence or "UNKNOWN"

        if isinstance(cross_policy_evidence, OntoEvidenceRef):
            evidence_refs.append(cross_policy_evidence)
            cross_pol = cross_policy_evidence.evidence_status
        else:
            cross_pol = cross_policy_evidence or "UNKNOWN"

        if isinstance(cross_formal_system_evidence, OntoEvidenceRef):
            evidence_refs.append(cross_formal_system_evidence)
            cross_formal = cross_formal_system_evidence.evidence_status
        else:
            cross_formal = cross_formal_system_evidence or "UNKNOWN"

        if isinstance(functional_evidence, OntoEvidenceRef):
            evidence_refs.append(functional_evidence)
            func_benefit = functional_evidence.evidence_status
        elif functional_evidence is not None:
            func_benefit = functional_evidence
        else:
            func_benefit = "UNKNOWN"
            if candidate.held_out_evaluation:
                mode = candidate.held_out_evaluation.get("replay_mode")
                if mode == "EXECUTED_HELD_OUT_REPLAY":
                    comp = candidate.held_out_evaluation.get("structural_compression_ratio", 1.0)
                    eval_red = candidate.held_out_evaluation.get("candidate_evaluation_reduction", 0.0)
                    branch_red = candidate.held_out_evaluation.get("proof_branch_reduction", 0.0)
                    success_delta = candidate.held_out_evaluation.get("held_out_success_rate_delta", 0.0)
                    if (comp > 1.0 or eval_red > 0.0 or branch_red > 0.0) and success_delta >= 0.0:
                        func_benefit = "SUPPORTED"
                    else:
                        func_benefit = "NOT_SUPPORTED"
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
            evidence_refs=evidence_refs,
            authority="NONE",
        )
