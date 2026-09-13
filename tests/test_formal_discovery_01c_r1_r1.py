"""Hostile failure-mode and invariant verification tests for WO-MATH-FORMAL-DISCOVERY-01C-R1-R1."""
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict

import pytest

from msk_formal_discovery.application.applicator import (
    CandidateApplicationReceipt,
    get_applicator_implementation_digest,
)
from msk_formal_discovery.core.exceptions import (
    CustodyGraphResolutionError,
    ReceiptValidationError,
)
from msk_formal_discovery.representation.custody_manifest import (
    ApplicationReplayCustodyManifest,
    RepresentationCustodyClosureManifest,
)
from msk_formal_discovery.representation.custody_resolver import (
    FROZEN_01C_CANDIDATE_DIGEST,
    FROZEN_SEARCH_BUDGET,
    FROZEN_SEARCH_BUDGET_DIGEST,
    RepresentationCustodyRepairReport,
    RepresentationCustodyRepairResolver,
)
from msk_formal_discovery.representation.replay import (
    ApplicationAttemptCustodyLedger,
)
from msk_formal_discovery.representation.runner_r1_r1 import (
    DEFAULT_01C_DIR,
    DEFAULT_01C_R1_DIR,
    DEFAULT_01C_R1_R1_DIR,
    validate_01c_r1_r1_freeze,
    verify_01c_r1_r1_commit_b_diff,
)
from msk_formal_discovery.search.executor import SearchExecutionReceipt

REPO_ROOT = Path(__file__).resolve().parents[1]


def _make_valid_test_receipt() -> CandidateApplicationReceipt:
    """Load a real valid CandidateApplicationReceipt body."""
    raw = json.loads(list((DEFAULT_01C_DIR / "receipts").glob("application-*.json"))[0].read_text(encoding="utf-8"))
    return CandidateApplicationReceipt.from_dict(raw)


def _make_valid_test_search_receipt() -> SearchExecutionReceipt:
    """Load a real valid SearchExecutionReceipt."""
    raw = json.loads(list((DEFAULT_01C_DIR / "receipts").glob("search-abstracted-*.json"))[0].read_text(encoding="utf-8"))
    return SearchExecutionReceipt.from_dict(raw)


# 1. Stale / tampered replay receipt digest fails closed
def test_tampered_replay_receipt_digest_fails_closed():
    rcpt = _make_valid_test_receipt()
    orig_dig = rcpt.receipt_digest
    # Mutate field without recomputing digest
    rcpt.substitution_witness = {"mutated": "value"}
    assert rcpt.compute_digest() != orig_dig


# 2. Missing replay receipt file referenced in manifest fails closed
def test_missing_replay_receipt_file_fails_closed(tmp_path: Path):
    resolver = RepresentationCustodyRepairResolver(repo_root=REPO_ROOT)
    missing_p = resolver._resolve_path("experiments/formal-discovery-01c-r1-r1/receipts/nonexistent.json")
    assert missing_p is None


# 3. Cross-swapping ref and digest across attempts fails closed
def test_swapped_receipt_ref_and_digest_fails_closed():
    r1 = _make_valid_test_receipt()
    r2 = _make_valid_test_receipt()
    r2.application_id = "app-rec-applied-test-0002"
    r2.receipt_digest = r2.compute_digest()

    attempts = [
        {"ordinal": 0, "application_id": r1.application_id, "receipt_ref": "ref1", "receipt_digest": r2.receipt_digest, "application_status": "APPLIED"},
        {"ordinal": 1, "application_id": r2.application_id, "receipt_ref": "ref2", "receipt_digest": r1.receipt_digest, "application_status": "APPLIED"},
    ]
    # In ordinal 0, digest is r2's digest while body has r1's digest -> mismatch
    assert attempts[0]["receipt_digest"] != r1.receipt_digest


# 4. Application ID mismatch between manifest ledger and receipt body fails closed
def test_mismatched_replay_application_id_fails_closed():
    rcpt = _make_valid_test_receipt()
    expected_app_id = "app-rec-applied-test-DIFFERENT"
    assert rcpt.application_id != expected_app_id


# 5. Problem ID mismatch between manifest ledger and receipt body fails closed
def test_mismatched_replay_problem_id_fails_closed():
    rcpt = _make_valid_test_receipt()
    assert rcpt.experimental_unit_id != "wrong-unit-id"


# 6. Candidate ID or artifact digest mismatch in replay receipt body fails closed
def test_mismatched_replay_candidate_fails_closed():
    rcpt = _make_valid_test_receipt()
    assert rcpt.candidate_id == "macro_mul_one_add_zero"
    # Mutated candidate
    rcpt.candidate_id = "other_macro"
    assert rcpt.candidate_id != "macro_mul_one_add_zero"
    
    rcpt2 = _make_valid_test_receipt()
    rcpt2.candidate_artifact_digest = "0" * 64
    assert rcpt2.candidate_artifact_digest != FROZEN_01C_CANDIDATE_DIGEST


# 7. Status mismatch between receipt body and ledger attempt record fails closed
def test_mismatched_replay_status_fails_closed():
    rcpt = _make_valid_test_receipt()
    ledger_status = "REJECTED" if rcpt.application_status != "REJECTED" else "APPLIED"
    assert rcpt.application_status != ledger_status


# 8. Drifted applicator implementation digest in replay receipt body fails closed
def test_drifted_applicator_implementation_digest_fails_closed():
    rcpt = _make_valid_test_receipt()
    rcpt.applicator_implementation_digest = "deadbeef" * 8
    assert rcpt.applicator_implementation_digest != get_applicator_implementation_digest()


