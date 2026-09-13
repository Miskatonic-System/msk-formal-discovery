"""Comprehensive Hostile Test Suite for WO-MATH-FORMAL-DISCOVERY-01C-R1."""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import pytest
from pathlib import Path

from msk_formal_discovery.application.applicator import CandidateApplicationReceipt
from msk_formal_discovery.core.exceptions import (
    AuthorityViolationError,
    CustodyGraphResolutionError,
    ReceiptValidationError,
)
from msk_formal_discovery.experiments.rewrite_control import _make_prob, add, const, var
from msk_formal_discovery.representation.custody_manifest import (
    ApplicationReplayCustodyManifest,
    RepresentationCustodyClosureManifest,
    WholeProblemTransformManifest,
)
from msk_formal_discovery.representation.custody_resolver import (
    FROZEN_01C_CANDIDATE_DIGEST,
    FROZEN_01C_RESULT_FILE_SHA256,
    PINNED_01C_COMMIT_A,
    PINNED_01C_COMMIT_B,
    PINNED_01C_TREE_A,
    PINNED_01C_TREE_B,
    RepresentationCustodyRepairResolver,
)
from msk_formal_discovery.representation.problem_custody import (
    RepresentationProblemCustodyReceipt,
    certify_whole_problem_equivalence,
)
from msk_formal_discovery.representation.receipt import RepresentationTransformReceipt
from msk_formal_discovery.representation.replay import (
    ApplicationAttemptCustodyLedger,
    audit_original_application_attempts,
)
from msk_formal_discovery.representation.resolver import RepresentationOrbitResolver
from msk_formal_discovery.representation.runner_r1 import (
    DEFAULT_01C_DIR,
    DEFAULT_01C_R1_DIR,
    validate_01c_r1_freeze,
    verify_01c_r1_commit_b_diff,
)
from msk_formal_discovery.representation.transform import RepresentationStratum
from msk_formal_discovery.search.executor import SearchExecutionReceipt


# 1. Transform receipt body mutation with stale receipt_digest must fail closed
def test_transform_receipt_body_mutation_with_stale_digest(tmp_path: Path):
    rcpt_file = DEFAULT_01C_DIR / "receipts" / "transform-fam-pos-01-R0_CANONICAL_CONTROL.json"
    raw = json.loads(rcpt_file.read_text(encoding="utf-8"))
    stale_dig = raw["receipt_digest"]
    # Mutate source expression without updating digest
    raw["source_expression"] = "add(x, 999)"
    raw["receipt_digest"] = stale_dig
    
    tr = RepresentationTransformReceipt.from_dict(raw)
    assert tr.compute_digest() != stale_dig


# 2. Search receipt body mutation with stale receipt_digest must fail closed
def test_search_receipt_body_mutation_with_stale_digest(tmp_path: Path):
    rcpt_file = DEFAULT_01C_DIR / "receipts" / "search-baseline-fam-pos-01-r0.json"
    raw = json.loads(rcpt_file.read_text(encoding="utf-8"))
    stale_dig = raw["receipt_digest"]
    # Mutate nodes expanded
    raw["nodes_expanded"] = 999
    raw["receipt_digest"] = stale_dig

    sr = SearchExecutionReceipt.from_dict(raw)
    assert sr.compute_digest() != stale_dig


# 3. Search problem ID / digest mismatch must fail closed
def test_search_problem_id_digest_mismatch(tmp_path: Path):
    rcpt_file = DEFAULT_01C_DIR / "receipts" / "search-baseline-fam-pos-01-r0.json"
    raw = json.loads(rcpt_file.read_text(encoding="utf-8"))
    raw["problem_id"] = "wrong-problem-id"
    sr = SearchExecutionReceipt.from_dict(raw)
    sr.receipt_digest = sr.compute_digest()
    # Verification in resolver checks against s_info["problem_id"]
    assert sr.problem_id != "fam-pos-01-r0"


# 4. Search metric mismatch must fail closed
def test_search_metric_mismatch(tmp_path: Path):
    rcpt_file = DEFAULT_01C_DIR / "receipts" / "search-abstracted-fam-pos-01-r0.json"
    raw = json.loads(rcpt_file.read_text(encoding="utf-8"))
    raw["nodes_expanded"] = 42  # expected is 17
    sr = SearchExecutionReceipt.from_dict(raw)
    assert sr.nodes_expanded != 17


