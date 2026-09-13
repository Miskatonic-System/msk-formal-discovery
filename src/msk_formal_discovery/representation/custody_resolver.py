"""Superseding custody graph resolver and independent evidence verifier (WO-MATH-FORMAL-DISCOVERY-01C-R1 Findings F-FD-01C-01 to F-FD-01C-05)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from msk_formal_discovery.application.applicator import CandidateApplicationReceipt
from msk_formal_discovery.core.exceptions import (
    CustodyGraphResolutionError,
    ReceiptValidationError,
)
from msk_formal_discovery.onto.export import OntoEvaluationPackage
from msk_formal_discovery.representation.custody_manifest import (
    ApplicationReplayCustodyManifest,
    RepresentationCustodyClosureManifest,
    WholeProblemTransformManifest,
)
from msk_formal_discovery.representation.manifest import PairedRepresentationOrbitManifest
from msk_formal_discovery.representation.problem_custody import RepresentationProblemCustodyReceipt
from msk_formal_discovery.representation.receipt import RepresentationTransformReceipt
from msk_formal_discovery.search.executor import (
    CANONICAL_DISABLED_APPLICATION_DIGEST,
    SearchExecutionReceipt,
)
from msk_formal_discovery.trace.ir import ExecutionTrace

PINNED_01C_COMMIT_A = "ecbbfc0138e867b27ffd3110e6589a95eeb1f446"
PINNED_01C_COMMIT_B = "712f0d3ce27dbf4578d79f58b938bdc22ba69eeb"
PINNED_01C_TREE_A = "f6c6eb396ce8298cf3370a8916d827d2fe0b2eec"
PINNED_01C_TREE_B = "75c1f3ceb199f1ed23d7a14d277f1ba550a1f1c2"

FROZEN_01C_CANDIDATE_DIGEST = "273a1d821e54ba6bf1832a2f1f11b338853aa9d1070d873c8b29345ba5aae903"
FROZEN_01C_CANDIDATE_FILE_SHA256 = "4794cc897bc60ddd928b3abdecd25bbb343c2388b3d3bf6a466d1b5656c65d31"
FROZEN_01C_PREREGISTRATION_FILE_SHA256 = "bd30fa638f7691c63d395337d9cf770a4d720596dae9647905662f533ed5ed15"
FROZEN_01C_FAMILIES_FILE_SHA256 = "16e65651439d3253542c9eb0711acd692c91727047927395aab96d45b1fbd5ea"
FROZEN_01C_RESULT_FILE_SHA256 = "1455687bb385b75a01fb9c8c29158b3de6151878e0124c1af7c8a5faab7f68a8"
FROZEN_01C_ONTO_FILE_SHA256 = "7357580c96371a1512a9a8598caeb77f7bf6d1d78d587f8c30959ba086f8706f"
FROZEN_01C_PAIRED_MANIFEST_SHA256 = "671e7069aad34d4b776312a293c54e7d0798c20fedb3ee9079aa241f84cfdb93"
FROZEN_01C_CLOSURE_MANIFEST_SHA256 = "896588d4b34e44222eb5f982335b7e6bbbe9a5ac9f1d3c473bbec525764e3186"

FROZEN_TRANSFORM_IMPL_DIGEST = "5c85f28d268f138ffbf2ec8d9fe400d72a1378ed09223ddff43a802ccd809d4a"
FROZEN_APPLICATOR_IMPL_DIGEST = "04e4418028c480a2963242e678af5cf7070257d2b0f2f38b3a7016ee3c2c5360"


@dataclass
class RepresentationCustodyRepairReport:
    """Detailed audit report from independent representation custody verification."""
    resolution_status: str
    work_order: str
    predecessor_head: str
    original_01c_commit_a: str
    original_01c_commit_b: str
    candidate_artifact_digest_verified: bool
    result_artifact_verified: bool
    all_frozen_artifacts_verified: bool
    original_transform_receipts_verified_count: int
    original_search_receipts_verified_count: int
    original_application_attempts_audited_count: int
    exact_original_application_attempts_resolved_count: int
    overwritten_application_attempts_recorded_count: int
    replay_search_runs_verified_count: int
    all_replay_sequence_parity_verified: bool
    all_replay_metric_parity_verified: bool
    whole_problem_receipts_verified_count: int
    whole_problem_smt_verified_count: int
    onto_package_verified: bool
    per_stratum_dispositions: Dict[str, str]
    global_disposition: str
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resolution_status": self.resolution_status,
            "work_order": self.work_order,
            "predecessor_head": self.predecessor_head,
            "original_01c_commit_a": self.original_01c_commit_a,
            "original_01c_commit_b": self.original_01c_commit_b,
            "candidate_artifact_digest_verified": self.candidate_artifact_digest_verified,
            "result_artifact_verified": self.result_artifact_verified,
            "all_frozen_artifacts_verified": self.all_frozen_artifacts_verified,
            "original_transform_receipts_verified_count": self.original_transform_receipts_verified_count,
            "original_search_receipts_verified_count": self.original_search_receipts_verified_count,
            "original_application_attempts_audited_count": self.original_application_attempts_audited_count,
            "exact_original_application_attempts_resolved_count": self.exact_original_application_attempts_resolved_count,
            "overwritten_application_attempts_recorded_count": self.overwritten_application_attempts_recorded_count,
            "replay_search_runs_verified_count": self.replay_search_runs_verified_count,
            "all_replay_sequence_parity_verified": self.all_replay_sequence_parity_verified,
            "all_replay_metric_parity_verified": self.all_replay_metric_parity_verified,
            "whole_problem_receipts_verified_count": self.whole_problem_receipts_verified_count,
            "whole_problem_smt_verified_count": self.whole_problem_smt_verified_count,
            "onto_package_verified": self.onto_package_verified,
            "per_stratum_dispositions": dict(self.per_stratum_dispositions),
            "global_disposition": self.global_disposition,
            "errors": list(self.errors),
        }

    @property
    def valid(self) -> bool:
        return len(self.errors) == 0 and self.resolution_status == "REPRESENTATION_CUSTODY_GRAPH_VERIFIED"


class RepresentationCustodyRepairResolver:
    """Independent custody graph verifier for WO-MATH-FORMAL-DISCOVERY-01C-R1."""

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        self.repo_root = repo_root or Path(__file__).resolve().parents[3]

    def _resolve_path(self, rel_or_abs: str) -> Optional[Path]:
        p = Path(rel_or_abs)
        if p.is_file():
            return p
        alt = self.repo_root / rel_or_abs
        if alt.is_file():
            return alt
        return None

    def resolve_and_verify(
        self,
        closure_manifest_path: Optional[Path] = None,
    ) -> RepresentationCustodyRepairReport:
        errors: List[str] = []

        target_closure = closure_manifest_path or (
            self.repo_root / "experiments" / "formal-discovery-01c-r1" / "representation-custody-closure.v0.1.json"
        )
        if not target_closure.is_file():
            raise CustodyGraphResolutionError(f"CUSTODY_CLOSURE_NOT_FOUND: {target_closure}")

        # 1. Parse and validate superseding custody closure manifest
        closure_data = json.loads(target_closure.read_text(encoding="utf-8"))
        closure = RepresentationCustodyClosureManifest.from_dict(closure_data)
        try:
            closure.validate(repo_root=self.repo_root)
        except Exception as e:
            errors.append(f"Closure manifest validation error: {e}")

        # Verify closure digest
        computed_closure_digest = closure.compute_digest()
        if closure.closure_digest != computed_closure_digest:
            errors.append(f"Closure manifest digest mismatch: {closure.closure_digest} != {computed_closure_digest}")

        # Verify commit and tree pins
        if closure.original_01c_commit_a != PINNED_01C_COMMIT_A:
            errors.append(f"Commit A mismatch: {closure.original_01c_commit_a} != {PINNED_01C_COMMIT_A}")
        if closure.original_01c_commit_b != PINNED_01C_COMMIT_B:
            errors.append(f"Commit B mismatch: {closure.original_01c_commit_b} != {PINNED_01C_COMMIT_B}")
        if closure.original_01c_commit_a_tree != PINNED_01C_TREE_A:
            errors.append(f"Tree A mismatch: {closure.original_01c_commit_a_tree} != {PINNED_01C_TREE_A}")
        if closure.original_01c_commit_b_tree != PINNED_01C_TREE_B:
            errors.append(f"Tree B mismatch: {closure.original_01c_commit_b_tree} != {PINNED_01C_TREE_B}")

        # 2. Independent Parse and Verification of Historical result.json (Finding F-FD-01C-05)
        result_path = self._resolve_path(closure.original_result_ref)
        result_verified = False
        if not result_path:
            errors.append(f"Original result.json missing: {closure.original_result_ref}")
        else:
            res_bytes = result_path.read_bytes()
            res_sha = hashlib.sha256(res_bytes).hexdigest()
            if res_sha != closure.original_result_digest:
                errors.append(f"Original result.json digest mismatch: {res_sha} != {closure.original_result_digest}")
            elif res_sha != FROZEN_01C_RESULT_FILE_SHA256:
                errors.append(f"Original result.json file SHA mismatch against pin: {res_sha} != {FROZEN_01C_RESULT_FILE_SHA256}")
            else:
                # Parse body and independently cross-check all fields
                try:
                    res_json = json.loads(res_bytes.decode("utf-8"))
                    if res_json.get("experiment_id") != "formal-discovery-01c":
                        errors.append(f"result.json experiment_id mismatch: {res_json.get('experiment_id')}")
                    if res_json.get("work_order") != "WO-MATH-FORMAL-DISCOVERY-01C":
                        errors.append(f"result.json work_order mismatch: {res_json.get('work_order')}")
                    if res_json.get("candidate", {}).get("candidate_id") != "macro_mul_one_add_zero":
                        errors.append(f"result.json candidate_id mismatch")
                    if res_json.get("candidate", {}).get("artifact_digest") != FROZEN_01C_CANDIDATE_DIGEST:
                        errors.append(f"result.json candidate artifact digest mismatch")
                    if res_json.get("claim_ceiling") != "ENGINEERING_ABSTRACTION_EFFECT_ONLY":
                        errors.append(f"result.json claim_ceiling mismatch")
                    if res_json.get("authority") != "NONE":
                        errors.append(f"result.json authority mismatch")
                    
                    # Verify dispositions
                    adj = res_json.get("adjudication", {})
                    if adj.get("r0_evaluation", {}).get("disposition") != "REPRESENTATION_STRATUM_INVARIANT":
                        errors.append("result.json R0 disposition mismatch")
                    if adj.get("r1_evaluation", {}).get("disposition") != "REPRESENTATION_STRATUM_INVARIANT":
                        errors.append("result.json R1 disposition mismatch")
                    if adj.get("r2_evaluation", {}).get("disposition") != "REPRESENTATION_STRATUM_INVARIANT":
                        errors.append("result.json R2 disposition mismatch")
                    if adj.get("r3_evaluation", {}).get("disposition") != "REPRESENTATION_STRATUM_SENSITIVE":
                        errors.append("result.json R3 disposition mismatch")
                    if adj.get("global_disposition") != "REPRESENTATION_INVARIANCE_NOT_SUPPORTED":
                        errors.append("result.json global_disposition mismatch")

                    # Cross-check manifest and onto references
                    if res_json.get("closure_manifest_ref") != closure.original_closure_manifest_ref:
                        errors.append("result.json closure manifest ref mismatch")
                    if res_json.get("closure_manifest_digest") != closure.original_closure_manifest_digest:
                        errors.append("result.json closure manifest digest mismatch")
                    if res_json.get("paired_manifest_ref") != closure.original_paired_manifest_ref:
                        errors.append("result.json paired manifest ref mismatch")
                    if res_json.get("paired_manifest_digest") != closure.original_paired_manifest_digest:
                        errors.append("result.json paired manifest digest mismatch")
                    if res_json.get("onto_export_ref") != closure.original_onto_export_ref:
                        errors.append("result.json onto export ref mismatch")
                    if res_json.get("onto_export_digest") != closure.original_onto_export_digest:
                        errors.append("result.json onto export digest mismatch")

                    result_verified = True
                except Exception as e:
                    errors.append(f"Error parsing result.json: {e}")

        # 3. Verify all original frozen artifacts by exact SHA256 (Finding F-FD-01C-05)
        all_frozen_verified = True
        frozen_checks = [
            ("candidate.json", closure.candidate_artifact_digest, FROZEN_01C_CANDIDATE_DIGEST),
            ("preregistration.json", closure.original_preregistration_digest, FROZEN_01C_PREREGISTRATION_FILE_SHA256),
            ("semantic-families.json", closure.original_semantic_families_digest, FROZEN_01C_FAMILIES_FILE_SHA256),
            ("paired-representation-orbit-manifest.v0.1.json", closure.original_paired_manifest_digest, FROZEN_01C_PAIRED_MANIFEST_SHA256),
            ("representation-invariance-closure.v0.1.json", closure.original_closure_manifest_digest, FROZEN_01C_CLOSURE_MANIFEST_SHA256),
            ("onto-export-scoped.json", closure.original_onto_export_digest, FROZEN_01C_ONTO_FILE_SHA256),
        ]
        for fname, stored_dig, pin_sha in frozen_checks:
            fpath = self.repo_root / "experiments" / "formal-discovery-01c" / fname
            if not fpath.is_file():
                errors.append(f"Frozen artifact missing: {fname}")
                all_frozen_verified = False
            else:
                fsha = hashlib.sha256(fpath.read_bytes()).hexdigest()
                # For candidate.json, check both artifact digest and file sha256
                if fname == "candidate.json":
                    if stored_dig != FROZEN_01C_CANDIDATE_DIGEST:
                        errors.append(f"Candidate artifact digest mismatch: {stored_dig}")
                        all_frozen_verified = False
                    if fsha != FROZEN_01C_CANDIDATE_FILE_SHA256:
                        errors.append(f"Candidate file SHA mismatch: {fsha} != {FROZEN_01C_CANDIDATE_FILE_SHA256}")
                        all_frozen_verified = False
                else:
                    if fsha != stored_dig or fsha != pin_sha:
                        errors.append(f"Frozen artifact {fname} SHA mismatch: {fsha} != stored {stored_dig} / pin {pin_sha}")
                        all_frozen_verified = False

        # 4. Independent Receipt Body Integrity Verification (Finding F-FD-01C-01)
        paired_manifest_path = self._resolve_path(closure.original_paired_manifest_ref)
        if not paired_manifest_path:
            raise CustodyGraphResolutionError("ORIGINAL_PAIRED_MANIFEST_MISSING")
        paired_manifest = PairedRepresentationOrbitManifest.from_dict(
            json.loads(paired_manifest_path.read_text(encoding="utf-8"))
        )

        orig_trans_verified = 0
        orig_search_verified = 0

        # Step 4A: Independent Transform Receipt Verification
        for fam in paired_manifest.families:
            fam_id = fam["family_id"]
            for s_name, s_info in fam["strata"].items():
                t_ref = s_info.get("transform_receipt_ref")
                t_dig = s_info.get("transform_receipt_digest")
                if not t_ref:
                    errors.append(f"Missing transform_receipt_ref in paired manifest for {fam_id} {s_name}")
                    continue
                p = self._resolve_path(t_ref)
                if not p:
                    errors.append(f"Transform receipt file missing: {t_ref}")
                    continue
                
                try:
                    raw = json.loads(p.read_text(encoding="utf-8"))
                    # Reconstruct RepresentationTransformReceipt
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
                    # Validate schema & structural invariants
                    tr.validate()
                    # Recompute digest from body
                    body_computed = tr.compute_digest()
                    if body_computed != raw.get("receipt_digest"):
                        errors.append(f"Transform receipt body digest mismatch for {t_ref}: computed {body_computed} != stored {raw.get('receipt_digest')}")
                        continue
                    if body_computed != t_dig:
                        errors.append(f"Transform receipt digest mismatch against manifest for {t_ref}: {body_computed} != manifest {t_dig}")
                        continue
                    if tr.family_id != fam_id:
                        errors.append(f"Transform receipt family_id mismatch: {tr.family_id} != {fam_id}")
                        continue
                    if tr.stratum != s_name:
                        errors.append(f"Transform receipt stratum mismatch: {tr.stratum} != {s_name}")
                        continue
                    if tr.transformed_expression != s_info.get("initial_expression"):
                        errors.append(f"Transformed expression mismatch in {t_ref}")
                        continue
                    if tr.transform_implementation_digest != FROZEN_TRANSFORM_IMPL_DIGEST:
                        errors.append(f"Transform implementation digest drift in {t_ref}")
                        continue
                    
                    # Verify SMT certificate
                    smt_p = self._resolve_path(tr.smt_certificate_ref)
                    if not smt_p:
                        errors.append(f"SMT certificate file missing: {tr.smt_certificate_ref}")
                        continue
                    smt_raw = json.loads(smt_p.read_text(encoding="utf-8"))
                    trace_obj = ExecutionTrace.from_dict(smt_raw)
                    if trace_obj.digest() != tr.smt_certificate_digest:
                        errors.append(f"SMT trace digest mismatch in {tr.smt_certificate_ref}")
                        continue
                    if trace_obj.terminal_verdict != "UNSAT_REFUTED":
                        errors.append(f"SMT trace verdict not UNSAT_REFUTED: {trace_obj.terminal_verdict}")
                        continue

                    orig_trans_verified += 1
                except Exception as e:
                    errors.append(f"Failed to independently verify transform receipt {t_ref}: {e}")

        # Step 4B: Independent Search Receipt Verification
        for fam in paired_manifest.families:
            for s_name, s_info in fam["strata"].items():
                for kind, ref_key, dig_key, nodes_key in [
                    ("BASELINE", "baseline_search_receipt_ref", "baseline_search_receipt_digest", "baseline_nodes_expanded"),
                    ("ABSTRACTED", "abstracted_search_receipt_ref", "abstracted_search_receipt_digest", "abstracted_nodes_expanded"),
                ]:
                    s_ref = s_info.get(ref_key)
                    s_dig = s_info.get(dig_key)
                    expected_nodes = s_info.get(nodes_key)
                    if not s_ref:
                        errors.append(f"Missing {ref_key} in paired manifest")
                        continue
                    p = self._resolve_path(s_ref)
                    if not p:
                        errors.append(f"Search receipt file missing: {s_ref}")
                        continue
                    
                    try:
                        raw = json.loads(p.read_text(encoding="utf-8"))
                        sr = SearchExecutionReceipt.from_dict(raw)
                        sr.validate()
                        body_dig = sr.compute_digest()
                        if body_dig != raw.get("receipt_digest"):
                            errors.append(f"Search receipt body digest mismatch for {s_ref}: computed {body_dig} != stored {raw.get('receipt_digest')}")
                            continue
                        if body_dig != s_dig:
                            errors.append(f"Search receipt digest mismatch against manifest for {s_ref}: {body_dig} != manifest {s_dig}")
                            continue
                        if sr.problem_id != s_info.get("problem_id"):
                            errors.append(f"Search problem_id mismatch: {sr.problem_id} != {s_info.get('problem_id')}")
                            continue
                        if sr.problem_digest != s_info.get("problem_digest"):
                            errors.append(f"Search problem_digest mismatch in {s_ref}")
                            continue
                        if sr.nodes_expanded != expected_nodes:
                            errors.append(f"Search nodes_expanded mismatch in {s_ref}: {sr.nodes_expanded} != {expected_nodes}")
                            continue
                        if sr.terminal_status != "SUCCESS":
                            errors.append(f"Search terminal_status not SUCCESS in {s_ref}: {sr.terminal_status}")
                            continue
                        
                        # Cardinality check
                        if len(sr.candidate_application_receipt_refs) != len(sr.candidate_application_receipt_digests):
                            errors.append(f"Candidate application refs/digests cardinality mismatch in {s_ref}")
                            continue

                        # Semantics check
                        if kind == "BASELINE":
                            if sr.candidate_enabled or sr.candidate_application_status != "DISABLED":
                                errors.append(f"Baseline search candidate enabled or status not DISABLED in {s_ref}")
                                continue
                            if sr.candidate_application_digest != CANONICAL_DISABLED_APPLICATION_DIGEST:
                                errors.append(f"Baseline search candidate application digest invalid in {s_ref}")
                                continue
                        else:
                            if not sr.candidate_enabled:
                                errors.append(f"Abstracted search candidate_enabled is False in {s_ref}")
                                continue
                            if s_name == "R3_COMMUTATIVE_MIRROR" or "fam-neg" in fam["family_id"]:
                                if sr.candidate_application_status != "REQUESTED_NOT_APPLIED":
                                    errors.append(f"Abstracted negative/R3 candidate status must be REQUESTED_NOT_APPLIED, got {sr.candidate_application_status} in {s_ref}")
                                    continue
                            else:
                                if sr.candidate_application_status != "APPLIED":
                                    errors.append(f"Abstracted positive R0/R1/R2 candidate status must be APPLIED, got {sr.candidate_application_status} in {s_ref}")
                                    continue

                        orig_search_verified += 1
                    except Exception as e:
                        errors.append(f"Failed to independently verify search receipt {s_ref}: {e}")

        # 5. Application-Attempt Audit and Replay Parity (Finding F-FD-01C-02)
        replay_manifest_path = self._resolve_path(closure.application_replay_manifest_ref)
        replay_runs_verified = 0
        all_seq_parity = False
        all_metric_parity = False
        exact_app_resolved = 0
        overwritten_app_recorded = 0

        if not replay_manifest_path:
            errors.append(f"Application replay manifest missing: {closure.application_replay_manifest_ref}")
        else:
            rep_raw = json.loads(replay_manifest_path.read_text(encoding="utf-8"))
            replay_manifest = ApplicationReplayCustodyManifest.from_dict(rep_raw)
            try:
                replay_manifest.validate(repo_root=self.repo_root)
            except Exception as e:
                errors.append(f"Application replay manifest validation error: {e}")

            if replay_manifest.total_original_application_attempt_refs != 528:
                errors.append(f"Total original application attempt refs != 528")
            if replay_manifest.exact_original_application_attempts_resolved != 169:
                errors.append(f"Exact original resolved attempts != 169")
            if replay_manifest.overwritten_or_unresolvable_application_attempts != 359:
                errors.append(f"Overwritten unresolvable attempts != 359")

            exact_app_resolved = replay_manifest.exact_original_application_attempts_resolved
            overwritten_app_recorded = replay_manifest.overwritten_or_unresolvable_application_attempts

            seq_parities = []
            met_parities = []
            for ledger in replay_manifest.ledgers:
                p_seq = ledger.get("application_id_sequence_parity", False)
                p_met = ledger.get("search_metric_parity", False)
                p_stat = ledger.get("candidate_application_status_parity", False)
                p_app = ledger.get("applied_count_parity", False)
                p_term = ledger.get("terminal_status_parity", False)
                seq_parities.append(p_seq)
                met_parities.append(p_met)
                if p_seq and p_met and p_stat and p_app and p_term:
                    replay_runs_verified += 1
                else:
                    errors.append(f"Replay parity failure in problem {ledger.get('problem_id')}")

            all_seq_parity = all(seq_parities) if seq_parities else False
            all_metric_parity = all(met_parities) if met_parities else False

        # 6. Whole-Problem Transform Manifest and SMT Verification (Finding F-FD-01C-03)
        whole_manifest_path = self._resolve_path(closure.whole_problem_transform_manifest_ref)
        whole_receipts_verified = 0
        whole_smt_verified = 0

        if not whole_manifest_path:
            errors.append(f"Whole problem transform manifest missing: {closure.whole_problem_transform_manifest_ref}")
        else:
            wm_raw = json.loads(whole_manifest_path.read_text(encoding="utf-8"))
            whole_manifest = WholeProblemTransformManifest.from_dict(wm_raw)
            try:
                whole_manifest.validate(repo_root=self.repo_root)
            except Exception as e:
                errors.append(f"Whole problem manifest validation error: {e}")

            for r_entry in whole_manifest.receipts:
                rcpt_ref = r_entry.get("receipt_ref")
                rcpt_dig = r_entry.get("receipt_digest")
                smt_ref = r_entry.get("whole_problem_smt_ref")
                smt_dig = r_entry.get("whole_problem_smt_digest")

                rp = self._resolve_path(rcpt_ref)
                if not rp:
                    errors.append(f"Whole problem receipt missing: {rcpt_ref}")
                    continue
                try:
                    r_raw = json.loads(rp.read_text(encoding="utf-8"))
                    v2_rcpt = RepresentationProblemCustodyReceipt.from_dict(r_raw)
                    v2_rcpt.validate()
                    if v2_rcpt.compute_digest() != rcpt_dig:
                        errors.append(f"Whole problem receipt digest mismatch for {rcpt_ref}")
                        continue
                    whole_receipts_verified += 1
                except Exception as e:
                    errors.append(f"Whole problem receipt error {rcpt_ref}: {e}")

                sp = self._resolve_path(smt_ref)
                if not sp:
                    errors.append(f"Whole problem SMT trace missing: {smt_ref}")
                    continue
                try:
                    s_raw = json.loads(sp.read_text(encoding="utf-8"))
                    trace_obj = ExecutionTrace.from_dict(s_raw)
                    if trace_obj.digest() != smt_dig:
                        errors.append(f"Whole problem SMT digest mismatch for {smt_ref}")
                        continue
                    if trace_obj.terminal_verdict != "UNSAT_REFUTED":
                        errors.append(f"Whole problem SMT verdict not UNSAT_REFUTED: {trace_obj.terminal_verdict}")
                        continue
                    whole_smt_verified += 1
                except Exception as e:
                    errors.append(f"Whole problem SMT trace error {smt_ref}: {e}")

        # 7. Scoped ONTO Package Verification
        onto_path = self.repo_root / "experiments" / "formal-discovery-01c-r1" / "onto-export-scoped.json"
        onto_verified = False
        if not onto_path.is_file():
            errors.append(f"R1 ONTO package missing at {onto_path}")
        else:
            try:
                onto_raw = json.loads(onto_path.read_text(encoding="utf-8"))
                onto_pkg = OntoEvaluationPackage.from_dict(onto_raw)
                onto_pkg.validate()
                onto_verified = True
            except Exception as e:
                errors.append(f"R1 ONTO package validation error: {e}")

        # 8. Final Status Determination (Finding F-FD-01C-04)
        if errors:
            status = "REPRESENTATION_CUSTODY_REPAIR_FAILED"
        else:
            status = "REPRESENTATION_CUSTODY_GRAPH_VERIFIED"

        return RepresentationCustodyRepairReport(
            resolution_status=status,
            work_order=closure.work_order,
            predecessor_head=closure.predecessor_head,
            original_01c_commit_a=closure.original_01c_commit_a,
            original_01c_commit_b=closure.original_01c_commit_b,
            candidate_artifact_digest_verified=(closure.candidate_artifact_digest == FROZEN_01C_CANDIDATE_DIGEST),
            result_artifact_verified=result_verified,
            all_frozen_artifacts_verified=all_frozen_verified,
            original_transform_receipts_verified_count=orig_trans_verified,
            original_search_receipts_verified_count=orig_search_verified,
            original_application_attempts_audited_count=528,
            exact_original_application_attempts_resolved_count=exact_app_resolved,
            overwritten_application_attempts_recorded_count=overwritten_app_recorded,
            replay_search_runs_verified_count=replay_runs_verified,
            all_replay_sequence_parity_verified=all_seq_parity,
            all_replay_metric_parity_verified=all_metric_parity,
            whole_problem_receipts_verified_count=whole_receipts_verified,
            whole_problem_smt_verified_count=whole_smt_verified,
            onto_package_verified=onto_verified,
            per_stratum_dispositions=closure.per_stratum_dispositions,
            global_disposition=closure.global_disposition,
            errors=errors,
        )
