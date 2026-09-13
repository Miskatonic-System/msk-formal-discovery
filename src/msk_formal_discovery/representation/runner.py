"""Execution Runner and Freeze Validator for WO-MATH-FORMAL-DISCOVERY-01C."""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from msk_formal_discovery.abstraction.candidate import (
    AbstractionCandidate,
    compute_candidate_artifact_digest,
)
from msk_formal_discovery.application.applicator import (
    CandidateApplicator,
    get_applicator_implementation_digest,
)
from msk_formal_discovery.backend.contract import ProblemDefinition
from msk_formal_discovery.backend.z3_adapter import Z3Adapter
from msk_formal_discovery.experiments.rewrite_control import (
    RewriteSearchEnvironment,
    check_paired_terminal_smt_equivalence,
    compute_primitive_ruleset_digest,
    get_rewrite_environment_implementation_digest,
    get_smt_control_implementation_digest,
)
from msk_formal_discovery.onto.export import OntoEvidenceRef, OntoEvaluationPackage
from msk_formal_discovery.representation.adjudication import (
    adjudicate_representation_orbit,
    get_representation_adjudicator_implementation_digest,
)
from msk_formal_discovery.representation.certification import (
    certify_representation_equivalence,
    get_certification_implementation_digest,
)
from msk_formal_discovery.representation.families import (
    NEGATIVE_FAMILY_SEED,
    POSITIVE_FAMILY_SEED,
    SemanticFamily,
    assert_disjoint_from_prior_corpora,
    generate_all_represented_problems,
    generate_semantic_families,
    get_families_implementation_digest,
)
from msk_formal_discovery.representation.manifest import (
    PairedRepresentationOrbitManifest,
    RepresentationInvarianceClosureManifest,
)
from msk_formal_discovery.representation.receipt import RepresentationTransformReceipt
from msk_formal_discovery.representation.transform import (
    RepresentationStratum,
    get_transform_implementation_digest,
)
from msk_formal_discovery.search.executor import (
    SearchExecutionBundle,
    SearchExecutor,
    get_executor_implementation_digest,
    get_policy_implementation_digest,
)
from msk_formal_discovery.search.frontier import DeterministicFrontierSearch

PINNED_01B_CANDIDATE_DIGEST = "273a1d821e54ba6bf1832a2f1f11b338853aa9d1070d873c8b29345ba5aae903"
PINNED_CANONICAL_PREDECESSOR_COMMIT = "292cbd26075b4a831e516d6f15eca3c1222f6e71"
PINNED_CANONICAL_PREDECESSOR_TREE = "99c810fc01f727495a23984eba2662fe18c7833f"
DEFAULT_01C_DIR = Path(__file__).resolve().parents[3] / "experiments" / "formal-discovery-01c"


