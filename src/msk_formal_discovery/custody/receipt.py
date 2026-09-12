"""Terminal State Custody Receipt model and validation (WO-MATH-FORMAL-DISCOVERY-01B-R2 Section 6)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import jsonschema

from msk_formal_discovery.core.exceptions import ReceiptValidationError, AuthorityViolationError
from msk_formal_discovery.core.terms import Term

SCHEMAS_DIR = Path(__file__).resolve().parents[3] / "schemas"
CUSTODY_RECEIPT_SCHEMA_PATH = SCHEMAS_DIR / "terminal-state-custody-receipt.v0.1.schema.json"


def compute_custody_receipt_digest(data: Dict[str, Any]) -> str:
    """Compute deterministic SHA-256 digest of custody receipt excluding receipt_digest."""
    d = {k: v for k, v in data.items() if k != "receipt_digest"}
    serialized = json.dumps(d, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass
class TerminalStateCustodyReceipt:
    """Receipt proving durable custody from search run to terminal canonical AST (Sections 6 & 7)."""
    schema_version: str
    custody_receipt_id: str
    custody_mode: str
    source_experiment_id: str
    source_work_order: str
    source_execution_commit: str
    source_execution_tree: str
    source_result_ref: str
    source_result_sha256: str
    problem_id: str
    problem_digest: str
    arm: str
    candidate_id: str
    candidate_enabled: bool
    candidate_application_status: str
    candidate_application_count: int
    search_run_ref: str
    search_run_digest: str
    original_search_receipt_ref: str
    original_search_receipt_digest: str
    replay_search_run_ref: str
    replay_search_run_digest: str
    terminal_state_id: str
    terminal_canonical_representation: str
    terminal_expression_digest: str
    source_recorded_terminal_digest: str
    terminal_digest_parity: bool
    nodes_expanded: int
    nodes_evaluated: int
    branch_count: int
    solved: bool
    metric_parity: bool
    application_parity: bool
    implementation_digests: Dict[str, str]
    replayed_at: str
    authority: str
    receipt_digest: str = ""
    replay_search_receipt_ref: str = ""
    replay_search_receipt_digest: str = ""

    def __post_init__(self) -> None:
        if not self.receipt_digest:
            self.receipt_digest = self.compute_digest()

    def compute_digest(self) -> str:
        return compute_custody_receipt_digest(self.to_dict())

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "schema_version": self.schema_version,
            "custody_receipt_id": self.custody_receipt_id,
            "custody_mode": self.custody_mode,
            "source_experiment_id": self.source_experiment_id,
            "source_work_order": self.source_work_order,
            "source_execution_commit": self.source_execution_commit,
            "source_execution_tree": self.source_execution_tree,
            "source_result_ref": self.source_result_ref,
            "source_result_sha256": self.source_result_sha256,
            "problem_id": self.problem_id,
            "problem_digest": self.problem_digest,
            "arm": self.arm,
            "candidate_id": self.candidate_id,
            "candidate_enabled": self.candidate_enabled,
            "candidate_application_status": self.candidate_application_status,
            "candidate_application_count": self.candidate_application_count,
            "search_run_ref": self.search_run_ref,
            "search_run_digest": self.search_run_digest,
            "original_search_receipt_ref": self.original_search_receipt_ref,
            "original_search_receipt_digest": self.original_search_receipt_digest,
            "replay_search_run_ref": self.replay_search_run_ref,
            "replay_search_run_digest": self.replay_search_run_digest,
            "terminal_state_id": self.terminal_state_id,
            "terminal_canonical_representation": self.terminal_canonical_representation,
            "terminal_expression_digest": self.terminal_expression_digest,
            "source_recorded_terminal_digest": self.source_recorded_terminal_digest,
            "terminal_digest_parity": self.terminal_digest_parity,
            "nodes_expanded": self.nodes_expanded,
            "nodes_evaluated": self.nodes_evaluated,
            "branch_count": self.branch_count,
            "solved": self.solved,
            "metric_parity": self.metric_parity,
            "application_parity": self.application_parity,
            "implementation_digests": self.implementation_digests,
            "replayed_at": self.replayed_at,
            "authority": self.authority,
            "receipt_digest": self.receipt_digest,
        }
        if self.replay_search_receipt_ref:
            d["replay_search_receipt_ref"] = self.replay_search_receipt_ref
        if self.replay_search_receipt_digest:
            d["replay_search_receipt_digest"] = self.replay_search_receipt_digest
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TerminalStateCustodyReceipt:
        return cls(
            schema_version=data["schema_version"],
            custody_receipt_id=data["custody_receipt_id"],
            custody_mode=data["custody_mode"],
            source_experiment_id=data["source_experiment_id"],
            source_work_order=data["source_work_order"],
            source_execution_commit=data["source_execution_commit"],
            source_execution_tree=data["source_execution_tree"],
            source_result_ref=data["source_result_ref"],
            source_result_sha256=data["source_result_sha256"],
            problem_id=data["problem_id"],
            problem_digest=data["problem_digest"],
            arm=data["arm"],
            candidate_id=data["candidate_id"],
            candidate_enabled=data["candidate_enabled"],
            candidate_application_status=data["candidate_application_status"],
            candidate_application_count=data["candidate_application_count"],
            search_run_ref=data["search_run_ref"],
            search_run_digest=data["search_run_digest"],
            original_search_receipt_ref=data["original_search_receipt_ref"],
            original_search_receipt_digest=data["original_search_receipt_digest"],
            replay_search_run_ref=data["replay_search_run_ref"],
            replay_search_run_digest=data["replay_search_run_digest"],
            terminal_state_id=data["terminal_state_id"],
            terminal_canonical_representation=data["terminal_canonical_representation"],
            terminal_expression_digest=data["terminal_expression_digest"],
            source_recorded_terminal_digest=data["source_recorded_terminal_digest"],
            terminal_digest_parity=data["terminal_digest_parity"],
            nodes_expanded=data["nodes_expanded"],
            nodes_evaluated=data["nodes_evaluated"],
            branch_count=data["branch_count"],
            solved=data["solved"],
            metric_parity=data["metric_parity"],
            application_parity=data["application_parity"],
            implementation_digests=data["implementation_digests"],
            replayed_at=data["replayed_at"],
            authority=data["authority"],
            receipt_digest=data.get("receipt_digest", ""),
            replay_search_receipt_ref=data.get("replay_search_receipt_ref", ""),
            replay_search_receipt_digest=data.get("replay_search_receipt_digest", ""),
        )

    def validate(self, schema_path: Optional[Path] = None) -> None:
        """Enforce strict custody invariants (Sections 6, 8, 11-15)."""
        if self.authority != "NONE":
            raise AuthorityViolationError(
                f"AUTHORITY_VIOLATION: authority must be 'NONE', got '{self.authority}'"
            )

        if self.source_work_order == "WO-MATH-FORMAL-DISCOVERY-01B-R3":
            if not self.replay_search_receipt_ref:
                raise ReceiptValidationError("MISSING_REPLAY_SEARCH_RECEIPT_REF: replay_search_receipt_ref required for R3")
            if not self.replay_search_receipt_digest:
                raise ReceiptValidationError("MISSING_REPLAY_SEARCH_RECEIPT_DIGEST: replay_search_receipt_digest required for R3")

        if self.replay_search_receipt_ref:
            p = Path(self.replay_search_receipt_ref)
            if not p.is_file():
                repo_root = Path(__file__).resolve().parents[3]
                alt_p = repo_root / self.replay_search_receipt_ref
                if alt_p.is_file():
                    p = alt_p
            if p.is_file() and self.replay_search_receipt_digest:
                actual_file_dig = hashlib.sha256(p.read_bytes()).hexdigest()
                if actual_file_dig != self.replay_search_receipt_digest:
                    raise ReceiptValidationError(
                        f"REPLAY_SEARCH_RECEIPT_DIGEST_MISMATCH: File digest {actual_file_dig} != {self.replay_search_receipt_digest}"
                    )

        if self.custody_mode != "DETERMINISTIC_EVIDENCE_REPLAY":
            raise ReceiptValidationError(
                f"INVALID_CUSTODY_MODE: Expected 'DETERMINISTIC_EVIDENCE_REPLAY', got '{self.custody_mode}'"
            )

        target_schema = schema_path or CUSTODY_RECEIPT_SCHEMA_PATH
        if target_schema.exists():
            schema_data = json.loads(target_schema.read_text(encoding="utf-8"))
            try:
                jsonschema.validate(self.to_dict(), schema_data)
            except jsonschema.ValidationError as e:
                raise ReceiptValidationError(f"CUSTODY_RECEIPT_SCHEMA_FAILED: {e.message}") from e

        if not self.search_run_ref:
            raise ReceiptValidationError("MISSING_ORIGINAL_SEARCH_RUN_REF: search_run_ref is empty")

        if not self.original_search_receipt_digest:
            raise ReceiptValidationError("MISSING_ORIGINAL_SEARCH_RECEIPT_DIGEST: original_search_receipt_digest is empty")

        r1_expected_sha = "49f70e4a700478f8a884b7a00b67540701d87f67ff6c32afaea67a39374f0881"
        if self.source_result_sha256 != r1_expected_sha:
            raise ReceiptValidationError(
                f"ORIGINAL_RESULT_DIGEST_MISMATCH: Expected {r1_expected_sha}, got {self.source_result_sha256}"
            )

        # Invariant: REPLAY_RUN_ID != ORIGINAL_RUN_ID (Section 15)
        if self.replay_search_run_ref == self.search_run_ref:
            raise ReceiptValidationError(
                f"REPLAY_IMPERSONATION_FORBIDDEN: replay_search_run_ref '{self.replay_search_run_ref}' matches original '{self.search_run_ref}'"
            )

        if not self.terminal_canonical_representation:
            raise ReceiptValidationError("MISSING_TERMINAL_CANONICAL_FORM: terminal_canonical_representation is empty")

        # Invariant: Canonical form must parse and hash to terminal_expression_digest (Section 12)
        try:
            parsed_term = Term.parse(self.terminal_canonical_representation)
            computed_term_digest = parsed_term.digest()
        except Exception as e:
            raise ReceiptValidationError(f"INVALID_TERMINAL_CANONICAL_REPRESENTATION: {e}") from e

        if computed_term_digest != self.terminal_expression_digest:
            raise ReceiptValidationError(
                f"CANONICAL_FORM_DIGEST_MISMATCH: Computed '{computed_term_digest}' != '{self.terminal_expression_digest}'"
            )

        # Invariant: Replay terminal digest must match source recorded terminal digest (Section 11)
        if self.terminal_expression_digest != self.source_recorded_terminal_digest:
            raise ReceiptValidationError(
                f"TERMINAL_DIGEST_PARITY_FAILED: Replay '{self.terminal_expression_digest}' != source '{self.source_recorded_terminal_digest}'"
            )
        if not self.terminal_digest_parity:
            raise ReceiptValidationError("TERMINAL_DIGEST_PARITY_FLAG_FALSE: terminal_digest_parity must be true")

        # Invariant: Metric parity (Section 13)
        if not self.metric_parity:
            raise ReceiptValidationError("SEARCH_METRIC_PARITY_FAILED: Replay metrics do not match original R1 record")

        # Invariant: Application parity (Section 14)
        if not self.application_parity:
            raise ReceiptValidationError("APPLICATION_PARITY_FAILED: Replay candidate application does not match original R1 record")

        if self.arm == "BASELINE":
            if self.candidate_enabled is not False:
                raise ReceiptValidationError("BASELINE_CANDIDATE_ENABLED: candidate_enabled must be false for BASELINE arm")
            if self.candidate_application_count != 0:
                raise ReceiptValidationError("BASELINE_APPLICATION_COUNT_NONZERO: application count must be 0 for BASELINE arm")
            if self.candidate_application_status != "DISABLED":
                raise ReceiptValidationError("BASELINE_APPLICATION_STATUS_NOT_DISABLED: status must be DISABLED for BASELINE arm")

        # Invariant: Receipt digest self-consistency
        expected_digest = self.compute_digest()
        if self.receipt_digest != expected_digest:
            raise ReceiptValidationError(
                f"RECEIPT_DIGEST_MISMATCH: '{self.receipt_digest}' != recomputed '{expected_digest}'"
            )
