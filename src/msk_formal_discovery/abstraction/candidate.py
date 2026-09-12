"""Abstraction candidate representations, fail-closed defaults, and lifecycle (WO-MATH-FORMAL-DISCOVERY-01A-R1)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from msk_formal_discovery.abstraction.anti_unification import (
    AdmissibilityReceipt,
    AdmissibilityStatus,
    AntiUnificationResult,
    StructuralAntiUnifier,
    create_admissibility_receipt,
)
from msk_formal_discovery.core.exceptions import AntiUnificationError, AuthorityViolationError
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
    discovery_problem_digests: List[str] = field(default_factory=list)
    qualification_trace_ids: List[str] = field(default_factory=list)
    qualification_problem_digests: List[str] = field(default_factory=list)
    status: CandidateStatus = CandidateStatus.PROPOSED
    admissibility_status: AdmissibilityStatus = AdmissibilityStatus.UNASSESSED
    admissibility_receipt: Optional[Dict[str, Any]] = None
    held_out_evaluation: Optional[Dict[str, Any]] = None
    blueprint_family: Optional[str] = None
    onto_export: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        # Enforce Section 23 & 25: QUALIFIED_HELD_OUT requires ADMISSIBLE and valid admissibility receipt
        if self.status == CandidateStatus.QUALIFIED_HELD_OUT:
            if self.admissibility_status != AdmissibilityStatus.ADMISSIBLE or not self.admissibility_receipt:
                self.status = CandidateStatus.REJECTED
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

        data: Dict[str, Any] = {
            "schema_version": "miskatonic.abstraction-candidate.v0.1",
            "candidate_id": self.candidate_id,
            "candidate_kind": self.candidate_kind.value if isinstance(self.candidate_kind, AbstractionKind) else str(self.candidate_kind),
            "status": self.status.value if isinstance(self.status, CandidateStatus) else str(self.status),
            "admissibility_status": self.admissibility_status.value if isinstance(self.admissibility_status, AdmissibilityStatus) else str(self.admissibility_status),
            "formal_specification": self.formal_specification,
            "anti_unification_evidence": {
                "algorithm_version": self.anti_unification_evidence.algorithm_version,
                "least_general_generalization": str(self.anti_unification_evidence.lgg_term),
                "source_trace_ids": list(self.anti_unification_evidence.substitution_witnesses.keys()),
                "substitution_witnesses": witness_list,
                "deterministic_digest": self.anti_unification_evidence.deterministic_digest,
            },
            "discovery_set_trace_ids": self.discovery_set_trace_ids,
            "discovery_problem_digests": self.discovery_problem_digests,
            "qualification_trace_ids": self.qualification_trace_ids,
            "qualification_problem_digests": self.qualification_problem_digests,
            "held_out_evaluation": held_out_data,
            "blueprint_family": self.blueprint_family,
            "onto_export": onto_data,
            "authority": self.authority,
        }
        if self.admissibility_receipt is not None:
            data["admissibility_receipt"] = self.admissibility_receipt
        return data


class CandidateFactory:
    """Governed synthesis path for abstraction candidates (Section 27)."""

    @staticmethod
    def from_pattern(
        pattern: Any,  # RecurringSubtracePattern
        candidate_kind: AbstractionKind = AbstractionKind.LEMMA,
        candidate_id: Optional[str] = None,
        discovery_problem_digests: Optional[List[str]] = None,
        blueprint_family: Optional[str] = None,
    ) -> AbstractionCandidate:
        """Automatically assess pattern, create receipt, bind receipt, and emit candidate."""
        if not getattr(pattern, "anti_unification_result", None):
            raise AntiUnificationError("Cannot synthesize candidate from pattern without anti-unification result")

        au_res: AntiUnificationResult = pattern.anti_unification_result
        terms = list(pattern.extracted_terms.items())
        branch_guards = getattr(pattern, "branch_guards", [])

        status = StructuralAntiUnifier.assess_admissibility(
            terms=terms,
            result=au_res,
            branch_guards=branch_guards,
        )

        receipt = create_admissibility_receipt(
            terms=terms,
            result=au_res,
            status=status,
            branch_guards=branch_guards,
            discovery_problem_digests=discovery_problem_digests or [],
        )

        cid = candidate_id or f"cand_{pattern.pattern_id}"
        free_v = sorted(list(au_res.lgg_term.free_vars()))
        formal_spec = {
            "name": cid,
            "canonical_representation": str(au_res.lgg_term),
            "statement": f"forall {', '.join(free_v)}, {au_res.lgg_term}" if free_v else str(au_res.lgg_term),
            "parameters": free_v,
            "signature": f"{cid}({', '.join(free_v)})",
            "guard": branch_guards[0] if (branch_guards and len(set(branch_guards)) == 1) else None,
        }

        source_trace_ids = list(pattern.extracted_terms.keys())
        cand_status = CandidateStatus.PROPOSED if status == AdmissibilityStatus.ADMISSIBLE else CandidateStatus.CANDIDATE_ONLY
        return AbstractionCandidate(
            candidate_id=cid,
            candidate_kind=candidate_kind,
            formal_specification=formal_spec,
            anti_unification_evidence=au_res,
            discovery_set_trace_ids=source_trace_ids,
            discovery_problem_digests=list(discovery_problem_digests or []),
            status=cand_status,
            admissibility_status=status,
            admissibility_receipt=receipt.to_dict(),
            blueprint_family=blueprint_family,
        )