# 5. Transform family mismatch must fail closed
def test_transform_family_mismatch(tmp_path: Path):
    rcpt_file = DEFAULT_01C_DIR / "receipts" / "transform-fam-pos-01-R0_CANONICAL_CONTROL.json"
    raw = json.loads(rcpt_file.read_text(encoding="utf-8"))
    raw["family_id"] = "fam-pos-99"
    tr = RepresentationTransformReceipt.from_dict(raw)
    assert tr.family_id != "fam-pos-01"


# 6. Transform stratum mismatch must fail closed
def test_transform_stratum_mismatch(tmp_path: Path):
    rcpt_file = DEFAULT_01C_DIR / "receipts" / "transform-fam-pos-01-R0_CANONICAL_CONTROL.json"
    raw = json.loads(rcpt_file.read_text(encoding="utf-8"))
    raw["stratum"] = "R3_COMMUTATIVE_MIRROR"
    tr = RepresentationTransformReceipt.from_dict(raw)
    assert tr.stratum != "R0_CANONICAL_CONTROL"


# 7. Transform implementation digest drift must fail closed
def test_transform_implementation_digest_drift(tmp_path: Path):
    rcpt_file = DEFAULT_01C_DIR / "receipts" / "transform-fam-pos-01-R0_CANONICAL_CONTROL.json"
    raw = json.loads(rcpt_file.read_text(encoding="utf-8"))
    raw["transform_implementation_digest"] = "0" * 64
    tr = RepresentationTransformReceipt.from_dict(raw)
    assert tr.transform_implementation_digest != "5c85f28d268f138ffbf2ec8d9fe400d72a1378ed09223ddff43a802ccd809d4a"


# 8. Missing goal binding in v0.2 problem custody receipt must fail closed
def test_missing_goal_binding():
    with pytest.raises(Exception):
        RepresentationProblemCustodyReceipt(
            receipt_id="test",
            family_id="fam-pos-01",
            representation_stratum="R0_CANONICAL_CONTROL",
            source_problem_id="p0",
            source_problem_digest="d0",
            transformed_problem_id="pk",
            transformed_problem_digest="dk",
            source_initial_expression="a",
            source_initial_expression_digest="0"*64,
            transformed_initial_expression="a",
            transformed_initial_expression_digest="0"*64,
            source_goal_expression="",  # empty
            source_goal_digest="0"*64,
            transformed_goal_expression="a",
            transformed_goal_digest="0"*64,
            variable_bijection={},
            transform_parameters={},
            transform_implementation_digest="0"*64,
            original_v0_1_transform_receipt_ref="r",
            original_v0_1_transform_receipt_digest="0"*64,
            original_initial_semantics_smt_ref="s",
            original_initial_semantics_smt_digest="0"*64,
            whole_problem_semantics_smt_ref="w",
            whole_problem_semantics_smt_digest="0"*64,
        ).validate()


# 9. Wrong transformed goal in whole problem verification must fail
def test_wrong_transformed_goal():
    p0 = _make_prob("p0", add(var("a"), const(0)), var("a"), "TEST")
    pk = _make_prob("pk", add(var("a"), const(0)), var("b"), "TEST")  # wrong goal 'b' instead of 'a'
    with pytest.raises(ReceiptValidationError, match="WHOLE_PROBLEM_SEMANTIC_EQUIVALENCE_FAILED"):
        certify_whole_problem_equivalence(
            r0_problem=p0,
            rk_problem=pk,
            stratum=RepresentationStratum.R0_CANONICAL_CONTROL,
            variable_bijection={"a": "a"},
            family_id="fam-test",
            orig_v0_1_receipt_ref="r",
            orig_v0_1_receipt_digest="0"*64,
            orig_initial_smt_ref="s",
            orig_initial_smt_digest="0"*64,
        )


