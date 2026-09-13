"""ONTO evaluation evidence exporter (WO-MATH-FORMAL-DISCOVERY-01A-R3)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional, Union

from msk_formal_discovery.abstraction.candidate import AbstractionCandidate, CandidateStatus
from msk_formal_discovery.core.exceptions import ReceiptValidationError

HEX_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class OntoEvidenceRef:
    """Evidence reference binding an artifact to an ONTO dimension (Sections 23-25)."""
    evidence_kind: str
    artifact_ref: str
    artifact_digest: str
    evidence_status: str  # "SUPPORTED", "NOT_SUPPORTED", "UNTESTED", "UNKNOWN"
    source_experimental_units: List[str] = field(default_factory=list)
    source_repository: Optional[str] = None
    source_commit: Optional[str] = None

    def validate(self, known_artifacts: Optional[Dict[str, str]] = None, require_durable: bool = False) -> None:
        """Validate evidence reference shape and artifact resolvability (Sections 23 & 25)."""
        if self.evidence_status in ("SUPPORTED", "NOT_SUPPORTED"):
            if not self.artifact_ref:
                raise ReceiptValidationError(
                    "ARTIFACT_REF_REQUIRED: artifact_ref cannot be empty for positive/negative evidence"
                )
            if not HEX_DIGEST_PATTERN.match(self.artifact_digest):
                raise ReceiptValidationError(
                    f"INVALID_ARTIFACT_DIGEST: artifact_digest '{self.artifact_digest}' must be 64-char lowercase hex"
                )
            if not self.source_experimental_units:
                raise ReceiptValidationError(
                    "EXPERIMENTAL_UNITS_REQUIRED: source_experimental_units cannot be empty for positive/negative evidence"
                )

            # Resolvability check per Section 23, 25 & 28
            p = Path(self.artifact_ref)
            if not p.is_file():
                repo_root = Path(__file__).resolve().parents[3]
                alt_p = repo_root / self.artifact_ref
                if alt_p.is_file():
                    p = alt_p

            if p.is_file():
                file_digest = hashlib.sha256(p.read_bytes()).hexdigest()
                if file_digest != self.artifact_digest:
                    raise ReceiptValidationError(
                        f"ARTIFACT_DIGEST_MISMATCH: File digest {file_digest} != {self.artifact_digest}"
                    )
            elif require_durable:
                raise ReceiptValidationError(
                    f"UNRESOLVABLE_DURABLE_EVIDENCE: Artifact '{self.artifact_ref}' does not exist on disk as a durable repository artifact"
                )
            elif known_artifacts is not None:
                if self.artifact_ref not in known_artifacts:
                    raise ReceiptValidationError(
                        f"UNRESOLVABLE_EVIDENCE_ARTIFACT: Artifact '{self.artifact_ref}' not found in known artifacts"
                    )
                if known_artifacts[self.artifact_ref] != self.artifact_digest:
                    raise ReceiptValidationError(
                        f"ARTIFACT_DIGEST_MISMATCH: Expected digest {known_artifacts[self.artifact_ref]}, got {self.artifact_digest}"
                    )
            elif self.artifact_ref in OntoExporter._KNOWN_ARTIFACT_REGISTRY:
                reg_digest = OntoExporter._KNOWN_ARTIFACT_REGISTRY[self.artifact_ref]
                if reg_digest != self.artifact_digest:
                    raise ReceiptValidationError(
                        f"ARTIFACT_DIGEST_MISMATCH: Registry digest {reg_digest} != {self.artifact_digest}"
                    )
            else:
                raise ReceiptValidationError(
                    f"UNRESOLVABLE_EVIDENCE_ARTIFACT: Artifact '{self.artifact_ref}' cannot be resolved to a known verified artifact"
                )

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "evidence_kind": self.evidence_kind,
            "artifact_ref": self.artifact_ref,
            "artifact_digest": self.artifact_digest,
            "evidence_status": self.evidence_status,
            "source_experimental_units": self.source_experimental_units,
        }
        if self.source_repository is not None:
            data["source_repository"] = self.source_repository
        if self.source_commit is not None:
            data["source_commit"] = self.source_commit
        return data


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
    functional_search_benefit_scope: Optional[str] = None
    representation_invariance_scope: Optional[str] = None
    alpha_renaming_invariance: Optional[str] = None
    associative_regrouping_invariance: Optional[str] = None
    commutative_mirror_invariance: Optional[str] = None
    end_to_end_runtime_benefit: str = "NOT_ESTABLISHED"
    claim_ceiling: str = "ENGINEERING_ABSTRACTION_EFFECT_ONLY"
    authority: str = "NONE"

    def validate(self) -> None:
        """Validate package invariants (WO-MATH-FORMAL-DISCOVERY-01B-R2 Sections 19-24)."""
        valid_runtime_states = {"SUPPORTED", "NOT_SUPPORTED", "NOT_ESTABLISHED", "UNKNOWN"}
        if self.end_to_end_runtime_benefit not in valid_runtime_states:
            raise ValueError(
                f"INVALID_RUNTIME_BENEFIT_STATE: {self.end_to_end_runtime_benefit} not in {valid_runtime_states}"
            )
        if self.end_to_end_runtime_benefit == "SUPPORTED":
            raise ValueError(
                "UNEARNED_RUNTIME_BENEFIT: end_to_end_runtime_benefit cannot be inferred as SUPPORTED from node expansion"
            )

        valid_rep_invariance = {"UNKNOWN", "UNTESTED", "NOT_SUPPORTED", "SUPPORTED"}
        if self.representation_invariance not in valid_rep_invariance:
            raise ValueError(
                f"UNEARNED_REPRESENTATION_INVARIANCE: representation_invariance '{self.representation_invariance}' not in {valid_rep_invariance}"
            )
        if self.representation_invariance == "SUPPORTED":
            if not self.representation_invariance_scope:
                raise ValueError(
                    "UNEARNED_REPRESENTATION_INVARIANCE: representation_invariance SUPPORTED requires representation_invariance_scope"
                )
            if self.representation_invariance_scope != "ALPHA_ASSOCIATIVE_COMMUTATIVE_IDENTITY_ORBIT_V0_1":
                raise ValueError(
                    f"INVALID_REPRESENTATION_INVARIANCE_SCOPE: Allowed positive scope is 'ALPHA_ASSOCIATIVE_COMMUTATIVE_IDENTITY_ORBIT_V0_1', got '{self.representation_invariance_scope}'"
                )
        if self.representation_invariance_scope is not None and self.representation_invariance_scope != "ALPHA_ASSOCIATIVE_COMMUTATIVE_IDENTITY_ORBIT_V0_1":
            raise ValueError(
                f"INVALID_REPRESENTATION_INVARIANCE_SCOPE: Got '{self.representation_invariance_scope}'"
            )

        if self.cross_search_policy_recurrence not in ("UNKNOWN", "UNTESTED", "NOT_SUPPORTED"):
            raise ValueError(
                f"UNEARNED_CROSS_POLICY_RECURRENCE: cross_search_policy_recurrence '{self.cross_search_policy_recurrence}' cannot be promoted without cross-policy evaluation"
            )
        if self.cross_formal_system_recurrence not in ("UNKNOWN", "UNTESTED", "NOT_SUPPORTED"):
            raise ValueError(
                f"UNEARNED_CROSS_FORMAL_SYSTEM_RECURRENCE: cross_formal_system_recurrence '{self.cross_formal_system_recurrence}' cannot be promoted without cross-formal-system evaluation"
            )

        if self.authority != "NONE":
            raise ValueError(f"AUTHORITY_VIOLATION: authority must be 'NONE', got '{self.authority}'")
        if self.claim_ceiling != "ENGINEERING_ABSTRACTION_EFFECT_ONLY":
            raise ValueError(f"CLAIM_CEILING_VIOLATION: claim_ceiling must be 'ENGINEERING_ABSTRACTION_EFFECT_ONLY', got '{self.claim_ceiling}'")

        if self.functional_search_benefit == "SUPPORTED":
            if not self.functional_search_benefit_scope:
                raise ValueError(
                    "UNSCOPED_FUNCTIONAL_BENEFIT: functional_search_benefit SUPPORTED requires functional_search_benefit_scope"
                )
            if self.functional_search_benefit_scope != "NODE_EXPANSION_SEARCH_STRUCTURE":
                raise ValueError(
                    f"INVALID_FUNCTIONAL_BENEFIT_SCOPE: Allowed positive scope is 'NODE_EXPANSION_SEARCH_STRUCTURE', got '{self.functional_search_benefit_scope}'"
                )
            supported_refs = [r for r in self.evidence_refs if r.evidence_status == "SUPPORTED"]
            if not supported_refs:
                raise ValueError(
                    "SUPPORTED_WITHOUT_EVIDENCE: functional_search_benefit SUPPORTED requires supported evidence_refs"
                )

        repo_root = Path(__file__).resolve().parents[3]
        for r in self.evidence_refs:
            if r.evidence_kind in ("TERMINAL_STATE_CUSTODY_CLOSURE", "REPRESENTATION_INVARIANCE_CLOSURE"):
                ref_lower = r.artifact_ref.lower()
                if "freeze" in ref_lower or (Path(r.artifact_ref).name.lower() == "result.json" or ("result" in Path(r.artifact_ref).name.lower() and "closure" not in Path(r.artifact_ref).name.lower())):
                    raise ReceiptValidationError(
                        f"EVIDENCE_KIND_TARGET_MISMATCH: {r.evidence_kind} cannot target result freeze artifact '{r.artifact_ref}'"
                    )
                if "closure" not in ref_lower:
                    raise ReceiptValidationError(
                        f"EVIDENCE_KIND_TARGET_MISMATCH: {r.evidence_kind} must target a closure manifest, got '{r.artifact_ref}'"
                    )
                p = Path(r.artifact_ref)
                if not p.is_file():
                    alt = repo_root / r.artifact_ref
                    if alt.is_file():
                        p = alt
                if p.is_file():
                    try:
                        raw = json.loads(p.read_text(encoding="utf-8"))
                        if "closure_status" not in raw and "closure_id" not in raw:
                            raise ReceiptValidationError(
                                f"EVIDENCE_KIND_TARGET_MISMATCH: Target '{r.artifact_ref}' is not a custody closure manifest"
                            )
                    except json.JSONDecodeError:
                        pass
            elif r.evidence_kind == "FROZEN_R1_SCIENTIFIC_RESULT":
                ref_lower = r.artifact_ref.lower()
                if "closure" in ref_lower:
                    raise ReceiptValidationError(
                        f"EVIDENCE_KIND_TARGET_MISMATCH: FROZEN_R1_SCIENTIFIC_RESULT cannot target custody closure manifest '{r.artifact_ref}'"
                    )
                if not ("freeze" in ref_lower or "result" in ref_lower):
                    raise ReceiptValidationError(
                        f"EVIDENCE_KIND_TARGET_MISMATCH: FROZEN_R1_SCIENTIFIC_RESULT must target result freeze artifact, got '{r.artifact_ref}'"
                    )
                p = Path(r.artifact_ref)
                if not p.is_file():
                    alt = repo_root / r.artifact_ref
                    if alt.is_file():
                        p = alt
                if p.is_file():
                    try:
                        raw = json.loads(p.read_text(encoding="utf-8"))
                        if "closure_status" in raw or "closure_id" in raw:
                            raise ReceiptValidationError(
                                f"EVIDENCE_KIND_TARGET_MISMATCH: Target '{r.artifact_ref}' is a closure manifest, not a frozen result"
                            )
                    except json.JSONDecodeError:
                        pass

        if self.functional_search_benefit == "SUPPORTED":
            for r in supported_refs:
                r.validate(require_durable=True)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
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
        if self.functional_search_benefit_scope is not None:
            data["functional_search_benefit_scope"] = self.functional_search_benefit_scope
        if self.representation_invariance_scope is not None:
            data["representation_invariance_scope"] = self.representation_invariance_scope
        if self.alpha_renaming_invariance is not None:
            data["alpha_renaming_invariance"] = self.alpha_renaming_invariance
        if self.associative_regrouping_invariance is not None:
            data["associative_regrouping_invariance"] = self.associative_regrouping_invariance
        if self.commutative_mirror_invariance is not None:
            data["commutative_mirror_invariance"] = self.commutative_mirror_invariance
        data["end_to_end_runtime_benefit"] = self.end_to_end_runtime_benefit
        data["claim_ceiling"] = self.claim_ceiling
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> OntoEvaluationPackage:
        evidence_refs = [
            OntoEvidenceRef(
                evidence_kind=ref["evidence_kind"],
                artifact_ref=ref["artifact_ref"],
                artifact_digest=ref["artifact_digest"],
                evidence_status=ref["evidence_status"],
                source_experimental_units=ref.get("source_experimental_units", []),
                source_repository=ref.get("source_repository"),
                source_commit=ref.get("source_commit"),
            )
            for ref in data.get("evidence_refs", [])
        ]
        return cls(
            package_id=data["package_id"],
            candidate_id=data["candidate_id"],
            recurrence_count=data["recurrence_count"],
            representation_invariance=data.get("representation_invariance", "UNKNOWN"),
            cross_search_policy_recurrence=data.get("cross_search_policy_recurrence", "UNKNOWN"),
            cross_formal_system_recurrence=data.get("cross_formal_system_recurrence", "UNKNOWN"),
            functional_search_benefit=data.get("functional_search_benefit", "UNKNOWN"),
            source_traces=list(data.get("source_traces", [])),
            structural_fingerprint=data.get("structural_fingerprint", "0" * 64),
            evidence_refs=evidence_refs,
            functional_search_benefit_scope=data.get("functional_search_benefit_scope"),
            representation_invariance_scope=data.get("representation_invariance_scope"),
            alpha_renaming_invariance=data.get("alpha_renaming_invariance"),
            associative_regrouping_invariance=data.get("associative_regrouping_invariance"),
            commutative_mirror_invariance=data.get("commutative_mirror_invariance"),
            end_to_end_runtime_benefit=data.get("end_to_end_runtime_benefit", "NOT_ESTABLISHED"),
            claim_ceiling=data.get("claim_ceiling", "ENGINEERING_ABSTRACTION_EFFECT_ONLY"),
            authority=data.get("authority", "NONE"),
        )


class OntoExporter:
    """Exports abstraction candidate evidence for external ONTO evaluation without pre-answering research questions (WO-MATH-FORMAL-DISCOVERY-01A-R4 Sections 26 & 27)."""

    FIXTURE_EVIDENCE_REGISTRY: ClassVar[Dict[str, str]] = {}
    _KNOWN_ARTIFACT_REGISTRY = FIXTURE_EVIDENCE_REGISTRY

    @classmethod
    def register_evidence_artifact(cls, artifact_ref: str, artifact_digest: str) -> None:
        """Register an artifact into FIXTURE_EVIDENCE_REGISTRY (for fixture testing only; not 01B executed authority)."""
        cls.FIXTURE_EVIDENCE_REGISTRY[artifact_ref] = artifact_digest

    register_artifact = register_evidence_artifact

    @classmethod
    def clear_evidence_registry(cls) -> None:
        """Clear registered fixture artifacts."""
        cls.FIXTURE_EVIDENCE_REGISTRY.clear()

    @staticmethod
    def export(
        candidate: AbstractionCandidate,
        representation_evidence: Optional[Union[OntoEvidenceRef, str]] = None,
        cross_policy_evidence: Optional[Union[OntoEvidenceRef, str]] = None,
        cross_formal_system_evidence: Optional[Union[OntoEvidenceRef, str]] = None,
        functional_evidence: Optional[Union[OntoEvidenceRef, List[OntoEvidenceRef], str]] = None,
        known_artifacts: Optional[Dict[str, str]] = None,
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
            representation_evidence.validate(known_artifacts=known_artifacts)
            evidence_refs.append(representation_evidence)
            rep_inv = representation_evidence.evidence_status
        else:
            rep_inv = representation_evidence or "UNKNOWN"

        if isinstance(cross_policy_evidence, OntoEvidenceRef):
            cross_policy_evidence.validate(known_artifacts=known_artifacts)
            evidence_refs.append(cross_policy_evidence)
            cross_pol = cross_policy_evidence.evidence_status
        else:
            cross_pol = cross_policy_evidence or "UNKNOWN"

        if isinstance(cross_formal_system_evidence, OntoEvidenceRef):
            cross_formal_system_evidence.validate(known_artifacts=known_artifacts)
            evidence_refs.append(cross_formal_system_evidence)
            cross_formal = cross_formal_system_evidence.evidence_status
        else:
            cross_formal = cross_formal_system_evidence or "UNKNOWN"

        if isinstance(functional_evidence, list):
            for ref in functional_evidence:
                if isinstance(ref, OntoEvidenceRef):
                    ref.validate(known_artifacts=known_artifacts)
                    evidence_refs.append(ref)
            if any(r.evidence_status == "SUPPORTED" for r in functional_evidence if isinstance(r, OntoEvidenceRef)):
                func_benefit = "SUPPORTED"
            else:
                func_benefit = "NOT_SUPPORTED"
        elif isinstance(functional_evidence, OntoEvidenceRef):
            functional_evidence.validate(known_artifacts=known_artifacts)
            evidence_refs.append(functional_evidence)
            func_benefit = functional_evidence.evidence_status
        elif functional_evidence is not None:
            func_benefit = functional_evidence
        else:
            func_benefit = "UNKNOWN"
            if candidate.held_out_evaluation:
                mode = candidate.held_out_evaluation.get("replay_mode")
                if mode == "EXECUTED_HELD_OUT_REPLAY" and candidate.status == CandidateStatus.QUALIFIED_HELD_OUT:
                    comp = candidate.held_out_evaluation.get("structural_compression_ratio", 1.0)
                    eval_red = candidate.held_out_evaluation.get("candidate_evaluation_reduction", 0.0)
                    branch_red = candidate.held_out_evaluation.get("proof_branch_reduction", 0.0)
                    success_delta = candidate.held_out_evaluation.get("held_out_success_rate_delta", 0.0)
                    if (comp > 1.0 or eval_red > 0.0 or branch_red > 0.0) and success_delta >= 0.0:
                        func_benefit = "SUPPORTED"
                        # Section 24: Automatically emit validated replay evidence reference
                        replay_digest = hashlib.sha256(
                            json.dumps(candidate.held_out_evaluation, sort_keys=True).encode("utf-8")
                        ).hexdigest()
                        art_ref = f"held-out-replay-{candidate.candidate_id}"
                        OntoExporter.register_evidence_artifact(art_ref, replay_digest)
                        units = list(
                            candidate.qualification_problem_digests
                            or candidate.qualification_trace_ids
                            or [hashlib.sha256(b"unit-default").hexdigest()]
                        )
                        auto_ref = OntoEvidenceRef(
                            evidence_kind="HELD_OUT_REPLAY",
                            artifact_ref=art_ref,
                            artifact_digest=replay_digest,
                            evidence_status="SUPPORTED",
                            source_experimental_units=units,
                        )
                        evidence_refs.append(auto_ref)
                    else:
                        func_benefit = "NOT_SUPPORTED"
                else:
                    # In 01A, candidate cannot achieve QUALIFIED_HELD_OUT because candidate_application_status
                    # is REQUESTED_NOT_APPLIED; functional_search_benefit remains UNTESTED.
                    func_benefit = "UNTESTED"

        # Section 24: Prohibit functional_search_benefit = SUPPORTED with empty evidence_refs
        if func_benefit == "SUPPORTED" and not any(r.evidence_status == "SUPPORTED" for r in evidence_refs):
            raise ValueError(
                "SUPPORTED_WITHOUT_EVIDENCE: functional_search_benefit cannot be SUPPORTED without valid evidence_refs"
            )

        scope = "NODE_EXPANSION_SEARCH_STRUCTURE" if func_benefit == "SUPPORTED" else None

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
            functional_search_benefit_scope=scope,
            end_to_end_runtime_benefit="NOT_ESTABLISHED",
            claim_ceiling="ENGINEERING_ABSTRACTION_EFFECT_ONLY",
            authority="NONE",
        )

    @staticmethod
    def export_scoped(
        candidate: AbstractionCandidate,
        functional_search_benefit_scope: str = "NODE_EXPANSION_SEARCH_STRUCTURE",
        end_to_end_runtime_benefit: str = "NOT_ESTABLISHED",
        claim_ceiling: str = "ENGINEERING_ABSTRACTION_EFFECT_ONLY",
        durable_evidence_ref: Optional[OntoEvidenceRef] = None,
        durable_evidence_refs: Optional[List[OntoEvidenceRef]] = None,
        representation_evidence: Optional[Union[OntoEvidenceRef, str]] = None,
        cross_policy_evidence: Optional[Union[OntoEvidenceRef, str]] = None,
        cross_formal_system_evidence: Optional[Union[OntoEvidenceRef, str]] = None,
    ) -> OntoEvaluationPackage:
        """Export scoped ONTO package enforcing strict authority scope (WO-MATH-FORMAL-DISCOVERY-01B-R2 Sections 19-24)."""
        func_ev: Any = durable_evidence_ref
        if durable_evidence_refs is not None:
            func_ev = durable_evidence_refs
        pkg = OntoExporter.export(
            candidate=candidate,
            representation_evidence=representation_evidence,
            cross_policy_evidence=cross_policy_evidence,
            cross_formal_system_evidence=cross_formal_system_evidence,
            functional_evidence=func_ev,
        )
        pkg.functional_search_benefit_scope = functional_search_benefit_scope
        pkg.end_to_end_runtime_benefit = end_to_end_runtime_benefit
        pkg.claim_ceiling = claim_ceiling
        pkg.validate()
        return pkg
