"""R2 Freeze Validator and Commit Invariants (WO-MATH-FORMAL-DISCOVERY-01B-R2 Sections 5, 30, 31)."""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from msk_formal_discovery.application.applicator import get_applicator_implementation_digest
from msk_formal_discovery.experiments.adjudication import get_adjudicator_implementation_digest
from msk_formal_discovery.experiments.rewrite_control import (
    get_rewrite_environment_implementation_digest,
    get_smt_control_implementation_digest,
)
from msk_formal_discovery.abstraction.selector import get_selector_implementation_digest
from msk_formal_discovery.abstraction.candidate import AbstractionCandidate

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_R1_DIR = REPO_ROOT / "experiments" / "formal-discovery-01b-r1"
DEFAULT_R2_DIR = REPO_ROOT / "experiments" / "formal-discovery-01b-r2"

R1_EXECUTION_COMMIT = "d421e48f5345b3f28493b2098b6dabaa3c4c41e0"
R1_EXECUTION_TREE = "de2faaf9be02dabca4993972d0423310e88ffbbe"
R1_RESULT_SHA256 = "49f70e4a700478f8a884b7a00b67540701d87f67ff6c32afaea67a39374f0881"
R1_CANDIDATE_ARTIFACT_DIGEST = "273a1d821e54ba6bf1832a2f1f11b338853aa9d1070d873c8b29345ba5aae903"


