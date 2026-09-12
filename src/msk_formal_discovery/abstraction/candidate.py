"""Abstraction candidate representations, fail-closed defaults, and lifecycle (WO-MATH-FORMAL-DISCOVERY-01A-R1)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from msk_formal_discovery.abstraction.anti_unification import (
    AdmissibilityStatus,
    AntiUnificationResult,
)
from msk_formal_discovery.core.exceptions import AuthorityViolationError
from msk_formal_discovery.core.terms import Term


class AbstractionKind(str, Enum):
    """Canonical kinds of abstraction candidates."""
    LEMMA = "LEMMA"
    REWRITE_RULE = "REWRITE_RULE"
    PRECONDITION = "PRECONDITION"
    NORMALIZATION_RULE = "NORMALIZATION_RULE"
    LIBRARY_BRIDGE = "LIBRARY_BRIDGE"
    TACTIC_MACRO = "TACTIC_MACRO"
    API_FUNCTION = "API_FUNCTION"
    MODULE_BOUNDARY = "MODULE_BOUNDARY"


class CandidateStatus(str, Enum):
    """Lifecycle status of an abstraction candidate."""
    PROPOSED = "PROPOSED"
    QUALIFIED_HELD_OUT = "QUALIFIED_HELD_OUT"
    REJECTED = "REJECTED"
    CANDIDATE_ONLY = "CANDIDATE_ONLY"


@dataclass
class AbstractionCandidate:
    """An abstraction candidate discovered through anti-unification.
    
    Authority Invariant: Candidate != accepted abstraction. Authority remains NONE.
    """
    candidate_id: str
    candidate_kind: AbstractionKind
    formal_specification: Dict[str, Any]
    anti_unification_evidence: AntiUnificationResult
    discovery_set_trace_ids: List[str]
    qualification_trace_ids: List[str] = field(default_factory=list)
    status: CandidateStatus = CandidateStatus.PROPOSED
    admissibility_status: AdmissibilityStatus = AdmissibilityStatus.ADMISSIBLE
    held_out_evaluation: Optional[Dict[str, Any]] = None
    blueprint_family: Optional[str] = None
    onto_export: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        # Enforce admissibility on lemma promotion
        if self.candidate_kind == AbstractionKind.LEMMA:
            if self.admissibility_status != AdmissibilityStatus.ADMISSIBLE:
                if self.status == CandidateStatus.QUALIFIED_HELD_OUT:
                    self.status = CandidateStatus.REJECTED

    @property
    def authority(self) -> str:
        return "NONE"

    def to_dict(self) -> Dict[str, Any]:
        witness_list = []
        for tid, subst in self.anti_unification_evidence.substitution_witnesses.items():
            witness_list.append({
                "trace_id": tid,
                "substitutions": {var: str(val) for var, val in subst.items()},
            })

        # Fail-closed defaults per Section 15
        held_out_data = self.held_out_evaluation or {
            "replay_mode": "UNTESTED",
            "is_held_out_disjoint_from_discovery": False,
            "supporting_trace_count": len(self.discovery_set_trace_ids),
            "structural_compression_ratio": 1.0,
            "proof_branch_reduction": 0.0,
            "candidate_evaluation_reduction": 0.0,
            "held_out_success_rate_delta": 0.0,
            "wall_time_delta_pct": 0.0,
        }

        # Fail-closed ONTO defaults per Section 15 & 16: UNKNOWN instead of true
        onto_data = self.onto_export or {
            "recurrence_count": len(self.discovery_set_trace_ids),
            "representation_invariance": "UNKNOWN",
            "cross_search_policy_recurrence": "UNKNOWN",
            "cross_formal_system_recurrence": "UNKNOWN",
            "functional_search_benefit": "UNKNOWN",
        }

        return {
            "schema_version": "miskatonic.abstraction-candidate.v0.1",
            "candidate_id": self.candidate_id,
            "candidate_kind": self.candidate_kind.value,
            "status": self.status.value,
            "admissibility_status": self.admissibility_status.value,
            "formal_specification": self.formal_specification,
            "anti_unification_evidence": {
                "algorithm_version": self.anti_unification_evidence.algorithm_version,
                "least_general_generalization": str(self.anti_unification_evidence.lgg_term),
                "source_trace_ids": list(self.anti_unification_evidence.substitution_witnesses.keys()),
                "substitution_witnesses": witness_list,
                "deterministic_digest": self.anti_unification_evidence.deterministic_digest,
            },
            "discovery_set_trace_ids": self.discovery_set_trace_ids,
            "qualification_trace_ids": self.qualification_trace_ids,
            "held_out_evaluation": held_out_data,
            "blueprint_family": self.blueprint_family,
            "onto_export": onto_data,
            "authority": self.authority,
        }
