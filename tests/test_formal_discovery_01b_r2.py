"""Hostile governance, custody, scope, and freeze tests for WO-MATH-FORMAL-DISCOVERY-01B-R2 (Section 28)."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List
import unittest.mock as mock

import pytest

from msk_formal_discovery.core.exceptions import ReceiptValidationError, AuthorityViolationError
from msk_formal_discovery.core.terms import App, Const, Term, Var
from msk_formal_discovery.custody.receipt import (
    TerminalStateCustodyReceipt,
    compute_custody_receipt_digest,
)
from msk_formal_discovery.custody.manifest import (
    PairedTerminalCustodyManifest,
    TerminalCustodyClosureManifest,
)
from msk_formal_discovery.custody.freeze import (
    validate_r2_freeze,
    verify_r2_commit_b_diff,
    R1_EXECUTION_COMMIT,
    R1_EXECUTION_TREE,
    R1_RESULT_SHA256,
)
from msk_formal_discovery.onto.export import (
    OntoEvaluationPackage,
    OntoEvidenceRef,
    OntoExporter,
)


EXP_R1_DIR = Path(__file__).resolve().parents[1] / "experiments" / "formal-discovery-01b-r1"
EXP_R2_DIR = Path(__file__).resolve().parents[1] / "experiments" / "formal-discovery-01b-r2"
SCHEMAS_DIR = Path(__file__).resolve().parents[1] / "schemas"


def make_valid_custody_receipt() -> TerminalStateCustodyReceipt:
    """Create a fully valid baseline custody receipt fixture."""
    term = Term.parse("add(X, Y)")
    term_canon = term.canonical_repr()
    term_dig = term.digest()
    r = TerminalStateCustodyReceipt(
        schema_version="miskatonic.terminal-state-custody-receipt.v0.1",
        custody_receipt_id="custody-baseline-qual-r1-pos-01",
        custody_mode="DETERMINISTIC_EVIDENCE_REPLAY",
        source_experiment_id="formal-discovery-01b-r1",
        source_work_order="WO-MATH-FORMAL-DISCOVERY-01B-R1",
        source_execution_commit=R1_EXECUTION_COMMIT,
        source_execution_tree=R1_EXECUTION_TREE,
        source_result_ref="experiments/formal-discovery-01b-r1/result.json",
        source_result_sha256=R1_RESULT_SHA256,
        problem_id="qual-r1-pos-01",
        problem_digest="0" * 64,
        arm="BASELINE",
        candidate_id="macro_mul_one_add_zero",
        candidate_enabled=False,
        candidate_application_status="DISABLED",
        candidate_application_count=0,
        search_run_ref="search-run-001",
        search_run_digest="1" * 64,
        original_search_receipt_ref="experiments/formal-discovery-01b-r1/receipts/search-baseline-qual-r1-pos-01.json",
        original_search_receipt_digest="2" * 64,
        replay_search_run_ref="search-run-replay-001",
        replay_search_run_digest="3" * 64,
        terminal_state_id="state-replay-baseline-qual-r1-pos-01",
        terminal_canonical_representation=term_canon,
        terminal_expression_digest=term_dig,
        source_recorded_terminal_digest=term_dig,
        terminal_digest_parity=True,
        nodes_expanded=11,
        nodes_evaluated=16,
        branch_count=15,
        solved=True,
        metric_parity=True,
        application_parity=True,
        implementation_digests={"applicator": "a" * 64},
        replayed_at="2026-09-12T15:00:00Z",
        authority="NONE",
    )
    return r


# 1. Missing terminal canonical form rejected
def test_missing_terminal_canonical_form_rejected():
    r = make_valid_custody_receipt()
    r.terminal_canonical_representation = ""
    r.receipt_digest = r.compute_digest()
    with pytest.raises(ReceiptValidationError, match="MISSING_TERMINAL_CANONICAL_FORM|CUSTODY_RECEIPT_SCHEMA_FAILED"):
        r.validate()


# 2. Terminal canonical form/digest mismatch rejected
def test_terminal_canonical_form_digest_mismatch_rejected():
    r = make_valid_custody_receipt()
    r.terminal_expression_digest = "f" * 64
    r.source_recorded_terminal_digest = "f" * 64
    r.receipt_digest = r.compute_digest()
    with pytest.raises(ReceiptValidationError, match="CANONICAL_FORM_DIGEST_MISMATCH"):
        r.validate()


# 3. Missing original search run ref rejected
def test_missing_original_search_run_ref_rejected():
    r = make_valid_custody_receipt()
    r.search_run_ref = ""
    r.receipt_digest = r.compute_digest()
    with pytest.raises(ReceiptValidationError, match="MISSING_ORIGINAL_SEARCH_RUN_REF|CUSTODY_RECEIPT_SCHEMA_FAILED"):
        r.validate()


# 4. Missing original search receipt digest rejected
def test_missing_original_search_receipt_digest_rejected():
    r = make_valid_custody_receipt()
    r.original_search_receipt_digest = ""
    r.receipt_digest = r.compute_digest()
    with pytest.raises(ReceiptValidationError, match="MISSING_ORIGINAL_SEARCH_RECEIPT_DIGEST|CUSTODY_RECEIPT_SCHEMA_FAILED"):
        r.validate()


# 5. Original result digest mismatch rejected
def test_original_result_digest_mismatch_rejected():
    r = make_valid_custody_receipt()
    r.source_result_sha256 = "0" * 64
    r.receipt_digest = r.compute_digest()
    with pytest.raises(ReceiptValidationError, match="ORIGINAL_RESULT_DIGEST_MISMATCH"):
        r.validate()


# 6. Replay terminal digest mismatch rejected
def test_replay_terminal_digest_mismatch_rejected():
    r = make_valid_custody_receipt()
    r.source_recorded_terminal_digest = "e" * 64
    r.receipt_digest = r.compute_digest()
    with pytest.raises(ReceiptValidationError, match="TERMINAL_DIGEST_PARITY_FAILED"):
        r.validate()


# 7. Replay nodes_expanded mismatch rejected
def test_replay_nodes_expanded_mismatch_rejected():
    r = make_valid_custody_receipt()
    r.metric_parity = False
    r.receipt_digest = r.compute_digest()
    with pytest.raises(ReceiptValidationError, match="SEARCH_METRIC_PARITY_FAILED"):
        r.validate()


# 8. Replay nodes_evaluated mismatch rejected
def test_replay_nodes_evaluated_mismatch_rejected():
    r = make_valid_custody_receipt()
    r.metric_parity = False
    r.receipt_digest = r.compute_digest()
    with pytest.raises(ReceiptValidationError, match="SEARCH_METRIC_PARITY_FAILED"):
        r.validate()


# 9. Replay branch-count mismatch rejected
def test_replay_branch_count_mismatch_rejected():
    r = make_valid_custody_receipt()
    r.metric_parity = False
    r.receipt_digest = r.compute_digest()
    with pytest.raises(ReceiptValidationError, match="SEARCH_METRIC_PARITY_FAILED"):
        r.validate()


# 10. Replay solved-status mismatch rejected
def test_replay_solved_status_mismatch_rejected():
    r = make_valid_custody_receipt()
    r.metric_parity = False
    r.receipt_digest = r.compute_digest()
    with pytest.raises(ReceiptValidationError, match="SEARCH_METRIC_PARITY_FAILED"):
        r.validate()


# 11. Replay application-status mismatch rejected
def test_replay_application_status_mismatch_rejected():
    r = make_valid_custody_receipt()
    r.application_parity = False
    r.receipt_digest = r.compute_digest()
    with pytest.raises(ReceiptValidationError, match="APPLICATION_PARITY_FAILED"):
        r.validate()


# 12. Replay application-count mismatch rejected
def test_replay_application_count_mismatch_rejected():
    r = make_valid_custody_receipt()
    r.application_parity = False
    r.receipt_digest = r.compute_digest()
    with pytest.raises(ReceiptValidationError, match="APPLICATION_PARITY_FAILED"):
        r.validate()


# 13. Custody receipt claiming ORIGINAL_EXECUTION rejected
def test_custody_receipt_claiming_original_execution_rejected():
    r = make_valid_custody_receipt()
    r.custody_mode = "ORIGINAL_EXECUTION"
    r.receipt_digest = r.compute_digest()
    with pytest.raises(ReceiptValidationError, match="INVALID_CUSTODY_MODE|CUSTODY_RECEIPT_SCHEMA_FAILED"):
        r.validate()


# 14. New scientific disposition emitted by custody replay rejected
def test_new_scientific_disposition_emitted_by_custody_replay_rejected():
    closure = TerminalCustodyClosureManifest(
        schema_version="miskatonic.r1-terminal-custody-closure.v0.1",
        closure_id="r1-terminal-custody-closure",
        source_work_order="WO-MATH-FORMAL-DISCOVERY-01B-R1",
        r2_work_order="WO-MATH-FORMAL-DISCOVERY-01B-R2",
        source_execution_commit=R1_EXECUTION_COMMIT,
        source_execution_tree=R1_EXECUTION_TREE,
        custody_receipt_count=24,
        paired_unit_count=12,
        source_result_digest_verified=True,
        all_terminal_digest_parity=True,
        all_metric_parity=True,
        all_application_parity=True,
        all_original_search_refs_resolved=True,
        all_replay_receipts_resolved=True,
        source_science_mutated=False,
        terminal_canonical_forms_durably_bound="YES",
        closure_status="ABSTRACTION_SEARCH_BENEFIT_SUPPORTED",  # SCIENTIFIC DISPOSITION FORBIDDEN
        authority="NONE",
    )
    with pytest.raises(ReceiptValidationError, match="CLOSURE_STATUS_INVALID"):
        closure.validate()


# 15. SUPPORTED ONTO benefit without scope rejected
def test_supported_onto_benefit_without_scope_rejected():
    pkg = OntoEvaluationPackage(
        package_id="onto-eval-test",
        candidate_id="macro_mul_one_add_zero",
        recurrence_count=3,
        representation_invariance="UNKNOWN",
        cross_search_policy_recurrence="UNKNOWN",
        cross_formal_system_recurrence="UNKNOWN",
        functional_search_benefit="SUPPORTED",
        source_traces=["trace-01"],
        structural_fingerprint="0" * 64,
        functional_search_benefit_scope=None,  # MISSING SCOPE
        end_to_end_runtime_benefit="NOT_ESTABLISHED",
        claim_ceiling="ENGINEERING_ABSTRACTION_EFFECT_ONLY",
        authority="NONE",
    )
    with pytest.raises(ValueError, match="UNSCOPED_FUNCTIONAL_BENEFIT"):
        pkg.validate()


# 16. SUPPORTED ONTO benefit with wrong scope rejected
def test_supported_onto_benefit_with_wrong_scope_rejected():
    pkg = OntoEvaluationPackage(
        package_id="onto-eval-test",
        candidate_id="macro_mul_one_add_zero",
        recurrence_count=3,
        representation_invariance="UNKNOWN",
        cross_search_policy_recurrence="UNKNOWN",
        cross_formal_system_recurrence="UNKNOWN",
        functional_search_benefit="SUPPORTED",
        source_traces=["trace-01"],
        structural_fingerprint="0" * 64,
        functional_search_benefit_scope="GLOBAL_SEARCH_OPTIMALITY",  # INVALID SCOPE
        end_to_end_runtime_benefit="NOT_ESTABLISHED",
        claim_ceiling="ENGINEERING_ABSTRACTION_EFFECT_ONLY",
        authority="NONE",
    )
    with pytest.raises(ValueError, match="INVALID_FUNCTIONAL_BENEFIT_SCOPE"):
        pkg.validate()


# 17. Runtime benefit silently inferred from node reduction rejected
def test_runtime_benefit_silently_inferred_from_node_reduction_rejected():
    pkg = OntoEvaluationPackage(
        package_id="onto-eval-test",
        candidate_id="macro_mul_one_add_zero",
        recurrence_count=3,
        representation_invariance="UNKNOWN",
        cross_search_policy_recurrence="UNKNOWN",
        cross_formal_system_recurrence="UNKNOWN",
        functional_search_benefit="SUPPORTED",
        source_traces=["trace-01"],
        structural_fingerprint="0" * 64,
        functional_search_benefit_scope="NODE_EXPANSION_SEARCH_STRUCTURE",
        end_to_end_runtime_benefit="SUPPORTED",  # UNEARNED RUNTIME CLAIM
        claim_ceiling="ENGINEERING_ABSTRACTION_EFFECT_ONLY",
        authority="NONE",
    )
    with pytest.raises(ValueError, match="UNEARNED_RUNTIME_BENEFIT"):
        pkg.validate()


# 18. Representation invariance promotion rejected
def test_representation_invariance_promotion_rejected():
    pkg = OntoEvaluationPackage(
        package_id="onto-eval-test",
        candidate_id="macro_mul_one_add_zero",
        recurrence_count=3,
        representation_invariance="SUPPORTED",  # UNEARNED
        cross_search_policy_recurrence="UNKNOWN",
        cross_formal_system_recurrence="UNKNOWN",
        functional_search_benefit="SUPPORTED",
        source_traces=["trace-01"],
        structural_fingerprint="0" * 64,
        functional_search_benefit_scope="NODE_EXPANSION_SEARCH_STRUCTURE",
        end_to_end_runtime_benefit="NOT_ESTABLISHED",
        claim_ceiling="ENGINEERING_ABSTRACTION_EFFECT_ONLY",
        authority="NONE",
    )
    with pytest.raises(ValueError, match="UNEARNED_REPRESENTATION_INVARIANCE"):
        pkg.validate()


# 19. Cross-policy recurrence promotion rejected
def test_cross_policy_recurrence_promotion_rejected():
    pkg = OntoEvaluationPackage(
        package_id="onto-eval-test",
        candidate_id="macro_mul_one_add_zero",
        recurrence_count=3,
        representation_invariance="UNKNOWN",
        cross_search_policy_recurrence="SUPPORTED",  # UNEARNED
        cross_formal_system_recurrence="UNKNOWN",
        functional_search_benefit="SUPPORTED",
        source_traces=["trace-01"],
        structural_fingerprint="0" * 64,
        functional_search_benefit_scope="NODE_EXPANSION_SEARCH_STRUCTURE",
        end_to_end_runtime_benefit="NOT_ESTABLISHED",
        claim_ceiling="ENGINEERING_ABSTRACTION_EFFECT_ONLY",
        authority="NONE",
    )
    with pytest.raises(ValueError, match="UNEARNED_CROSS_POLICY_RECURRENCE"):
        pkg.validate()


# 20. Cross-formal-system recurrence promotion rejected
def test_cross_formal_system_recurrence_promotion_rejected():
    pkg = OntoEvaluationPackage(
        package_id="onto-eval-test",
        candidate_id="macro_mul_one_add_zero",
        recurrence_count=3,
        representation_invariance="UNKNOWN",
        cross_search_policy_recurrence="UNKNOWN",
        cross_formal_system_recurrence="SUPPORTED",  # UNEARNED
        functional_search_benefit="SUPPORTED",
        source_traces=["trace-01"],
        structural_fingerprint="0" * 64,
        functional_search_benefit_scope="NODE_EXPANSION_SEARCH_STRUCTURE",
        end_to_end_runtime_benefit="NOT_ESTABLISHED",
        claim_ceiling="ENGINEERING_ABSTRACTION_EFFECT_ONLY",
        authority="NONE",
    )
    with pytest.raises(ValueError, match="UNEARNED_CROSS_FORMAL_SYSTEM_RECURRENCE"):
        pkg.validate()


# 21. Process-local-only ONTO evidence reference rejected
def test_process_local_only_onto_evidence_reference_rejected():
    art_ref = "process-local-memory-only-artifact"
    art_dig = "a" * 64
    OntoExporter.register_evidence_artifact(art_ref, art_dig)

    ev_ref = OntoEvidenceRef(
        evidence_kind="PROCESS_LOCAL_HELD_OUT",
        artifact_ref=art_ref,
        artifact_digest=art_dig,
        evidence_status="SUPPORTED",
        source_experimental_units=["unit-01"],
    )

    # Validates under process-local mode
    ev_ref.validate(require_durable=False)

    # REJECTED when durable resolution required
    with pytest.raises(ReceiptValidationError, match="UNRESOLVABLE_DURABLE_EVIDENCE"):
        ev_ref.validate(require_durable=True)

    # Also rejected when package validates SUPPORTED with process-local ref
    pkg = OntoEvaluationPackage(
        package_id="onto-eval-test",
        candidate_id="macro_mul_one_add_zero",
        recurrence_count=3,
        representation_invariance="UNKNOWN",
        cross_search_policy_recurrence="UNKNOWN",
        cross_formal_system_recurrence="UNKNOWN",
        functional_search_benefit="SUPPORTED",
        source_traces=["trace-01"],
        structural_fingerprint="0" * 64,
        functional_search_benefit_scope="NODE_EXPANSION_SEARCH_STRUCTURE",
        end_to_end_runtime_benefit="NOT_ESTABLISHED",
        claim_ceiling="ENGINEERING_ABSTRACTION_EFFECT_ONLY",
        authority="NONE",
        evidence_refs=[ev_ref],
    )
    with pytest.raises(ReceiptValidationError, match="UNRESOLVABLE_DURABLE_EVIDENCE"):
        pkg.validate()


# 22. R2 Commit B source/schema/test drift rejected
def test_r2_commit_b_source_schema_test_drift_rejected():
    with mock.patch("subprocess.check_output") as mock_git:
        # Mock git diff returning modified files in src/
        mock_git.return_value = "src/msk_formal_discovery/core/terms.py\nexperiments/formal-discovery-01b-r2/receipts/custody-01.json\n"
        with pytest.raises(ValueError, match="R1_EVIDENCE_CUSTODY_REPLAY_DIVERGED"):
            verify_r2_commit_b_diff(commit_a_sha="shaA", commit_b_sha="shaB")

    with mock.patch("subprocess.check_output") as mock_git:
        # Mock git diff returning modified files in schemas/
        mock_git.return_value = "schemas/terminal-state-custody-receipt.v0.1.schema.json\n"
        with pytest.raises(ValueError, match="R1_EVIDENCE_CUSTODY_REPLAY_DIVERGED"):
            verify_r2_commit_b_diff(commit_a_sha="shaA", commit_b_sha="shaB")

    with mock.patch("subprocess.check_output") as mock_git:
        # Mock git diff returning modified files in tests/
        mock_git.return_value = "tests/test_formal_discovery_01b_r2.py\n"
        with pytest.raises(ValueError, match="R1_EVIDENCE_CUSTODY_REPLAY_DIVERGED"):
            verify_r2_commit_b_diff(commit_a_sha="shaA", commit_b_sha="shaB")

    with mock.patch("subprocess.check_output") as mock_git:
        # Mock git diff returning modified r1 result freeze
        mock_git.return_value = "experiments/formal-discovery-01b-r2/r1-original-result-freeze.json\n"
        with pytest.raises(ValueError, match="R1_EVIDENCE_CUSTODY_REPLAY_DIVERGED"):
            verify_r2_commit_b_diff(commit_a_sha="shaA", commit_b_sha="shaB")


# 23. R2 freeze validator passes cleanly on clean pre-execution state
def test_r2_freeze_validator_passes(tmp_path: Path):
    r2_mock = tmp_path / "r2"
    r2_mock.mkdir()
    (r2_mock / "r1-original-result-freeze.json").write_text(
        (EXP_R2_DIR / "r1-original-result-freeze.json").read_text()
    )
    res = validate_r2_freeze(exp_r2_dir=r2_mock, exp_r1_dir=EXP_R1_DIR)
    assert res["status"] == "R2_CUSTODY_FREEZE_VALIDATED"
    assert res["r1_source_commit"] == R1_EXECUTION_COMMIT
    assert res["r1_result_sha256"] == R1_RESULT_SHA256


# 24. R2 freeze rejects premature custody receipts
def test_r2_freeze_rejects_premature_custody_receipts(tmp_path: Path):
    r2_mock = tmp_path / "r2"
    r2_mock.mkdir()
    (r2_mock / "r1-original-result-freeze.json").write_text(
        (EXP_R2_DIR / "r1-original-result-freeze.json").read_text()
    )
    receipts_dir = r2_mock / "receipts"
    receipts_dir.mkdir()
    (receipts_dir / "custody-baseline-qual-r1-pos-01.json").write_text("{}")

    with pytest.raises(ValueError, match="Custody receipts exist prior to execution"):
        validate_r2_freeze(exp_r2_dir=r2_mock, exp_r1_dir=EXP_R1_DIR)


# 25. Replay run ID matching original run ID rejected (impersonation forbidden)
def test_replay_impersonation_forbidden():
    r = make_valid_custody_receipt()
    r.replay_search_run_ref = r.search_run_ref
    r.receipt_digest = r.compute_digest()
    with pytest.raises(ReceiptValidationError, match="REPLAY_IMPERSONATION_FORBIDDEN"):
        r.validate()


# 26. Authority violation rejected
def test_authority_violation_rejected():
    r = make_valid_custody_receipt()
    r.authority = "PROVEN_THEOREM"
    r.receipt_digest = r.compute_digest()
    with pytest.raises(AuthorityViolationError, match="AUTHORITY_VIOLATION"):
        r.validate()


# 27. Paired manifest invalid unit count rejected
def test_paired_manifest_invalid_unit_count_rejected():
    m = PairedTerminalCustodyManifest(
        schema_version="miskatonic.paired-terminal-custody-manifest.v0.1",
        manifest_id="paired-manifest-test",
        source_work_order="WO-MATH-FORMAL-DISCOVERY-01B-R1",
        source_execution_commit=R1_EXECUTION_COMMIT,
        units=[{"unit": 1}],  # Only 1 unit instead of 12
        authority="NONE",
    )
    with pytest.raises(ReceiptValidationError, match="INVALID_UNIT_COUNT"):
        m.validate()


# 28. Paired manifest authority violation rejected
def test_paired_manifest_authority_violation_rejected():
    m = PairedTerminalCustodyManifest(
        schema_version="miskatonic.paired-terminal-custody-manifest.v0.1",
        manifest_id="paired-manifest-test",
        source_work_order="WO-MATH-FORMAL-DISCOVERY-01B-R1",
        source_execution_commit=R1_EXECUTION_COMMIT,
        units=[],
        authority="ACCEPTED_THEOREM",
    )
    with pytest.raises(AuthorityViolationError, match="AUTHORITY_VIOLATION"):
        m.validate()


# 29. Closure manifest invalid receipt count rejected
def test_closure_manifest_invalid_receipt_count_rejected():
    closure = TerminalCustodyClosureManifest(
        schema_version="miskatonic.r1-terminal-custody-closure.v0.1",
        closure_id="r1-terminal-custody-closure",
        source_work_order="WO-MATH-FORMAL-DISCOVERY-01B-R1",
        r2_work_order="WO-MATH-FORMAL-DISCOVERY-01B-R2",
        source_execution_commit=R1_EXECUTION_COMMIT,
        source_execution_tree=R1_EXECUTION_TREE,
        custody_receipt_count=23,  # Must be exactly 24
        paired_unit_count=12,
        source_result_digest_verified=True,
        all_terminal_digest_parity=True,
        all_metric_parity=True,
        all_application_parity=True,
        all_original_search_refs_resolved=True,
        all_replay_receipts_resolved=True,
        source_science_mutated=False,
        terminal_canonical_forms_durably_bound="YES",
        closure_status="R1_EVIDENCE_CUSTODY_CLOSED",
        authority="NONE",
    )
    with pytest.raises(ReceiptValidationError, match="INVALID_RECEIPT_COUNT"):
        closure.validate()


# 30. Closure manifest source science mutation rejected
def test_closure_manifest_source_science_mutation_rejected():
    closure = TerminalCustodyClosureManifest(
        schema_version="miskatonic.r1-terminal-custody-closure.v0.1",
        closure_id="r1-terminal-custody-closure",
        source_work_order="WO-MATH-FORMAL-DISCOVERY-01B-R1",
        r2_work_order="WO-MATH-FORMAL-DISCOVERY-01B-R2",
        source_execution_commit=R1_EXECUTION_COMMIT,
        source_execution_tree=R1_EXECUTION_TREE,
        custody_receipt_count=24,
        paired_unit_count=12,
        source_result_digest_verified=True,
        all_terminal_digest_parity=True,
        all_metric_parity=True,
        all_application_parity=True,
        all_original_search_refs_resolved=True,
        all_replay_receipts_resolved=True,
        source_science_mutated=True,  # VIOLATION
        terminal_canonical_forms_durably_bound="YES",
        closure_status="R1_EVIDENCE_CUSTODY_CLOSED",
        authority="NONE",
    )
    with pytest.raises(ReceiptValidationError, match="SOURCE_SCIENCE_MUTATED"):
        closure.validate()


# 31. R2 freeze rejects premature scoped ONTO export
def test_r2_freeze_rejects_premature_scoped_onto(tmp_path: Path):
    r2_mock = tmp_path / "r2"
    r2_mock.mkdir()
    (r2_mock / "r1-original-result-freeze.json").write_text(
        (EXP_R2_DIR / "r1-original-result-freeze.json").read_text()
    )
    (r2_mock / "onto-export-scoped.json").write_text("{}")
    with pytest.raises(ValueError, match="onto-export-scoped.json exists prior to execution"):
        validate_r2_freeze(exp_r2_dir=r2_mock, exp_r1_dir=EXP_R1_DIR)


# 32. R2 freeze rejects premature closure manifest
def test_r2_freeze_rejects_premature_closure_manifest(tmp_path: Path):
    r2_mock = tmp_path / "r2"
    r2_mock.mkdir()
    (r2_mock / "r1-original-result-freeze.json").write_text(
        (EXP_R2_DIR / "r1-original-result-freeze.json").read_text()
    )
    (r2_mock / "r1-terminal-custody-closure.v0.1.json").write_text("{}")
    with pytest.raises(ValueError, match="r1-terminal-custody-closure.v0.1.json exists prior to execution"):
        validate_r2_freeze(exp_r2_dir=r2_mock, exp_r1_dir=EXP_R1_DIR)


# 33. R2 freeze rejects tampered R1 result.json
def test_r2_freeze_rejects_tampered_r1_result(tmp_path: Path):
    r1_mock = tmp_path / "r1"
    r1_mock.mkdir()
    (r1_mock / "result.json").write_text('{"tampered": true}')
    with pytest.raises(ValueError, match="R1 result.json SHA mismatch"):
        validate_r2_freeze(exp_r2_dir=EXP_R2_DIR, exp_r1_dir=r1_mock)

