"""Superseding custody graph resolver and independent evidence verifier (WO-MATH-FORMAL-DISCOVERY-01C-R1 & R1-R1)."""
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

PINNED_01C_R1_COMMIT_A = "89fc1d6e4f290af0e8b4a61bc753efce04170526"
PINNED_01C_R1_COMMIT_B = "1097bd5c1b165184bdfdd7323f8e2e7c25699f3c"
PINNED_01C_R1_TREE_A = "231b157807531345e792ab13a3fb3d1730137693"
PINNED_01C_R1_TREE_B = "11de77b7b2f679212f0cb630cc071da8d3291010"

FROZEN_01C_CANDIDATE_DIGEST = "273a1d821e54ba6bf1832a2f1f11b338853aa9d1070d873c8b29345ba5aae903"
FROZEN_01C_CANDIDATE_FILE_SHA256 = "4794cc897bc60ddd928b3abdecd25bbb343c2388b3d3bf6a466d1b5656c65d31"
FROZEN_01C_PREREGISTRATION_FILE_SHA256 = "bd30fa638f7691c63d395337d9cf770a4d720596dae9647905662f533ed5ed15"
FROZEN_01C_FAMILIES_FILE_SHA256 = "16e65651439d3253542c9eb0711acd692c91727047927395aab96d45b1fbd5ea"
FROZEN_01C_RESULT_FILE_SHA256 = "1455687bb385b75a01fb9c8c29158b3de6151878e0124c1af7c8a5faab7f68a8"
FROZEN_01C_ONTO_FILE_SHA256 = "7357580c96371a1512a9a8598caeb77f7bf6d1d78d587f8c30959ba086f8706f"
FROZEN_01C_PAIRED_MANIFEST_SHA256 = "671e7069aad34d4b776312a293c54e7d0798c20fedb3ee9079aa241f84cfdb93"
FROZEN_01C_CLOSURE_MANIFEST_SHA256 = "896588d4b34e44222eb5f982335b7e6bbbe9a5ac9f1d3c473bbec525764e3186"

FROZEN_01C_R1_APPLICATION_REPLAY_MANIFEST_SHA256 = "5b7756eabd4f488ff5e0b3e747226dfb9574d4ab02a39e98c4ecf0c2c8b97e6f"
FROZEN_01C_R1_CLOSURE_MANIFEST_SHA256 = "d5d92178da7473690b0bd4520ce0d7492d49f97c830887ca63a8e0e3375a1d2c"
FROZEN_01C_R1_CLOSURE_DIGEST = "ac06e32b19eb4c27fa240211e7ecc043dd00f132b0a926ab7b52d3e3241fd6e3"
FROZEN_01C_R1_WHOLE_PROBLEM_MANIFEST_SHA256 = "12f14b366dbf5264158379c1de47f8b80cab25ad985e5490875a5f89f342d0da"
FROZEN_01C_R1_ONTO_FILE_SHA256 = "48a9ba5309c7e8ad0f97dbbd5f44466900614cc4543ba22c0d889a3dd339c748"

FROZEN_TRANSFORM_IMPL_DIGEST = "5c85f28d268f138ffbf2ec8d9fe400d72a1378ed09223ddff43a802ccd809d4a"
FROZEN_APPLICATOR_IMPL_DIGEST = "04e4418028c480a2963242e678af5cf7070257d2b0f2f38b3a7016ee3c2c5360"

FROZEN_SEARCH_BUDGET = {"max_expansions": 100}
FROZEN_SEARCH_BUDGET_DIGEST = "33e3063843806441f4193971b31f4c3093393af722d83f8f95cc11ff669f9635"


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
    search_replay_receipts_verified_count: int = 0
    application_replay_receipts_verified_count: int = 0
    all_applied_count_parity_verified: bool = False
    all_search_budget_parity_verified: bool = False
    search_budget_digest_verified: bool = False
    original_attempt_body_custody: str = "PARTIAL_AND_EXPLICIT"
    deterministic_replay_attempt_body_custody: str = "COMPLETE"
    derived_sequence_parity_count: int = 0
    derived_search_metric_parity_count: int = 0
    derived_candidate_status_parity_count: int = 0
    derived_terminal_status_parity_count: int = 0
    derived_search_substrate_parity_count: int = 0
    derived_applied_count_parity_count: int = 0

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
            "search_replay_receipts_verified_count": self.search_replay_receipts_verified_count,
            "application_replay_receipts_verified_count": self.application_replay_receipts_verified_count,
            "all_applied_count_parity_verified": self.all_applied_count_parity_verified,
            "all_search_budget_parity_verified": self.all_search_budget_parity_verified,
            "search_budget_digest_verified": self.search_budget_digest_verified,
            "original_attempt_body_custody": self.original_attempt_body_custody,
            "deterministic_replay_attempt_body_custody": self.deterministic_replay_attempt_body_custody,
            "derived_sequence_parity_count": self.derived_sequence_parity_count,
            "derived_search_metric_parity_count": self.derived_search_metric_parity_count,
            "derived_candidate_status_parity_count": self.derived_candidate_status_parity_count,
            "derived_terminal_status_parity_count": self.derived_terminal_status_parity_count,
            "derived_search_substrate_parity_count": self.derived_search_substrate_parity_count,
            "derived_applied_count_parity_count": self.derived_applied_count_parity_count,
        }

    @property
    def valid(self) -> bool:
        return len(self.errors) == 0 and self.resolution_status == "REPRESENTATION_CUSTODY_GRAPH_VERIFIED"


