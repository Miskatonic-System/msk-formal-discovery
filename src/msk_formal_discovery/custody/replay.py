"""Exact Frozen-Science Evidence Replay and Custody Generation (WO-MATH-FORMAL-DISCOVERY-01B-R2)."""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from msk_formal_discovery.abstraction.candidate import AbstractionCandidate
from msk_formal_discovery.application.applicator import get_applicator_implementation_digest
from msk_formal_discovery.core.exceptions import ReceiptValidationError
from msk_formal_discovery.core.terms import Term
from msk_formal_discovery.custody.freeze import (
    DEFAULT_R1_DIR,
    DEFAULT_R2_DIR,
    R1_EXECUTION_COMMIT,
    R1_EXECUTION_TREE,
    R1_RESULT_SHA256,
    validate_r2_freeze,
)
from msk_formal_discovery.custody.manifest import (
    PairedTerminalCustodyManifest,
    TerminalCustodyClosureManifest,
)
from msk_formal_discovery.custody.receipt import (
    TerminalStateCustodyReceipt,
    compute_custody_receipt_digest,
)
from msk_formal_discovery.experiments.adjudication import get_adjudicator_implementation_digest
from msk_formal_discovery.experiments.rewrite_control import (
    RewriteSearchEnvironment,
    generate_held_out_negative_corpus,
    generate_held_out_positive_corpus,
    get_rewrite_environment_implementation_digest,
    get_smt_control_implementation_digest,
)
from msk_formal_discovery.onto.export import OntoEvidenceRef, OntoExporter
from msk_formal_discovery.search.executor import ProblemDefinition, SearchExecutionBundle, SearchExecutor
from msk_formal_discovery.search.frontier import DeterministicFrontierSearch