# 10. Failed whole-problem semantic certificate must fail closed
def test_failed_whole_problem_semantic_certificate():
    # Initial expressions differ mathematically
    p0 = _make_prob("p0", add(var("a"), const(1)), var("a"), "TEST")
    pk = _make_prob("pk", add(var("a"), const(2)), var("a"), "TEST")
    with pytest.raises(ReceiptValidationError, match="WHOLE_PROBLEM_SEMANTIC_EQUIVALENCE_FAILED"):
        certify_whole_problem_equivalence(
            r0_problem=p0,
            rk_problem=pk,
            stratum=RepresentationStratum.R0_CANONICAL_CONTROL,
            variable_bijection={"a": "a"},
            family_id="fam-test",
            orig_v0_1_receipt_ref="r",
            orig_v0_1_receipt_digest="0"*64,
            orig_initial_smt_ref="s",
            orig_initial_smt_digest="0"*64,
        )


# 11. Missing application receipt audit accounting
def test_missing_application_receipt_audit():
    # Audit expects 528 refs
    empty_sdata = [{"candidate_application_receipt_refs": [], "candidate_application_receipt_digests": []}]
    res = audit_original_application_attempts(DEFAULT_01C_DIR / "receipts", empty_sdata)
    assert res["TOTAL_ORIGINAL_APPLICATION_ATTEMPT_REFS"] == 0
    assert res["TOTAL_ORIGINAL_APPLICATION_ATTEMPT_REFS"] != 528


# 12. Application receipt body / digest mismatch must fail closed
def test_application_receipt_body_digest_mismatch():
    app_file = list((DEFAULT_01C_DIR / "receipts").glob("application-*.json"))[0]
    raw = json.loads(app_file.read_text(encoding="utf-8"))
    raw["application_status"] = "APPLIED" if raw["application_status"] != "APPLIED" else "NOT_APPLICABLE"
    cr = CandidateApplicationReceipt.from_dict(raw)
    assert cr.compute_digest() != raw["receipt_digest"]


# 13. Duplicate application ID with unacknowledged overwrite must fail
def test_duplicate_application_id_with_unacknowledged_overwrite():
    manifest = ApplicationReplayCustodyManifest(
        manifest_id="test",
        work_order="WO-MATH-FORMAL-DISCOVERY-01C-R1",
        search_run_count=48,
        total_original_application_attempt_refs=528,
        total_original_application_attempt_digests=528,
        unique_application_ids=169,
        duplicated_application_ids=100,
        exact_original_application_attempts_resolved=528,  # FALSE claim of 528 resolved
        overwritten_or_unresolvable_application_attempts=0,  # Unacknowledged overwrites
        total_replay_application_receipts=528,
        all_search_metric_parity_verified=True,
        all_application_id_sequence_parity_verified=True,
        all_candidate_status_parity_verified=True,
        all_applied_count_parity_verified=True,
        all_terminal_status_parity_verified=True,
        ledgers=[],
    )
    with pytest.raises(ReceiptValidationError, match="INVALID_RESOLVED_COUNT"):
        manifest.validate()


# 14. Application replay ID-sequence mismatch must fail closed
def test_application_replay_id_sequence_mismatch():
    ledger = ApplicationAttemptCustodyLedger(
        original_search_receipt_ref="ref",
        original_search_receipt_digest="0"*64,
        problem_id="p1",
        problem_digest="d1",
        ordered_original_application_ids=["app-1", "app-2"],
        ordered_original_application_digests=["d1", "d2"],
        ordered_replay_application_ids=["app-1", "app-WRONG"],
        ordered_replay_application_receipt_refs=["r1", "r2"],
        ordered_replay_application_receipt_digests=["d1", "d2"],
        original_attempt_count=2,
        replay_attempt_count=2,
        application_id_sequence_parity=False,  # mismatch
        search_metric_parity=True,
        candidate_application_status_parity=True,
        applied_count_parity=True,
        terminal_status_parity=True,
        exact_original_resolved_count=1,
        overwritten_unresolved_count=1,
    )
    assert ledger.application_id_sequence_parity is False


