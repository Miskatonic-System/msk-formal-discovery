"""Custody Manifests and Closure Record (WO-MATH-FORMAL-DISCOVERY-01B-R2 Sections 16 & 18)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from msk_formal_discovery.core.exceptions import ReceiptValidationError, AuthorityViolationError


@dataclass
class PairedTerminalCustodyManifest:
    """Manifest binding baseline and abstracted terminal custody per experimental unit (Section 16)."""
    schema_version: str
    manifest_id: str
    source_work_order: str
    source_execution_commit: str
    units: List[Dict[str, Any]] = field(default_factory=list)
    authority: str = "NONE"

    def manifest_digest(self) -> str:
        d = {k: v for k, v in self.to_dict().items() if k != "manifest_digest"}
        serialized = json.dumps(d, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "manifest_id": self.manifest_id,
            "source_work_order": self.source_work_order,
            "source_execution_commit": self.source_execution_commit,
            "units": self.units,
            "authority": self.authority,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PairedTerminalCustodyManifest:
        return cls(
            schema_version=data["schema_version"],
            manifest_id=data["manifest_id"],
            source_work_order=data["source_work_order"],
            source_execution_commit=data["source_execution_commit"],
            units=list(data.get("units", [])),
            authority=data.get("authority", "NONE"),
        )

    def validate(self) -> None:
        if self.authority != "NONE":
            raise AuthorityViolationError(f"AUTHORITY_VIOLATION: authority must be 'NONE', got '{self.authority}'")
        if len(self.units) != 12:
            raise ReceiptValidationError(f"INVALID_UNIT_COUNT: Expected exactly 12 units, got {len(self.units)}")
        for u in self.units:
            for req in [
                "problem_id",
                "problem_digest",
                "baseline_custody_receipt_ref",
                "baseline_custody_receipt_digest",
                "abstracted_custody_receipt_ref",
                "abstracted_custody_receipt_digest",
                "baseline_terminal_digest",
                "abstracted_terminal_digest",
                "baseline_terminal_canonical_representation",
                "abstracted_terminal_canonical_representation",
                "original_paired_smt_receipt_ref",
                "original_paired_smt_receipt_digest",
                "r1_smt_verdict",
                "terminal_digest_equality",
                "custody_replay_parity_status",
            ]:
                if req not in u:
                    raise ReceiptValidationError(f"MISSING_MANIFEST_FIELD: Unit missing '{req}'")
            if not u["terminal_digest_equality"]:
                raise ReceiptValidationError(f"TERMINAL_DIGEST_EQUALITY_FAILED: Unit {u['problem_id']}")
            if u["custody_replay_parity_status"] != "PARITY_VERIFIED":
                raise ReceiptValidationError(f"PARITY_NOT_VERIFIED: Unit {u['problem_id']}")


@dataclass
class TerminalCustodyClosureManifest:
    """Closure manifest attesting full search-to-terminal custody and R1 science closure (Section 18)."""
    schema_version: str
    closure_id: str
    source_work_order: str
    r2_work_order: str
    source_execution_commit: str
    source_execution_tree: str
    custody_receipt_count: int
    paired_unit_count: int
    source_result_digest_verified: bool
    all_terminal_digest_parity: bool
    all_metric_parity: bool
    all_application_parity: bool
    all_original_search_refs_resolved: bool
    all_replay_receipts_resolved: bool
    source_science_mutated: bool
    terminal_canonical_forms_durably_bound: str
    closure_status: str
    authority: str = "NONE"
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
            "source_work_order": self.source_work_order,
            "r2_work_order": self.r2_work_order,
            "source_execution_commit": self.source_execution_commit,
            "source_execution_tree": self.source_execution_tree,
            "custody_receipt_count": self.custody_receipt_count,
            "paired_unit_count": self.paired_unit_count,
            "source_result_digest_verified": self.source_result_digest_verified,
            "all_terminal_digest_parity": self.all_terminal_digest_parity,
            "all_metric_parity": self.all_metric_parity,
            "all_application_parity": self.all_application_parity,
            "all_original_search_refs_resolved": self.all_original_search_refs_resolved,
            "all_replay_receipts_resolved": self.all_replay_receipts_resolved,
            "source_science_mutated": self.source_science_mutated,
            "terminal_canonical_forms_durably_bound": self.terminal_canonical_forms_durably_bound,
            "closure_status": self.closure_status,
            "authority": self.authority,
            "closure_digest": self.closure_digest,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TerminalCustodyClosureManifest:
        return cls(
            schema_version=data["schema_version"],
            closure_id=data["closure_id"],
            source_work_order=data["source_work_order"],
            r2_work_order=data["r2_work_order"],
            source_execution_commit=data["source_execution_commit"],
            source_execution_tree=data["source_execution_tree"],
            custody_receipt_count=data["custody_receipt_count"],
            paired_unit_count=data["paired_unit_count"],
            source_result_digest_verified=data["source_result_digest_verified"],
            all_terminal_digest_parity=data["all_terminal_digest_parity"],
            all_metric_parity=data["all_metric_parity"],
            all_application_parity=data["all_application_parity"],
            all_original_search_refs_resolved=data["all_original_search_refs_resolved"],
            all_replay_receipts_resolved=data["all_replay_receipts_resolved"],
            source_science_mutated=data["source_science_mutated"],
            terminal_canonical_forms_durably_bound=data["terminal_canonical_forms_durably_bound"],
            closure_status=data["closure_status"],
            authority=data.get("authority", "NONE"),
            closure_digest=data.get("closure_digest", ""),
        )

    def validate(self) -> None:
        if self.authority != "NONE":
            raise AuthorityViolationError(f"AUTHORITY_VIOLATION: authority must be 'NONE', got '{self.authority}'")
        if self.custody_receipt_count != 24:
            raise ReceiptValidationError(f"INVALID_RECEIPT_COUNT: Expected 24, got {self.custody_receipt_count}")
        if self.paired_unit_count != 12:
            raise ReceiptValidationError(f"INVALID_PAIRED_UNIT_COUNT: Expected 12, got {self.paired_unit_count}")
        if not self.source_result_digest_verified:
            raise ReceiptValidationError("SOURCE_RESULT_NOT_VERIFIED")
        if not self.all_terminal_digest_parity:
            raise ReceiptValidationError("TERMINAL_PARITY_FAILED")
        if not self.all_metric_parity:
            raise ReceiptValidationError("METRIC_PARITY_FAILED")
        if not self.all_application_parity:
            raise ReceiptValidationError("APPLICATION_PARITY_FAILED")
        if not self.all_original_search_refs_resolved:
            raise ReceiptValidationError("ORIGINAL_SEARCH_REFS_UNRESOLVED")
        if not self.all_replay_receipts_resolved:
            raise ReceiptValidationError("REPLAY_RECEIPTS_UNRESOLVED")
        if self.source_science_mutated:
            raise ReceiptValidationError("SOURCE_SCIENCE_MUTATED")
        if self.terminal_canonical_forms_durably_bound != "YES":
            raise ReceiptValidationError("TERMINAL_CANONICAL_FORMS_NOT_DURABLY_BOUND")
        if self.closure_status != "R1_EVIDENCE_CUSTODY_CLOSED":
            raise ReceiptValidationError(f"CLOSURE_STATUS_INVALID: {self.closure_status}")
