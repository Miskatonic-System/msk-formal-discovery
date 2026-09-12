"""Custody graph resolver and verifier (WO-MATH-FORMAL-DISCOVERY-01B-R3 Finding F-FD-01B-R2-01)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from msk_formal_discovery.core.exceptions import (
    CustodyGraphResolutionError,
    ReceiptValidationError,
)
from msk_formal_discovery.custody.manifest import (
    PairedTerminalCustodyManifest,
    TerminalCustodyClosureManifest,
)
from msk_formal_discovery.custody.receipt import TerminalStateCustodyReceipt
from msk_formal_discovery.onto.export import OntoEvaluationPackage
from msk_formal_discovery.search.executor import SearchExecutionReceipt

PINNED_R1_EXECUTION_COMMIT = "d421e48f5345b3f28493b2098b6dabaa3c4c41e0"
PINNED_R1_EXECUTION_TREE = "de2faaf9be02dabca4993972d0423310e88ffbbe"
FROZEN_R1_RESULT_SHA256 = "49f70e4a700478f8a884b7a00b67540701d87f67ff6c32afaea67a39374f0881"
FROZEN_R1_RESULT_DESCRIPTOR_DIGEST = "7a9b7a14857311e8609ced51d2e7a0c6fa5a3d4ba78a453910ff28d9302d155a"
FROZEN_R1_CANDIDATE_DIGEST = "273a1d821e54ba6bf1832a2f1f11b338853aa9d1070d873c8b29345ba5aae903"


@dataclass
class CustodyGraphResolutionReport:
    """Report detailing independent verification of every custody graph edge."""
    resolution_status: str
    source_execution_commit: str
    source_execution_tree: str
    r1_result_resolved: bool
    frozen_r1_result_resolved: bool
    original_search_receipts_resolved: int
    original_smt_receipts_resolved: int
    replay_search_receipts_resolved: int
    custody_receipts_resolved: int
    paired_manifest_resolved: bool
    closure_manifest_resolved: bool
    onto_package_resolved: bool
    terminal_digest_parity_count: int
    metric_parity_count: int
    application_parity_count: int
    paired_terminal_parity_count: int
    all_original_search_refs_resolved: bool
    all_replay_search_receipts_resolved: bool
    all_replay_receipts_resolved: bool
    all_smt_receipts_resolved: bool
    terminal_canonical_forms_durably_bound: str
    source_science_mutated: bool
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resolution_status": self.resolution_status,
            "source_execution_commit": self.source_execution_commit,
            "source_execution_tree": self.source_execution_tree,
            "r1_result_resolved": self.r1_result_resolved,
            "frozen_r1_result_resolved": self.frozen_r1_result_resolved,
            "original_search_receipts_resolved": self.original_search_receipts_resolved,
            "original_smt_receipts_resolved": self.original_smt_receipts_resolved,
            "replay_search_receipts_resolved": self.replay_search_receipts_resolved,
            "custody_receipts_resolved": self.custody_receipts_resolved,
            "paired_manifest_resolved": self.paired_manifest_resolved,
            "closure_manifest_resolved": self.closure_manifest_resolved,
            "onto_package_resolved": self.onto_package_resolved,
            "terminal_digest_parity_count": self.terminal_digest_parity_count,
            "metric_parity_count": self.metric_parity_count,
            "application_parity_count": self.application_parity_count,
            "paired_terminal_parity_count": self.paired_terminal_parity_count,
            "all_original_search_refs_resolved": self.all_original_search_refs_resolved,
            "all_replay_search_receipts_resolved": self.all_replay_search_receipts_resolved,
            "all_replay_receipts_resolved": self.all_replay_receipts_resolved,
            "all_smt_receipts_resolved": self.all_smt_receipts_resolved,
            "terminal_canonical_forms_durably_bound": self.terminal_canonical_forms_durably_bound,
            "source_science_mutated": self.source_science_mutated,
            "errors": list(self.errors),
        }


class CustodyGraphResolver:
    """Independently dereferences and verifies every edge of the 01B custody graph."""

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        pinned_commit: str = PINNED_R1_EXECUTION_COMMIT,
        pinned_tree: str = PINNED_R1_EXECUTION_TREE,
        r1_result_sha256: str = FROZEN_R1_RESULT_SHA256,
        frozen_r1_result_digest: str = FROZEN_R1_RESULT_DESCRIPTOR_DIGEST,
        r1_candidate_artifact_digest: str = FROZEN_R1_CANDIDATE_DIGEST,
    ) -> None:
        self.repo_root = repo_root or Path(__file__).resolve().parents[3]
        self.pinned_commit = pinned_commit
        self.pinned_tree = pinned_tree
        self.r1_result_sha256 = r1_result_sha256
        self.frozen_r1_result_digest = frozen_r1_result_digest
        self.r1_candidate_artifact_digest = r1_candidate_artifact_digest

    def resolve_git_blob(self, commit: str, relative_path: str) -> bytes:
        """Resolve blob content directly from pinned git commit."""
        try:
            return subprocess.check_output(
                ["git", "show", f"{commit}:{relative_path}"],
                cwd=str(self.repo_root),
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as e:
            msg = e.stderr.decode("utf-8", errors="replace").strip() if e.stderr else str(e)
            raise CustodyGraphResolutionError(
                f"GIT_BLOB_RESOLUTION_FAILED: Cannot resolve '{relative_path}' in commit '{commit}': {msg}"
            ) from e

    def verify_pinned_commit_and_tree(self) -> None:
        """Verify git commit and tree match pinned science identities."""
        try:
            actual_tree = subprocess.check_output(
                ["git", "rev-parse", f"{self.pinned_commit}^{{tree}}"],
                cwd=str(self.repo_root),
                stderr=subprocess.PIPE,
                text=True,
            ).strip()
        except subprocess.CalledProcessError as e:
            raise CustodyGraphResolutionError(
                f"PINNED_COMMIT_RESOLUTION_FAILED: Cannot resolve tree for commit '{self.pinned_commit}'"
            ) from e

        if actual_tree != self.pinned_tree:
            raise CustodyGraphResolutionError(
                f"PINNED_COMMIT_TREE_MISMATCH: Tree '{actual_tree}' != expected '{self.pinned_tree}'"
            )

    def resolve_and_verify(
        self,
        closure_manifest_path: Optional[Path] = None,
        onto_package_path: Optional[Path] = None,
        paired_manifest_path: Optional[Path] = None,
        fail_fast: bool = True,
    ) -> CustodyGraphResolutionReport:
        """Resolve and verify all edges in the custody graph."""
        errors: List[str] = []

        def handle_error(msg: str) -> None:
            errors.append(msg)
            if fail_fast:
                raise CustodyGraphResolutionError(msg)

        # 1. Verify Git commit and tree
        try:
            self.verify_pinned_commit_and_tree()
        except CustodyGraphResolutionError as e:
            handle_error(str(e))

        # 2. Resolve R1 result from pinned Git commit
        r1_result_resolved = False
        r1_result_data: Dict[str, Any] = {}
        per_unit_evaluations: Dict[str, Any] = {}
        try:
            raw_res = self.resolve_git_blob(self.pinned_commit, "experiments/formal-discovery-01b-r1/result.json")
            actual_sha = hashlib.sha256(raw_res).hexdigest()
            if actual_sha != self.r1_result_sha256:
                handle_error(f"R1_RESULT_SHA256_MISMATCH: Computed {actual_sha} != {self.r1_result_sha256}")
            r1_result_data = json.loads(raw_res.decode("utf-8"))
            cand = r1_result_data.get("candidate", {})
            if cand.get("artifact_digest") != self.r1_candidate_artifact_digest:
                handle_error(f"R1_CANDIDATE_DIGEST_MISMATCH: {cand.get('artifact_digest')} != {self.r1_candidate_artifact_digest}")
            for u in r1_result_data.get("per_unit_evaluations", []):
                per_unit_evaluations[u["problem_id"]] = u
            r1_result_resolved = True
        except Exception as e:
            handle_error(f"R1_RESULT_RESOLUTION_FAILED: {e}")

        # 3. Resolve frozen R1 result descriptor from disk
        frozen_r1_result_resolved = False
        freeze_file = self.repo_root / "experiments" / "formal-discovery-01b-r2" / "r1-original-result-freeze.json"
        if not freeze_file.is_file():
            handle_error(f"FROZEN_R1_RESULT_FILE_NOT_FOUND: {freeze_file}")
        else:
            freeze_sha = hashlib.sha256(freeze_file.read_bytes()).hexdigest()
            if freeze_sha != self.frozen_r1_result_digest:
                handle_error(f"FROZEN_R1_RESULT_DIGEST_MISMATCH: Computed {freeze_sha} != {self.frozen_r1_result_digest}")
            else:
                try:
                    freeze_data = json.loads(freeze_file.read_text(encoding="utf-8"))
                    if freeze_data.get("source_execution_commit") != self.pinned_commit:
                        handle_error(f"FROZEN_R1_COMMIT_MISMATCH: {freeze_data.get('source_execution_commit')} != {self.pinned_commit}")
                    if freeze_data.get("source_execution_tree") != self.pinned_tree:
                        handle_error(f"FROZEN_R1_TREE_MISMATCH: {freeze_data.get('source_execution_tree')} != {self.pinned_tree}")
                    if freeze_data.get("result_sha256") != self.r1_result_sha256:
                        handle_error(f"FROZEN_R1_RESULT_SHA_MISMATCH: {freeze_data.get('result_sha256')} != {self.r1_result_sha256}")
                    frozen_r1_result_resolved = True
                except Exception as e:
                    handle_error(f"FROZEN_R1_RESULT_PARSE_FAILED: {e}")

        # 4. Resolve Closure Manifest (if provided or present)
        closure_manifest_resolved = False
        closure_manifest_obj: Optional[TerminalCustodyClosureManifest] = None
        closure_path = closure_manifest_path or (
            self.repo_root / "experiments" / "formal-discovery-01b-r3" / "r1-terminal-custody-closure.v0.1.json"
        )
        if closure_path.is_file():
            try:
                raw_closure = json.loads(closure_path.read_text(encoding="utf-8"))
                closure_manifest_obj = TerminalCustodyClosureManifest.from_dict(raw_closure)
                closure_manifest_obj.validate()
                if closure_manifest_obj.source_execution_commit != self.pinned_commit:
                    handle_error(f"CLOSURE_COMMIT_MISMATCH: {closure_manifest_obj.source_execution_commit} != {self.pinned_commit}")
                if closure_manifest_obj.source_execution_tree != self.pinned_tree:
                    handle_error(f"CLOSURE_TREE_MISMATCH: {closure_manifest_obj.source_execution_tree} != {self.pinned_tree}")
                if closure_manifest_obj.frozen_r1_result_digest != self.frozen_r1_result_digest:
                    handle_error(f"CLOSURE_FROZEN_R1_DIGEST_MISMATCH: {closure_manifest_obj.frozen_r1_result_digest} != {self.frozen_r1_result_digest}")
                closure_manifest_resolved = True
                if paired_manifest_path is None and closure_manifest_obj.paired_manifest_ref:
                    p = Path(closure_manifest_obj.paired_manifest_ref)
                    if not p.is_file():
                        p = self.repo_root / closure_manifest_obj.paired_manifest_ref
                    paired_manifest_path = p
            except Exception as e:
                handle_error(f"CLOSURE_MANIFEST_RESOLUTION_FAILED: {e}")
        elif closure_manifest_path is not None:
            handle_error(f"CLOSURE_MANIFEST_FILE_NOT_FOUND: {closure_manifest_path}")

        # 5. Resolve Paired Manifest
        paired_manifest_resolved = False
        paired_manifest_obj: Optional[PairedTerminalCustodyManifest] = None
        target_paired_path = paired_manifest_path or (
            self.repo_root / "experiments" / "formal-discovery-01b-r3" / "paired-terminal-custody-manifest.v0.1.json"
        )
        if not target_paired_path.is_file():
            handle_error(f"PAIRED_MANIFEST_FILE_NOT_FOUND: {target_paired_path}")
        else:
            try:
                paired_bytes = target_paired_path.read_bytes()
                paired_sha = hashlib.sha256(paired_bytes).hexdigest()
                if closure_manifest_obj and closure_manifest_obj.paired_manifest_digest:
                    if paired_sha != closure_manifest_obj.paired_manifest_digest:
                        handle_error(f"PAIRED_MANIFEST_DIGEST_MISMATCH: {paired_sha} != {closure_manifest_obj.paired_manifest_digest}")
                raw_paired = json.loads(paired_bytes.decode("utf-8"))
                paired_manifest_obj = PairedTerminalCustodyManifest.from_dict(raw_paired)
                paired_manifest_obj.validate()
                if len(paired_manifest_obj.units) != 12:
                    handle_error(f"INVALID_UNIT_COUNT: Expected 12 units, got {len(paired_manifest_obj.units)}")
                paired_manifest_resolved = True
            except Exception as e:
                handle_error(f"PAIRED_MANIFEST_RESOLUTION_FAILED: {e}")

        # 6. Resolve all edges for the 12 units (24 arms, 12 SMT receipts)
        original_search_receipts_resolved = 0
        original_smt_receipts_resolved = 0
        replay_search_receipts_resolved = 0
        custody_receipts_resolved = 0
        terminal_digest_parity_count = 0
        metric_parity_count = 0
        application_parity_count = 0
        paired_terminal_parity_count = 0

        if paired_manifest_obj:
            for unit in paired_manifest_obj.units:
                pid = unit.get("problem_id") if isinstance(unit, dict) else getattr(unit, "problem_id", "")
                smt_ref = (
                    unit.get("original_paired_smt_receipt_ref") or unit.get("smt_receipt_ref")
                    if isinstance(unit, dict)
                    else getattr(unit, "original_paired_smt_receipt_ref", getattr(unit, "smt_receipt_ref", ""))
                )
                smt_dig = (
                    unit.get("original_paired_smt_receipt_digest") or unit.get("smt_receipt_digest")
                    if isinstance(unit, dict)
                    else getattr(unit, "original_paired_smt_receipt_digest", getattr(unit, "smt_receipt_digest", ""))
                )

                # 6a. Verify original SMT receipt from pinned Git commit
                try:
                    raw_smt = self.resolve_git_blob(self.pinned_commit, smt_ref)
                    act_smt_sha = hashlib.sha256(raw_smt).hexdigest()
                    if act_smt_sha != smt_dig:
                        handle_error(f"SMT_RECEIPT_DIGEST_MISMATCH for {pid}: {act_smt_sha} != {smt_dig}")
                    smt_data = json.loads(raw_smt.decode("utf-8"))
                    smt_verdict = smt_data.get("terminal_verdict") or smt_data.get("verdict") or (smt_data.get("execution_receipt") or {}).get("terminal_classification")
                    if smt_verdict != "UNSAT_REFUTED":
                        handle_error(f"SMT_VERDICT_NOT_UNSAT_REFUTED for {pid}: {smt_verdict}")
                    original_smt_receipts_resolved += 1
                except Exception as e:
                    handle_error(f"SMT_RESOLUTION_FAILED for {pid}: {e}")

                # 6b. Verify both arms (baseline & abstracted)
                unit_terminal_digests: Dict[str, str] = {}
                for arm in ("baseline", "abstracted"):
                    if isinstance(unit, dict):
                        cust_ref = unit.get(f"{arm}_custody_receipt_ref") or unit.get(f"{arm}_receipt_ref")
                        cust_dig = unit.get(f"{arm}_custody_receipt_digest") or unit.get(f"{arm}_receipt_digest")
                    else:
                        cust_ref = getattr(unit, f"{arm}_custody_receipt_ref", getattr(unit, f"{arm}_receipt_ref", ""))
                        cust_dig = getattr(unit, f"{arm}_custody_receipt_digest", getattr(unit, f"{arm}_receipt_digest", ""))

                    cust_path = Path(cust_ref)
                    if not cust_path.is_file():
                        cust_path = self.repo_root / cust_ref
                    if not cust_path.is_file() and paired_manifest_path:
                        alt = paired_manifest_path.parent / "receipts" / Path(cust_ref).name
                        if alt.is_file():
                            cust_path = alt
                    if not cust_path.is_file():
                        handle_error(f"CUSTODY_RECEIPT_FILE_NOT_FOUND: {cust_ref}")
                        continue

                    cust_bytes = cust_path.read_bytes()
                    file_sha = hashlib.sha256(cust_bytes).hexdigest()
                    try:
                        cust_data = json.loads(cust_bytes.decode("utf-8"))
                        file_receipt_dig = cust_data.get("receipt_digest", "")
                    except Exception:
                        file_receipt_dig = ""
                    if cust_dig not in (file_receipt_dig, file_sha):
                        handle_error(f"CUSTODY_RECEIPT_DIGEST_MISMATCH for {cust_ref}: {cust_dig} != {file_receipt_dig}")
                        continue

                    try:
                        cust_receipt = TerminalStateCustodyReceipt.from_dict(cust_data)
                        cust_receipt.validate()

                        if cust_receipt.arm.lower() != arm:
                            handle_error(f"CUSTODY_ARM_MISMATCH: {cust_receipt.arm} != {arm}")
                        if cust_receipt.problem_id != pid:
                            handle_error(f"CUSTODY_PROBLEM_ID_MISMATCH: {cust_receipt.problem_id} != {pid}")
                        if cust_receipt.source_execution_commit != self.pinned_commit:
                            handle_error(f"CUSTODY_COMMIT_MISMATCH: {cust_receipt.source_execution_commit} != {self.pinned_commit}")
                        if cust_receipt.source_execution_tree != self.pinned_tree:
                            handle_error(f"CUSTODY_TREE_MISMATCH: {cust_receipt.source_execution_tree} != {self.pinned_tree}")
                        if cust_receipt.source_result_sha256 != self.r1_result_sha256:
                            handle_error(f"CUSTODY_SOURCE_RESULT_SHA_MISMATCH: {cust_receipt.source_result_sha256} != {self.r1_result_sha256}")

                        unit_terminal_digests[arm] = cust_receipt.terminal_expression_digest

                        # Verify original search receipt from pinned Git commit
                        raw_orig = self.resolve_git_blob(self.pinned_commit, cust_receipt.original_search_receipt_ref)
                        act_orig_sha = hashlib.sha256(raw_orig).hexdigest()
                        if act_orig_sha != cust_receipt.original_search_receipt_digest:
                            handle_error(f"ORIGINAL_SEARCH_RECEIPT_DIGEST_MISMATCH for {cust_receipt.original_search_receipt_ref}: {act_orig_sha} != {cust_receipt.original_search_receipt_digest}")
                        
                        orig_search_data = json.loads(raw_orig.decode("utf-8"))
                        orig_receipt = SearchExecutionReceipt.from_dict(orig_search_data)
                        orig_receipt.validate()

                        if orig_receipt.run_id != cust_receipt.search_run_ref:
                            handle_error(f"ORIG_SEARCH_RUN_REF_MISMATCH: {orig_receipt.run_id} != {cust_receipt.search_run_ref}")
                        if orig_receipt.receipt_digest != cust_receipt.search_run_digest:
                            handle_error(f"ORIG_SEARCH_RUN_DIGEST_MISMATCH: {orig_receipt.receipt_digest} != {cust_receipt.search_run_digest}")
                        if orig_receipt.problem_id != cust_receipt.problem_id:
                            handle_error(f"ORIG_SEARCH_PROBLEM_ID_MISMATCH: {orig_receipt.problem_id} != {cust_receipt.problem_id}")
                        if orig_receipt.problem_digest != cust_receipt.problem_digest:
                            handle_error(f"ORIG_SEARCH_PROBLEM_DIGEST_MISMATCH: {orig_receipt.problem_digest} != {cust_receipt.problem_digest}")

                        # Arm semantics
                        if arm == "baseline":
                            if orig_receipt.candidate_enabled is not False or orig_receipt.candidate_application_status != "DISABLED":
                                handle_error(f"ORIG_BASELINE_ARM_SEMANTICS_MISMATCH for {cust_receipt.problem_id}")
                        else:
                            if orig_receipt.candidate_enabled is not True or orig_receipt.candidate_application_status not in ("APPLIED", "REQUESTED_NOT_APPLIED", "NOT_APPLICABLE"):
                                handle_error(f"ORIG_ABSTRACTED_ARM_SEMANTICS_MISMATCH for {cust_receipt.problem_id}")
                            if orig_receipt.candidate_id != cust_receipt.candidate_id:
                                handle_error(f"ORIG_CANDIDATE_ID_MISMATCH: {orig_receipt.candidate_id} != {cust_receipt.candidate_id}")
                        if orig_receipt.candidate_application_status != cust_receipt.candidate_application_status:
                            handle_error(f"CUSTODY_APPLICATION_STATUS_MISMATCH for {cust_receipt.problem_id}: {orig_receipt.candidate_application_status} != {cust_receipt.candidate_application_status}")

                        # Metrics match between original receipt and custody receipt
                        if orig_receipt.nodes_expanded != cust_receipt.nodes_expanded:
                            handle_error(f"ORIG_NODES_EXPANDED_MISMATCH for {cust_receipt.problem_id}: {orig_receipt.nodes_expanded} != {cust_receipt.nodes_expanded}")
                        if orig_receipt.nodes_evaluated != cust_receipt.nodes_evaluated:
                            handle_error(f"ORIG_NODES_EVALUATED_MISMATCH for {cust_receipt.problem_id}: {orig_receipt.nodes_evaluated} != {cust_receipt.nodes_evaluated}")
                        if orig_receipt.branch_count != cust_receipt.branch_count:
                            handle_error(f"ORIG_BRANCH_COUNT_MISMATCH for {cust_receipt.problem_id}: {orig_receipt.branch_count} != {cust_receipt.branch_count}")
                        if (orig_receipt.terminal_status == "SUCCESS") != cust_receipt.solved:
                            handle_error(f"ORIG_SOLVED_STATUS_MISMATCH for {cust_receipt.problem_id}: {orig_receipt.terminal_status} vs solved={cust_receipt.solved}")

                        # Check against frozen R1 result per_unit_evaluations
                        if cust_receipt.problem_id in per_unit_evaluations:
                            u_eval = per_unit_evaluations[cust_receipt.problem_id]
                            arm_prefix = arm.lower()
                            exp_nodes = u_eval.get(f"{arm_prefix}_nodes")
                            exp_eval = u_eval.get(f"{arm_prefix}_evaluated")
                            exp_branch = u_eval.get(f"{arm_prefix}_branches")
                            if exp_nodes is not None and orig_receipt.nodes_expanded != exp_nodes:
                                handle_error(f"R1_RESULT_NODES_MISMATCH for {cust_receipt.problem_id}: {orig_receipt.nodes_expanded} != {exp_nodes}")
                            if exp_eval is not None and orig_receipt.nodes_evaluated != exp_eval:
                                handle_error(f"R1_RESULT_EVAL_MISMATCH for {cust_receipt.problem_id}: {orig_receipt.nodes_evaluated} != {exp_eval}")
                            if exp_branch is not None and orig_receipt.branch_count != exp_branch:
                                handle_error(f"R1_RESULT_BRANCH_MISMATCH for {cust_receipt.problem_id}: {orig_receipt.branch_count} != {exp_branch}")

                        original_search_receipts_resolved += 1

                        # Verify replay search receipt on disk
                        if not cust_receipt.replay_search_receipt_ref or not cust_receipt.replay_search_receipt_digest:
                            handle_error(f"MISSING_REPLAY_SEARCH_RECEIPT_BINDING in {cust_receipt.custody_receipt_id}")
                            continue

                        rep_p = Path(cust_receipt.replay_search_receipt_ref)
                        if not rep_p.is_file():
                            rep_p = self.repo_root / cust_receipt.replay_search_receipt_ref
                        if not rep_p.is_file() and paired_manifest_path:
                            alt = paired_manifest_path.parent / "receipts" / Path(cust_receipt.replay_search_receipt_ref).name
                            if alt.is_file():
                                rep_p = alt
                        if not rep_p.is_file():
                            handle_error(f"REPLAY_SEARCH_RECEIPT_FILE_NOT_FOUND: {cust_receipt.replay_search_receipt_ref}")
                            continue

                        rep_bytes = rep_p.read_bytes()
                        act_rep_sha = hashlib.sha256(rep_bytes).hexdigest()
                        if act_rep_sha != cust_receipt.replay_search_receipt_digest:
                            handle_error(f"REPLAY_SEARCH_RECEIPT_DIGEST_MISMATCH: {act_rep_sha} != {cust_receipt.replay_search_receipt_digest}")
                            continue

                        rep_search_data = json.loads(rep_bytes.decode("utf-8"))
                        rep_receipt = SearchExecutionReceipt.from_dict(rep_search_data)
                        rep_receipt.validate()

                        if rep_receipt.run_id != cust_receipt.replay_search_run_ref:
                            handle_error(f"REPLAY_SEARCH_RUN_REF_MISMATCH: {rep_receipt.run_id} != {cust_receipt.replay_search_run_ref}")
                        if rep_receipt.receipt_digest != cust_receipt.replay_search_run_digest:
                            handle_error(f"REPLAY_SEARCH_RUN_DIGEST_MISMATCH: {rep_receipt.receipt_digest} != {cust_receipt.replay_search_run_digest}")
                        if rep_receipt.problem_id != cust_receipt.problem_id:
                            handle_error(f"REPLAY_PROBLEM_ID_MISMATCH: {rep_receipt.problem_id} != {cust_receipt.problem_id}")
                        if rep_receipt.problem_digest != cust_receipt.problem_digest:
                            handle_error(f"REPLAY_PROBLEM_DIGEST_MISMATCH: {rep_receipt.problem_digest} != {cust_receipt.problem_digest}")

                        if arm == "baseline":
                            if rep_receipt.candidate_enabled is not False or rep_receipt.candidate_application_status != "DISABLED":
                                handle_error(f"REPLAY_BASELINE_ARM_SEMANTICS_MISMATCH for {cust_receipt.problem_id}")
                        else:
                            if rep_receipt.candidate_enabled is not True or rep_receipt.candidate_application_status not in ("APPLIED", "REQUESTED_NOT_APPLIED", "NOT_APPLICABLE"):
                                handle_error(f"REPLAY_ABSTRACTED_ARM_SEMANTICS_MISMATCH for {cust_receipt.problem_id}")
                            if rep_receipt.candidate_id != cust_receipt.candidate_id:
                                handle_error(f"REPLAY_CANDIDATE_ID_MISMATCH: {rep_receipt.candidate_id} != {cust_receipt.candidate_id}")
                        if rep_receipt.candidate_application_status != cust_receipt.candidate_application_status:
                            handle_error(f"REPLAY_APPLICATION_STATUS_MISMATCH for {cust_receipt.problem_id}: {rep_receipt.candidate_application_status} != {cust_receipt.candidate_application_status}")

                        if rep_receipt.nodes_expanded != cust_receipt.nodes_expanded:
                            handle_error(f"REPLAY_NODES_EXPANDED_MISMATCH: {rep_receipt.nodes_expanded} != {cust_receipt.nodes_expanded}")
                        if rep_receipt.nodes_evaluated != cust_receipt.nodes_evaluated:
                            handle_error(f"REPLAY_NODES_EVALUATED_MISMATCH: {rep_receipt.nodes_evaluated} != {cust_receipt.nodes_evaluated}")
                        if rep_receipt.branch_count != cust_receipt.branch_count:
                            handle_error(f"REPLAY_BRANCH_COUNT_MISMATCH: {rep_receipt.branch_count} != {cust_receipt.branch_count}")

                        replay_search_receipts_resolved += 1

                        # Parity checks
                        if (
                            bool(cust_receipt.terminal_digest_parity)
                            and cust_receipt.terminal_expression_digest == cust_receipt.source_recorded_terminal_digest
                        ):
                            terminal_digest_parity_count += 1
                        else:
                            handle_error(f"TERMINAL_DIGEST_PARITY_FAILED for {cust_receipt.custody_receipt_id}")

                        if bool(cust_receipt.metric_parity):
                            metric_parity_count += 1
                        else:
                            handle_error(f"METRIC_PARITY_FAILED for {cust_receipt.custody_receipt_id}")

                        if bool(cust_receipt.application_parity):
                            application_parity_count += 1
                        else:
                            handle_error(f"APPLICATION_PARITY_FAILED for {cust_receipt.custody_receipt_id}")

                        custody_receipts_resolved += 1

                    except Exception as e:
                        handle_error(f"CUSTODY_RECEIPT_VERIFICATION_FAILED for {cust_ref}: {e}")

                # Unit-level paired parity
                term_eq = unit.get("terminal_digest_equality") if isinstance(unit, dict) else getattr(unit, "terminal_digest_equality", getattr(unit, "terminal_digest_match", False))
                parity_st = unit.get("custody_replay_parity_status") if isinstance(unit, dict) else getattr(unit, "custody_replay_parity_status", "")
                if term_eq and parity_st == "PARITY_VERIFIED":
                    b_dig = unit_terminal_digests.get("baseline")
                    a_dig = unit_terminal_digests.get("abstracted")
                    if b_dig and a_dig and b_dig == a_dig:
                        paired_terminal_parity_count += 1
                    else:
                        handle_error(f"PAIRED_TERMINAL_DIGESTS_DISAGREE for {pid}: baseline {b_dig} != abstracted {a_dig}")
                else:
                    handle_error(f"PAIRED_TERMINAL_PARITY_STATUS_INVALID for {pid}")

        # 7. Resolve ONTO package (if provided or present)
        onto_package_resolved = False
        onto_path = onto_package_path or (
            self.repo_root / "experiments" / "formal-discovery-01b-r3" / "onto-export-scoped.json"
        )
        if onto_path.is_file():
            try:
                raw_onto = json.loads(onto_path.read_text(encoding="utf-8"))
                pkg = OntoEvaluationPackage.from_dict(raw_onto)
                pkg.validate()

                if pkg.functional_search_benefit != "SUPPORTED":
                    handle_error(f"ONTO_BENEFIT_NOT_SUPPORTED: {pkg.functional_search_benefit}")
                if pkg.functional_search_benefit_scope != "NODE_EXPANSION_SEARCH_STRUCTURE":
                    handle_error(f"ONTO_SCOPE_INVALID: {pkg.functional_search_benefit_scope}")
                if pkg.end_to_end_runtime_benefit != "NOT_ESTABLISHED":
                    handle_error(f"ONTO_RUNTIME_BENEFIT_NOT_ESTABLISHED: {pkg.end_to_end_runtime_benefit}")
                if pkg.authority != "NONE":
                    handle_error(f"ONTO_AUTHORITY_INVALID: {pkg.authority}")
                if pkg.claim_ceiling != "ENGINEERING_ABSTRACTION_EFFECT_ONLY":
                    handle_error(f"ONTO_CLAIM_CEILING_INVALID: {pkg.claim_ceiling}")

                has_freeze_ref = False
                has_closure_ref = False
                for r in pkg.evidence_refs:
                    if r.evidence_kind == "FROZEN_R1_SCIENTIFIC_RESULT":
                        has_freeze_ref = True
                        if r.artifact_digest != self.frozen_r1_result_digest:
                            handle_error(f"ONTO_FROZEN_R1_DIGEST_MISMATCH: {r.artifact_digest} != {self.frozen_r1_result_digest}")
                    elif r.evidence_kind == "TERMINAL_STATE_CUSTODY_CLOSURE":
                        has_closure_ref = True
                        if closure_manifest_obj:
                            valid_digests = {closure_manifest_obj.closure_digest}
                            if closure_manifest_path and closure_manifest_path.is_file():
                                valid_digests.add(hashlib.sha256(closure_manifest_path.read_bytes()).hexdigest())
                            if r.artifact_digest not in valid_digests:
                                handle_error(f"ONTO_CLOSURE_DIGEST_MISMATCH: {r.artifact_digest} not in {valid_digests}")

                if not has_freeze_ref:
                    handle_error("ONTO_PACKAGE_MISSING_FROZEN_R1_SCIENTIFIC_RESULT_REF")
                if not has_closure_ref:
                    handle_error("ONTO_PACKAGE_MISSING_TERMINAL_STATE_CUSTODY_CLOSURE_REF")

                onto_package_resolved = True
            except Exception as e:
                handle_error(f"ONTO_PACKAGE_RESOLUTION_FAILED: {e}")
        elif onto_package_path is not None:
            handle_error(f"ONTO_PACKAGE_FILE_NOT_FOUND: {onto_package_path}")

        # 8. Compute closure booleans dynamically from verification results
        all_original_search_refs_resolved = (original_search_receipts_resolved == 24)
        all_replay_search_receipts_resolved = (replay_search_receipts_resolved == 24)
        all_replay_receipts_resolved = (custody_receipts_resolved == 24)
        all_smt_receipts_resolved = (original_smt_receipts_resolved == 12)
        terminal_canonical_forms_durably_bound = (
            "YES"
            if (terminal_digest_parity_count == 24 and paired_terminal_parity_count == 12)
            else "NO"
        )
        source_science_mutated = not r1_result_resolved

        success = (
            r1_result_resolved
            and frozen_r1_result_resolved
            and all_original_search_refs_resolved
            and all_replay_search_receipts_resolved
            and all_replay_receipts_resolved
            and all_smt_receipts_resolved
            and paired_manifest_resolved
            and (terminal_digest_parity_count == 24)
            and (metric_parity_count == 24)
            and (application_parity_count == 24)
            and (paired_terminal_parity_count == 12)
            and (terminal_canonical_forms_durably_bound == "YES")
            and not source_science_mutated
            and len(errors) == 0
        )

        resolution_status = "RESOLVED_AND_VERIFIED" if success else "RESOLUTION_FAILED"

        return CustodyGraphResolutionReport(
            resolution_status=resolution_status,
            source_execution_commit=self.pinned_commit,
            source_execution_tree=self.pinned_tree,
            r1_result_resolved=r1_result_resolved,
            frozen_r1_result_resolved=frozen_r1_result_resolved,
            original_search_receipts_resolved=original_search_receipts_resolved,
            original_smt_receipts_resolved=original_smt_receipts_resolved,
            replay_search_receipts_resolved=replay_search_receipts_resolved,
            custody_receipts_resolved=custody_receipts_resolved,
            paired_manifest_resolved=paired_manifest_resolved,
            closure_manifest_resolved=closure_manifest_resolved,
            onto_package_resolved=onto_package_resolved,
            terminal_digest_parity_count=terminal_digest_parity_count,
            metric_parity_count=metric_parity_count,
            application_parity_count=application_parity_count,
            paired_terminal_parity_count=paired_terminal_parity_count,
            all_original_search_refs_resolved=all_original_search_refs_resolved,
            all_replay_search_receipts_resolved=all_replay_search_receipts_resolved,
            all_replay_receipts_resolved=all_replay_receipts_resolved,
            all_smt_receipts_resolved=all_smt_receipts_resolved,
            terminal_canonical_forms_durably_bound=terminal_canonical_forms_durably_bound,
            source_science_mutated=source_science_mutated,
            errors=errors,
        )
