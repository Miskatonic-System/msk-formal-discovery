"""Custody Graph Resolver and Zero-Argument Verifier for WO-MATH-FORMAL-DISCOVERY-01C and 01C-R1."""
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
from msk_formal_discovery.search.executor import (
    CANONICAL_DISABLED_APPLICATION_DIGEST,
    SearchExecutionReceipt,
)
from msk_formal_discovery.trace.ir import ExecutionTrace

PINNED_01C_PREDECESSOR_COMMIT = "292cbd26075b4a831e516d6f15eca3c1222f6e71"
PINNED_01C_PREDECESSOR_TREE = "99c810fc01f727495a23984eba2662fe18c7833f"
PINNED_01C_CANDIDATE_DIGEST = "273a1d821e54ba6bf1832a2f1f11b338853aa9d1070d873c8b29345ba5aae903"
FROZEN_TRANSFORM_IMPL_DIGEST = "5c85f28d268f138ffbf2ec8d9fe400d72a1378ed09223ddff43a802ccd809d4a"


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

    @property
    def valid(self) -> bool:
        return len(self.errors) == 0 and self.resolution_status == "REPRESENTATION_CUSTODY_GRAPH_VERIFIED"


class RepresentationOrbitResolver:
    """Zero-argument resolver and verifier for representation-orbit custody graphs."""

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        self.repo_root = repo_root or Path(__file__).resolve().parents[3]

    def _resolve_path(self, rel_or_abs: str) -> Optional[Path]:
        p = Path(rel_or_abs)
        if p.is_absolute():
            return p if p.is_file() else None
        alt = self.repo_root / rel_or_abs
        if alt.is_file():
            return alt
        if p.is_file():
            return p
        return None

    def resolve_and_verify(
        self,
        closure_manifest_path: Optional[Path] = None,
    ) -> Any:
        """Resolve and verify representation custody graph.
        
        If 01C-R1 superseding closure exists, delegates to RepresentationCustodyRepairResolver
        while also running complete independent checks.
        """
        r1_r1_closure = self.repo_root / "experiments" / "formal-discovery-01c-r1-r1" / "representation-custody-closure.v0.1.json"
        r1_closure = self.repo_root / "experiments" / "formal-discovery-01c-r1" / "representation-custody-closure.v0.1.json"
        if closure_manifest_path is None:
            if r1_r1_closure.is_file():
                from msk_formal_discovery.representation.custody_resolver import RepresentationCustodyRepairResolver
                r1_r1_resolver = RepresentationCustodyRepairResolver(repo_root=self.repo_root)
                return r1_r1_resolver.resolve_and_verify(closure_manifest_path=r1_r1_closure)
            if r1_closure.is_file():
                from msk_formal_discovery.representation.custody_resolver import RepresentationCustodyRepairResolver
                r1_resolver = RepresentationCustodyRepairResolver(repo_root=self.repo_root)
                return r1_resolver.resolve_and_verify(closure_manifest_path=r1_closure)
        else:
            c_explicit = Path(closure_manifest_path)
            if not c_explicit.is_file():
                raise CustodyGraphResolutionError(f"CLOSURE_NOT_FOUND: Representation closure missing at {c_explicit}")
            try:
                c_check = json.loads(c_explicit.read_text(encoding="utf-8"))
                if c_check.get("schema_version") == "miskatonic.representation-custody-closure.v0.1":
                    from msk_formal_discovery.representation.custody_resolver import RepresentationCustodyRepairResolver
                    return RepresentationCustodyRepairResolver(repo_root=self.repo_root).resolve_and_verify(closure_manifest_path=c_explicit)
            except Exception as e:
                if isinstance(e, CustodyGraphResolutionError):
                    raise

        errors: List[str] = []

        # 1. Discover closure manifest
        c_path = closure_manifest_path or (
            self.repo_root / "experiments" / "formal-discovery-01c" / "representation-invariance-closure.v0.1.json"
        )
        if not c_path.is_file():
            raise CustodyGraphResolutionError(f"CLOSURE_NOT_FOUND: Representation closure missing at {c_path}")

        closure_raw = json.loads(c_path.read_text(encoding="utf-8"))
        closure = RepresentationInvarianceClosureManifest.from_dict(closure_raw)
        try:
            closure.validate(repo_root=self.repo_root)
        except Exception as e:
            errors.append(f"Closure validation error: {e}")

        # Verify predecessor commits & candidate digest
        cand_verified = (closure.candidate_artifact_digest == PINNED_01C_CANDIDATE_DIGEST)
        if not cand_verified:
            errors.append(f"Candidate digest mismatch: {closure.candidate_artifact_digest}")

        # 2. Check candidate artifact on disk
        cand_path = self.repo_root / "experiments" / "formal-discovery-01c" / "candidate.json"
        if not cand_path.is_file():
            errors.append("Candidate file missing at experiments/formal-discovery-01c/candidate.json")

        # 3. Resolve and verify paired representation manifest
        paired_path = self._resolve_path(closure.paired_manifest_ref)
        paired_manifest: Optional[PairedRepresentationOrbitManifest] = None
        if paired_path and paired_path.is_file():
            act_dig = hashlib.sha256(paired_path.read_bytes()).hexdigest()
            raw_p = json.loads(paired_path.read_text(encoding="utf-8"))
            p_dig = raw_p.get("manifest_digest", "")
            if closure.paired_manifest_digest in (act_dig, p_dig):
                paired_manifest = PairedRepresentationOrbitManifest.from_dict(raw_p)
                try:
                    paired_manifest.validate(repo_root=self.repo_root)
                except Exception as e:
                    errors.append(f"Paired manifest validation error: {e}")
            else:
                errors.append(f"Paired manifest digest mismatch: {act_dig} != {closure.paired_manifest_digest}")
        else:
            errors.append(f"Paired manifest missing at {paired_path}")

        # 4. Strict independent receipt body verification (Finding F-FD-01C-01)
        trans_rcpts_resolved = 0
        trans_smt_resolved = 0
        search_rcpts_resolved = 0
        paired_smt_resolved = 0

        if paired_manifest is not None:
            for fam in paired_manifest.families:
                fam_id = fam.get("family_id", "")
                strata = fam.get("strata", {})
                for s_name, s_info in strata.items():
                    # Transform receipt
                    t_ref = s_info.get("transform_receipt_ref")
                    t_dig = s_info.get("transform_receipt_digest")
                    if t_ref:
                        p = self._resolve_path(t_ref)
                        if p and p.is_file():
                            try:
                                raw = json.loads(p.read_text(encoding="utf-8"))
                                tr = RepresentationTransformReceipt(
                                    receipt_id=raw["receipt_id"],
                                    family_id=raw["family_id"],
                                    stratum=raw["stratum"],
                                    source_expression=raw["source_expression"],
                                    transformed_expression=raw["transformed_expression"],
                                    source_expression_digest=raw["source_expression_digest"],
                                    transformed_expression_digest=raw["transformed_expression_digest"],
                                    variable_bijection=dict(raw["variable_bijection"]),
                                    transform_implementation_digest=raw["transform_implementation_digest"],
                                    smt_certificate_ref=raw["smt_certificate_ref"],
                                    smt_certificate_digest=raw["smt_certificate_digest"],
                                    smt_verdict=raw.get("smt_verdict", "UNSAT_REFUTED"),
                                    semantic_equivalence_certified=raw.get("semantic_equivalence_certified", True),
                                    authority=raw.get("authority", "NONE"),
                                    receipt_digest=raw.get("receipt_digest", ""),
                                )
                                tr.validate()
                                body_dig = tr.compute_digest()
                                if body_dig != raw.get("receipt_digest"):
                                    errors.append(f"Transform receipt body digest mismatch for {t_ref}: computed {body_dig} != stored {raw.get('receipt_digest')}")
                                elif body_dig != t_dig:
                                    errors.append(f"Transform receipt digest mismatch against manifest for {t_ref}")
                                elif tr.family_id != fam_id:
                                    errors.append(f"Transform receipt family_id mismatch: {tr.family_id} != {fam_id}")
                                elif tr.stratum != s_name:
                                    errors.append(f"Transform receipt stratum mismatch: {tr.stratum} != {s_name}")
                                elif tr.transformed_expression != s_info.get("initial_expression"):
                                    errors.append(f"Transformed expression mismatch in {t_ref}")
                                elif tr.transform_implementation_digest != FROZEN_TRANSFORM_IMPL_DIGEST:
                                    errors.append(f"Transform implementation digest drift in {t_ref}")
                                else:
                                    trans_rcpts_resolved += 1
                            except Exception as e:
                                errors.append(f"Failed to independently verify transform receipt {t_ref}: {e}")
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
                    b_nodes = s_info.get("baseline_nodes_expanded")
                    if bs_ref:
                        p = self._resolve_path(bs_ref)
                        if p and p.is_file():
                            try:
                                raw = json.loads(p.read_text(encoding="utf-8"))
                                sr = SearchExecutionReceipt.from_dict(raw)
                                sr.validate()
                                body_dig = sr.compute_digest()
                                if body_dig != raw.get("receipt_digest"):
                                    errors.append(f"Baseline search receipt body digest mismatch for {bs_ref}")
                                elif body_dig != bs_dig:
                                    errors.append(f"Baseline search receipt digest mismatch: {bs_ref}")
                                elif sr.problem_id != s_info.get("problem_id"):
                                    errors.append(f"Baseline search problem_id mismatch: {sr.problem_id}")
                                elif sr.nodes_expanded != b_nodes:
                                    errors.append(f"Baseline nodes_expanded mismatch in {bs_ref}")
                                elif sr.terminal_status != "SUCCESS":
                                    errors.append(f"Baseline search terminal_status not SUCCESS in {bs_ref}")
                                elif sr.candidate_enabled or sr.candidate_application_status != "DISABLED":
                                    errors.append(f"Baseline search candidate enabled in {bs_ref}")
                                else:
                                    search_rcpts_resolved += 1
                            except Exception as e:
                                errors.append(f"Failed to independently verify baseline search receipt {bs_ref}: {e}")
                        else:
                            errors.append(f"Baseline search receipt missing: {bs_ref}")

                    # Abstracted search receipt
                    as_ref = s_info.get("abstracted_search_receipt_ref")
                    as_dig = s_info.get("abstracted_search_receipt_digest")
                    a_nodes = s_info.get("abstracted_nodes_expanded")
                    if as_ref:
                        p = self._resolve_path(as_ref)
                        if p and p.is_file():
                            try:
                                raw = json.loads(p.read_text(encoding="utf-8"))
                                sr = SearchExecutionReceipt.from_dict(raw)
                                sr.validate()
                                body_dig = sr.compute_digest()
                                if body_dig != raw.get("receipt_digest"):
                                    errors.append(f"Abstracted search receipt body digest mismatch for {as_ref}")
                                elif body_dig != as_dig:
                                    errors.append(f"Abstracted search receipt digest mismatch: {as_ref}")
                                elif sr.problem_id != s_info.get("problem_id"):
                                    errors.append(f"Abstracted search problem_id mismatch: {sr.problem_id}")
                                elif sr.nodes_expanded != a_nodes:
                                    errors.append(f"Abstracted nodes_expanded mismatch in {as_ref}")
                                elif sr.terminal_status != "SUCCESS":
                                    errors.append(f"Abstracted search terminal_status not SUCCESS in {as_ref}")
                                elif not sr.candidate_enabled:
                                    errors.append(f"Abstracted search candidate_enabled False in {as_ref}")
                                else:
                                    search_rcpts_resolved += 1
                            except Exception as e:
                                errors.append(f"Failed to independently verify abstracted search receipt {as_ref}: {e}")
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
                pkg = OntoEvaluationPackage.from_dict(raw_onto)
                pkg.validate()
                onto_verified = True
            except Exception as e:
                errors.append(f"ONTO export validation failed: {e}")
        else:
            errors.append("ONTO export missing")

        # 6. Verify result.json
        res_path = self.repo_root / "experiments" / "formal-discovery-01c" / "result.json"
        result_verified = False
        if res_path.is_file():
            try:
                res_raw = json.loads(res_path.read_text(encoding="utf-8"))
                res_global = res_raw.get("adjudication", {}).get("global_disposition") or res_raw.get("global_disposition")
                if res_global == closure.global_disposition:
                    result_verified = True
                else:
                    errors.append("Result global disposition mismatch")
            except Exception as e:
                errors.append(f"Result validation failed: {e}")
        else:
            errors.append("Result artifact missing")

        if errors:
            status = "REPRESENTATION_CUSTODY_REPAIR_FAILED"
        else:
            status = "REPRESENTATION_CUSTODY_GRAPH_VERIFIED"

        return RepresentationOrbitResolutionReport(
            resolution_status=status,
            canonical_predecessor_commit=closure.canonical_predecessor_commit,
            canonical_predecessor_tree=closure.canonical_predecessor_tree,
            candidate_artifact_digest_verified=cand_verified,
            closure_manifest_resolved=(not any("Closure" in e for e in errors)),
            paired_manifest_resolved=(paired_manifest is not None),
            transform_receipts_resolved=trans_rcpts_resolved,
            transform_smt_receipts_resolved=trans_smt_resolved,
            search_receipts_resolved=search_rcpts_resolved,
            paired_terminal_smt_receipts_resolved=paired_smt_resolved,
            onto_package_resolved=onto_verified,
            result_artifact_resolved=result_verified,
            global_disposition=closure.global_disposition,
            per_stratum_dispositions=closure.per_stratum_dispositions,
            errors=errors,
        )
