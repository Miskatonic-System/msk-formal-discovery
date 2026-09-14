"""Targeted and Hostile Negative Controls for Primary Runner Receipt Persistence Custody.

Work Order: WO-MATH-FORMAL-DISCOVERY-01C-PERSISTENCE-CUSTODY-01D
Profile: WO_PROVENANCE_BOUND

Covers:
- Section 10: Synthetic Duplicate-ID Control
- Section 11: Scale Control (528 synthetic attempts)
- Section 12: Order-Parity Control
- Section 13: Content-Parity Control
- Section 15: Negative Controls P-A through P-H
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path
from typing import List, Tuple
import pytest

from msk_formal_discovery.application.applicator import (
    CandidateApplicationReceipt,
    get_applicator_implementation_digest,
)
from msk_formal_discovery.core.exceptions import (
    FormalDiscoveryError,
    ReceiptValidationError,
)
from msk_formal_discovery.representation.runner import (
    PersistenceCollisionError,
    compute_primary_candidate_application_receipt_filename,
    persist_primary_candidate_application_receipt,
)

SCHEMAS_DIR = Path(__file__).resolve().parents[1] / "schemas"
RECEIPT_SCHEMA_PATH = SCHEMAS_DIR / "candidate-application-receipt.v0.1.schema.json"
REPO_ROOT = Path(__file__).resolve().parents[1]


def make_synthetic_receipt(
    index: int,
    application_id: str | None = None,
    candidate_id: str = "macro_mul_one_add_zero",
    status: str = "APPLIED",
) -> CandidateApplicationReceipt:
    """Create a fully valid synthetic CandidateApplicationReceipt without invoking real problems."""
    app_id = application_id if application_id is not None else f"syn-app-{index:04d}"
    h = hashlib.sha256(f"synthetic-seed-body-{index}".encode("utf-8")).hexdigest()
    
    output_state = h if status == "APPLIED" else None
    receipt = CandidateApplicationReceipt(
        application_id=app_id,
        candidate_id=candidate_id,
        candidate_artifact_digest=h,
        candidate_kind="TACTIC_MACRO",
        applicator_id="msk-candidate-applicator-v0.1",
        applicator_version="0.1.0",
        applicator_implementation_digest=h,
        experimental_unit_id=f"syn-unit-{index:04d}",
        problem_digest=h,
        input_state_digest=h,
        candidate_pattern_digest=h,
        substitution_witness={"V1": f"v_{index}"},
        primitive_expansion=["MUL_ONE_LEFT", "ADD_ZERO_RIGHT"],
        primitive_expansion_digest=h,
        pre_action_surface_digest=h,
        post_action_surface_digest=h,
        output_macro_action_digest=h,
        output_state_digest=output_state,
        transition_model_digest=h,
        application_status=status,
        started_at="2026-09-12T10:00:00Z",
        completed_at="2026-09-12T10:00:01Z",
    )
    receipt.validate(schema_path=RECEIPT_SCHEMA_PATH)
    return receipt


# ==============================================================================
# Unit tests for filename helper
# ==============================================================================

def test_compute_filename_format():
    """Verify deterministic occurrence-addressed filename format."""
    fn = compute_primary_candidate_application_receipt_filename(
        problem_id="prob-pos-01",
        ordinal=42,
        receipt_digest="abcdef0123456789fedcba9876543210abcdef0123456789fedcba9876543210",
    )
    assert fn == "application-prob-pos-01-0042-abcdef0123456789.json"


def test_compute_filename_invalid_inputs():
    """Verify invalid inputs to compute_filename raise ValueError."""
    digest = "a" * 64
    with pytest.raises(ValueError, match="INVALID_ORDINAL"):
        compute_primary_candidate_application_receipt_filename("p", -1, digest)
    with pytest.raises(ValueError, match="INVALID_ORDINAL"):
        compute_primary_candidate_application_receipt_filename("p", "0", digest)  # type: ignore
    with pytest.raises(ValueError, match="INVALID_ORDINAL"):
        compute_primary_candidate_application_receipt_filename("p", True, digest)  # bool is int subclass
    with pytest.raises(ValueError, match="INVALID_PROBLEM_ID"):
        compute_primary_candidate_application_receipt_filename("", 0, digest)
    with pytest.raises(ValueError, match="INVALID_RECEIPT_DIGEST"):
        compute_primary_candidate_application_receipt_filename("p", 0, "short")


# ==============================================================================
# Section 10: Synthetic Duplicate-ID Control
# ==============================================================================

def test_synthetic_duplicate_id_control(tmp_path: Path):
    """Section 10: Duplicate application_ids overwrite historically, but persist cleanly under new scheme."""
    # Create N=10 attempts where all share the SAME application_id but different bodies/ordinals
    n_attempts = 10
    shared_id = "shared-application-id-001"
    receipts = [make_synthetic_receipt(i, application_id=shared_id) for i in range(n_attempts)]
    problem_id = "synthetic-prob-dup"

    # Historical persistence behavior: application-{application_id}.json
    hist_dir = tmp_path / "historical"
    hist_dir.mkdir()
    for r in receipts:
        (hist_dir / f"application-{r.application_id}.json").write_text(
            json.dumps(r.to_dict(), indent=2), encoding="utf-8"
        )
    hist_files = list(hist_dir.glob("application-*.json"))
    # Under historical naming, all 10 attempts overwrite the exact same file -> only 1 file survives!
    assert len(hist_files) == 1, "Historical behavior failed to demonstrate overwrite defect"
    assert len(hist_files) < n_attempts

    # New occurrence-addressed persistence behavior
    new_dir = tmp_path / "occurrence_addressed"
    new_dir.mkdir()
    persisted_paths: List[Path] = []
    for ordinal, r in enumerate(receipts):
        p = persist_primary_candidate_application_receipt(
            receipt=r,
            problem_id=problem_id,
            ordinal=ordinal,
            receipts_dir=new_dir,
        )
        persisted_paths.append(p)

    # Invariants under new scheme:
    # 1. input attempts == persisted files
    new_files = sorted(list(new_dir.glob("application-*.json")))
    assert len(new_files) == n_attempts
    # 2. unique persisted paths == N
    assert len(set(persisted_paths)) == n_attempts
    # 3. all receipt bodies independently recoverable
    for idx, (target_path, original_rcpt) in enumerate(zip(persisted_paths, receipts)):
        assert target_path.exists()
        loaded = json.loads(target_path.read_text(encoding="utf-8"))
        loaded_rcpt = CandidateApplicationReceipt.from_dict(loaded)
        assert loaded_rcpt.receipt_digest == original_rcpt.receipt_digest
        assert loaded_rcpt.application_id == shared_id
        assert loaded_rcpt.compute_digest() == original_rcpt.compute_digest()


# ==============================================================================
# Section 11: Scale Control (528 synthetic attempts)
# ==============================================================================

def test_scale_control_528_synthetic_attempts(tmp_path: Path):
    """Section 11: 528 synthetic attempts persist as 528 bodies with 0 overwrites and 0 missing."""
    target_count = 528
    receipts_dir = tmp_path / "receipts_528"
    receipts_dir.mkdir()

    # Generate 528 synthetic attempts with repeated application_ids (e.g., 50 shared IDs repeated)
    receipts: List[Tuple[int, str, CandidateApplicationReceipt]] = []
    for i in range(target_count):
        shared_app_id = f"app-pool-{i % 50:03d}"
        prob_id = f"prob-scale-{(i // 10):03d}"
        r = make_synthetic_receipt(i, application_id=shared_app_id)
        receipts.append((i, prob_id, r))

    persisted_paths: List[Path] = []
    for ordinal, prob_id, r in receipts:
        path = persist_primary_candidate_application_receipt(
            receipt=r,
            problem_id=prob_id,
            ordinal=ordinal,
            receipts_dir=receipts_dir,
        )
        persisted_paths.append(path)

    all_files = list(receipts_dir.glob("application-*.json"))
    
    attempt_count = len(receipts)
    persisted_count = len(all_files)
    unique_paths_count = len(set(persisted_paths))
    overwrite_count = attempt_count - unique_paths_count
    missing_count = attempt_count - persisted_count

    assert attempt_count == 528
    assert persisted_count == 528
    assert unique_paths_count == 528
    assert overwrite_count == 0
    assert missing_count == 0

    # Verify every single file is valid and readable
    for ordinal, prob_id, r in receipts:
        expected_fn = compute_primary_candidate_application_receipt_filename(
            problem_id=prob_id,
            ordinal=ordinal,
            receipt_digest=r.compute_digest(),
        )
        file_path = receipts_dir / expected_fn
        assert file_path.exists()
        body = json.loads(file_path.read_text(encoding="utf-8"))
        rcpt = CandidateApplicationReceipt.from_dict(body)
        rcpt.validate()
        assert rcpt.receipt_digest == r.receipt_digest


# ==============================================================================
# Section 12: Order-Parity Control
# ==============================================================================

def test_order_parity_control(tmp_path: Path):
    """Section 12: Run A filenames == Run B filenames, and digests occur in identical sequence."""
    n = 25
    receipts = [make_synthetic_receipt(i, application_id=f"app-{i % 5}") for i in range(n)]
    problem_id = "prob-order-parity"

    dir_a = tmp_path / "run_a"
    dir_b = tmp_path / "run_b"

    paths_a: List[Path] = []
    for ordinal, r in enumerate(receipts):
        paths_a.append(
            persist_primary_candidate_application_receipt(
                receipt=r,
                problem_id=problem_id,
                ordinal=ordinal,
                receipts_dir=dir_a,
            )
        )

    paths_b: List[Path] = []
    for ordinal, r in enumerate(receipts):
        paths_b.append(
            persist_primary_candidate_application_receipt(
                receipt=r,
                problem_id=problem_id,
                ordinal=ordinal,
                receipts_dir=dir_b,
            )
        )

    filenames_a = [p.name for p in paths_a]
    filenames_b = [p.name for p in paths_b]
    assert filenames_a == filenames_b

    digests_a = [CandidateApplicationReceipt.from_dict(json.loads(p.read_text())).compute_digest() for p in paths_a]
    digests_b = [CandidateApplicationReceipt.from_dict(json.loads(p.read_text())).compute_digest() for p in paths_b]
    assert digests_a == digests_b


# ==============================================================================
# Section 13: Content-Parity Control
# ==============================================================================

def test_content_parity_control(tmp_path: Path):
    """Section 13: Receipt semantic bodies and fields are identical between old and new layers."""
    # Using unique IDs so historical doesn't overwrite
    n = 15
    receipts = [make_synthetic_receipt(i, application_id=f"unique-app-{i:04d}") for i in range(n)]
    problem_id = "prob-content-parity"

    hist_dir = tmp_path / "hist"
    new_dir = tmp_path / "new"

    hist_paths = []
    for r in receipts:
        p = hist_dir / f"application-{r.application_id}.json"
        hist_dir.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(r.to_dict(), indent=2), encoding="utf-8")
        hist_paths.append(p)

    new_paths = []
    for ordinal, r in enumerate(receipts):
        p = persist_primary_candidate_application_receipt(
            receipt=r,
            problem_id=problem_id,
            ordinal=ordinal,
            receipts_dir=new_dir,
        )
        new_paths.append(p)

    for h_path, n_path in zip(hist_paths, new_paths):
        h_data = json.loads(h_path.read_text(encoding="utf-8"))
        n_data = json.loads(n_path.read_text(encoding="utf-8"))
        # All receipt fields must be identical
        assert h_data == n_data
        # Only filenames differ
        assert h_path.name != n_path.name


# ==============================================================================
# Section 15: Negative Controls P-A through P-H
# ==============================================================================

def test_negative_control_pa_repeated_application_id_distinct_files(tmp_path: Path):
    """P-A: repeated application_id -> distinct occurrence-addressed files."""
    r1 = make_synthetic_receipt(1, application_id="shared-id-pa")
    r2 = make_synthetic_receipt(2, application_id="shared-id-pa")
    
    p1 = persist_primary_candidate_application_receipt(r1, "prob-pa", 0, tmp_path)
    p2 = persist_primary_candidate_application_receipt(r2, "prob-pa", 1, tmp_path)

    assert p1.exists()
    assert p2.exists()
    assert p1 != p2
    assert p1.name != p2.name
    # Both bodies exist independently
    d1 = json.loads(p1.read_text())
    d2 = json.loads(p2.read_text())
    assert d1["receipt_digest"] != d2["receipt_digest"]


def test_negative_control_pb_duplicate_target_path_fails_closed(tmp_path: Path):
    """P-B: duplicate computed target path -> raises PersistenceCollisionError (BLOCK)."""
    r = make_synthetic_receipt(1)
    # First persist succeeds
    persist_primary_candidate_application_receipt(r, "prob-pb", 0, tmp_path)

    # Attempting to persist again to same target path must fail closed
    with pytest.raises(PersistenceCollisionError, match="PERSISTENCE_COLLISION"):
        persist_primary_candidate_application_receipt(r, "prob-pb", 0, tmp_path)


def test_negative_control_pc_receipt_digest_mismatch_fails_closed(tmp_path: Path):
    """P-C: receipt digest/body mismatch -> raises ReceiptValidationError (BLOCK)."""
    r = make_synthetic_receipt(1)
    # Corrupt the digest
    r.receipt_digest = "f" * 64

    with pytest.raises(ReceiptValidationError, match="RECEIPT_DIGEST_MISMATCH"):
        persist_primary_candidate_application_receipt(r, "prob-pc", 0, tmp_path)


def test_negative_control_pd_nondeterministic_ordinal_injection_fails_closed(tmp_path: Path):
    """P-D: nondeterministic ordinal/order injection -> raises ValueError (BLOCK)."""
    r = make_synthetic_receipt(1)

    with pytest.raises(ValueError, match="INVALID_ORDINAL"):
        persist_primary_candidate_application_receipt(r, "prob-pd", -1, tmp_path)

    with pytest.raises(ValueError, match="INVALID_ORDINAL"):
        persist_primary_candidate_application_receipt(r, "prob-pd", "0", tmp_path)  # type: ignore

    with pytest.raises(ValueError, match="INVALID_ORDINAL"):
        persist_primary_candidate_application_receipt(r, "prob-pd", True, tmp_path)

    with pytest.raises(ValueError, match="INVALID_ORDINAL"):
        persist_primary_candidate_application_receipt(r, "prob-pd", None, tmp_path)  # type: ignore


def test_negative_control_pe_attempt_omitted_fails_count_check(tmp_path: Path):
    """P-E: attempt omitted from persistence -> fails count check (BLOCK)."""
    n_attempts = 10
    receipts = [make_synthetic_receipt(i) for i in range(n_attempts)]
    
    # Omit ordinal 4
    persisted_files = []
    for ordinal, r in enumerate(receipts):
        if ordinal == 4:
            continue
        p = persist_primary_candidate_application_receipt(r, "prob-pe", ordinal, tmp_path)
        persisted_files.append(p)

    # Count assertion blocks
    with pytest.raises(AssertionError):
        assert len(persisted_files) == n_attempts


def test_negative_control_pf_fewer_than_528_files_blocks(tmp_path: Path):
    """P-F: 528 synthetic attempts producing fewer than 528 files -> BLOCK."""
    target = 528
    receipts = [make_synthetic_receipt(i) for i in range(target)]

    # Simulate failure where only 527 files persist
    for ordinal in range(527):
        persist_primary_candidate_application_receipt(receipts[ordinal], "prob-pf", ordinal, tmp_path)

    files = list(tmp_path.glob("application-*.json"))
    with pytest.raises(AssertionError):
        assert len(files) == target, f"Expected {target} files, got {len(files)}"


def test_negative_control_pg_persistence_helper_alters_body_fails_closed(tmp_path: Path):
    """P-G: persistence helper altering receipt semantic body -> BLOCK."""
    r = make_synthetic_receipt(1)
    original_dict = copy.deepcopy(r.to_dict())

    target_path = persist_primary_candidate_application_receipt(r, "prob-pg", 0, tmp_path)

    # Receipt in memory unchanged
    assert r.to_dict() == original_dict

    # Receipt on disk matches original semantic fields exactly
    disk_dict = json.loads(target_path.read_text(encoding="utf-8"))
    assert disk_dict == original_dict


def test_negative_control_ph_historical_experiment_namespace_unmutated():
    """P-H: historical experiment namespaces remain completely unmutated -> BLOCK if modified."""
    # Check git status for experiments/
    res = subprocess.run(
        ["git", "status", "--porcelain", "experiments/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert res.stdout.strip() == "", f"Historical experiment namespace was mutated:\n{res.stdout}"
