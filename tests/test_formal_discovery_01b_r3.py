"""Hostile custody graph, replay receipt, scope, and freeze tests for WO-MATH-FORMAL-DISCOVERY-01B-R3."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List
import unittest.mock as mock

import pytest

from msk_formal_discovery.core.exceptions import (
    AuthorityViolationError,
    CustodyGraphResolutionError,
    ReceiptValidationError,
)
from msk_formal_discovery.core.terms import Term
from msk_formal_discovery.custody.freeze import (
    DEFAULT_R1_DIR,
    DEFAULT_R2_DIR,
    DEFAULT_R3_DIR,
    R1_EXECUTION_COMMIT,
    R1_EXECUTION_TREE,
    R1_RESULT_SHA256,
    validate_r3_freeze,
    verify_r3_commit_b_diff,
)
from msk_formal_discovery.custody.manifest import (
    PairedTerminalCustodyManifest,
    TerminalCustodyClosureManifest,
)
from msk_formal_discovery.custody.receipt import (
    TerminalStateCustodyReceipt,
    compute_custody_receipt_digest,
)
from msk_formal_discovery.custody.resolver import (
    CustodyGraphResolutionReport,
    CustodyGraphResolver,
    FROZEN_R1_RESULT_DESCRIPTOR_DIGEST,
)
from msk_formal_discovery.onto.export import (
    OntoEvaluationPackage,
    OntoEvidenceRef,
    OntoExporter,
)
from msk_formal_discovery.search.executor import SearchExecutionReceipt

REPO_ROOT = Path(__file__).resolve().parents[1]
EXP_R1_DIR = REPO_ROOT / "experiments" / "formal-discovery-01b-r1"
EXP_R2_DIR = REPO_ROOT / "experiments" / "formal-discovery-01b-r2"
EXP_R3_DIR = REPO_ROOT / "experiments" / "formal-discovery-01b-r3"


def make_valid_r3_custody_receipt(tmp_path: Path) -> TerminalStateCustodyReceipt:
    """Create a fully valid baseline R3 custody receipt with a dummy replay search receipt on disk."""
    term = Term.parse("add(X, Y)")
    term_canon = term.canonical_repr()
    term_dig = term.digest()

    rep_file = tmp_path / "search-replay-baseline-test.json"
    rep_receipt = SearchExecutionReceipt(
        executor_id="msk-search-executor-v0.1",
        executor_version="0.1.0",
        executor_implementation_digest="11604c8c51ab6e4e953cff839a5655bcb188c5b2e3851b798ab16b3bb563e359",
        run_id="run-replay-001",
        problem_id="qual-r1-pos-01",
        problem_digest="0" * 64,
        backend_id="internal_search_engine",
        backend_configuration_digest="44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
        search_policy="deterministic_frontier_search",
        search_policy_configuration_digest="44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
        search_budget_digest="44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
        random_seed=42,
        corpus_context_digest="44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
        source_graph_context_digest="44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
        environment_identity_digest="44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
        candidate_id=None,
        candidate_enabled=False,
        started_at="2026-09-12T15:00:00Z",
        completed_at="2026-09-12T15:00:01Z",
        nodes_expanded=11,
        nodes_evaluated=16,
        branch_count=15,
        terminal_status="SUCCESS",
        wall_time_ms=10.0,
        resulting_trace_refs=[],
        resulting_trace_digests=[],
        initial_state_digest="0" * 64,
        transition_model_digest="0" * 64,
        search_policy_implementation_digest="0" * 64,
        candidate_application_status="DISABLED",
        candidate_application_digest="0" * 64,
        candidate_application_receipt_refs=[],
        candidate_application_receipt_digests=[],
    )
    rep_bytes = json.dumps(rep_receipt.to_dict(), indent=2).encode("utf-8")
    rep_file.write_bytes(rep_bytes)
    rep_digest = hashlib.sha256(rep_bytes).hexdigest()

    return TerminalStateCustodyReceipt(
        schema_version="miskatonic.terminal-state-custody-receipt.v0.1",
        custody_receipt_id="custody-baseline-qual-r1-pos-01",
        custody_mode="DETERMINISTIC_EVIDENCE_REPLAY",
        source_experiment_id="formal-discovery-01b-r1",
        source_work_order="WO-MATH-FORMAL-DISCOVERY-01B-R3",
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
        replay_search_run_ref="run-replay-001",
        replay_search_run_digest=rep_receipt.receipt_digest,
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
        replay_search_receipt_ref=str(rep_file),
        replay_search_receipt_digest=rep_digest,
    )


# 1. R3 Freeze validator passes on initial repo state
def test_r3_freeze_validator_passes(tmp_path: Path):
    r3_tmp = tmp_path / "formal-discovery-01b-r3"
    res = validate_r3_freeze(exp_r3_dir=r3_tmp)
    assert res["status"] == "R3_CUSTODY_FREEZE_VALIDATED"
    assert res["r1_source_commit"] == R1_EXECUTION_COMMIT
    assert res["r1_source_tree"] == R1_EXECUTION_TREE
    assert res["r1_freeze_sha256"] == FROZEN_R1_RESULT_DESCRIPTOR_DIGEST


# 2. R3 Freeze fails if R3 execution artifacts already exist
def test_r3_freeze_fails_if_artifacts_preexist(tmp_path: Path):
    r3_tmp = tmp_path / "formal-discovery-01b-r3"
    receipts = r3_tmp / "receipts"
    receipts.mkdir(parents=True)
    (receipts / "search-replay-baseline-test.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="R3_FREEZE_VALIDATION_FAILED: R3 receipts exist prior to execution"):
        validate_r3_freeze(exp_r3_dir=r3_tmp)


# 3. R3 Freeze fails if R3 closure manifest already exists
def test_r3_freeze_fails_if_closure_preexists(tmp_path: Path):
    r3_tmp = tmp_path / "formal-discovery-01b-r3"
    r3_tmp.mkdir(parents=True)
    (r3_tmp / "r1-terminal-custody-closure.v0.1.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="R3_FREEZE_VALIDATION_FAILED: r1-terminal-custody-closure.v0.1.json exists"):
        validate_r3_freeze(exp_r3_dir=r3_tmp)


# 4. R3 Custody receipt requires replay search receipt bindings
def test_r3_custody_receipt_requires_replay_search_bindings(tmp_path: Path):
    r = make_valid_r3_custody_receipt(tmp_path)
    r.replay_search_receipt_ref = ""
    with pytest.raises(ReceiptValidationError, match="MISSING_REPLAY_SEARCH_RECEIPT_REF"):
        r.validate()

    r2 = make_valid_r3_custody_receipt(tmp_path)
    r2.replay_search_receipt_digest = ""
    with pytest.raises(ReceiptValidationError, match="MISSING_REPLAY_SEARCH_RECEIPT_DIGEST"):
        r2.validate()


# 5. R3 Custody receipt fails when replay search receipt file digest mismatches
def test_r3_custody_receipt_replay_search_digest_mismatch(tmp_path: Path):
    r = make_valid_r3_custody_receipt(tmp_path)
    r.replay_search_receipt_digest = "f" * 64
    with pytest.raises(ReceiptValidationError, match="REPLAY_SEARCH_RECEIPT_DIGEST_MISMATCH"):
        r.validate()


# 6. Commit B diff validator passes on additions-only in R3
def test_r3_commit_b_diff_additions_only():
    mock_diff = (
        "A\texperiments/formal-discovery-01b-r3/receipts/search-replay-baseline-01.json\n"
        "A\texperiments/formal-discovery-01b-r3/receipts/custody-baseline-01.json\n"
        "A\texperiments/formal-discovery-01b-r3/paired-terminal-custody-manifest.v0.1.json\n"
        "A\texperiments/formal-discovery-01b-r3/r1-terminal-custody-closure.v0.1.json\n"
        "A\texperiments/formal-discovery-01b-r3/onto-export-scoped.json\n"
    )
    with mock.patch("subprocess.check_output", return_value=mock_diff):
        res = verify_r3_commit_b_diff(commit_a_sha="shaA", commit_b_sha="shaB")
        assert res["status"] == "COMMIT_B_DELTA_VALIDATED"
        assert res["total_files_added"] == 5


# 7. Commit B diff validator fails on modifications, deletions, or renames
def test_r3_commit_b_diff_fails_on_modifications():
    mock_diff = (
        "M\texperiments/formal-discovery-01b-r3/receipts/search-replay-baseline-01.json\n"
    )
    with mock.patch("subprocess.check_output", return_value=mock_diff):
        with pytest.raises(ValueError, match="NON_ADDITION_STATUS"):
            verify_r3_commit_b_diff(commit_a_sha="shaA", commit_b_sha="shaB")


# 8. Commit B diff validator fails on out-of-scope paths
def test_r3_commit_b_diff_fails_on_out_of_scope():
    mock_diff = (
        "A\tsrc/msk_formal_discovery/custody/resolver.py\n"
        "A\texperiments/formal-discovery-01b-r3/r1-terminal-custody-closure.v0.1.json\n"
    )
    with mock.patch("subprocess.check_output", return_value=mock_diff):
        with pytest.raises(ValueError, match="OUT_OF_SCOPE_PATH"):
            verify_r3_commit_b_diff(commit_a_sha="shaA", commit_b_sha="shaB")


# 9. Resolver fails when git tree of pinned commit mismatches
def test_resolver_fails_on_pinned_tree_mismatch():
    resolver = CustodyGraphResolver()
    with mock.patch("subprocess.check_output", return_value="0" * 40):
        with pytest.raises(CustodyGraphResolutionError, match="PINNED_COMMIT_TREE_MISMATCH"):
            resolver.resolve_and_verify(fail_fast=True)


# 10. Resolver fails when original search receipt cannot be dereferenced from Git
def test_resolver_fails_on_git_blob_error():
    resolver = CustodyGraphResolver()
    with mock.patch.object(resolver, "resolve_git_blob", side_effect=CustodyGraphResolutionError("GIT_BLOB_RESOLUTION_FAILED")):
        with pytest.raises(CustodyGraphResolutionError, match="GIT_BLOB_RESOLUTION_FAILED"):
            resolver.resolve_and_verify(fail_fast=True)


# 11. Resolver fails when original search receipt digest mismatches
def test_resolver_fails_on_orig_receipt_digest_mismatch():
    resolver = CustodyGraphResolver()
    # Mock original blob returning modified content
    orig_blob = b'{"modified": true}'
    with mock.patch.object(resolver, "resolve_git_blob", return_value=orig_blob):
        with pytest.raises(CustodyGraphResolutionError, match="R1_RESULT_SHA256_MISMATCH|ORIGINAL_SEARCH_RECEIPT_DIGEST_MISMATCH"):
            resolver.resolve_and_verify(fail_fast=True)


# 12. Resolver fails when search_run_ref or search_run_digest disagrees
def test_resolver_fails_on_search_run_ref_mismatch():
    # If run_id in original receipt != search_run_ref in custody receipt
    resolver = CustodyGraphResolver()
    real_resolve = resolver.resolve_git_blob
    def fake_resolve(commit, path):
        blob = real_resolve(commit, path)
        if "search-" in path:
            data = json.loads(blob.decode("utf-8"))
            data["run_id"] = "tampered-run-id"
            data["receipt_digest"] = SearchExecutionReceipt.from_dict(data).compute_digest()
            return json.dumps(data).encode("utf-8")
        return blob
    with mock.patch.object(resolver, "resolve_git_blob", side_effect=fake_resolve):
        with pytest.raises(CustodyGraphResolutionError):
            resolver.resolve_and_verify(fail_fast=True)


# 13. Resolver fails when metrics disagree across evidence edges
def test_resolver_fails_on_metric_disagreement():
    resolver = CustodyGraphResolver()
    real_resolve = resolver.resolve_git_blob
    def fake_resolve(commit, path):
        blob = real_resolve(commit, path)
        if "search-" in path:
            data = json.loads(blob.decode("utf-8"))
            data["nodes_expanded"] = 999999
            data["receipt_digest"] = SearchExecutionReceipt.from_dict(data).compute_digest()
            return json.dumps(data).encode("utf-8")
        return blob
    with mock.patch.object(resolver, "resolve_git_blob", side_effect=fake_resolve):
        with pytest.raises(CustodyGraphResolutionError):
            resolver.resolve_and_verify(fail_fast=True)


# 14. ONTO evaluation package fails on evidence_kind target semantic mismatch
def test_onto_evidence_kind_target_mismatch():
    # TERMINAL_STATE_CUSTODY_CLOSURE pointing to result freeze artifact must fail
    freeze_ref = OntoEvidenceRef(
        evidence_kind="TERMINAL_STATE_CUSTODY_CLOSURE",
        artifact_ref="experiments/formal-discovery-01b-r2/r1-original-result-freeze.json",
        artifact_digest="7a9b7a14857311e8609ced51d2e7a0c6fa5a3d4ba78a453910ff28d9302d155a",
        evidence_status="SUPPORTED",
        source_experimental_units=["unit1"],
    )
    pkg = OntoEvaluationPackage(
        package_id="pkg-test",
        candidate_id="cand-01",
        recurrence_count=1,
        representation_invariance="UNKNOWN",
        cross_search_policy_recurrence="UNKNOWN",
        cross_formal_system_recurrence="UNKNOWN",
        functional_search_benefit="SUPPORTED",
        source_traces=["t1"],
        structural_fingerprint="0" * 64,
        evidence_refs=[freeze_ref],
        functional_search_benefit_scope="NODE_EXPANSION_SEARCH_STRUCTURE",
    )
    with pytest.raises(ReceiptValidationError, match="EVIDENCE_KIND_TARGET_MISMATCH"):
        pkg.validate()

    # FROZEN_R1_SCIENTIFIC_RESULT pointing to closure manifest must fail
    closure_ref = OntoEvidenceRef(
        evidence_kind="FROZEN_R1_SCIENTIFIC_RESULT",
        artifact_ref="experiments/formal-discovery-01b-r2/r1-terminal-custody-closure.v0.1.json",
        artifact_digest="988ba97e74889c1737be7f3d5386dbb2da6da1ff65d491a62dd98018eec4a282",
        evidence_status="SUPPORTED",
        source_experimental_units=["unit1"],
    )
    pkg2 = OntoEvaluationPackage(
        package_id="pkg-test-2",
        candidate_id="cand-01",
        recurrence_count=1,
        representation_invariance="UNKNOWN",
        cross_search_policy_recurrence="UNKNOWN",
        cross_formal_system_recurrence="UNKNOWN",
        functional_search_benefit="SUPPORTED",
        source_traces=["t1"],
        structural_fingerprint="0" * 64,
        evidence_refs=[closure_ref],
        functional_search_benefit_scope="NODE_EXPANSION_SEARCH_STRUCTURE",
    )
    with pytest.raises(ReceiptValidationError, match="EVIDENCE_KIND_TARGET_MISMATCH"):
        pkg2.validate()


# 15. Closure manifest fails when closure booleans are promoted without resolution
def test_closure_manifest_fails_on_unresolved_flags():
    manifest = TerminalCustodyClosureManifest(
        schema_version="miskatonic.r1-terminal-custody-closure.v0.1",
        closure_id="closure-test",
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
        all_original_search_refs_resolved=False,  # Unresolved!
        all_replay_receipts_resolved=True,
        source_science_mutated=False,
        terminal_canonical_forms_durably_bound="YES",
        closure_status="R1_EVIDENCE_CUSTODY_GRAPH_CLOSED",
        authority="NONE",
        r3_work_order="WO-MATH-FORMAL-DISCOVERY-01B-R3",
        all_replay_search_receipts_resolved=True,
        all_smt_receipts_resolved=True,
    )
    with pytest.raises(ReceiptValidationError, match="ORIGINAL_SEARCH_REFS_UNRESOLVED"):
        manifest.validate()

    manifest.all_original_search_refs_resolved = True
    manifest.all_replay_search_receipts_resolved = False  # Unresolved replay search!
    with pytest.raises(ReceiptValidationError, match="REPLAY_SEARCH_RECEIPTS_UNRESOLVED"):
        manifest.validate()

    manifest.all_replay_search_receipts_resolved = True
    manifest.all_smt_receipts_resolved = False  # Unresolved SMT!
    with pytest.raises(ReceiptValidationError, match="SMT_RECEIPTS_UNRESOLVED"):
        manifest.validate()


# 16. Closure manifest fails when paired manifest digest mismatches
def test_closure_manifest_fails_on_paired_manifest_digest_mismatch():
    manifest = TerminalCustodyClosureManifest(
        schema_version="miskatonic.r1-terminal-custody-closure.v0.1",
        closure_id="closure-test",
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
        closure_status="R1_EVIDENCE_CUSTODY_GRAPH_CLOSED",
        authority="NONE",
        r3_work_order="WO-MATH-FORMAL-DISCOVERY-01B-R3",
        all_replay_search_receipts_resolved=True,
        all_smt_receipts_resolved=True,
        paired_manifest_ref="experiments/formal-discovery-01b-r2/paired-terminal-custody-manifest.v0.1.json",
        paired_manifest_digest="0" * 64,  # Intentionally corrupted digest
    )
    with pytest.raises(ReceiptValidationError, match="PAIRED_MANIFEST_DIGEST_MISMATCH"):
        manifest.validate()


# 17. Default-path end-to-end custody graph resolution succeeds (WO-MATH-FORMAL-DISCOVERY-01B-R3-R1)
def test_default_path_custody_graph_resolution():
    resolver = CustodyGraphResolver()
    report = resolver.resolve_and_verify(fail_fast=True)

    assert report.resolution_status == "RESOLVED_AND_VERIFIED"
    assert report.r1_result_resolved is True
    assert report.frozen_r1_result_resolved is True

    assert report.original_search_receipts_resolved == 24
    assert report.original_smt_receipts_resolved == 12
    assert report.replay_search_receipts_resolved == 24
    assert report.custody_receipts_resolved == 24

    assert report.paired_manifest_resolved is True
    assert report.closure_manifest_resolved is True
    assert report.onto_package_resolved is True

    assert report.terminal_digest_parity_count == 24
    assert report.metric_parity_count == 24
    assert report.application_parity_count == 24
    assert report.paired_terminal_parity_count == 12

    assert report.all_original_search_refs_resolved is True
    assert report.all_replay_search_receipts_resolved is True
    assert report.all_replay_receipts_resolved is True
    assert report.all_smt_receipts_resolved is True

    assert report.terminal_canonical_forms_durably_bound == "YES"
    assert report.source_science_mutated is False
    assert report.errors == []


# 18. Equivalence between default-path and explicit-path resolution (WO-MATH-FORMAL-DISCOVERY-01B-R3-R1)
def test_default_and_explicit_path_equivalence():
    resolver = CustodyGraphResolver()
    rep_default = resolver.resolve_and_verify(fail_fast=True)
    rep_explicit = resolver.resolve_and_verify(
        closure_manifest_path=Path("experiments/formal-discovery-01b-r3/r1-terminal-custody-closure.v0.1.json"),
        onto_package_path=Path("experiments/formal-discovery-01b-r3/onto-export-scoped.json"),
        paired_manifest_path=Path("experiments/formal-discovery-01b-r3/paired-terminal-custody-manifest.v0.1.json"),
        fail_fast=True,
    )
    assert rep_default.to_dict() == rep_explicit.to_dict()


# 19. Hostile control: tampering ONTO closure artifact digest fails closed (WO-MATH-FORMAL-DISCOVERY-01B-R3-R1)
@pytest.mark.parametrize("bad_digest", [
    "1" * 64,  # wrong file SHA
    "2" * 64,  # wrong internal closure digest
    "deadbeef" * 8,  # arbitrary corrupted digest
])
def test_resolver_rejects_tampered_onto_closure_digest(tmp_path: Path, bad_digest: str):
    onto_file = REPO_ROOT / "experiments" / "formal-discovery-01b-r3" / "onto-export-scoped.json"
    onto_data = json.loads(onto_file.read_text(encoding="utf-8"))
    for ref in onto_data["evidence_refs"]:
        if ref["evidence_kind"] == "TERMINAL_STATE_CUSTODY_CLOSURE":
            ref["artifact_digest"] = bad_digest
    tampered_onto = tmp_path / "onto-export-tampered.json"
    tampered_onto.write_text(json.dumps(onto_data), encoding="utf-8")

    resolver = CustodyGraphResolver()
    with pytest.raises(CustodyGraphResolutionError, match="ARTIFACT_DIGEST_MISMATCH|ONTO_CLOSURE_DIGEST_MISMATCH"):
        resolver.resolve_and_verify(onto_package_path=tampered_onto, fail_fast=True)