def create_r1_original_result_freeze(
    r1_dir: Optional[Path] = None,
    out_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Create durable source-freeze artifact for immutable R1 result (Section 5)."""
    target_r1 = r1_dir or DEFAULT_R1_DIR
    target_out = out_path or (DEFAULT_R2_DIR / "r1-original-result-freeze.json")

    res_file = target_r1 / "result.json"
    if not res_file.exists():
        raise FileNotFoundError(f"R1 result file not found: {res_file}")

    res_bytes = res_file.read_bytes()
    res_sha = hashlib.sha256(res_bytes).hexdigest()
    try:
        res_blob = subprocess.check_output(
            ["git", "rev-parse", f"HEAD:experiments/formal-discovery-01b-r1/result.json"],
            cwd=str(REPO_ROOT),
            text=True,
        ).strip()
    except Exception:
        res_blob = "unknown"

    res = json.loads(res_bytes.decode("utf-8"))

    freeze = {
        "schema_version": "miskatonic.r1-original-result-freeze.v0.1",
        "freeze_id": "r1-original-result-freeze",
        "repository": "Miskatonic-System/msk-formal-discovery",
        "source_work_order": "WO-MATH-FORMAL-DISCOVERY-01B-R1",
        "source_execution_commit": R1_EXECUTION_COMMIT,
        "source_execution_tree": R1_EXECUTION_TREE,
        "result_path": "experiments/formal-discovery-01b-r1/result.json",
        "result_git_blob": res_blob,
        "result_sha256": res_sha,
        "experiment_id": res["experiment_id"],
        "candidate_id": res["candidate"]["candidate_id"],
        "candidate_artifact_digest": res["candidate"]["artifact_digest"],
        "r1_disposition": res["adjudication"]["disposition"],
        "authority": "NONE",
        "claim_ceiling": res["claim_ceiling"],
        "replay_target": f"IMMUTABLE_R1_RESULT_AT_{R1_EXECUTION_COMMIT}",
        "units": res["per_unit_evaluations"],
        "smt_outcomes": res["smt_semantic_verification"],
        "metrics_summary": {
            "positive_total_baseline_nodes": res["adjudication"]["positive_total_baseline_nodes"],
            "positive_total_abstracted_nodes": res["adjudication"]["positive_total_abstracted_nodes"],
            "positive_node_delta": res["adjudication"]["positive_node_delta"],
            "positive_node_reduction_pct": res["adjudication"]["positive_node_reduction_pct"],
            "positive_median_delta": res["adjudication"]["positive_median_delta"],
            "positive_improved_count": res["adjudication"]["positive_improved_count"],
            "positive_total_count": res["adjudication"]["positive_total_count"],
            "negative_total_baseline_nodes": res["adjudication"]["negative_total_baseline_nodes"],
            "negative_total_abstracted_nodes": res["adjudication"]["negative_total_abstracted_nodes"],
            "negative_node_delta": res["adjudication"]["negative_node_delta"],
            "negative_applications_count": res["adjudication"]["negative_applications_count"],
        },
    }

    target_out.parent.mkdir(parents=True, exist_ok=True)
    target_out.write_text(json.dumps(freeze, indent=2), encoding="utf-8")
    return freeze


def validate_r2_freeze(
    exp_r2_dir: Optional[Path] = None,
    exp_r1_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Validate all pre-execution invariants prior to R2 Commit B (Section 30)."""
    target_r2 = exp_r2_dir or DEFAULT_R2_DIR
    target_r1 = exp_r1_dir or DEFAULT_R1_DIR

    # 1. Check R1 Result SHA256
    res_file = target_r1 / "result.json"
    if not res_file.exists():
        raise ValueError("R2_FREEZE_VALIDATION_FAILED: R1 result.json missing")
    actual_res_sha = hashlib.sha256(res_file.read_bytes()).hexdigest()
    if actual_res_sha != R1_RESULT_SHA256:
        raise ValueError(f"R2_FREEZE_VALIDATION_FAILED: R1 result.json SHA mismatch: {actual_res_sha} != {R1_RESULT_SHA256}")

    # 2. Check Candidate Digest
    cand_file = target_r1 / "candidate.json"
    if not cand_file.exists():
        raise ValueError("R2_FREEZE_VALIDATION_FAILED: R1 candidate.json missing")
    cand_dict = json.loads(cand_file.read_text(encoding="utf-8"))
    cand = AbstractionCandidate.from_dict(cand_dict)
    actual_cand_dig = cand.artifact_digest()
    if actual_cand_dig != R1_CANDIDATE_ARTIFACT_DIGEST:
        raise ValueError(f"R2_FREEZE_VALIDATION_FAILED: R1 candidate artifact digest mismatch: {actual_cand_dig}")

    # 3. Check Implementation Digests against Preregistration
    prereg_file = target_r1 / "preregistration.json"
    prereg = json.loads(prereg_file.read_text(encoding="utf-8"))
    expected_digs = prereg["implementation_digests"]

    actual_app = get_applicator_implementation_digest()
    if actual_app != expected_digs["applicator"]:
        raise ValueError(f"R2_FREEZE_VALIDATION_FAILED: Applicator digest drift: {actual_app} != {expected_digs['applicator']}")

    actual_env = get_rewrite_environment_implementation_digest()
    if actual_env != expected_digs["environment"]:
        raise ValueError(f"R2_FREEZE_VALIDATION_FAILED: Environment digest drift: {actual_env} != {expected_digs['environment']}")

    actual_sel = get_selector_implementation_digest()
    if actual_sel != expected_digs["selector"]:
        raise ValueError(f"R2_FREEZE_VALIDATION_FAILED: Selector digest drift: {actual_sel} != {expected_digs['selector']}")

    actual_smt = get_smt_control_implementation_digest()
    if actual_smt != expected_digs["smt_control"]:
        raise ValueError(f"R2_FREEZE_VALIDATION_FAILED: SMT control digest drift: {actual_smt} != {expected_digs['smt_control']}")

    actual_adj = get_adjudicator_implementation_digest()
    if actual_adj != expected_digs["adjudicator"]:
        raise ValueError(f"R2_FREEZE_VALIDATION_FAILED: Adjudicator digest drift: {actual_adj} != {expected_digs['adjudicator']}")

    # 4. Check custody schema exists
    schema_file = REPO_ROOT / "schemas" / "terminal-state-custody-receipt.v0.1.schema.json"
    if not schema_file.exists():
        raise ValueError("R2_FREEZE_VALIDATION_FAILED: terminal-state-custody-receipt.v0.1.schema.json missing")
    schema_sha = hashlib.sha256(schema_file.read_bytes()).hexdigest()

    # 5. Check r1-original-result-freeze.json exists in R2
    freeze_file = target_r2 / "r1-original-result-freeze.json"
    if not freeze_file.exists():
        raise ValueError("R2_FREEZE_VALIDATION_FAILED: r1-original-result-freeze.json missing")

    # 6. Verify zero R2 replay execution artifacts exist prior to Commit B
    receipts_dir = target_r2 / "receipts"
    if receipts_dir.exists():
        custody_receipts = list(receipts_dir.glob("custody-*.json"))
        if custody_receipts:
            raise ValueError(
                f"R2_FREEZE_VALIDATION_FAILED: Custody receipts exist prior to execution: {[r.name for r in custody_receipts]}"
            )

    scoped_onto = target_r2 / "onto-export-scoped.json"
    if scoped_onto.exists():
        raise ValueError("R2_FREEZE_VALIDATION_FAILED: onto-export-scoped.json exists prior to execution")

    closure_manifest = target_r2 / "r1-terminal-custody-closure.v0.1.json"
    if closure_manifest.exists():
        raise ValueError("R2_FREEZE_VALIDATION_FAILED: r1-terminal-custody-closure.v0.1.json exists prior to execution")

    return {
        "status": "R2_CUSTODY_FREEZE_VALIDATED",
        "r1_source_commit": R1_EXECUTION_COMMIT,
        "r1_source_tree": R1_EXECUTION_TREE,
        "r1_result_sha256": R1_RESULT_SHA256,
        "candidate_artifact_digest": R1_CANDIDATE_ARTIFACT_DIGEST,
        "custody_schema_sha256": schema_sha,
        "applicator_digest": actual_app,
        "environment_digest": actual_env,
        "selector_digest": actual_sel,
        "smt_control_digest": actual_smt,
        "adjudicator_digest": actual_adj,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


def verify_r2_commit_b_diff(
    repo_dir: Optional[Path] = None,
    commit_a_sha: str = "",
    commit_b_sha: str = "",
) -> Dict[str, Any]:
    """Verify that Commit B delta contains strictly R2 execution evidence (Section 31)."""
    target_repo = repo_dir or REPO_ROOT
    if not commit_a_sha or not commit_b_sha:
        raise ValueError("commit_a_sha and commit_b_sha required")

    out = subprocess.check_output(
        ["git", "diff", "--name-only", commit_a_sha, commit_b_sha],
        cwd=str(target_repo),
        text=True,
    )
    changed_files = [line.strip() for line in out.strip().split("\n") if line.strip()]

    prohibited_prefixes = ("src/", "schemas/", "tests/", "experiments/formal-discovery-01b-r1/", "experiments/formal-discovery-01b/")
    prohibited_exact = (
        "experiments/formal-discovery-01b-r2/r1-original-result-freeze.json",
    )

    violations = []
    for f in changed_files:
        if f.startswith(prohibited_prefixes) or f in prohibited_exact:
            violations.append(f)

    if violations:
        raise ValueError(f"R1_EVIDENCE_CUSTODY_REPLAY_DIVERGED: Prohibited files changed in Commit B: {violations}")

    return {
        "status": "COMMIT_B_DELTA_VALIDATED",
        "total_files_changed": len(changed_files),
        "changed_files": changed_files,
        "violations": [],
    }