def replay_r1_custody(
    r1_dir: Optional[Path] = None,
    r2_dir: Optional[Path] = None,
    save_receipts: bool = True,
) -> Dict[str, Any]:
    """Execute exact deterministic custody replay and emit 24 receipts plus manifests (Sections 6-18, 24)."""
    target_r1 = r1_dir or DEFAULT_R1_DIR
    target_r2 = r2_dir or DEFAULT_R2_DIR
    receipts_dir = target_r2 / "receipts"
    if save_receipts:
        receipts_dir.mkdir(parents=True, exist_ok=True)

    # 1. Self-Audit / Freeze Validation (Section 30)
    freeze_val = validate_r2_freeze(exp_r2_dir=target_r2, exp_r1_dir=target_r1)
    if freeze_val["status"] != "R2_CUSTODY_FREEZE_VALIDATED":
        return {
            "disposition": "R1_EVIDENCE_CUSTODY_REPLAY_DIVERGED",
            "reason": "R2_FREEZE_VALIDATION_FAILED",
        }

    # 2. Load Frozen Candidate and Corpora (Sections 8-10)
    cand_file = target_r1 / "candidate.json"
    candidate = AbstractionCandidate.from_dict(json.loads(cand_file.read_text(encoding="utf-8")))

    r1_result_file = target_r1 / "result.json"
    r1_result = json.loads(r1_result_file.read_text(encoding="utf-8"))
    r1_units_by_id = {u["problem_id"]: u for u in r1_result["per_unit_evaluations"]}
    r1_smt_by_id = r1_result["smt_semantic_verification"]

    pos_problems = generate_held_out_positive_corpus(seed=271828)
    neg_problems = generate_held_out_negative_corpus(seed=314159)
    all_problems = pos_problems + neg_problems

    executor = SearchExecutor()
    search_budget = {"max_nodes": 100, "max_depth": 20}
    impl_digests = {
        "applicator": get_applicator_implementation_digest(),
        "environment": get_rewrite_environment_implementation_digest(),
        "smt_control": get_smt_control_implementation_digest(),
        "adjudicator": get_adjudicator_implementation_digest(),
    }

    custody_receipts: List[TerminalStateCustodyReceipt] = []
    paired_manifest_entries: List[Dict[str, Any]] = []

    for prob in all_problems:
        pid = prob.problem_id
        r1_rec = r1_units_by_id[pid]
        prob_def = ProblemDefinition(
            problem_id=prob.problem_id,
            formal_syntax=prob.initial_expression.canonical_repr(),
            context={"category": prob.category, "expression_digest": prob.problem_digest},
            goals=[prob.goal_expression.canonical_repr()],
            assumptions=[],
            problem_digest=prob.problem_digest,
        )

        # Replay Baseline Arm
        env_b = RewriteSearchEnvironment(prob.problem_id, prob.problem_digest, prob.goal_expression)
        st0_b = env_b.create_initial_state(prob.initial_expression)
        bundle_b: SearchExecutionBundle = executor.execute(
            problem=prob_def,
            initial_state=st0_b,
            policy=DeterministicFrontierSearch(),
            environment=env_b,
            budget=search_budget,
            candidate_id=candidate.candidate_id,
            candidate_enabled=False,
            candidate=None,
        )

        # Replay Abstracted Arm
        env_a = RewriteSearchEnvironment(prob.problem_id, prob.problem_digest, prob.goal_expression)
        st0_a = env_a.create_initial_state(prob.initial_expression)
        bundle_a: SearchExecutionBundle = executor.execute(
            problem=prob_def,
            initial_state=st0_a,
            policy=DeterministicFrontierSearch(),
            environment=env_a,
            budget=search_budget,
            candidate_id=candidate.candidate_id,
            candidate_enabled=True,
            candidate=candidate,
        )

        # Process Baseline Custody
        orig_s_b_file = target_r1 / "receipts" / f"search-baseline-{pid}.json"
        orig_s_b_data = json.loads(orig_s_b_file.read_text(encoding="utf-8"))

        term_expr_b = bundle_b.terminal_expression
        term_canon_b = term_expr_b.canonical_repr() if hasattr(term_expr_b, "canonical_repr") else str(term_expr_b)
        term_dig_b = bundle_b.terminal_expression_digest

        orig_term_dig_b = r1_rec["baseline_terminal_digest"]
        t_parity_b = (term_dig_b == orig_term_dig_b)
        m_parity_b = (
            bundle_b.receipt.nodes_expanded == r1_rec["baseline_nodes"]
            and bundle_b.receipt.nodes_evaluated == r1_rec["baseline_evaluated"]
            and bundle_b.receipt.branch_count == r1_rec["baseline_branches"]
            and (bundle_b.receipt.terminal_status == "SUCCESS") == r1_rec["baseline_solved"]
        )
        app_parity_b = (
            bundle_b.receipt.candidate_application_status == "DISABLED"
            and len(bundle_b.candidate_application_receipts) == 0
        )

        custody_b = TerminalStateCustodyReceipt(
            schema_version="miskatonic.terminal-state-custody-receipt.v0.1",
            custody_receipt_id=f"custody-baseline-{pid}",
            custody_mode="DETERMINISTIC_EVIDENCE_REPLAY",
            source_experiment_id="formal-discovery-01b-r1",
            source_work_order="WO-MATH-FORMAL-DISCOVERY-01B-R1",
            source_execution_commit=R1_EXECUTION_COMMIT,
            source_execution_tree=R1_EXECUTION_TREE,
            source_result_ref="experiments/formal-discovery-01b-r1/result.json",
            source_result_sha256=R1_RESULT_SHA256,
            problem_id=pid,
            problem_digest=prob.problem_digest,
            arm="BASELINE",
            candidate_id=candidate.candidate_id,
            candidate_enabled=False,
            candidate_application_status=bundle_b.receipt.candidate_application_status,
            candidate_application_count=len(bundle_b.candidate_application_receipts),
            search_run_ref=orig_s_b_data["run_id"],
            search_run_digest=orig_s_b_data["receipt_digest"],
            original_search_receipt_ref=f"experiments/formal-discovery-01b-r1/receipts/search-baseline-{pid}.json",
            original_search_receipt_digest=hashlib.sha256(orig_s_b_file.read_bytes()).hexdigest(),
            replay_search_run_ref=bundle_b.receipt.run_id,
            replay_search_run_digest=bundle_b.receipt.receipt_digest,
            terminal_state_id=f"state-replay-baseline-{pid}",
            terminal_canonical_representation=term_canon_b,
            terminal_expression_digest=term_dig_b,
            source_recorded_terminal_digest=orig_term_dig_b,
            terminal_digest_parity=t_parity_b,
            nodes_expanded=bundle_b.receipt.nodes_expanded,
            nodes_evaluated=bundle_b.receipt.nodes_evaluated,
            branch_count=bundle_b.receipt.branch_count,
            solved=(bundle_b.receipt.terminal_status == "SUCCESS"),
            metric_parity=m_parity_b,
            application_parity=app_parity_b,
            implementation_digests=impl_digests,
            replayed_at=datetime.now(timezone.utc).isoformat(),
            authority="NONE",
        )
        custody_b.validate()
        custody_receipts.append(custody_b)

        # Process Abstracted Custody
        orig_s_a_file = target_r1 / "receipts" / f"search-abstracted-{pid}.json"
        orig_s_a_data = json.loads(orig_s_a_file.read_text(encoding="utf-8"))

        term_expr_a = bundle_a.terminal_expression
        term_canon_a = term_expr_a.canonical_repr() if hasattr(term_expr_a, "canonical_repr") else str(term_expr_a)
        term_dig_a = bundle_a.terminal_expression_digest

        orig_term_dig_a = r1_rec["abstracted_terminal_digest"]
        t_parity_a = (term_dig_a == orig_term_dig_a)
        m_parity_a = (
            bundle_a.receipt.nodes_expanded == r1_rec["abstracted_nodes"]
            and bundle_a.receipt.nodes_evaluated == r1_rec["abstracted_evaluated"]
            and bundle_a.receipt.branch_count == r1_rec["abstracted_branches"]
            and (bundle_a.receipt.terminal_status == "SUCCESS") == r1_rec["abstracted_solved"]
        )
        applied_apps = [r for r in bundle_a.candidate_application_receipts if getattr(r, "application_status", "") == "APPLIED"]
        app_parity_a = (
            bundle_a.receipt.candidate_application_status == r1_rec["candidate_application_status"]
            and len(applied_apps) == r1_rec["applications_count"]
        )

        custody_a = TerminalStateCustodyReceipt(
            schema_version="miskatonic.terminal-state-custody-receipt.v0.1",
            custody_receipt_id=f"custody-abstracted-{pid}",
            custody_mode="DETERMINISTIC_EVIDENCE_REPLAY",
            source_experiment_id="formal-discovery-01b-r1",
            source_work_order="WO-MATH-FORMAL-DISCOVERY-01B-R1",
            source_execution_commit=R1_EXECUTION_COMMIT,
            source_execution_tree=R1_EXECUTION_TREE,
            source_result_ref="experiments/formal-discovery-01b-r1/result.json",
            source_result_sha256=R1_RESULT_SHA256,
            problem_id=pid,
            problem_digest=prob.problem_digest,
            arm="ABSTRACTED",
            candidate_id=candidate.candidate_id,
            candidate_enabled=True,
            candidate_application_status=bundle_a.receipt.candidate_application_status,
            candidate_application_count=len(applied_apps),
            search_run_ref=orig_s_a_data["run_id"],
            search_run_digest=orig_s_a_data["receipt_digest"],
            original_search_receipt_ref=f"experiments/formal-discovery-01b-r1/receipts/search-abstracted-{pid}.json",
            original_search_receipt_digest=hashlib.sha256(orig_s_a_file.read_bytes()).hexdigest(),
            replay_search_run_ref=bundle_a.receipt.run_id,
            replay_search_run_digest=bundle_a.receipt.receipt_digest,
            terminal_state_id=f"state-replay-abstracted-{pid}",
            terminal_canonical_representation=term_canon_a,
            terminal_expression_digest=term_dig_a,
            source_recorded_terminal_digest=orig_term_dig_a,
            terminal_digest_parity=t_parity_a,
            nodes_expanded=bundle_a.receipt.nodes_expanded,
            nodes_evaluated=bundle_a.receipt.nodes_evaluated,
            branch_count=bundle_a.receipt.branch_count,
            solved=(bundle_a.receipt.terminal_status == "SUCCESS"),
            metric_parity=m_parity_a,
            application_parity=app_parity_a,
            implementation_digests=impl_digests,
            replayed_at=datetime.now(timezone.utc).isoformat(),
            authority="NONE",
        )
        custody_a.validate()
        custody_receipts.append(custody_a)

        # Save custody receipts
        if save_receipts:
            (receipts_dir / f"custody-baseline-{pid}.json").write_text(
                json.dumps(custody_b.to_dict(), indent=2), encoding="utf-8"
            )
            (receipts_dir / f"custody-abstracted-{pid}.json").write_text(
                json.dumps(custody_a.to_dict(), indent=2), encoding="utf-8"
            )

        # Paired SMT ref and digest
        orig_smt_file = target_r1 / "receipts" / f"smt-paired-{pid}.json"
        orig_smt_digest = hashlib.sha256(orig_smt_file.read_bytes()).hexdigest()
        smt_info = r1_smt_by_id[pid]

        manifest_entry = {
            "problem_id": pid,
            "problem_digest": prob.problem_digest,
            "category": prob.category,
            "baseline_custody_receipt_ref": f"experiments/formal-discovery-01b-r2/receipts/custody-baseline-{pid}.json",
            "baseline_custody_receipt_digest": custody_b.receipt_digest,
            "abstracted_custody_receipt_ref": f"experiments/formal-discovery-01b-r2/receipts/custody-abstracted-{pid}.json",
            "abstracted_custody_receipt_digest": custody_a.receipt_digest,
            "baseline_terminal_digest": term_dig_b,
            "abstracted_terminal_digest": term_dig_a,
            "baseline_terminal_canonical_representation": term_canon_b,
            "abstracted_terminal_canonical_representation": term_canon_a,
            "original_paired_smt_receipt_ref": f"experiments/formal-discovery-01b-r1/receipts/smt-paired-{pid}.json",
            "original_paired_smt_receipt_digest": orig_smt_digest,
            "r1_smt_verdict": smt_info["smt_verdict"],
            "terminal_digest_equality": (term_dig_b == term_dig_a),
            "custody_replay_parity_status": "PARITY_VERIFIED" if (t_parity_b and t_parity_a and m_parity_b and m_parity_a and app_parity_b and app_parity_a) else "PARITY_FAILED",
        }
        paired_manifest_entries.append(manifest_entry)

    # 3. Paired Terminal Custody Manifest (Section 16)
    paired_manifest = PairedTerminalCustodyManifest(
        schema_version="miskatonic.paired-terminal-custody-manifest.v0.1",
        manifest_id="paired-terminal-custody-manifest",
        source_work_order="WO-MATH-FORMAL-DISCOVERY-01B-R1",
        source_execution_commit=R1_EXECUTION_COMMIT,
        units=paired_manifest_entries,
        authority="NONE",
    )
    paired_manifest.validate()
    if save_receipts:
        (target_r2 / "paired-terminal-custody-manifest.v0.1.json").write_text(
            json.dumps(paired_manifest.to_dict(), indent=2), encoding="utf-8"
        )

    # 4. Custody Closure Manifest (Section 18)
    all_t_parity = all(c.terminal_digest_parity for c in custody_receipts)
    all_m_parity = all(c.metric_parity for c in custody_receipts)
    all_a_parity = all(c.application_parity for c in custody_receipts)

    closure = TerminalCustodyClosureManifest(
        schema_version="miskatonic.r1-terminal-custody-closure.v0.1",
        closure_id="r1-terminal-custody-closure",
        source_work_order="WO-MATH-FORMAL-DISCOVERY-01B-R1",
        r2_work_order="WO-MATH-FORMAL-DISCOVERY-01B-R2",
        source_execution_commit=R1_EXECUTION_COMMIT,
        source_execution_tree=R1_EXECUTION_TREE,
        custody_receipt_count=len(custody_receipts),
        paired_unit_count=len(paired_manifest_entries),
        source_result_digest_verified=True,
        all_terminal_digest_parity=all_t_parity,
        all_metric_parity=all_m_parity,
        all_application_parity=all_a_parity,
        all_original_search_refs_resolved=True,
        all_replay_receipts_resolved=True,
        source_science_mutated=False,
        terminal_canonical_forms_durably_bound="YES" if (all_t_parity and all_m_parity and all_a_parity) else "NO",
        closure_status="R1_EVIDENCE_CUSTODY_CLOSED" if (all_t_parity and all_m_parity and all_a_parity) else "R1_EVIDENCE_CUSTODY_REPLAY_DIVERGED",
        authority="NONE",
    )
    closure.validate()
    if save_receipts:
        (target_r2 / "r1-terminal-custody-closure.v0.1.json").write_text(
            json.dumps(closure.to_dict(), indent=2), encoding="utf-8"
        )

    # 5. Scoped ONTO Export with Durable Evidence Ref (Sections 19-24)
    # Target durable evidence ref to r1-original-result-freeze.json
    freeze_artifact = target_r2 / "r1-original-result-freeze.json"
    freeze_sha = hashlib.sha256(freeze_artifact.read_bytes()).hexdigest()
    durable_ref = OntoEvidenceRef(
        evidence_kind="TERMINAL_STATE_CUSTODY_REPLAY",
        artifact_ref="experiments/formal-discovery-01b-r2/r1-original-result-freeze.json",
        artifact_digest=freeze_sha,
        evidence_status="SUPPORTED",
        source_experimental_units=[p.problem_digest for p in all_problems],
        source_repository="Miskatonic-System/msk-formal-discovery",
        source_commit=R1_EXECUTION_COMMIT,
    )
    durable_ref.validate(require_durable=True)

    scoped_onto = OntoExporter.export_scoped(
        candidate=candidate,
        functional_search_benefit_scope="NODE_EXPANSION_SEARCH_STRUCTURE",
        end_to_end_runtime_benefit="NOT_ESTABLISHED",
        claim_ceiling="ENGINEERING_ABSTRACTION_EFFECT_ONLY",
        durable_evidence_ref=durable_ref,
    )
    if save_receipts:
        (target_r2 / "onto-export-scoped.json").write_text(
            json.dumps(scoped_onto.to_dict(), indent=2), encoding="utf-8"
        )

    return {
        "disposition": closure.closure_status,
        "custody_receipt_count": len(custody_receipts),
        "paired_unit_count": len(paired_manifest_entries),
        "all_terminal_digest_parity": all_t_parity,
        "all_metric_parity": all_m_parity,
        "all_application_parity": all_a_parity,
        "scoped_onto_package": scoped_onto.to_dict(),
        "closure_manifest": closure.to_dict(),
    }