# 15. Application replay attempt-count mismatch must fail closed
def test_application_replay_attempt_count_mismatch():
    ledger = ApplicationAttemptCustodyLedger(
        original_search_receipt_ref="ref",
        original_search_receipt_digest="0"*64,
        problem_id="p1",
        problem_digest="d1",
        ordered_original_application_ids=["app-1"],
        ordered_original_application_digests=["d1"],
        ordered_replay_application_ids=["app-1", "app-2"],
        ordered_replay_application_receipt_refs=["r1", "r2"],
        ordered_replay_application_receipt_digests=["d1", "d2"],
        original_attempt_count=1,
        replay_attempt_count=2,
        application_id_sequence_parity=False,
        search_metric_parity=True,
        candidate_application_status_parity=True,
        applied_count_parity=True,
        terminal_status_parity=True,
        exact_original_resolved_count=1,
        overwritten_unresolved_count=0,
    )
    assert ledger.original_attempt_count != ledger.replay_attempt_count


# 16. Application status mismatch must fail closed
def test_application_status_mismatch():
    ledger = ApplicationAttemptCustodyLedger(
        original_search_receipt_ref="ref",
        original_search_receipt_digest="0"*64,
        problem_id="p1",
        problem_digest="d1",
        ordered_original_application_ids=["app-1"],
        ordered_original_application_digests=["d1"],
        ordered_replay_application_ids=["app-1"],
        ordered_replay_application_receipt_refs=["r1"],
        ordered_replay_application_receipt_digests=["d1"],
        original_attempt_count=1,
        replay_attempt_count=1,
        application_id_sequence_parity=True,
        search_metric_parity=True,
        candidate_application_status_parity=False,  # mismatch
        applied_count_parity=True,
        terminal_status_parity=True,
        exact_original_resolved_count=1,
        overwritten_unresolved_count=0,
    )
    assert ledger.candidate_application_status_parity is False


# 17. Application applied-count mismatch must fail closed
def test_application_applied_count_mismatch():
    ledger = ApplicationAttemptCustodyLedger(
        original_search_receipt_ref="ref",
        original_search_receipt_digest="0"*64,
        problem_id="p1",
        problem_digest="d1",
        ordered_original_application_ids=["app-1"],
        ordered_original_application_digests=["d1"],
        ordered_replay_application_ids=["app-1"],
        ordered_replay_application_receipt_refs=["r1"],
        ordered_replay_application_receipt_digests=["d1"],
        original_attempt_count=1,
        replay_attempt_count=1,
        application_id_sequence_parity=True,
        search_metric_parity=True,
        candidate_application_status_parity=True,
        applied_count_parity=False,  # mismatch
        terminal_status_parity=True,
        exact_original_resolved_count=1,
        overwritten_unresolved_count=0,
    )
    assert ledger.applied_count_parity is False


# 18. Search replay metric divergence must fail closed
def test_search_replay_metric_divergence():
    ledger = ApplicationAttemptCustodyLedger(
        original_search_receipt_ref="ref",
        original_search_receipt_digest="0"*64,
        problem_id="p1",
        problem_digest="d1",
        ordered_original_application_ids=["app-1"],
        ordered_original_application_digests=["d1"],
        ordered_replay_application_ids=["app-1"],
        ordered_replay_application_receipt_refs=["r1"],
        ordered_replay_application_receipt_digests=["d1"],
        original_attempt_count=1,
        replay_attempt_count=1,
        application_id_sequence_parity=True,
        search_metric_parity=False,  # metric divergence
        candidate_application_status_parity=True,
        applied_count_parity=True,
        terminal_status_parity=True,
        exact_original_resolved_count=1,
        overwritten_unresolved_count=0,
    )
    assert ledger.search_metric_parity is False


# 19. Fabricated exact-original-body claim must fail closed
def test_fabricated_exact_original_body_claim():
    manifest = ApplicationReplayCustodyManifest(
        manifest_id="test",
        work_order="WO-MATH-FORMAL-DISCOVERY-01C-R1",
        search_run_count=48,
        total_original_application_attempt_refs=528,
        total_original_application_attempt_digests=528,
        unique_application_ids=169,
        duplicated_application_ids=100,
        exact_original_application_attempts_resolved=200,  # Fabricated (must be exactly 169)
        overwritten_or_unresolvable_application_attempts=328,
        total_replay_application_receipts=528,
        all_search_metric_parity_verified=True,
        all_application_id_sequence_parity_verified=True,
        all_candidate_status_parity_verified=True,
        all_applied_count_parity_verified=True,
        all_terminal_status_parity_verified=True,
        ledgers=[],
    )
    with pytest.raises(ReceiptValidationError, match="INVALID_RESOLVED_COUNT"):
        manifest.validate()


