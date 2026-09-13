"""Manifests for whole-problem transformation, application replay custody, and final 01C-R1 closure (WO-MATH-FORMAL-DISCOVERY-01C-R1)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import jsonschema

from msk_formal_discovery.core.exceptions import (
    AuthorityViolationError,
    ReceiptValidationError,
)

WHOLE_PROBLEM_MANIFEST_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "schemas" / "whole-problem-transform-manifest.v0.1.schema.json"
)
APPLICATION_REPLAY_MANIFEST_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "schemas" / "application-replay-custody-manifest.v0.1.schema.json"
)
REPRESENTATION_CUSTODY_CLOSURE_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "schemas" / "representation-custody-closure.v0.1.schema.json"
)


@dataclass
class WholeProblemTransformManifest:
    """Manifest binding all 48 v0.2 whole-problem representation custody receipts and SMT certificates."""
    manifest_id: str
    work_order: str
    problem_receipt_count: int
    whole_problem_smt_count: int
    all_whole_problem_certificates_verified: bool
    receipts: List[Dict[str, Any]]
    authority: str = "NONE"
    schema_version: str = "miskatonic.whole-problem-transform-manifest.v0.1"
    manifest_digest: str = ""

    def __post_init__(self) -> None:
        if not self.manifest_digest:
            self.manifest_digest = self.compute_digest()

    def compute_digest(self) -> str:
        d = {k: v for k, v in self.to_dict().items() if k != "manifest_digest"}
        serialized = json.dumps(d, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "manifest_id": self.manifest_id,
            "work_order": self.work_order,
            "problem_receipt_count": self.problem_receipt_count,
            "whole_problem_smt_count": self.whole_problem_smt_count,
            "all_whole_problem_certificates_verified": self.all_whole_problem_certificates_verified,
            "receipts": list(self.receipts),
            "authority": self.authority,
            "manifest_digest": self.manifest_digest,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WholeProblemTransformManifest:
        return cls(
            schema_version=data.get("schema_version", "miskatonic.whole-problem-transform-manifest.v0.1"),
            manifest_id=data["manifest_id"],
            work_order=data["work_order"],
            problem_receipt_count=data["problem_receipt_count"],
            whole_problem_smt_count=data["whole_problem_smt_count"],
            all_whole_problem_certificates_verified=data["all_whole_problem_certificates_verified"],
            receipts=list(data["receipts"]),
            authority=data.get("authority", "NONE"),
            manifest_digest=data.get("manifest_digest", ""),
        )

    def validate(self, repo_root: Optional[Path] = None) -> None:
        if self.authority != "NONE":
            raise AuthorityViolationError(f"AUTHORITY_VIOLATION: authority must be 'NONE', got '{self.authority}'")
        if self.problem_receipt_count != 48:
            raise ReceiptValidationError(f"INVALID_PROBLEM_RECEIPT_COUNT: Expected 48, got {self.problem_receipt_count}")
        if self.whole_problem_smt_count != 48:
            raise ReceiptValidationError(f"INVALID_SMT_COUNT: Expected 48, got {self.whole_problem_smt_count}")
        if not self.all_whole_problem_certificates_verified:
            raise ReceiptValidationError("ALL_WHOLE_PROBLEM_CERTIFICATES_NOT_VERIFIED")

        if WHOLE_PROBLEM_MANIFEST_SCHEMA_PATH.is_file():
            schema_data = json.loads(WHOLE_PROBLEM_MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
            try:
                jsonschema.validate(self.to_dict(), schema_data)
            except jsonschema.exceptions.ValidationError as e:
                raise ReceiptValidationError(f"WHOLE_PROBLEM_MANIFEST_SCHEMA_ERROR: {e.message}") from e

        computed = self.compute_digest()
        if self.manifest_digest != computed:
            raise ReceiptValidationError(
                f"WHOLE_PROBLEM_MANIFEST_DIGEST_MISMATCH: Stored {self.manifest_digest} != computed {computed}"
            )


@dataclass
class ApplicationReplayCustodyManifest:
    """Manifest attesting deterministic application replay custody across all 48 abstracted searches."""
    manifest_id: str
    work_order: str
    search_run_count: int
    total_original_application_attempt_refs: int
    total_original_application_attempt_digests: int
    unique_application_ids: int
    duplicated_application_ids: int
    exact_original_application_attempts_resolved: int
    overwritten_or_unresolvable_application_attempts: int
    total_replay_application_receipts: int
    all_search_metric_parity_verified: bool
    all_application_id_sequence_parity_verified: bool
    all_candidate_status_parity_verified: bool
    all_applied_count_parity_verified: bool
    all_terminal_status_parity_verified: bool
    ledgers: List[Dict[str, Any]]
    authority: str = "NONE"
    all_search_budget_parity_verified: Optional[bool] = None
    search_budget_digest: Optional[str] = None
    search_replay_receipt_count: Optional[int] = None
    all_replay_search_receipts_verified: Optional[bool] = None
    all_replay_application_receipts_verified: Optional[bool] = None
    schema_version: str = "miskatonic.application-replay-custody-manifest.v0.1"
    manifest_digest: str = ""

    def __post_init__(self) -> None:
        if not self.manifest_digest:
            self.manifest_digest = self.compute_digest()

    def compute_digest(self) -> str:
        d = {k: v for k, v in self.to_dict().items() if k != "manifest_digest"}
        serialized = json.dumps(d, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "schema_version": self.schema_version,
            "manifest_id": self.manifest_id,
            "work_order": self.work_order,
            "search_run_count": self.search_run_count,
            "total_original_application_attempt_refs": self.total_original_application_attempt_refs,
            "total_original_application_attempt_digests": self.total_original_application_attempt_digests,
            "unique_application_ids": self.unique_application_ids,
            "duplicated_application_ids": self.duplicated_application_ids,
            "exact_original_application_attempts_resolved": self.exact_original_application_attempts_resolved,
            "overwritten_or_unresolvable_application_attempts": self.overwritten_or_unresolvable_application_attempts,
            "total_replay_application_receipts": self.total_replay_application_receipts,
            "all_search_metric_parity_verified": self.all_search_metric_parity_verified,
            "all_application_id_sequence_parity_verified": self.all_application_id_sequence_parity_verified,
            "all_candidate_status_parity_verified": self.all_candidate_status_parity_verified,
            "all_applied_count_parity_verified": self.all_applied_count_parity_verified,
            "all_terminal_status_parity_verified": self.all_terminal_status_parity_verified,
            "ledgers": list(self.ledgers),
            "authority": self.authority,
            "manifest_digest": self.manifest_digest,
        }
        if self.all_search_budget_parity_verified is not None:
            res["all_search_budget_parity_verified"] = self.all_search_budget_parity_verified
        if self.search_budget_digest is not None:
            res["search_budget_digest"] = self.search_budget_digest
        if self.search_replay_receipt_count is not None:
            res["search_replay_receipt_count"] = self.search_replay_receipt_count
        if self.all_replay_search_receipts_verified is not None:
            res["all_replay_search_receipts_verified"] = self.all_replay_search_receipts_verified
        if self.all_replay_application_receipts_verified is not None:
            res["all_replay_application_receipts_verified"] = self.all_replay_application_receipts_verified
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ApplicationReplayCustodyManifest:
        return cls(
            schema_version=data.get("schema_version", "miskatonic.application-replay-custody-manifest.v0.1"),
            manifest_id=data["manifest_id"],
            work_order=data["work_order"],
            search_run_count=data["search_run_count"],
            total_original_application_attempt_refs=data["total_original_application_attempt_refs"],
            total_original_application_attempt_digests=data["total_original_application_attempt_digests"],
            unique_application_ids=data["unique_application_ids"],
            duplicated_application_ids=data["duplicated_application_ids"],
            exact_original_application_attempts_resolved=data["exact_original_application_attempts_resolved"],
            overwritten_or_unresolvable_application_attempts=data["overwritten_or_unresolvable_application_attempts"],
            total_replay_application_receipts=data["total_replay_application_receipts"],
            all_search_metric_parity_verified=data["all_search_metric_parity_verified"],
            all_application_id_sequence_parity_verified=data["all_application_id_sequence_parity_verified"],
            all_candidate_status_parity_verified=data["all_candidate_status_parity_verified"],
            all_applied_count_parity_verified=data["all_applied_count_parity_verified"],
            all_terminal_status_parity_verified=data["all_terminal_status_parity_verified"],
            ledgers=list(data["ledgers"]),
            authority=data.get("authority", "NONE"),
            all_search_budget_parity_verified=data.get("all_search_budget_parity_verified"),
            search_budget_digest=data.get("search_budget_digest"),
            search_replay_receipt_count=data.get("search_replay_receipt_count"),
            all_replay_search_receipts_verified=data.get("all_replay_search_receipts_verified"),
            all_replay_application_receipts_verified=data.get("all_replay_application_receipts_verified"),
            manifest_digest=data.get("manifest_digest", ""),
        )

    def validate(self, repo_root: Optional[Path] = None) -> None:
        if self.authority != "NONE":
            raise AuthorityViolationError(f"AUTHORITY_VIOLATION: authority must be 'NONE', got '{self.authority}'")
        if self.search_run_count != 48:
            raise ReceiptValidationError(f"INVALID_SEARCH_RUN_COUNT: Expected 48, got {self.search_run_count}")
        if self.total_original_application_attempt_refs != 528:
            raise ReceiptValidationError(f"INVALID_TOTAL_REFS: Expected 528, got {self.total_original_application_attempt_refs}")
        if self.exact_original_application_attempts_resolved != 169:
            raise ReceiptValidationError(f"INVALID_RESOLVED_COUNT: Expected 169, got {self.exact_original_application_attempts_resolved}")
        if self.overwritten_or_unresolvable_application_attempts != 359:
            raise ReceiptValidationError(f"INVALID_OVERWRITTEN_COUNT: Expected 359, got {self.overwritten_or_unresolvable_application_attempts}")
        if not self.all_search_metric_parity_verified or not self.all_application_id_sequence_parity_verified:
            raise ReceiptValidationError("PARITY_VERIFICATION_FAILED")

        if APPLICATION_REPLAY_MANIFEST_SCHEMA_PATH.is_file():
            schema_data = json.loads(APPLICATION_REPLAY_MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
            try:
                jsonschema.validate(self.to_dict(), schema_data)
            except jsonschema.exceptions.ValidationError as e:
                raise ReceiptValidationError(f"APPLICATION_REPLAY_MANIFEST_SCHEMA_ERROR: {e.message}") from e

        computed = self.compute_digest()
        if self.manifest_digest != computed:
            raise ReceiptValidationError(
                f"APPLICATION_REPLAY_MANIFEST_DIGEST_MISMATCH: Stored {self.manifest_digest} != computed {computed}"
            )


@dataclass
class RepresentationCustodyClosureManifest:
    """Superseding custody closure manifest binding the complete 01C evidence graph."""
    closure_id: str
    work_order: str
    predecessor_head: str
    original_01c_commit_a: str
    original_01c_commit_b: str
    original_01c_commit_a_tree: str
    original_01c_commit_b_tree: str
    candidate_id: str
    candidate_artifact_digest: str
    original_preregistration_ref: str
    original_preregistration_digest: str
    original_semantic_families_ref: str
    original_semantic_families_digest: str
    original_result_ref: str
    original_result_digest: str
    original_paired_manifest_ref: str
    original_paired_manifest_digest: str
    original_closure_manifest_ref: str
    original_closure_manifest_digest: str
    original_onto_export_ref: str
    original_onto_export_digest: str
    whole_problem_transform_manifest_ref: str
    whole_problem_transform_manifest_digest: str
    application_replay_manifest_ref: str
    application_replay_manifest_digest: str
    transform_receipt_count: int
    search_receipt_count: int
    all_original_transform_receipts_verified: bool
    all_original_search_receipts_verified: bool
    exact_original_application_attempts_resolved: int
    overwritten_or_unresolvable_application_attempts: int
    per_stratum_dispositions: Dict[str, str]
    global_disposition: str
    representation_invariance_scope: str = "ALPHA_ASSOCIATIVE_COMMUTATIVE_IDENTITY_ORBIT_V0_1"
    functional_search_benefit_scope: str = "NODE_EXPANSION_SEARCH_STRUCTURE"
    end_to_end_runtime_benefit: str = "NOT_ESTABLISHED"
    claim_ceiling: str = "ENGINEERING_ABSTRACTION_EFFECT_ONLY"
    authority: str = "NONE"
    closure_status: str = "REPRESENTATION_CUSTODY_GRAPH_CLOSED"
    original_r1_commit_a: Optional[str] = None
    original_r1_commit_b: Optional[str] = None
    original_r1_commit_a_tree: Optional[str] = None
    original_r1_commit_b_tree: Optional[str] = None
    original_r1_closure_manifest_ref: Optional[str] = None
    original_r1_closure_manifest_digest: Optional[str] = None
    search_replay_receipt_count: Optional[int] = None
    application_replay_receipt_count: Optional[int] = None
    all_replay_search_receipts_verified: Optional[bool] = None
    all_replay_application_receipts_verified: Optional[bool] = None
    all_applied_count_parity_verified: Optional[bool] = None
    all_search_budget_parity_verified: Optional[bool] = None
    search_budget_digest: Optional[str] = None
    original_attempt_body_custody: Optional[str] = None
    deterministic_replay_attempt_body_custody: Optional[str] = None
    schema_version: str = "miskatonic.representation-custody-closure.v0.1"
    closure_digest: str = ""

    def __post_init__(self) -> None:
        if not self.closure_digest:
            self.closure_digest = self.compute_digest()

    def compute_digest(self) -> str:
        d = {k: v for k, v in self.to_dict().items() if k != "closure_digest"}
        serialized = json.dumps(d, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "schema_version": self.schema_version,
            "closure_id": self.closure_id,
            "work_order": self.work_order,
            "predecessor_head": self.predecessor_head,
            "original_01c_commit_a": self.original_01c_commit_a,
            "original_01c_commit_b": self.original_01c_commit_b,
            "original_01c_commit_a_tree": self.original_01c_commit_a_tree,
            "original_01c_commit_b_tree": self.original_01c_commit_b_tree,
            "candidate_id": self.candidate_id,
            "candidate_artifact_digest": self.candidate_artifact_digest,
            "original_preregistration_ref": self.original_preregistration_ref,
            "original_preregistration_digest": self.original_preregistration_digest,
            "original_semantic_families_ref": self.original_semantic_families_ref,
            "original_semantic_families_digest": self.original_semantic_families_digest,
            "original_result_ref": self.original_result_ref,
            "original_result_digest": self.original_result_digest,
            "original_paired_manifest_ref": self.original_paired_manifest_ref,
            "original_paired_manifest_digest": self.original_paired_manifest_digest,
            "original_closure_manifest_ref": self.original_closure_manifest_ref,
            "original_closure_manifest_digest": self.original_closure_manifest_digest,
            "original_onto_export_ref": self.original_onto_export_ref,
            "original_onto_export_digest": self.original_onto_export_digest,
            "whole_problem_transform_manifest_ref": self.whole_problem_transform_manifest_ref,
            "whole_problem_transform_manifest_digest": self.whole_problem_transform_manifest_digest,
            "application_replay_manifest_ref": self.application_replay_manifest_ref,
            "application_replay_manifest_digest": self.application_replay_manifest_digest,
            "transform_receipt_count": self.transform_receipt_count,
            "search_receipt_count": self.search_receipt_count,
            "all_original_transform_receipts_verified": self.all_original_transform_receipts_verified,
            "all_original_search_receipts_verified": self.all_original_search_receipts_verified,
            "exact_original_application_attempts_resolved": self.exact_original_application_attempts_resolved,
            "overwritten_or_unresolvable_application_attempts": self.overwritten_or_unresolvable_application_attempts,
            "per_stratum_dispositions": dict(self.per_stratum_dispositions),
            "global_disposition": self.global_disposition,
            "representation_invariance_scope": self.representation_invariance_scope,
            "functional_search_benefit_scope": self.functional_search_benefit_scope,
            "end_to_end_runtime_benefit": self.end_to_end_runtime_benefit,
            "claim_ceiling": self.claim_ceiling,
            "authority": self.authority,
            "closure_status": self.closure_status,
            "closure_digest": self.closure_digest,
        }
        if self.original_r1_commit_a is not None:
            res["original_r1_commit_a"] = self.original_r1_commit_a
        if self.original_r1_commit_b is not None:
            res["original_r1_commit_b"] = self.original_r1_commit_b
        if self.original_r1_commit_a_tree is not None:
            res["original_r1_commit_a_tree"] = self.original_r1_commit_a_tree
        if self.original_r1_commit_b_tree is not None:
            res["original_r1_commit_b_tree"] = self.original_r1_commit_b_tree
        if self.original_r1_closure_manifest_ref is not None:
            res["original_r1_closure_manifest_ref"] = self.original_r1_closure_manifest_ref
        if self.original_r1_closure_manifest_digest is not None:
            res["original_r1_closure_manifest_digest"] = self.original_r1_closure_manifest_digest
        if self.search_replay_receipt_count is not None:
            res["search_replay_receipt_count"] = self.search_replay_receipt_count
        if self.application_replay_receipt_count is not None:
            res["application_replay_receipt_count"] = self.application_replay_receipt_count
        if self.all_replay_search_receipts_verified is not None:
            res["all_replay_search_receipts_verified"] = self.all_replay_search_receipts_verified
        if self.all_replay_application_receipts_verified is not None:
            res["all_replay_application_receipts_verified"] = self.all_replay_application_receipts_verified
        if self.all_applied_count_parity_verified is not None:
            res["all_applied_count_parity_verified"] = self.all_applied_count_parity_verified
        if self.all_search_budget_parity_verified is not None:
            res["all_search_budget_parity_verified"] = self.all_search_budget_parity_verified
        if self.search_budget_digest is not None:
            res["search_budget_digest"] = self.search_budget_digest
        if self.original_attempt_body_custody is not None:
            res["original_attempt_body_custody"] = self.original_attempt_body_custody
        if self.deterministic_replay_attempt_body_custody is not None:
            res["deterministic_replay_attempt_body_custody"] = self.deterministic_replay_attempt_body_custody
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RepresentationCustodyClosureManifest:
        return cls(
            schema_version=data.get("schema_version", "miskatonic.representation-custody-closure.v0.1"),
            closure_id=data["closure_id"],
            work_order=data["work_order"],
            predecessor_head=data["predecessor_head"],
            original_01c_commit_a=data["original_01c_commit_a"],
            original_01c_commit_b=data["original_01c_commit_b"],
            original_01c_commit_a_tree=data["original_01c_commit_a_tree"],
            original_01c_commit_b_tree=data["original_01c_commit_b_tree"],
            candidate_id=data["candidate_id"],
            candidate_artifact_digest=data["candidate_artifact_digest"],
            original_preregistration_ref=data["original_preregistration_ref"],
            original_preregistration_digest=data["original_preregistration_digest"],
            original_semantic_families_ref=data["original_semantic_families_ref"],
            original_semantic_families_digest=data["original_semantic_families_digest"],
            original_result_ref=data["original_result_ref"],
            original_result_digest=data["original_result_digest"],
            original_paired_manifest_ref=data["original_paired_manifest_ref"],
            original_paired_manifest_digest=data["original_paired_manifest_digest"],
            original_closure_manifest_ref=data["original_closure_manifest_ref"],
            original_closure_manifest_digest=data["original_closure_manifest_digest"],
            original_onto_export_ref=data["original_onto_export_ref"],
            original_onto_export_digest=data["original_onto_export_digest"],
            whole_problem_transform_manifest_ref=data["whole_problem_transform_manifest_ref"],
            whole_problem_transform_manifest_digest=data["whole_problem_transform_manifest_digest"],
            application_replay_manifest_ref=data["application_replay_manifest_ref"],
            application_replay_manifest_digest=data["application_replay_manifest_digest"],
            transform_receipt_count=data["transform_receipt_count"],
            search_receipt_count=data["search_receipt_count"],
            all_original_transform_receipts_verified=data["all_original_transform_receipts_verified"],
            all_original_search_receipts_verified=data["all_original_search_receipts_verified"],
            exact_original_application_attempts_resolved=data["exact_original_application_attempts_resolved"],
            overwritten_or_unresolvable_application_attempts=data["overwritten_or_unresolvable_application_attempts"],
            per_stratum_dispositions=dict(data["per_stratum_dispositions"]),
            global_disposition=data["global_disposition"],
            representation_invariance_scope=data.get("representation_invariance_scope", "ALPHA_ASSOCIATIVE_COMMUTATIVE_IDENTITY_ORBIT_V0_1"),
            functional_search_benefit_scope=data.get("functional_search_benefit_scope", "NODE_EXPANSION_SEARCH_STRUCTURE"),
            end_to_end_runtime_benefit=data.get("end_to_end_runtime_benefit", "NOT_ESTABLISHED"),
            claim_ceiling=data.get("claim_ceiling", "ENGINEERING_ABSTRACTION_EFFECT_ONLY"),
            authority=data.get("authority", "NONE"),
            closure_status=data.get("closure_status", "REPRESENTATION_CUSTODY_GRAPH_CLOSED"),
            original_r1_commit_a=data.get("original_r1_commit_a"),
            original_r1_commit_b=data.get("original_r1_commit_b"),
            original_r1_commit_a_tree=data.get("original_r1_commit_a_tree"),
            original_r1_commit_b_tree=data.get("original_r1_commit_b_tree"),
            original_r1_closure_manifest_ref=data.get("original_r1_closure_manifest_ref"),
            original_r1_closure_manifest_digest=data.get("original_r1_closure_manifest_digest"),
            search_replay_receipt_count=data.get("search_replay_receipt_count"),
            application_replay_receipt_count=data.get("application_replay_receipt_count"),
            all_replay_search_receipts_verified=data.get("all_replay_search_receipts_verified"),
            all_replay_application_receipts_verified=data.get("all_replay_application_receipts_verified"),
            all_applied_count_parity_verified=data.get("all_applied_count_parity_verified"),
            all_search_budget_parity_verified=data.get("all_search_budget_parity_verified"),
            search_budget_digest=data.get("search_budget_digest"),
            original_attempt_body_custody=data.get("original_attempt_body_custody"),
            deterministic_replay_attempt_body_custody=data.get("deterministic_replay_attempt_body_custody"),
            closure_digest=data.get("closure_digest", ""),
        )

    def validate(self, repo_root: Optional[Path] = None) -> None:
        if self.authority != "NONE":
            raise AuthorityViolationError(f"AUTHORITY_VIOLATION: authority must be 'NONE', got '{self.authority}'")
        if self.closure_status != "REPRESENTATION_CUSTODY_GRAPH_CLOSED":
            raise ReceiptValidationError(f"INVALID_CLOSURE_STATUS: {self.closure_status}")
        if not self.all_original_transform_receipts_verified or not self.all_original_search_receipts_verified:
            raise ReceiptValidationError("ALL_ORIGINAL_RECEIPTS_NOT_VERIFIED")

        if REPRESENTATION_CUSTODY_CLOSURE_SCHEMA_PATH.is_file():
            schema_data = json.loads(REPRESENTATION_CUSTODY_CLOSURE_SCHEMA_PATH.read_text(encoding="utf-8"))
            try:
                jsonschema.validate(self.to_dict(), schema_data)
            except jsonschema.exceptions.ValidationError as e:
                raise ReceiptValidationError(f"REPRESENTATION_CUSTODY_CLOSURE_SCHEMA_ERROR: {e.message}") from e

        computed = self.compute_digest()
        if self.closure_digest != computed:
            raise ReceiptValidationError(
                f"CLOSURE_DIGEST_MISMATCH: Stored {self.closure_digest} != computed {computed}"
            )