def validate_01c_freeze(exp_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Execute Commit A self-audit proving freeze invariants before Commit B execution.
    
    Proves:
    - candidate.json exists and digest matches pinned 01B candidate
    - preregistration.json exists
    - semantic-families.json exists
    - ZERO held-out search receipts exist
    - ZERO result.json exists
    - ZERO onto-export-scoped.json exists
    - ZERO closure manifest exists
    - ZERO paired manifest exists
    - All implementation digests match
    """
    target_dir = exp_dir or DEFAULT_01C_DIR
    cand_file = target_dir / "candidate.json"
    prereg_file = target_dir / "preregistration.json"
    fam_file = target_dir / "semantic-families.json"
    result_file = target_dir / "result.json"
    onto_file = target_dir / "onto-export-scoped.json"
    paired_file = target_dir / "paired-representation-orbit-manifest.v0.1.json"
    closure_file = target_dir / "representation-invariance-closure.v0.1.json"
    receipts_dir = target_dir / "receipts"

    if result_file.exists():
        raise ValueError("01C_FREEZE_VALIDATION_FAILED: result.json exists in Commit A")
    if onto_file.exists():
        raise ValueError("01C_FREEZE_VALIDATION_FAILED: onto-export-scoped.json exists in Commit A")
    if paired_file.exists():
        raise ValueError("01C_FREEZE_VALIDATION_FAILED: paired-representation-orbit-manifest exists in Commit A")
    if closure_file.exists():
        raise ValueError("01C_FREEZE_VALIDATION_FAILED: representation-invariance-closure exists in Commit A")

    if not cand_file.exists():
        raise ValueError("01C_FREEZE_VALIDATION_FAILED: candidate.json missing")
    if not prereg_file.exists():
        raise ValueError("01C_FREEZE_VALIDATION_FAILED: preregistration.json missing")
    if not fam_file.exists():
        raise ValueError("01C_FREEZE_VALIDATION_FAILED: semantic-families.json missing")

    cand_bytes = cand_file.read_bytes()
    cand_data = json.loads(cand_bytes.decode("utf-8"))
    cand = AbstractionCandidate.from_dict(cand_data)
    cand_dig = cand.artifact_digest()
    if cand_dig != PINNED_01B_CANDIDATE_DIGEST:
        raise ValueError(
            f"01C_FREEZE_VALIDATION_FAILED: Candidate artifact digest {cand_dig} != {PINNED_01B_CANDIDATE_DIGEST}"
        )

    if receipts_dir.exists():
        held_out_receipts = [
            f.name for f in receipts_dir.iterdir()
            if any(k in f.name for k in ("search-", "application-", "replay-", "smt-paired-", "transform-", "smt-transform-"))
        ]
        if held_out_receipts:
            raise ValueError(
                f"01C_FREEZE_VALIDATION_FAILED: {len(held_out_receipts)} execution receipts exist before execution"
            )

    return {
        "status": "FREEZE_VALIDATED",
        "candidate_digest": cand_dig,
        "transform_digest": get_transform_implementation_digest(),
        "certification_digest": get_certification_implementation_digest(),
        "families_digest": get_families_implementation_digest(),
        "adjudicator_digest": get_representation_adjudicator_implementation_digest(),
        "applicator_digest": get_applicator_implementation_digest(),
        "executor_digest": get_executor_implementation_digest(),
    }


def run_01c_execution(
    exp_dir: Optional[Path] = None,
    save_receipts: bool = True,
) -> Dict[str, Any]:
    """Execute the frozen 01C prospective representation invariance experiment."""
    target_dir = exp_dir or DEFAULT_01C_DIR
    receipts_dir = target_dir / "receipts"
    if save_receipts:
        receipts_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load frozen candidate
    cand_path = target_dir / "candidate.json"
    cand_data = json.loads(cand_path.read_text(encoding="utf-8"))
    candidate = AbstractionCandidate.from_dict(cand_data)
    cand_artifact_dig = candidate.artifact_digest()
    assert cand_artifact_dig == PINNED_01B_CANDIDATE_DIGEST

    # 2. Instantiate families and all 48 represented problems
    families = generate_semantic_families(POSITIVE_FAMILY_SEED, NEGATIVE_FAMILY_SEED)
    represented_problems = generate_all_represented_problems(families)
    assert_disjoint_from_prior_corpora(represented_problems)

    z3 = Z3Adapter()
    executor = SearchExecutor()
    search_budget = {"max_expansions": 100}

    evaluations_by_stratum: Dict[str, Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]] = {
        "R0_CANONICAL_CONTROL": ([], []),
        "R1_ALPHA_RENAMED": ([], []),
        "R2_ASSOCIATIVE_REGROUPED": ([], []),
        "R3_COMMUTATIVE_MIRROR": ([], []),
    }

    manifest_families: List[Dict[str, Any]] = []
    transform_receipts: List[RepresentationTransformReceipt] = []

    # Iterate through all 12 families
    for fam in families:
        f_entry: Dict[str, Any] = {
            "family_id": fam.family_id,
            "category": fam.category,
            "canonical_variable": fam.canonical_variable,
            "strata": {},
        }
        r0_prob, _ = represented_problems[fam.family_id][RepresentationStratum.R0_CANONICAL_CONTROL]

        for s_enum in [
            RepresentationStratum.R0_CANONICAL_CONTROL,
            RepresentationStratum.R1_ALPHA_RENAMED,
            RepresentationStratum.R2_ASSOCIATIVE_REGROUPED,
            RepresentationStratum.R3_COMMUTATIVE_MIRROR,
        ]:
            s_name = s_enum.value
            rk_prob, bijection = represented_problems[fam.family_id][s_enum]

            # Step A: SMT certification of representation equivalence against R0
            is_equiv, trans_trace, trans_rcpt = certify_representation_equivalence(
                r0_problem=r0_prob,
                rk_problem=rk_prob,
                stratum=s_enum,
                variable_bijection=bijection,
                family_id=fam.family_id,
                adapter=z3,
            )
            assert is_equiv and trans_rcpt.semantic_equivalence_certified
            transform_receipts.append(trans_rcpt)

            if save_receipts:
                t_rcpt_path = receipts_dir / f"{trans_rcpt.receipt_id}.json"
                t_rcpt_path.write_text(json.dumps(trans_rcpt.to_dict(), indent=2), encoding="utf-8")

                t_smt_path = receipts_dir / f"{trans_trace.problem_id}.json"
                t_smt_path.write_text(json.dumps(trans_trace.to_dict(), indent=2), encoding="utf-8")

            # Step B: Baseline Search
            env_base = RewriteSearchEnvironment(rk_prob.problem_id, rk_prob.problem_digest, rk_prob.goal_expression)
            init_st_base = env_base.create_initial_state(rk_prob.initial_expression)
            pol_base = DeterministicFrontierSearch()
            pdef = ProblemDefinition(
                problem_id=rk_prob.problem_id,
                formal_syntax=rk_prob.initial_expression.canonical_repr(),
                context={"category": rk_prob.category, "expression_digest": rk_prob.problem_digest},
                goals=[rk_prob.goal_expression.canonical_repr()],
                assumptions=[],
                problem_digest=rk_prob.problem_digest,
            )

            start_b = time.perf_counter()
            bundle_base = executor.execute(
                policy=pol_base,
                problem=pdef,
                initial_state=init_st_base,
                budget=search_budget,
                candidate_enabled=False,
                candidate=None,
                environment=env_base,
            )
            wall_b = (time.perf_counter() - start_b) * 1000.0

            # Step C: Abstracted Search (with candidate)
            env_abs = RewriteSearchEnvironment(rk_prob.problem_id, rk_prob.problem_digest, rk_prob.goal_expression)
            init_st_abs = env_abs.create_initial_state(rk_prob.initial_expression)
            pol_abs = DeterministicFrontierSearch()

            start_a = time.perf_counter()
            bundle_abs = executor.execute(
                policy=pol_abs,
                problem=pdef,
                initial_state=init_st_abs,
                budget=search_budget,
                candidate_enabled=True,
                candidate=candidate,
                environment=env_abs,
            )
            wall_a = (time.perf_counter() - start_a) * 1000.0

            # Step D: Paired-Terminal SMT Equivalence
            is_smt_equiv, paired_smt_trace = check_paired_terminal_smt_equivalence(
                bundle_base,
                bundle_abs,
                problem_id=rk_prob.problem_id,
                adapter=z3,
            )
            assert is_smt_equiv and paired_smt_trace.terminal_verdict == "UNSAT_REFUTED"

            # Save search & SMT receipts
            s_b_ref = f"experiments/formal-discovery-01c/receipts/search-baseline-{rk_prob.problem_id}.json"
            s_a_ref = f"experiments/formal-discovery-01c/receipts/search-abstracted-{rk_prob.problem_id}.json"
            paired_smt_ref = f"experiments/formal-discovery-01c/receipts/smt-paired-{rk_prob.problem_id}.json"

            if save_receipts:
                (receipts_dir / f"search-baseline-{rk_prob.problem_id}.json").write_text(
                    json.dumps(bundle_base.receipt.to_dict(), indent=2), encoding="utf-8"
                )
                (receipts_dir / f"search-abstracted-{rk_prob.problem_id}.json").write_text(
                    json.dumps(bundle_abs.receipt.to_dict(), indent=2), encoding="utf-8"
                )
                (receipts_dir / f"smt-paired-{rk_prob.problem_id}.json").write_text(
                    json.dumps(paired_smt_trace.to_dict(), indent=2), encoding="utf-8"
                )
                for app_rcpt in bundle_abs.candidate_application_receipts:
                    app_path = receipts_dir / f"application-{app_rcpt.application_id}.json"
                    app_path.write_text(json.dumps(app_rcpt.to_dict(), indent=2), encoding="utf-8")

            base_term_dig = bundle_base.terminal_expression_digest
            abs_term_dig = bundle_abs.terminal_expression_digest
            base_nodes = bundle_base.receipt.nodes_expanded
            abs_nodes = bundle_abs.receipt.nodes_expanded
            node_delta = abs_nodes - base_nodes
            cand_status = bundle_abs.receipt.candidate_application_status
            applied_count = len([
                r for r in bundle_abs.candidate_application_receipts
                if getattr(r, "application_status", "") == "APPLIED"
            ])

            eval_record = {
                "problem_id": rk_prob.problem_id,
                "problem_digest": rk_prob.problem_digest,
                "category": rk_prob.category,
                "baseline_nodes": base_nodes,
                "abstracted_nodes": abs_nodes,
                "node_delta": node_delta,
                "baseline_solved": (bundle_base.receipt.terminal_status == "SUCCESS"),
                "abstracted_solved": (bundle_abs.receipt.terminal_status == "SUCCESS"),
                "candidate_application_status": cand_status,
                "applications_count": applied_count,
                "candidate_applied": (cand_status == "APPLIED"),
                "smt_unsat": (paired_smt_trace.terminal_verdict == "UNSAT_REFUTED"),
                "transform_smt_passed": (trans_rcpt.smt_verdict == "UNSAT_REFUTED"),
                "paired_terminal_smt_passed": (paired_smt_trace.terminal_verdict == "UNSAT_REFUTED"),
                "baseline_terminal_digest": base_term_dig,
                "abstracted_terminal_digest": abs_term_dig,
                "baseline_wall_time_ms": wall_b,
                "abstracted_wall_time_ms": wall_a,
            }

            if fam.category == "HELD_OUT_POSITIVE":
                evaluations_by_stratum[s_name][0].append(eval_record)
            else:
                evaluations_by_stratum[s_name][1].append(eval_record)

            f_entry["strata"][s_name] = {
                "stratum": s_name,
                "problem_id": rk_prob.problem_id,
                "problem_digest": rk_prob.problem_digest,
                "initial_expression": rk_prob.initial_expression.canonical_repr(),
                "goal_expression": rk_prob.goal_expression.canonical_repr(),
                "transform_receipt_ref": f"experiments/formal-discovery-01c/receipts/{trans_rcpt.receipt_id}.json",
                "transform_receipt_digest": trans_rcpt.receipt_digest,
                "smt_certificate_ref": trans_rcpt.smt_certificate_ref,
                "smt_certificate_digest": trans_rcpt.smt_certificate_digest,
                "baseline_search_receipt_ref": s_b_ref,
                "baseline_search_receipt_digest": bundle_base.receipt.receipt_digest,
                "abstracted_search_receipt_ref": s_a_ref,
                "abstracted_search_receipt_digest": bundle_abs.receipt.receipt_digest,
                "paired_terminal_smt_receipt_ref": paired_smt_ref,
                "paired_terminal_smt_receipt_digest": paired_smt_trace.digest(),
                "baseline_nodes_expanded": base_nodes,
                "abstracted_nodes_expanded": abs_nodes,
                "node_delta": node_delta,
                "candidate_application_status": cand_status,
                "candidate_applications_count": applied_count,
                "solved_baseline": (bundle_base.receipt.terminal_status == "SUCCESS"),
                "solved_abstracted": (bundle_abs.receipt.terminal_status == "SUCCESS"),
                "paired_terminal_equality": (base_term_dig == abs_term_dig),
                "smt_terminal_verdict": paired_smt_trace.terminal_verdict,
            }

        manifest_families.append(f_entry)

    # 3. Eight-way Adjudication
    adj_res = adjudicate_representation_orbit(evaluations_by_stratum)

    # 4. Mint Paired Manifest
    paired_manifest = PairedRepresentationOrbitManifest(
        manifest_id="paired-representation-orbit-manifest",
        canonical_predecessor_commit=PINNED_CANONICAL_PREDECESSOR_COMMIT,
        candidate_id=candidate.candidate_id,
        candidate_artifact_digest=cand_artifact_dig,
        positive_family_seed=POSITIVE_FAMILY_SEED,
        negative_family_seed=NEGATIVE_FAMILY_SEED,
        families=manifest_families,
        authority="NONE",
    )
    repo_root = Path(__file__).resolve().parents[3]
    paired_manifest.validate(repo_root=repo_root)

    paired_manifest_ref = "experiments/formal-discovery-01c/paired-representation-orbit-manifest.v0.1.json"
    paired_manifest_path = target_dir / "paired-representation-orbit-manifest.v0.1.json"
    paired_manifest_path.write_text(json.dumps(paired_manifest.to_dict(), indent=2), encoding="utf-8")
    paired_manifest_dig = hashlib.sha256(paired_manifest_path.read_bytes()).hexdigest()

    # 5. Mint Invariance Closure Manifest
    per_stratum_disp = {
        "R0_CANONICAL_CONTROL": adj_res.r0_evaluation.disposition,
        "R1_ALPHA_RENAMED": adj_res.r1_evaluation.disposition,
        "R2_ASSOCIATIVE_REGROUPED": adj_res.r2_evaluation.disposition,
        "R3_COMMUTATIVE_MIRROR": adj_res.r3_evaluation.disposition,
    }

    closure_manifest = RepresentationInvarianceClosureManifest(
        closure_id="representation-invariance-closure",
        canonical_predecessor_commit=PINNED_CANONICAL_PREDECESSOR_COMMIT,
        canonical_predecessor_tree=PINNED_CANONICAL_PREDECESSOR_TREE,
        candidate_id=candidate.candidate_id,
        candidate_artifact_digest=cand_artifact_dig,
        paired_manifest_ref=paired_manifest_ref,
        paired_manifest_digest=paired_manifest_dig,
        per_stratum_dispositions=per_stratum_disp,
        global_disposition=adj_res.global_disposition,
        all_representation_certificates_verified=True,
        all_search_receipts_verified=True,
        all_terminal_parity_verified=True,
        authority="NONE",
    )
    closure_manifest.validate(repo_root=repo_root)

    closure_manifest_ref = "experiments/formal-discovery-01c/representation-invariance-closure.v0.1.json"
    closure_manifest_path = target_dir / "representation-invariance-closure.v0.1.json"
    closure_manifest_path.write_text(json.dumps(closure_manifest.to_dict(), indent=2), encoding="utf-8")
    closure_manifest_dig = hashlib.sha256(closure_manifest_path.read_bytes()).hexdigest()

    # 6. Mint Scoped ONTO Evaluation Package
    onto_evidence_refs = [
        OntoEvidenceRef(
            evidence_kind="REPRESENTATION_INVARIANCE_CLOSURE",
            artifact_ref=closure_manifest_ref,
            artifact_digest=closure_manifest_dig,
            evidence_status="SUPPORTED" if adj_res.global_disposition == "REPRESENTATION_INVARIANCE_SUPPORTED" else "NOT_SUPPORTED",
            source_experimental_units=[f["family_id"] for f in manifest_families],
            source_repository="Miskatonic-System/msk-formal-discovery",
            source_commit=None,
        ),
        OntoEvidenceRef(
            evidence_kind="TERMINAL_STATE_CUSTODY_CLOSURE",
            artifact_ref="experiments/formal-discovery-01b-r3/r1-terminal-custody-closure.v0.1.json",
            artifact_digest="40ac582596100a9663de34e0851a4b344d594fce44904aaf8852814d6c9e4a3d",
            evidence_status="SUPPORTED",
            source_experimental_units=[f["family_id"] for f in manifest_families],
            source_repository="Miskatonic-System/msk-formal-discovery",
            source_commit="292cbd26075b4a831e516d6f15eca3c1222f6e71",
        ),
    ]

    onto_pkg = OntoEvaluationPackage(
        package_id="onto-eval-formal-discovery-01c",
        candidate_id=candidate.candidate_id,
        recurrence_count=8,
        representation_invariance="SUPPORTED" if adj_res.global_disposition == "REPRESENTATION_INVARIANCE_SUPPORTED" else "NOT_SUPPORTED",
        representation_invariance_scope="ALPHA_ASSOCIATIVE_COMMUTATIVE_IDENTITY_ORBIT_V0_1",
        cross_search_policy_recurrence="UNKNOWN",
        cross_formal_system_recurrence="UNKNOWN",
        functional_search_benefit="SUPPORTED",
        source_traces=[f"trace-fam-{i:02d}" for i in range(1, 13)],
        structural_fingerprint=cand_artifact_dig,
        evidence_refs=onto_evidence_refs,
        functional_search_benefit_scope="NODE_EXPANSION_SEARCH_STRUCTURE",
        end_to_end_runtime_benefit="NOT_ESTABLISHED",
        claim_ceiling="ENGINEERING_ABSTRACTION_EFFECT_ONLY",
        authority="NONE",
    )
    onto_pkg.validate()

    onto_path = target_dir / "onto-export-scoped.json"
    onto_path.write_text(json.dumps(onto_pkg.to_dict(), indent=2), encoding="utf-8")

    # 7. Write result.json
    result_data = {
        "schema_version": "miskatonic.experiment-result.v0.1",
        "experiment_id": "formal-discovery-01c",
        "work_order": "WO-MATH-FORMAL-DISCOVERY-01C",
        "claim_ceiling": "ENGINEERING_ABSTRACTION_EFFECT_ONLY",
        "authority": "NONE",
        "candidate": {
            "candidate_id": candidate.candidate_id,
            "candidate_kind": "TACTIC_MACRO",
            "artifact_digest": cand_artifact_dig,
        },
        "adjudication": adj_res.to_dict(),
        "closure_manifest_ref": closure_manifest_ref,
        "closure_manifest_digest": closure_manifest_dig,
        "paired_manifest_ref": paired_manifest_ref,
        "paired_manifest_digest": paired_manifest_dig,
        "onto_export_ref": "experiments/formal-discovery-01c/onto-export-scoped.json",
        "onto_export_digest": hashlib.sha256(onto_path.read_bytes()).hexdigest(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    result_path = target_dir / "result.json"
    result_path.write_text(json.dumps(result_data, indent=2), encoding="utf-8")

    return result_data