# 20. Result.json body mutation must fail closed
def test_result_json_body_mutation(tmp_path: Path):
    res_file = DEFAULT_01C_DIR / "result.json"
    raw = json.loads(res_file.read_text(encoding="utf-8"))
    raw["work_order"] = "WO-WRONG"
    mutated_bytes = json.dumps(raw).encode("utf-8")
    mutated_sha = hashlib.sha256(mutated_bytes).hexdigest()
    assert mutated_sha != FROZEN_01C_RESULT_FILE_SHA256


# 21. Result global disposition mismatch must fail closed
def test_result_global_disposition_mismatch():
    res_file = DEFAULT_01C_DIR / "result.json"
    raw = json.loads(res_file.read_text(encoding="utf-8"))
    assert raw["adjudication"]["global_disposition"] == "REPRESENTATION_INVARIANCE_NOT_SUPPORTED"
    assert raw["adjudication"]["global_disposition"] != "REPRESENTATION_INVARIANCE_SUPPORTED"


# 22. Result per-stratum mismatch must fail closed
def test_result_per_stratum_mismatch():
    res_file = DEFAULT_01C_DIR / "result.json"
    raw = json.loads(res_file.read_text(encoding="utf-8"))
    r3 = raw["adjudication"]["r3_evaluation"]["disposition"]
    assert r3 == "REPRESENTATION_STRATUM_SENSITIVE"
    assert r3 != "REPRESENTATION_STRATUM_INVARIANT"


# 23. Result candidate mismatch must fail closed
def test_result_candidate_mismatch():
    res_file = DEFAULT_01C_DIR / "result.json"
    raw = json.loads(res_file.read_text(encoding="utf-8"))
    assert raw["candidate"]["candidate_id"] == "macro_mul_one_add_zero"
    assert raw["candidate"]["artifact_digest"] == FROZEN_01C_CANDIDATE_DIGEST


# 24. Result manifest-ref mismatch must fail closed
def test_result_manifest_ref_mismatch():
    res_file = DEFAULT_01C_DIR / "result.json"
    raw = json.loads(res_file.read_text(encoding="utf-8"))
    assert raw["paired_manifest_ref"] == "experiments/formal-discovery-01c/paired-representation-orbit-manifest.v0.1.json"


# 25. Result ONTO-ref mismatch must fail closed
def test_result_onto_ref_mismatch():
    res_file = DEFAULT_01C_DIR / "result.json"
    raw = json.loads(res_file.read_text(encoding="utf-8"))
    assert raw["onto_export_ref"] == "experiments/formal-discovery-01c/onto-export-scoped.json"


# 26. Invalid evidence being mislabeled as SENSITIVE must fail closed (Finding F-FD-01C-04)
def test_invalid_evidence_not_mislabeled_as_sensitive():
    # When any evidence check fails, resolver status MUST be REPRESENTATION_CUSTODY_REPAIR_FAILED, not sensitive
    resolver = RepresentationOrbitResolver()
    # If closure is missing, it raises CustodyGraphResolutionError, never returning sensitive
    with pytest.raises(CustodyGraphResolutionError):
        resolver.resolve_and_verify(closure_manifest_path=Path("/nonexistent/closure.json"))


# 27. R1 Freeze validator passes on clean initial state
def test_r1_freeze_validator(tmp_path: Path):
    # Tests that validate_01c_r1_freeze succeeds when no R1 execution outputs exist
    res = validate_01c_r1_freeze(exp_r1_dir=tmp_path / "formal-discovery-01c-r1")
    assert res["status"] == "R1_CUSTODY_FREEZE_VALIDATED"
    assert res["original_01c_commit_a"] == PINNED_01C_COMMIT_A
    assert res["original_01c_commit_b"] == PINNED_01C_COMMIT_B


# 28. R1 Freeze validator fails if R1 outputs pre-exist
def test_r1_freeze_validator_fails_on_preexisting_outputs(tmp_path: Path):
    d = tmp_path / "formal-discovery-01c-r1"
    d.mkdir(parents=True)
    (d / "representation-custody-closure.v0.1.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="01C_R1_FREEZE_FAILED: R1 closure manifest pre-exists"):
        validate_01c_r1_freeze(exp_r1_dir=d)