class RepresentationCustodyRepairResolver:
    """Independent custody graph verifier for WO-MATH-FORMAL-DISCOVERY-01C-R1 and 01C-R1-R1."""

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
    ) -> RepresentationCustodyRepairReport:
        errors: List[str] = []

        if closure_manifest_path:
            target_closure = closure_manifest_path
        elif (self.repo_root / "experiments" / "formal-discovery-01c-r1-r1" / "representation-custody-closure.v0.1.json").is_file():
            target_closure = self.repo_root / "experiments" / "formal-discovery-01c-r1-r1" / "representation-custody-closure.v0.1.json"
        else:
            target_closure = self.repo_root / "experiments" / "formal-discovery-01c-r1" / "representation-custody-closure.v0.1.json"

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

        is_r1_r1 = (closure.work_order == "WO-MATH-FORMAL-DISCOVERY-01C-R1-R1")
        if is_r1_r1:
            if closure.original_r1_commit_a != PINNED_01C_R1_COMMIT_A:
                errors.append(f"R1 Commit A mismatch: {closure.original_r1_commit_a} != {PINNED_01C_R1_COMMIT_A}")
            if closure.original_r1_commit_b != PINNED_01C_R1_COMMIT_B:
                errors.append(f"R1 Commit B mismatch: {closure.original_r1_commit_b} != {PINNED_01C_R1_COMMIT_B}")
            if closure.original_r1_commit_a_tree != PINNED_01C_R1_TREE_A:
                errors.append(f"R1 Tree A mismatch: {closure.original_r1_commit_a_tree} != {PINNED_01C_R1_TREE_A}")
            if closure.original_r1_commit_b_tree != PINNED_01C_R1_TREE_B:
                errors.append(f"R1 Tree B mismatch: {closure.original_r1_commit_b_tree} != {PINNED_01C_R1_TREE_B}")
            if closure.predecessor_head != PINNED_01C_R1_COMMIT_B:
                errors.append(f"Predecessor head mismatch: {closure.predecessor_head} != {PINNED_01C_R1_COMMIT_B}")
            if closure.search_budget_digest != FROZEN_SEARCH_BUDGET_DIGEST:
                errors.append(f"Closure search budget digest mismatch: {closure.search_budget_digest} != {FROZEN_SEARCH_BUDGET_DIGEST}")
            if closure.original_attempt_body_custody != "PARTIAL_AND_EXPLICIT":
                errors.append(f"Original attempt body custody must be PARTIAL_AND_EXPLICIT, got {closure.original_attempt_body_custody}")
            if closure.deterministic_replay_attempt_body_custody != "COMPLETE":
                errors.append(f"Deterministic replay attempt body custody must be COMPLETE, got {closure.deterministic_replay_attempt_body_custody}")

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

        if is_r1_r1:
            r1_frozen_checks = [
                ("application-replay-custody-manifest.v0.1.json", FROZEN_01C_R1_APPLICATION_REPLAY_MANIFEST_SHA256),
                ("representation-custody-closure.v0.1.json", FROZEN_01C_R1_CLOSURE_MANIFEST_SHA256),
                ("whole-problem-transform-manifest.v0.1.json", FROZEN_01C_R1_WHOLE_PROBLEM_MANIFEST_SHA256),
                ("onto-export-scoped.json", FROZEN_01C_R1_ONTO_FILE_SHA256),
            ]
            for fname, pin_sha in r1_frozen_checks:
                fpath = self.repo_root / "experiments" / "formal-discovery-01c-r1" / fname
                if not fpath.is_file():
                    errors.append(f"Historical 01C-R1 artifact missing: {fname}")
                    all_frozen_verified = False
                else:
                    fsha = hashlib.sha256(fpath.read_bytes()).hexdigest()
                    if fsha != pin_sha:
                        errors.append(f"Historical 01C-R1 artifact {fname} SHA mismatch: {fsha} != pin {pin_sha}")
                        all_frozen_verified = False

            if closure.original_r1_closure_manifest_ref:
                r1_c_p = self._resolve_path(closure.original_r1_closure_manifest_ref)
                if not r1_c_p:
                    errors.append(f"R1 closure manifest missing: {closure.original_r1_closure_manifest_ref}")
                else:
                    r1_c_data = json.loads(r1_c_p.read_text(encoding="utf-8"))
                    if r1_c_data.get("closure_digest") != closure.original_r1_closure_manifest_digest:
                        errors.append("R1 closure manifest digest mismatch against closure")
                    if r1_c_data.get("closure_digest") != FROZEN_01C_R1_CLOSURE_DIGEST:
                        errors.append("R1 closure manifest digest mismatch against pin")

        # 4. Independent Receipt Body Integrity Verification (Finding F-FD-01C-01)
        paired_manifest_path = self._resolve_path(closure.original_paired_manifest_ref)
        if not paired_manifest_path:
            raise CustodyGraphResolutionError("ORIGINAL_PAIRED_MANIFEST_MISSING")
        paired_manifest = PairedRepresentationOrbitManifest.from_dict(
            json.loads(paired_manifest_path.read_text(encoding="utf-8"))
        )
        try:
            paired_manifest.validate(repo_root=self.repo_root)
        except Exception as e:
            errors.append(f"Paired manifest validation error: {e}")

        orig_trans_verified = 0
        orig_search_verified = 0

        # Step 4A: Independent Transform Receipt Verification
        for fam in paired_manifest.families:
            fam_id = fam["family_id"]
            for s_name, s_info in fam["strata"].items():
                t_ref = s_info.get("transform_receipt_ref")
                t_dig = s_info.get("transform_receipt_digest")
                if not t_ref:
                    errors.append(f"Missing transform_receipt_ref for {fam_id}:{s_name}")
                    continue
                p = self._resolve_path(t_ref)
                if not p:
                    errors.append(f"Transform receipt file missing: {t_ref}")
                    continue
                
                try:
                    raw = json.loads(p.read_text(encoding="utf-8"))
                    tr = RepresentationTransformReceipt.from_dict(raw)
                    tr.validate()
                    body_dig = tr.compute_digest()
                    if body_dig != raw.get("receipt_digest"):
                        errors.append(f"Transform receipt body digest mismatch for {t_ref}: computed {body_dig} != stored {raw.get('receipt_digest')}")
                        continue
                    if body_dig != t_dig:
                        errors.append(f"Transform receipt digest mismatch against manifest for {t_ref}: {body_dig} != manifest {t_dig}")
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
        paired_strata_by_problem_id: Dict[str, Dict[str, Any]] = {}
        original_abstracted_search_receipts: Dict[str, SearchExecutionReceipt] = {}

        for fam in paired_manifest.families:
            for s_name, s_info in fam["strata"].items():
                p_id = s_info.get("problem_id")
                if p_id:
                    paired_strata_by_problem_id[p_id] = s_info
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
                        
                        if len(sr.candidate_application_receipt_refs) != len(sr.candidate_application_receipt_digests):
                            errors.append(f"Candidate application refs/digests cardinality mismatch in {s_ref}")
                            continue

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
                            original_abstracted_search_receipts[sr.problem_id] = sr

                        orig_search_verified += 1
                    except Exception as e:
                        errors.append(f"Failed to independently verify search receipt {s_ref}: {e}")

        # 5. Application-Attempt Audit and Replay Parity (Finding F-FD-01C-02, F-FD-01C-R1-01 to 03, F-FD-01C-R1-R1-01)
        replay_manifest_path = self._resolve_path(closure.application_replay_manifest_ref)
        replay_runs_verified = 0
        all_seq_parity = False
        all_metric_parity = False
        all_candidate_status_parity = False
        all_terminal_status_parity = False
        all_search_budget_parity = False
        all_app_cnt_parity = False
        search_budget_digest_verified = False
        exact_app_resolved = 0
        overwritten_app_recorded = 0
        replay_search_rcpts_verified = 0
        replay_app_rcpts_verified = 0

        seq_parities: List[bool] = []
        met_parities: List[bool] = []
        stat_parities: List[bool] = []
        term_parities: List[bool] = []
        sub_parities: List[bool] = []
        app_cnt_parities: List[bool] = []

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
                errors.append("Total original application attempt refs != 528")
            if replay_manifest.exact_original_application_attempts_resolved != 169:
                errors.append("Exact original resolved attempts != 169")
            if replay_manifest.overwritten_or_unresolvable_application_attempts != 359:
                errors.append("Overwritten unresolvable attempts != 359")
            if replay_manifest.search_budget_digest != FROZEN_SEARCH_BUDGET_DIGEST:
                errors.append(f"Replay manifest search budget digest mismatch: {replay_manifest.search_budget_digest} != {FROZEN_SEARCH_BUDGET_DIGEST}")
            else:
                search_budget_digest_verified = True

            exact_app_resolved = replay_manifest.exact_original_application_attempts_resolved
            overwritten_app_recorded = replay_manifest.overwritten_or_unresolvable_application_attempts

            for ledger in replay_manifest.ledgers:
                prob_id = ledger.get("problem_id", "")
                if not prob_id:
                    errors.append("Ledger missing problem_id")
                    continue

                s_info = paired_strata_by_problem_id.get(prob_id)
                if not s_info:
                    errors.append(f"Problem {prob_id} missing from paired manifest strata")
                    continue

                # 1. Resolve immutable original abstracted search receipt
                orig_sr = original_abstracted_search_receipts.get(prob_id)
                if not orig_sr:
                    orig_s_ref = s_info.get("abstracted_search_receipt_ref") or ledger.get("original_search_receipt_ref")
                    orig_sp = self._resolve_path(orig_s_ref) if orig_s_ref else None
                    if not orig_sp:
                        errors.append(f"Original abstracted search receipt missing for problem {prob_id}: {orig_s_ref}")
                        continue
                    try:
                        orig_raw = json.loads(orig_sp.read_text(encoding="utf-8"))
                        orig_sr = SearchExecutionReceipt.from_dict(orig_raw)
                        orig_sr.validate()
                        if orig_sr.compute_digest() != orig_raw.get("receipt_digest"):
                            errors.append(f"Original search receipt digest mismatch for {orig_s_ref}")
                            continue
                    except Exception as e:
                        errors.append(f"Failed to load original search receipt {orig_s_ref}: {e}")
                        continue

                # 2. Resolve persisted replay search receipt
                replay_s_ref = ledger.get("replay_search_receipt_ref")
                replay_s_dig = ledger.get("replay_search_receipt_digest")
                rep_sr: Optional[SearchExecutionReceipt] = None
                if not replay_s_ref:
                    if is_r1_r1:
                        errors.append(f"Missing replay_search_receipt_ref in ledger for {prob_id}")
                else:
                    rsp = self._resolve_path(replay_s_ref)
                    if not rsp:
                        errors.append(f"Replay search receipt missing: {replay_s_ref}")
                    else:
                        try:
                            sraw = json.loads(rsp.read_text(encoding="utf-8"))
                            rep_sr = SearchExecutionReceipt.from_dict(sraw)
                            rep_sr.validate()
                            rcomp_dig = rep_sr.compute_digest()
                            if rcomp_dig != sraw.get("receipt_digest"):
                                errors.append(f"Replay search receipt body digest mismatch for {replay_s_ref}")
                                rep_sr = None
                            elif rcomp_dig != replay_s_dig:
                                errors.append(f"Replay search receipt digest mismatch against ledger for {replay_s_ref}: {rcomp_dig} != {replay_s_dig}")
                                rep_sr = None
                            else:
                                replay_search_rcpts_verified += 1
                        except Exception as e:
                            errors.append(f"Failed to independently verify replay search receipt {replay_s_ref}: {e}")
                            rep_sr = None

                # 3. Resolve all persisted replay CandidateApplicationReceipt bodies
                replay_app_attempts = ledger.get("replay_application_attempts")
                valid_replay_car_bodies: List[CandidateApplicationReceipt] = []
                car_bodies_valid = True

                if replay_app_attempts is None:
                    if is_r1_r1:
                        errors.append(f"Missing replay_application_attempts in ledger for {prob_id}")
                        car_bodies_valid = False
                else:
                    if len(replay_app_attempts) != ledger.get("replay_attempt_count"):
                        errors.append(f"Replay attempt count mismatch in {prob_id}: {len(replay_app_attempts)} != {ledger.get('replay_attempt_count')}")
                        car_bodies_valid = False
                    if len(replay_app_attempts) != len(ledger.get("ordered_replay_application_receipt_refs", [])):
                        errors.append(f"Replay receipt refs count mismatch in {prob_id}")
                        car_bodies_valid = False
                    if len(replay_app_attempts) != len(ledger.get("ordered_replay_application_receipt_digests", [])):
                        errors.append(f"Replay receipt digests count mismatch in {prob_id}")
                        car_bodies_valid = False

                    for attempt in replay_app_attempts:
                        ord_idx = attempt.get("ordinal", 0)
                        a_ref = attempt.get("receipt_ref")
                        a_dig = attempt.get("receipt_digest")
                        a_id = attempt.get("application_id")
                        a_stat = attempt.get("application_status")

                        if not ledger.get("ordered_replay_application_receipt_refs") or ord_idx >= len(ledger["ordered_replay_application_receipt_refs"]) or a_ref != ledger["ordered_replay_application_receipt_refs"][ord_idx]:
                            errors.append(f"Replay attempt ref mismatch at ordinal {ord_idx} in {prob_id}")
                            car_bodies_valid = False
                            continue
                        if not ledger.get("ordered_replay_application_receipt_digests") or ord_idx >= len(ledger["ordered_replay_application_receipt_digests"]) or a_dig != ledger["ordered_replay_application_receipt_digests"][ord_idx]:
                            errors.append(f"Replay attempt digest mismatch at ordinal {ord_idx} in {prob_id}")
                            car_bodies_valid = False
                            continue

                        ap = self._resolve_path(a_ref)
                        if not ap:
                            errors.append(f"Replay application receipt missing: {a_ref}")
                            car_bodies_valid = False
                            continue

                        try:
                            araw = json.loads(ap.read_text(encoding="utf-8"))
                            required_receipt_keys = {
                                "schema_version", "application_id", "candidate_id",
                                "candidate_artifact_digest", "experimental_unit_id", "problem_digest",
                                "application_status", "applicator_implementation_digest", "receipt_digest"
                            }
                            if not required_receipt_keys.issubset(araw.keys()):
                                errors.append(f"Partial/summary masquerade detected in replay receipt: {a_ref}")
                                car_bodies_valid = False
                                continue

                            car = CandidateApplicationReceipt.from_dict(araw)
                            car.validate()
                            car_comp_dig = car.compute_digest()

                            if car_comp_dig != araw.get("receipt_digest"):
                                errors.append(f"Replay application receipt body digest mismatch for {a_ref}")
                                car_bodies_valid = False
                            elif car_comp_dig != a_dig:
                                errors.append(f"Replay application receipt digest mismatch against attempt for {a_ref}: {car_comp_dig} != {a_dig}")
                                car_bodies_valid = False
                            elif car.application_id != a_id:
                                errors.append(f"Replay application receipt id mismatch in {a_ref}: {car.application_id} != {a_id}")
                                car_bodies_valid = False
                            elif car.experimental_unit_id != prob_id:
                                errors.append(f"Replay application receipt problem_id mismatch in {a_ref}: {car.experimental_unit_id} != {prob_id}")
                                car_bodies_valid = False
                            elif car.problem_digest != ledger.get("problem_digest"):
                                errors.append(f"Replay application receipt problem_digest mismatch in {a_ref}")
                                car_bodies_valid = False
                            elif car.candidate_id != "macro_mul_one_add_zero":
                                errors.append(f"Replay application receipt candidate_id mismatch in {a_ref}: {car.candidate_id}")
                                car_bodies_valid = False
                            elif car.candidate_artifact_digest != FROZEN_01C_CANDIDATE_DIGEST:
                                errors.append(f"Replay application receipt candidate artifact digest mismatch in {a_ref}")
                                car_bodies_valid = False
                            elif car.applicator_implementation_digest != FROZEN_APPLICATOR_IMPL_DIGEST:
                                errors.append(f"Applicator implementation digest drift in {a_ref}: {car.applicator_implementation_digest}")
                                car_bodies_valid = False
                            elif car.application_status != a_stat:
                                errors.append(f"Application status mismatch in {a_ref}: {car.application_status} != {a_stat}")
                                car_bodies_valid = False
                            else:
                                valid_replay_car_bodies.append(car)
                                replay_app_rcpts_verified += 1
                        except Exception as e:
                            errors.append(f"Failed to independently verify replay application receipt {a_ref}: {e}")
                            car_bodies_valid = False

                # 4. Independent Replay-Parity Derivations (Finding F-FD-01C-R1-R1-01)
                is_pos_applied = (
                    "fam-pos" in s_info.get("problem_id", "")
                    and s_info.get("stratum") != "R3_COMMUTATIVE_MIRROR"
                )
                exp_cand_status = "APPLIED" if is_pos_applied else "REQUESTED_NOT_APPLIED"

                if is_r1_r1:
                    if rep_sr is None or orig_sr is None:
                        seq_parities.append(False)
                        met_parities.append(False)
                        stat_parities.append(False)
                        term_parities.append(False)
                        sub_parities.append(False)
                        app_cnt_parities.append(False)
                        continue

                    # A. Application ID Sequence Parity
                    orig_app_ids = list(orig_sr.candidate_application_receipt_refs)
                    rep_app_ids = list(rep_sr.candidate_application_receipt_refs)
                    ledger_orig_ids = list(ledger.get("ordered_original_application_ids", []))
                    ledger_rep_ids = list(ledger.get("ordered_replay_application_ids", []))
                    attempt_app_ids = [a.get("application_id") for a in (replay_app_attempts or [])]
                    body_app_ids = [c.application_id for c in valid_replay_car_bodies]

                    derived_seq_parity = bool(
                        car_bodies_valid
                        and orig_app_ids == rep_app_ids == ledger_orig_ids == ledger_rep_ids == attempt_app_ids == body_app_ids
                    )
                    if not derived_seq_parity:
                        errors.append(f"Derived application ID sequence parity failed for {prob_id}")
                    if ledger.get("application_id_sequence_parity") != derived_seq_parity:
                        errors.append(
                            f"Application ID sequence parity ledger mismatch for {prob_id}: "
                            f"ledger={ledger.get('application_id_sequence_parity')} != derived={derived_seq_parity}"
                        )

                    # B. Search Metric Parity
                    exp_nodes = s_info.get("abstracted_nodes_expanded")
                    derived_met_parity = bool(
                        orig_sr.nodes_expanded == rep_sr.nodes_expanded == exp_nodes
                        and orig_sr.nodes_evaluated == rep_sr.nodes_evaluated
                        and orig_sr.branch_count == rep_sr.branch_count
                    )
                    if not derived_met_parity:
                        errors.append(
                            f"Derived search metric parity failed for {prob_id}: "
                            f"orig_nodes={orig_sr.nodes_expanded}, rep_nodes={rep_sr.nodes_expanded}, exp={exp_nodes}, "
                            f"orig_eval={orig_sr.nodes_evaluated}, rep_eval={rep_sr.nodes_evaluated}, "
                            f"orig_branch={orig_sr.branch_count}, rep_branch={rep_sr.branch_count}"
                        )
                    if ledger.get("search_metric_parity") != derived_met_parity:
                        errors.append(
                            f"Search metric parity ledger mismatch for {prob_id}: "
                            f"ledger={ledger.get('search_metric_parity')} != derived={derived_met_parity}"
                        )

                    # C. Candidate Application Status Parity
                    derived_stat_parity = bool(
                        orig_sr.candidate_enabled is True
                        and rep_sr.candidate_enabled is True
                        and orig_sr.candidate_id == "macro_mul_one_add_zero"
                        and rep_sr.candidate_id == "macro_mul_one_add_zero"
                        and orig_sr.candidate_application_status == rep_sr.candidate_application_status == exp_cand_status
                    )
                    if not derived_stat_parity:
                        errors.append(
                            f"Derived candidate status parity failed for {prob_id}: "
                            f"orig_status={orig_sr.candidate_application_status}, rep_status={rep_sr.candidate_application_status}, exp={exp_cand_status}, "
                            f"orig_id={orig_sr.candidate_id}, rep_id={rep_sr.candidate_id}, "
                            f"orig_enabled={orig_sr.candidate_enabled}, rep_enabled={rep_sr.candidate_enabled}"
                        )
                    if ledger.get("candidate_application_status_parity") != derived_stat_parity:
                        errors.append(
                            f"Candidate status parity ledger mismatch for {prob_id}: "
                            f"ledger={ledger.get('candidate_application_status_parity')} != derived={derived_stat_parity}"
                        )

                    # D. Terminal Status Parity
                    derived_term_parity = bool(
                        orig_sr.terminal_status == "SUCCESS"
                        and rep_sr.terminal_status == "SUCCESS"
                    )
                    if not derived_term_parity:
                        errors.append(
                            f"Derived terminal status parity failed for {prob_id}: "
                            f"orig_term={orig_sr.terminal_status}, rep_term={rep_sr.terminal_status}"
                        )
                    if ledger.get("terminal_status_parity") != derived_term_parity:
                        errors.append(
                            f"Terminal status parity ledger mismatch for {prob_id}: "
                            f"ledger={ledger.get('terminal_status_parity')} != derived={derived_term_parity}"
                        )

                    # E. Search Substrate Parity (Frozen Substrate)
                    derived_sub_parity = bool(
                        orig_sr.problem_id == rep_sr.problem_id == s_info.get("problem_id") == ledger.get("problem_id")
                        and orig_sr.problem_digest == rep_sr.problem_digest == s_info.get("problem_digest") == ledger.get("problem_digest")
                        and orig_sr.search_policy == rep_sr.search_policy
                        and orig_sr.search_policy_implementation_digest == rep_sr.search_policy_implementation_digest
                        and orig_sr.environment_identity_digest == rep_sr.environment_identity_digest
                        and orig_sr.search_budget_digest == rep_sr.search_budget_digest == FROZEN_SEARCH_BUDGET_DIGEST
                        and ledger.get("search_budget_digest") == FROZEN_SEARCH_BUDGET_DIGEST
                    )
                    if not derived_sub_parity:
                        errors.append(
                            f"Derived search substrate parity failed for {prob_id}: "
                            f"p_id=({orig_sr.problem_id}, {rep_sr.problem_id}, {s_info.get('problem_id')}, {ledger.get('problem_id')}), "
                            f"p_dig=({orig_sr.problem_digest[:8]}, {rep_sr.problem_digest[:8]}, {s_info.get('problem_digest', '')[:8]}), "
                            f"policy=({orig_sr.search_policy}, {rep_sr.search_policy}), "
                            f"policy_impl=({orig_sr.search_policy_implementation_digest[:8]}, {rep_sr.search_policy_implementation_digest[:8]}), "
                            f"env=({orig_sr.environment_identity_digest[:8]}, {rep_sr.environment_identity_digest[:8]}), "
                            f"budget=({orig_sr.search_budget_digest[:8]}, {rep_sr.search_budget_digest[:8]}, {FROZEN_SEARCH_BUDGET_DIGEST[:8]})"
                        )
                    if "search_budget_parity" in ledger and ledger.get("search_budget_parity") != derived_sub_parity:
                        errors.append(
                            f"Search budget parity ledger mismatch for {prob_id}: "
                            f"ledger={ledger.get('search_budget_parity')} != derived={derived_sub_parity}"
                        )

                    # F. 4-Way Applied Count Numerical Equality Parity
                    paired_count = s_info.get("candidate_applications_count")
                    orig_app_cnt = sum(1 for ref in orig_sr.candidate_application_receipt_refs if ref.startswith("app-rec-applied-"))
                    rep_body_app_cnt = sum(1 for c in valid_replay_car_bodies if c.application_status == "APPLIED")
                    rep_app_cnt = sum(1 for ref in rep_sr.candidate_application_receipt_refs if ref.startswith("app-rec-applied-"))

                    derived_app_cnt_parity = bool(
                        car_bodies_valid
                        and paired_count == orig_app_cnt == rep_body_app_cnt == rep_app_cnt
                    )
                    if not derived_app_cnt_parity:
                        errors.append(
                            f"Derived applied count parity failed for {prob_id}: "
                            f"paired={paired_count}, orig_sr={orig_app_cnt}, rep_bodies={rep_body_app_cnt}, rep_sr={rep_app_cnt}"
                        )
                    if ledger.get("applied_count_parity") != derived_app_cnt_parity:
                        errors.append(
                            f"Applied count parity ledger mismatch for {prob_id}: "
                            f"ledger={ledger.get('applied_count_parity')} != derived={derived_app_cnt_parity}"
                        )
                    if "original_applied_count" in ledger and ledger["original_applied_count"] != paired_count:
                        errors.append(
                            f"Ledger original_applied_count {ledger['original_applied_count']} != paired manifest count {paired_count} for {prob_id}"
                        )
                    if "replay_applied_count" in ledger and ledger["replay_applied_count"] != rep_body_app_cnt:
                        errors.append(
                            f"Ledger replay_applied_count {ledger['replay_applied_count']} != derived replay body count {rep_body_app_cnt} for {prob_id}"
                        )
                else:
                    # Backward compatibility for historical 01C-R1
                    orig_app_ids = list(orig_sr.candidate_application_receipt_refs) if orig_sr else []
                    derived_seq_parity = bool(
                        orig_app_ids == ledger.get("ordered_original_application_ids", []) == ledger.get("ordered_replay_application_ids", [])
                    )
                    exp_nodes = s_info.get("abstracted_nodes_expanded")
                    derived_met_parity = bool(orig_sr and orig_sr.nodes_expanded == exp_nodes)
                    derived_stat_parity = bool(orig_sr and orig_sr.candidate_application_status == exp_cand_status)
                    derived_term_parity = bool(orig_sr and orig_sr.terminal_status == "SUCCESS")
                    derived_sub_parity = True
                    paired_count = s_info.get("candidate_applications_count")
                    orig_app_cnt = sum(1 for ref in orig_sr.candidate_application_receipt_refs if ref.startswith("app-rec-applied-")) if orig_sr else 0
                    derived_app_cnt_parity = bool(
                        ledger.get("original_applied_count") == paired_count == orig_app_cnt == ledger.get("replay_applied_count")
                    )

                seq_parities.append(derived_seq_parity)
                met_parities.append(derived_met_parity)
                stat_parities.append(derived_stat_parity)
                term_parities.append(derived_term_parity)
                sub_parities.append(derived_sub_parity)
                app_cnt_parities.append(derived_app_cnt_parity)

                if (
                    derived_seq_parity
                    and derived_met_parity
                    and derived_stat_parity
                    and derived_term_parity
                    and derived_sub_parity
                    and derived_app_cnt_parity
                ):
                    replay_runs_verified += 1

            all_seq_parity = (len(seq_parities) == 48 and all(seq_parities))
            all_metric_parity = (len(met_parities) == 48 and all(met_parities))
            all_candidate_status_parity = (len(stat_parities) == 48 and all(stat_parities))
            all_terminal_status_parity = (len(term_parities) == 48 and all(term_parities))
            all_search_budget_parity = (len(sub_parities) == 48 and all(sub_parities))
            all_app_cnt_parity = (len(app_cnt_parities) == 48 and all(app_cnt_parities))

            if not all_seq_parity:
                errors.append("Not all replay sequence parities verified across 48 runs")
            if not all_metric_parity:
                errors.append("Not all replay metric parities verified across 48 runs")
            if not all_candidate_status_parity:
                errors.append("Not all candidate status parities verified across 48 runs")
            if not all_terminal_status_parity:
                errors.append("Not all terminal status parities verified across 48 runs")
            if not all_search_budget_parity:
                errors.append("Not all search budget parities verified across 48 runs")
            if not all_app_cnt_parity:
                errors.append("Not all applied count parities verified across 48 runs")

            if replay_manifest.all_application_id_sequence_parity_verified != all_seq_parity:
                errors.append("Manifest all_application_id_sequence_parity_verified disagrees with derived parity")
            if replay_manifest.all_search_metric_parity_verified != all_metric_parity:
                errors.append("Manifest all_search_metric_parity_verified disagrees with derived parity")
            if replay_manifest.all_candidate_status_parity_verified != all_candidate_status_parity:
                errors.append("Manifest all_candidate_status_parity_verified disagrees with derived parity")
            if replay_manifest.all_terminal_status_parity_verified != all_terminal_status_parity:
                errors.append("Manifest all_terminal_status_parity_verified disagrees with derived parity")
            if replay_manifest.all_applied_count_parity_verified != all_app_cnt_parity:
                errors.append("Manifest all_applied_count_parity_verified disagrees with derived parity")
            if replay_manifest.all_search_budget_parity_verified is not None and replay_manifest.all_search_budget_parity_verified != all_search_budget_parity:
                errors.append("Manifest all_search_budget_parity_verified disagrees with derived parity")
            if replay_manifest.search_budget_digest != FROZEN_SEARCH_BUDGET_DIGEST:
                errors.append("Manifest search_budget_digest does not match frozen digest")

            if is_r1_r1:
                if closure.all_applied_count_parity_verified != all_app_cnt_parity:
                    errors.append("Closure all_applied_count_parity_verified disagrees with derived parity")
                if closure.all_search_budget_parity_verified != all_search_budget_parity:
                    errors.append("Closure all_search_budget_parity_verified disagrees with derived parity")

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
        if is_r1_r1:
            onto_path = self.repo_root / "experiments" / "formal-discovery-01c-r1-r1" / "onto-export-scoped.json"
        else:
            onto_path = self.repo_root / "experiments" / "formal-discovery-01c-r1" / "onto-export-scoped.json"

        onto_verified = False
        if not onto_path.is_file():
            errors.append(f"ONTO package missing at {onto_path}")
        else:
            try:
                onto_raw = json.loads(onto_path.read_text(encoding="utf-8"))
                onto_pkg = OntoEvaluationPackage.from_dict(onto_raw)
                onto_pkg.validate()
                onto_verified = True
            except Exception as e:
                errors.append(f"ONTO package validation error: {e}")

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
            search_replay_receipts_verified_count=replay_search_rcpts_verified,
            application_replay_receipts_verified_count=replay_app_rcpts_verified,
            all_applied_count_parity_verified=all_app_cnt_parity,
            all_search_budget_parity_verified=all_search_budget_parity,
            search_budget_digest_verified=search_budget_digest_verified,
            original_attempt_body_custody=closure.original_attempt_body_custody or "PARTIAL_AND_EXPLICIT",
            deterministic_replay_attempt_body_custody=closure.deterministic_replay_attempt_body_custody or "COMPLETE",
            derived_sequence_parity_count=sum(1 for p in seq_parities if p),
            derived_search_metric_parity_count=sum(1 for p in met_parities if p),
            derived_candidate_status_parity_count=sum(1 for p in stat_parities if p),
            derived_terminal_status_parity_count=sum(1 for p in term_parities if p),
            derived_search_substrate_parity_count=sum(1 for p in sub_parities if p),
            derived_applied_count_parity_count=sum(1 for p in app_cnt_parities if p),
        )
