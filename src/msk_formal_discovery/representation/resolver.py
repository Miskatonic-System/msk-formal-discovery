"""Custody Graph Resolver and Zero-Argument Verifier for WO-MATH-FORMAL-DISCOVERY-01C."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from msk_formal_discovery.core.exceptions import (
    AuthorityViolationError,
    CustodyGraphResolutionError,
    ReceiptValidationError,
)
from msk_formal_discovery.onto.export import OntoEvaluationPackage
from msk_formal_discovery.representation.manifest import (
    PairedRepresentationOrbitManifest,
    RepresentationInvarianceClosureManifest,
)
from msk_formal_discovery.representation.receipt import RepresentationTransformReceipt
from msk_formal_discovery.trace.ir import ExecutionTrace

PINNED_01C_PREDECESSOR_COMMIT = "292cbd26075b4a831e516d6f15eca3c1222f6e71"
PINNED_01C_PREDECESSOR_TREE = "99c810fc01f727495a23984eba2662fe18c7833f"
PINNED_01C_CANDIDATE_DIGEST = "273a1d821e54ba6bf1832a2f1f11b338853aa9d1070d873c8b29345ba5aae903"


@dataclass
class RepresentationOrbitResolutionReport:
    """Report detailing independent verification of every edge of the 01C custody graph."""
    resolution_status: str
    canonical_predecessor_commit: str
    canonical_predecessor_tree: str
    candidate_artifact_digest_verified: bool
    closure_manifest_resolved: bool
    paired_manifest_resolved: bool
    transform_receipts_resolved: int
    transform_smt_receipts_resolved: int
    search_receipts_resolved: int
    paired_terminal_smt_receipts_resolved: int
    onto_package_resolved: bool
    result_artifact_resolved: bool
    global_disposition: str
    per_stratum_dispositions: Dict[str, str]
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resolution_status": self.resolution_status,
            "canonical_predecessor_commit": self.canonical_predecessor_commit,
            "canonical_predecessor_tree": self.canonical_predecessor_tree,
            "candidate_artifact_digest_verified": self.candidate_artifact_digest_verified,
            "closure_manifest_resolved": self.closure_manifest_resolved,
            "paired_manifest_resolved": self.paired_manifest_resolved,
            "transform_receipts_resolved": self.transform_receipts_resolved,
            "transform_smt_receipts_resolved": self.transform_smt_receipts_resolved,
            "search_receipts_resolved": self.search_receipts_resolved,
            "paired_terminal_smt_receipts_resolved": self.paired_terminal_smt_receipts_resolved,
            "onto_package_resolved": self.onto_package_resolved,
            "result_artifact_resolved": self.result_artifact_resolved,
            "global_disposition": self.global_disposition,
            "per_stratum_dispositions": dict(self.per_stratum_dispositions),
            "errors": list(self.errors),
        }


class RepresentationOrbitResolver:
    """Independently verifies and resolves the 01C representation orbit custody graph."""

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        pinned_commit: str = PINNED_01C_PREDECESSOR_COMMIT,
        pinned_tree: str = PINNED_01C_PREDECESSOR_TREE,
        pinned_candidate_digest: str = PINNED_01C_CANDIDATE_DIGEST,
    ) -> None:
        self.repo_root = repo_root or Path(__file__).resolve().parents[3]
        self.pinned_commit = pinned_commit
        self.pinned_tree = pinned_tree
        self.pinned_candidate_digest = pinned_candidate_digest

    def resolve_and_verify(
        self,
        closure_manifest_path: Optional[Path] = None,
    ) -> RepresentationOrbitResolutionReport:
        """Execute complete custody graph verification (zero-argument callable)."""
        errors: List[str] = []
        default_closure_rel = "experiments/formal-discovery-01c/representation-invariance-closure.v0.1.json"
        c_path = closure_manifest_path or (self.repo_root / default_closure_rel)

        if not c_path.is_file():
            raise CustodyGraphResolutionError(f"CLOSURE_NOT_FOUND: Closure manifest missing at '{c_path}'")

        # 1. Load and validate closure manifest
        closure_raw = json.loads(c_path.read_text(encoding="utf-8"))
        closure = RepresentationInvarianceClosureManifest.from_dict(closure_raw)
        try:
            closure.validate(repo_root=self.repo_root)
        except Exception as e:
            errors.append(f"Closure manifest invalid: {e}")

        if closure.canonical_predecessor_commit != self.pinned_commit:
            errors.append(f"Predecessor commit mismatch: {closure.canonical_predecessor_commit} != {self.pinned_commit}")
        if closure.canonical_predecessor_tree != self.pinned_tree:
            errors.append(f"Predecessor tree mismatch: {closure.canonical_predecessor_tree} != {self.pinned_tree}")
        if closure.candidate_artifact_digest != self.pinned_candidate_digest:
            errors.append(f"Candidate digest mismatch: {closure.candidate_artifact_digest} != {self.pinned_candidate_digest}")

        # 2. Verify candidate artifact on disk
        cand_path = self.repo_root / "experiments" / "formal-discovery-01c" / "candidate.json"
        cand_verified = False
        if cand_path.is_file():
            cand_raw = json.loads(cand_path.read_text(encoding="utf-8"))
            from msk_formal_discovery.abstraction.candidate import AbstractionCandidate
            cand_obj = AbstractionCandidate.from_dict(cand_raw)
            if cand_obj.artifact_digest() == self.pinned_candidate_digest:
                cand_verified = True
            else:
                errors.append(f"Candidate artifact digest on disk {cand_obj.artifact_digest()} != {self.pinned_candidate_digest}")
        else:
            errors.append(f"Candidate artifact missing at {cand_path}")

        # 3. Load and validate paired manifest
        paired_path = Path(closure.paired_manifest_ref)
        if not paired_path.is_file():
            paired_path = self.repo_root / closure.paired_manifest_ref

        paired_verified = False
        paired_manifest: Optional[PairedRepresentationOrbitManifest] = None
        if paired_path.is_file():
            act_dig = hashlib.sha256(paired_path.read_bytes()).hexdigest()
            p_raw = json.loads(paired_path.read_text(encoding="utf-8"))
            if p_raw.get("manifest_digest") == closure.paired_manifest_digest or act_dig == closure.paired_manifest_digest:
                paired_verified = True
                paired_manifest = PairedRepresentationOrbitManifest.from_dict(p_raw)
                try:
                    paired_manifest.validate(repo_root=self.repo_root)
                except Exception as e:
                    errors.append(f"Paired manifest invalid: {e}")
            else:
                errors.append(f"Paired manifest digest mismatch: {act_dig} != {closure.paired_manifest_digest}")
        else:
            errors.append(f"Paired manifest missing at {paired_path}")

        # 4. Dereference and verify every receipt edge in paired manifest
        trans_rcpts_resolved = 0
        trans_smt_resolved = 0
        search_rcpts_resolved = 0
        paired_smt_resolved = 0

        if paired_manifest is not None:
            for fam in paired_manifest.families:
                strata = fam.get("strata", {})
                for s_name, s_info in strata.items():
                    # Transform receipt
                    t_ref = s_info.get("transform_receipt_ref")
                    t_dig = s_info.get("transform_receipt_digest")
                    if t_ref:
                        p = self._resolve_path(t_ref)
                        if p and p.is_file():
                            raw = json.loads(p.read_text(encoding="utf-8"))
                            if raw.get("receipt_digest") == t_dig:
                                trans_rcpts_resolved += 1
                            else:
                                errors.append(f"Transform receipt digest mismatch for {t_ref}")
                        else:
                            errors.append(f"Transform receipt missing: {t_ref}")

                    # Transform SMT receipt
                    tsmt_ref = s_info.get("smt_certificate_ref")
                    tsmt_dig = s_info.get("smt_certificate_digest")
                    if tsmt_ref:
                        p = self._resolve_path(tsmt_ref)
                        if p and p.is_file():
                            raw = json.loads(p.read_text(encoding="utf-8"))
                            trace_obj = ExecutionTrace.from_dict(raw)
                            if trace_obj.digest() == tsmt_dig and trace_obj.terminal_verdict == "UNSAT_REFUTED":
                                trans_smt_resolved += 1
                            else:
                                errors.append(f"Transform SMT receipt mismatch/unverified for {tsmt_ref}")
                        else:
                            errors.append(f"Transform SMT receipt missing: {tsmt_ref}")

                    # Baseline search receipt
                    bs_ref = s_info.get("baseline_search_receipt_ref")
                    bs_dig = s_info.get("baseline_search_receipt_digest")
                    if bs_ref:
                        p = self._resolve_path(bs_ref)
                        if p and p.is_file():
                            raw = json.loads(p.read_text(encoding="utf-8"))
                            if raw.get("receipt_digest") == bs_dig:
                                search_rcpts_resolved += 1
                            else:
                                errors.append(f"Baseline search receipt digest mismatch: {bs_ref}")
                        else:
                            errors.append(f"Baseline search receipt missing: {bs_ref}")

                    # Abstracted search receipt
                    as_ref = s_info.get("abstracted_search_receipt_ref")
                    as_dig = s_info.get("abstracted_search_receipt_digest")
                    if as_ref:
                        p = self._resolve_path(as_ref)
                        if p and p.is_file():
                            raw = json.loads(p.read_text(encoding="utf-8"))
                            if raw.get("receipt_digest") == as_dig:
                                search_rcpts_resolved += 1
                            else:
                                errors.append(f"Abstracted search receipt digest mismatch: {as_ref}")
                        else:
                            errors.append(f"Abstracted search receipt missing: {as_ref}")

                    # Paired terminal SMT receipt
                    psmt_ref = s_info.get("paired_terminal_smt_receipt_ref")
                    psmt_dig = s_info.get("paired_terminal_smt_receipt_digest")
                    if psmt_ref:
                        p = self._resolve_path(psmt_ref)
                        if p and p.is_file():
                            raw = json.loads(p.read_text(encoding="utf-8"))
                            trace_obj = ExecutionTrace.from_dict(raw)
                            if trace_obj.digest() == psmt_dig and trace_obj.terminal_verdict == "UNSAT_REFUTED":
                                paired_smt_resolved += 1
                            else:
                                errors.append(f"Paired terminal SMT receipt mismatch/unverified: {psmt_ref}")
                        else:
                            errors.append(f"Paired terminal SMT receipt missing: {psmt_ref}")

        # 5. Verify ONTO export
        onto_path = self.repo_root / "experiments" / "formal-discovery-01c" / "onto-export-scoped.json"
        onto_verified = False
        if onto_path.is_file():
            try:
                raw_onto = json.loads(onto_path.read_text(encoding="utf-8"))
                onto_pkg = OntoEvaluationPackage.from_dict(raw_onto)
                onto_pkg.validate()
                onto_verified = True
            except Exception as e:
                errors.append(f"ONTO package invalid: {e}")
        else:
            errors.append(f"ONTO export missing at {onto_path}")

        # 6. Verify result.json
        res_path = self.repo_root / "experiments" / "formal-discovery-01c" / "result.json"
        res_verified = res_path.is_file()
        if not res_verified:
            errors.append(f"result.json missing at {res_path}")

        status = "REPRESENTATION_CUSTODY_GRAPH_VERIFIED" if not errors else "RESOLUTION_FAILED"
        if errors:
            raise CustodyGraphResolutionError(f"Custody graph verification failed with errors: {errors}")

        return RepresentationOrbitResolutionReport(
            resolution_status=status,
            canonical_predecessor_commit=closure.canonical_predecessor_commit,
            canonical_predecessor_tree=closure.canonical_predecessor_tree,
            candidate_artifact_digest_verified=cand_verified,
            closure_manifest_resolved=True,
            paired_manifest_resolved=paired_verified,
            transform_receipts_resolved=trans_rcpts_resolved,
            transform_smt_receipts_resolved=trans_smt_resolved,
            search_receipts_resolved=search_rcpts_resolved,
            paired_terminal_smt_receipts_resolved=paired_smt_resolved,
            onto_package_resolved=onto_verified,
            result_artifact_resolved=res_verified,
            global_disposition=closure.global_disposition,
            per_stratum_dispositions=closure.per_stratum_dispositions,
            errors=errors,
        )

    def _resolve_path(self, ref: str) -> Optional[Path]:
        p = Path(ref)
        if p.is_file():
            return p
        alt = self.repo_root / ref
        if alt.is_file():
            return alt
        return None