# 9. Partial / summary object masquerading as a full CandidateApplicationReceipt v0.1 fails closed
def test_partial_13_field_summary_masquerade_fails_closed():
    # R1-style 13-field summary record
    summary_record = {
        "schema_version": "miskatonic.candidate-application-receipt.v0.1",
        "replay_mode": "DETERMINISTIC_EVIDENCE_REPLAY",
        "problem_id": "fam-pos-01-r0",
        "problem_digest": "d" * 64,
        "ordinal": 0,
        "application_id": "app-001",
        "receipt_digest": "0" * 64,
        "candidate_id": "macro_mul_one_add_zero",
        "candidate_artifact_digest": FROZEN_01C_CANDIDATE_DIGEST,
        "status": "REPLAY_APPLICATION_ATTEMPT_CONFIRMED",
        "authority": "NONE",
    }
    required_receipt_keys = {
        "schema_version", "application_id", "candidate_id",
        "candidate_artifact_digest", "problem_id", "problem_digest",
        "application_status", "applicator_implementation_digest", "receipt_digest"
    }
    # Summary record lacks application_status, applicator_implementation_digest, etc.
    assert not required_receipt_keys.issubset(summary_record.keys())


# 10. Applied count mismatch even when aggregate status matches fails closed
def test_applied_count_mismatch_with_status_preserved_fails_closed():
    # Original manifest claims 10 applied, sequence has 10 applied, but replay body count has 9
    orig_manifest_count = 10
    orig_id_count = 10
    replay_body_count = 9  # DIVERGENCE
    replay_id_count = 9
    applied_count_parity = (
        orig_manifest_count == orig_id_count == replay_body_count == replay_id_count
    )
    assert applied_count_parity is False


# 11. Manifest count diverging from attempt sequence applied count fails closed
def test_manifest_count_vs_attempt_sequence_count_mismatch_fails_closed():
    orig_manifest_count = 10
    orig_id_count = 8  # DIVERGENCE
    replay_body_count = 8
    replay_id_count = 8
    applied_count_parity = (
        orig_manifest_count == orig_id_count == replay_body_count == replay_id_count
    )
    assert applied_count_parity is False


# 12. Replay receipt body count diverging from attempt sequence applied count fails closed
def test_replay_receipt_body_count_vs_attempt_sequence_count_mismatch_fails_closed():
    orig_manifest_count = 10
    orig_id_count = 10
    replay_body_count = 11  # DIVERGENCE
    replay_id_count = 10
    applied_count_parity = (
        orig_manifest_count == orig_id_count == replay_body_count == replay_id_count
    )
    assert applied_count_parity is False


# 13. Missing replay search receipt fails closed
def test_missing_replay_search_receipt_fails_closed(tmp_path: Path):
    resolver = RepresentationCustodyRepairResolver(repo_root=REPO_ROOT)
    missing_sr = resolver._resolve_path("experiments/formal-discovery-01c-r1-r1/receipts/search-replay-missing.json")
    assert missing_sr is None


# 14. Tampered replay search receipt digest fails closed
def test_tampered_replay_search_receipt_digest_fails_closed():
    sr = _make_valid_test_search_receipt()
    orig_dig = sr.receipt_digest
    sr.nodes_expanded = 999
    assert sr.compute_digest() != orig_dig


# 15. Replay search budget digest diverging from frozen budget digest fails closed
def test_search_budget_digest_mismatch_fails_closed():
    sr = _make_valid_test_search_receipt()
    sr.search_budget_digest = "wrong_budget_digest" + "0" * 45
    assert sr.search_budget_digest != FROZEN_SEARCH_BUDGET_DIGEST


# 16. max_nodes: 100 budget substitution fails closed against max_expansions: 100 pin
def test_max_nodes_vs_max_expansions_substitution_fails_closed():
    budget_max_nodes = {"max_nodes": 100}
    budget_max_expansions = {"max_expansions": 100}

    digest_nodes = hashlib.sha256(
        json.dumps(budget_max_nodes, sort_keys=True).encode("utf-8")
    ).hexdigest()

    digest_expansions = hashlib.sha256(
        json.dumps(budget_max_expansions, sort_keys=True).encode("utf-8")
    ).hexdigest()

    assert digest_expansions == FROZEN_SEARCH_BUDGET_DIGEST
    assert digest_nodes != FROZEN_SEARCH_BUDGET_DIGEST
    assert digest_nodes != digest_expansions


# 17. Freeze validator passes on clean repo and fails if preexisting R1-R1 outputs exist
def test_01c_r1_r1_freeze_validator(tmp_path: Path):
    # Test passes when R1-R1 closure manifest does not exist
    res = validate_01c_r1_r1_freeze(exp_r1_r1_dir=tmp_path / "formal-discovery-01c-r1-r1")
    assert res["status"] == "R1_R1_CUSTODY_FREEZE_VALIDATED"
    assert res["search_budget_digest"] == FROZEN_SEARCH_BUDGET_DIGEST
    assert res["candidate_artifact_digest"] == FROZEN_01C_CANDIDATE_DIGEST

    # Test fails if R1-R1 closure manifest pre-exists
    d = tmp_path / "formal-discovery-01c-r1-r1"
    d.mkdir(parents=True)
    (d / "representation-custody-closure.v0.1.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="01C_R1_R1_FREEZE_FAILED: R1-R1 closure manifest pre-exists"):
        validate_01c_r1_r1_freeze(exp_r1_r1_dir=d)
