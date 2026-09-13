"""Paired Representation Orbit Manifest and Invariance Closure Manifest (WO-MATH-FORMAL-DISCOVERY-01C)."""
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

PAIRED_MANIFEST_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "schemas" / "paired-representation-orbit-manifest.v0.1.schema.json"
)
CLOSURE_MANIFEST_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "schemas" / "representation-invariance-closure.v0.1.schema.json"
)


@dataclass
class PairedRepresentationOrbitManifest:
    """Paired manifest linking all 4 representation strata and search arms per semantic family."""
    manifest_id: str
    canonical_predecessor_commit: str
    candidate_id: str
    candidate_artifact_digest: str
    positive_family_seed: int
    negative_family_seed: int
    families: List[Dict[str, Any]]
    experiment_id: str = "formal-discovery-01c"
    schema_version: str = "miskatonic.paired-representation-orbit-manifest.v0.1"
    authority: str = "NONE"
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
            "experiment_id": self.experiment_id,
            "canonical_predecessor_commit": self.canonical_predecessor_commit,
            "candidate_id": self.candidate_id,
            "candidate_artifact_digest": self.candidate_artifact_digest,
            "positive_family_seed": self.positive_family_seed,
            "negative_family_seed": self.negative_family_seed,
            "families": list(self.families),
            "authority": self.authority,
            "manifest_digest": self.manifest_digest,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PairedRepresentationOrbitManifest:
        return cls(
            schema_version=data.get("schema_version", "miskatonic.paired-representation-orbit-manifest.v0.1"),
            manifest_id=data["manifest_id"],
            experiment_id=data.get("experiment_id", "formal-discovery-01c"),
            canonical_predecessor_commit=data["canonical_predecessor_commit"],
            candidate_id=data["candidate_id"],
            candidate_artifact_digest=data["candidate_artifact_digest"],
            positive_family_seed=data["positive_family_seed"],
            negative_family_seed=data["negative_family_seed"],
            families=list(data["families"]),
            authority=data.get("authority", "NONE"),
            manifest_digest=data.get("manifest_digest", ""),
        )

    def validate(self, repo_root: Optional[Path] = None) -> None:
        if self.authority != "NONE":
            raise AuthorityViolationError(f"AUTHORITY_VIOLATION: authority must be 'NONE', got '{self.authority}'")
        if len(self.families) != 12:
            raise ReceiptValidationError(f"INVALID_FAMILY_COUNT: Expected 12 families, got {len(self.families)}")

        if PAIRED_MANIFEST_SCHEMA_PATH.is_file():
            schema_data = json.loads(PAIRED_MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
            try:
                jsonschema.validate(self.to_dict(), schema_data)
            except jsonschema.exceptions.ValidationError as e:
                raise ReceiptValidationError(f"PAIRED_ORBIT_MANIFEST_SCHEMA_ERROR: {e.message}") from e

        computed = self.compute_digest()
        if self.manifest_digest != computed:
            raise ReceiptValidationError(
                f"MANIFEST_DIGEST_MISMATCH: Computed {computed} != {self.manifest_digest}"
            )

        root = repo_root or Path(__file__).resolve().parents[3]
        for f_entry in self.families:
            for s_name in ["R0_CANONICAL_CONTROL", "R1_ALPHA_RENAMED", "R2_ASSOCIATIVE_REGROUPED", "R3_COMMUTATIVE_MIRROR"]:
                if s_name not in f_entry.get("strata", {}):
                    raise ReceiptValidationError(f"MISSING_STRATUM: Family {f_entry.get('family_id')} missing {s_name}")
                s_dict = f_entry["strata"][s_name]
                # Check refs if on disk
                for ref_key, dig_key in [
                    ("transform_receipt_ref", "transform_receipt_digest"),
                    ("smt_certificate_ref", "smt_certificate_digest"),
                    ("baseline_search_receipt_ref", "baseline_search_receipt_digest"),
                    ("abstracted_search_receipt_ref", "abstracted_search_receipt_digest"),
                    ("paired_terminal_smt_receipt_ref", "paired_terminal_smt_receipt_digest"),
                ]:
                    ref_val = s_dict.get(ref_key)
                    dig_val = s_dict.get(dig_key)
                    if ref_val and dig_val:
                        p = Path(ref_val)
                        if not p.is_file():
                            alt = root / ref_val
                            if alt.is_file():
                                p = alt
                        if p.is_file():
                            act_dig = hashlib.sha256(p.read_bytes()).hexdigest()
                            # May match file sha256, internal receipt_digest, or ExecutionTrace.digest()
                            raw_val = None
                            try:
                                raw_val = json.loads(p.read_text(encoding="utf-8"))
                            except Exception:
                                pass
                            internal_dig = raw_val.get("receipt_digest") or raw_val.get("trace_digest") if isinstance(raw_val, dict) else None
                            trace_dig = (
                                hashlib.sha256(json.dumps(raw_val, sort_keys=True).encode("utf-8")).hexdigest()
                                if isinstance(raw_val, dict) and ("trace_id" in raw_val or "events" in raw_val)
                                else None
                            )
                            if dig_val not in (act_dig, internal_dig, trace_dig):
                                raise ReceiptValidationError(
                                    f"RECEIPT_DIGEST_MISMATCH: {ref_key} {ref_val} digest {act_dig} != {dig_val}"
                                )


@dataclass
class RepresentationInvarianceClosureManifest:
    """Closure manifest attesting complete representation-orbit invariance evaluation."""
    closure_id: str
    canonical_predecessor_commit: str
    canonical_predecessor_tree: str
    candidate_id: str
    candidate_artifact_digest: str
    paired_manifest_ref: str
    paired_manifest_digest: str
    per_stratum_dispositions: Dict[str, str]
    global_disposition: str
    all_representation_certificates_verified: bool
    all_search_receipts_verified: bool
    all_terminal_parity_verified: bool
    family_count: int = 12
    represented_problem_count: int = 48
    search_receipt_count: int = 96
    transform_receipt_count: int = 48
    smt_certificate_count: int = 48
    paired_terminal_smt_receipt_count: int = 48
    representation_invariance_scope: str = "ALPHA_ASSOCIATIVE_COMMUTATIVE_IDENTITY_ORBIT_V0_1"
    functional_search_benefit_scope: str = "NODE_EXPANSION_SEARCH_STRUCTURE"
    end_to_end_runtime_benefit: str = "NOT_ESTABLISHED"
    claim_ceiling: str = "ENGINEERING_ABSTRACTION_EFFECT_ONLY"
    authority: str = "NONE"
    closure_status: str = "REPRESENTATION_ORBIT_EVALUATION_CLOSED"
    work_order: str = "WO-MATH-FORMAL-DISCOVERY-01C"
    schema_version: str = "miskatonic.representation-invariance-closure.v0.1"
    closure_digest: str = ""

    def __post_init__(self) -> None:
        if not self.closure_digest:
            self.closure_digest = self.compute_digest()

    def compute_digest(self) -> str:
        d = {k: v for k, v in self.to_dict().items() if k != "closure_digest"}
        serialized = json.dumps(d, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "closure_id": self.closure_id,
            "work_order": self.work_order,
            "canonical_predecessor_commit": self.canonical_predecessor_commit,
            "canonical_predecessor_tree": self.canonical_predecessor_tree,
            "candidate_id": self.candidate_id,
            "candidate_artifact_digest": self.candidate_artifact_digest,
            "paired_manifest_ref": self.paired_manifest_ref,
            "paired_manifest_digest": self.paired_manifest_digest,
            "family_count": self.family_count,
            "represented_problem_count": self.represented_problem_count,
            "search_receipt_count": self.search_receipt_count,
            "transform_receipt_count": self.transform_receipt_count,
            "smt_certificate_count": self.smt_certificate_count,
            "paired_terminal_smt_receipt_count": self.paired_terminal_smt_receipt_count,
            "per_stratum_dispositions": dict(self.per_stratum_dispositions),
            "global_disposition": self.global_disposition,
            "representation_invariance_scope": self.representation_invariance_scope,
            "functional_search_benefit_scope": self.functional_search_benefit_scope,
            "end_to_end_runtime_benefit": self.end_to_end_runtime_benefit,
            "claim_ceiling": self.claim_ceiling,
            "authority": self.authority,
            "all_representation_certificates_verified": self.all_representation_certificates_verified,
            "all_search_receipts_verified": self.all_search_receipts_verified,
            "all_terminal_parity_verified": self.all_terminal_parity_verified,
            "closure_status": self.closure_status,
            "closure_digest": self.closure_digest,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RepresentationInvarianceClosureManifest:
        return cls(
            schema_version=data.get("schema_version", "miskatonic.representation-invariance-closure.v0.1"),
            closure_id=data["closure_id"],
            work_order=data.get("work_order", "WO-MATH-FORMAL-DISCOVERY-01C"),
            canonical_predecessor_commit=data["canonical_predecessor_commit"],
            canonical_predecessor_tree=data["canonical_predecessor_tree"],
            candidate_id=data["candidate_id"],
            candidate_artifact_digest=data["candidate_artifact_digest"],
            paired_manifest_ref=data["paired_manifest_ref"],
            paired_manifest_digest=data["paired_manifest_digest"],
            family_count=data.get("family_count", 12),
            represented_problem_count=data.get("represented_problem_count", 48),
            search_receipt_count=data.get("search_receipt_count", 96),
            transform_receipt_count=data.get("transform_receipt_count", 48),
            smt_certificate_count=data.get("smt_certificate_count", 48),
            paired_terminal_smt_receipt_count=data.get("paired_terminal_smt_receipt_count", 48),
            per_stratum_dispositions=dict(data["per_stratum_dispositions"]),
            global_disposition=data["global_disposition"],
            representation_invariance_scope=data.get("representation_invariance_scope", "ALPHA_ASSOCIATIVE_COMMUTATIVE_IDENTITY_ORBIT_V0_1"),
            functional_search_benefit_scope=data.get("functional_search_benefit_scope", "NODE_EXPANSION_SEARCH_STRUCTURE"),
            end_to_end_runtime_benefit=data.get("end_to_end_runtime_benefit", "NOT_ESTABLISHED"),
            claim_ceiling=data.get("claim_ceiling", "ENGINEERING_ABSTRACTION_EFFECT_ONLY"),
            authority=data.get("authority", "NONE"),
            all_representation_certificates_verified=data["all_representation_certificates_verified"],
            all_search_receipts_verified=data["all_search_receipts_verified"],
            all_terminal_parity_verified=data["all_terminal_parity_verified"],
            closure_status=data.get("closure_status", "REPRESENTATION_ORBIT_EVALUATION_CLOSED"),
            closure_digest=data.get("closure_digest", ""),
        )

    def validate(self, repo_root: Optional[Path] = None) -> None:
        if self.authority != "NONE":
            raise AuthorityViolationError(f"AUTHORITY_VIOLATION: authority must be 'NONE', got '{self.authority}'")
        if self.family_count != 12:
            raise ReceiptValidationError(f"INVALID_FAMILY_COUNT: Expected 12, got {self.family_count}")
        if self.represented_problem_count != 48:
            raise ReceiptValidationError(f"INVALID_PROBLEM_COUNT: Expected 48, got {self.represented_problem_count}")
        if self.search_receipt_count != 96:
            raise ReceiptValidationError(f"INVALID_SEARCH_RECEIPT_COUNT: Expected 96, got {self.search_receipt_count}")
        if self.transform_receipt_count != 48:
            raise ReceiptValidationError(f"INVALID_TRANSFORM_RECEIPT_COUNT: Expected 48, got {self.transform_receipt_count}")
        if self.smt_certificate_count != 48:
            raise ReceiptValidationError(f"INVALID_SMT_COUNT: Expected 48, got {self.smt_certificate_count}")
        if self.paired_terminal_smt_receipt_count != 48:
            raise ReceiptValidationError(f"INVALID_PAIRED_SMT_COUNT: Expected 48, got {self.paired_terminal_smt_receipt_count}")
        if not self.all_representation_certificates_verified:
            raise ReceiptValidationError("ALL_REPRESENTATION_CERTIFICATES_NOT_VERIFIED")
        if not self.all_search_receipts_verified:
            raise ReceiptValidationError("ALL_SEARCH_RECEIPTS_NOT_VERIFIED")
        if not self.all_terminal_parity_verified:
            raise ReceiptValidationError("ALL_TERMINAL_PARITY_NOT_VERIFIED")
        if self.representation_invariance_scope != "ALPHA_ASSOCIATIVE_COMMUTATIVE_IDENTITY_ORBIT_V0_1":
            raise ReceiptValidationError(f"INVALID_REPRESENTATION_SCOPE: {self.representation_invariance_scope}")
        if self.closure_status != "REPRESENTATION_ORBIT_EVALUATION_CLOSED":
            raise ReceiptValidationError(f"INVALID_CLOSURE_STATUS: {self.closure_status}")

        if CLOSURE_MANIFEST_SCHEMA_PATH.is_file():
            schema_data = json.loads(CLOSURE_MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
            try:
                jsonschema.validate(self.to_dict(), schema_data)
            except jsonschema.exceptions.ValidationError as e:
                raise ReceiptValidationError(f"CLOSURE_MANIFEST_SCHEMA_ERROR: {e.message}") from e

        computed = self.compute_digest()
        if self.closure_digest != computed:
            raise ReceiptValidationError(
                f"CLOSURE_DIGEST_MISMATCH: Computed {computed} != {self.closure_digest}"
            )

        root = repo_root or Path(__file__).resolve().parents[3]
        if self.paired_manifest_ref:
            p = Path(self.paired_manifest_ref)
            if not p.is_file():
                alt = root / self.paired_manifest_ref
                if alt.is_file():
                    p = alt
            if p.is_file():
                act_dig = hashlib.sha256(p.read_bytes()).hexdigest()
                raw = json.loads(p.read_text(encoding="utf-8"))
                manifest_dig = raw.get("manifest_digest", "")
                if self.paired_manifest_digest not in (act_dig, manifest_dig):
                    raise ReceiptValidationError(
                        f"PAIRED_MANIFEST_DIGEST_MISMATCH: {act_dig} != {self.paired_manifest_digest}"
                    )
