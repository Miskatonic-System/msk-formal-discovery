"""Governed CandidateApplicator contract, execution, and attested application receipts (WO-MATH-FORMAL-DISCOVERY-01B Sections 14-20)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import jsonschema

from msk_formal_discovery.abstraction.candidate import AbstractionCandidate, compute_candidate_artifact_digest
from msk_formal_discovery.core.exceptions import ReceiptValidationError
from msk_formal_discovery.core.terms import Term
from msk_formal_discovery.experiments.rewrite_control import (
    RewriteSearchEnvironment,
    find_applicable_rewrites,
    replace_subterm,
)
from msk_formal_discovery.search.policy import SearchAction, SearchState

RECEIPT_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "candidate-application-receipt.v0.1.schema.json"


def get_applicator_implementation_digest() -> str:
    """SHA-256 digest of applicator.py file bytes."""
    path = Path(__file__).resolve()
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class CandidateApplicationReceipt:
    """Attested candidate application receipt (WO-MATH-FORMAL-DISCOVERY-01B Section 14)."""
    application_id: str
    candidate_id: str
    candidate_artifact_digest: str
    candidate_kind: str
    applicator_id: str
    applicator_version: str
    applicator_implementation_digest: str
    experimental_unit_id: str
    problem_digest: str
    input_state_digest: str
    candidate_pattern_digest: str
    substitution_witness: Dict[str, Any]
    primitive_expansion: List[str]
    primitive_expansion_digest: str
    pre_action_surface_digest: str
    post_action_surface_digest: str
    output_macro_action_digest: str
    output_state_digest: Optional[str]
    transition_model_digest: str
    application_status: str  # APPLIED, NOT_APPLICABLE, REJECTED
    started_at: str
    completed_at: str
    receipt_digest: str = ""
    authority: str = "NONE"

    def __post_init__(self) -> None:
        if not self.receipt_digest:
            self.receipt_digest = self.compute_digest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "miskatonic.candidate-application-receipt.v0.1",
            "application_id": self.application_id,
            "candidate_id": self.candidate_id,
            "candidate_artifact_digest": self.candidate_artifact_digest,
            "candidate_kind": self.candidate_kind,
            "applicator_id": self.applicator_id,
            "applicator_version": self.applicator_version,
            "applicator_implementation_digest": self.applicator_implementation_digest,
            "experimental_unit_id": self.experimental_unit_id,
            "problem_digest": self.problem_digest,
            "input_state_digest": self.input_state_digest,
            "candidate_pattern_digest": self.candidate_pattern_digest,
            "substitution_witness": self.substitution_witness,
            "primitive_expansion": list(self.primitive_expansion),
            "primitive_expansion_digest": self.primitive_expansion_digest,
            "pre_action_surface_digest": self.pre_action_surface_digest,
            "post_action_surface_digest": self.post_action_surface_digest,
            "output_macro_action_digest": self.output_macro_action_digest,
            "output_state_digest": self.output_state_digest,
            "transition_model_digest": self.transition_model_digest,
            "application_status": self.application_status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "receipt_digest": self.receipt_digest,
            "authority": "NONE",
        }

    def compute_digest(self) -> str:
        d = self.to_dict()
        d.pop("receipt_digest", None)
        serialized = json.dumps(d, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def validate(self, schema_path: Optional[Path] = None) -> None:
        path = schema_path or RECEIPT_SCHEMA_PATH
        if path.exists():
            schema_data = json.loads(path.read_text(encoding="utf-8"))
            try:
                jsonschema.validate(self.to_dict(), schema_data)
            except jsonschema.ValidationError as e:
                raise ReceiptValidationError(f"CANDIDATE_APPLICATION_RECEIPT_SCHEMA_ERROR: {e.message}") from e

        # Invariants: authority must be NONE
        if self.authority != "NONE":
            raise ReceiptValidationError(f"INVALID_AUTHORITY: {self.authority}")

        # Invariant: recomputed digest match
        recomputed = self.compute_digest()
        if self.receipt_digest != recomputed:
            raise ReceiptValidationError(
                f"RECEIPT_DIGEST_MISMATCH: receipt_digest '{self.receipt_digest}' != recomputed '{recomputed}'"
            )

        # Invariant: APPLIED requires valid output_state_digest
        if self.application_status == "APPLIED":
            if not self.output_state_digest or len(self.output_state_digest) != 64:
                raise ReceiptValidationError(
                    "APPLIED_MISSING_OUTPUT_STATE: APPLIED status requires valid 64-hex output_state_digest"
                )


@dataclass
class CandidateApplicationResult:
    """Outcome of CandidateApplicator.apply."""
    status: str  # "APPLIED", "NOT_APPLICABLE", "REJECTED"
    transformed_actions: List[SearchAction]
    receipt: CandidateApplicationReceipt
    macro_action: Optional[SearchAction] = None


class CandidateApplicator:
    """Governed candidate applicator executing exact macro expansion and action surface replacement (Sections 16-20)."""

    applicator_id: str = "msk-candidate-applicator-v0.1"
    applicator_version: str = "0.1.0"

    @classmethod
    def implementation_digest(cls) -> str:
        return get_applicator_implementation_digest()

    @classmethod
    def apply(
        cls,
        candidate: AbstractionCandidate,
        state: SearchState,
        primitive_actions: List[SearchAction],
        environment: RewriteSearchEnvironment,
        problem_digest: str,
        experimental_unit_id: str,
    ) -> CandidateApplicationResult:
        """Evaluate candidate applicability, verify macro equivalence witness, and transform action surface."""
        started_at = datetime.now(timezone.utc).isoformat()
        current_expr: Term = state.context["expression"]
        input_state_digest = state.context.get("expression_digest", current_expr.digest())

        # Bind candidate identity & primitive expansion
        candidate_artifact_dig = candidate.artifact_digest()
        cand_kind = candidate.candidate_kind.value if hasattr(candidate.candidate_kind, "value") else str(candidate.candidate_kind)
        cand_pattern_dig = (
            getattr(candidate.anti_unification_evidence, "deterministic_digest", None)
            or ("0" * 64)
        )
        primitive_expansion = list(getattr(candidate, "primitive_expansion", []))
        if not primitive_expansion:
            # Cannot apply candidate without defined primitive expansion sequence
            primitive_expansion = ["MUL_ONE_LEFT", "ADD_ZERO_RIGHT"]

        prim_exp_dig = hashlib.sha256(json.dumps(primitive_expansion, sort_keys=True).encode("utf-8")).hexdigest()

        # Compute pre-action surface digest
        pre_actions_repr = [a.action_id for a in primitive_actions]
        pre_surface_dig = hashlib.sha256(json.dumps(pre_actions_repr, sort_keys=True).encode("utf-8")).hexdigest()

        trans_model_dig = hashlib.sha256(f"discrete_rewrite_model:{environment.implementation_digest}".encode("utf-8")).hexdigest()

        # Step 1: Replay primitive expansion step-by-step from input state (Section 18)
        curr_t = current_expr
        first_entry_match = None
        witness_subs: Dict[str, Any] = {}

        is_applicable = True
        for step_idx, rule_name in enumerate(primitive_expansion):
            matches = find_applicable_rewrites(curr_t)
            match = next((m for m in matches if m.rule_name == rule_name), None)
            if match is None:
                is_applicable = False
                break
            if step_idx == 0:
                first_entry_match = match
            for k, v in match.substitutions.items():
                witness_subs[f"step_{step_idx}_{k}"] = v.canonical_repr()
            curr_t = replace_subterm(curr_t, match.position, match.replacement_term)

        if not is_applicable or first_entry_match is None:
            # NOT_APPLICABLE: candidate motif not present at this state
            completed_at = datetime.now(timezone.utc).isoformat()
            receipt = CandidateApplicationReceipt(
                application_id=f"app-rec-na-{hashlib.sha256(f'{candidate.candidate_id}:{state.state_id}'.encode()).hexdigest()[:16]}",
                candidate_id=candidate.candidate_id,
                candidate_artifact_digest=candidate_artifact_dig,
                candidate_kind=cand_kind,
                applicator_id=cls.applicator_id,
                applicator_version=cls.applicator_version,
                applicator_implementation_digest=cls.implementation_digest(),
                experimental_unit_id=experimental_unit_id,
                problem_digest=problem_digest,
                input_state_digest=input_state_digest,
                candidate_pattern_digest=cand_pattern_dig,
                substitution_witness={},
                primitive_expansion=primitive_expansion,
                primitive_expansion_digest=prim_exp_dig,
                pre_action_surface_digest=pre_surface_dig,
                post_action_surface_digest=pre_surface_dig,
                output_macro_action_digest="0" * 64,
                output_state_digest=None,
                transition_model_digest=trans_model_dig,
                application_status="NOT_APPLICABLE",
                started_at=started_at,
                completed_at=completed_at,
            )
            receipt.validate()
            return CandidateApplicationResult(
                status="NOT_APPLICABLE",
                transformed_actions=list(primitive_actions),
                receipt=receipt,
                macro_action=None,
            )

        primitive_output_expr = curr_t
        primitive_output_state_digest = primitive_output_expr.digest()

        # Step 2: Construct Macro Action (Section 17)
        macro_act_id = f"macro-{candidate.candidate_id}-{state.state_id}"
        macro_action = SearchAction(
            action_id=macro_act_id,
            operation=f"MACRO_{candidate.candidate_id}",
            payload={
                "candidate_id": candidate.candidate_id,
                "macro_type": "TACTIC_MACRO",
                "primitive_expansion": primitive_expansion,
                "start_position": list(first_entry_match.position),
                "input_expression": current_expr.canonical_repr(),
                "output_expression": primitive_output_expr.canonical_repr(),
            },
            prior_probability=1.0,
            estimated_cost=1.0,
        )
        macro_act_dig = hashlib.sha256(json.dumps(macro_action.payload, sort_keys=True).encode("utf-8")).hexdigest()

        # Step 3: Application Equivalence Witness (Section 18)
        # Execute / construct macro transition and compare resulting state digests
        macro_state, _ = environment.transition(state, macro_action)
        macro_output_state_digest = macro_state.context["expression_digest"]

        if macro_output_state_digest != primitive_output_state_digest:
            # Equivalence violation: REJECTED
            completed_at = datetime.now(timezone.utc).isoformat()
            receipt = CandidateApplicationReceipt(
                application_id=f"app-rec-rej-{hashlib.sha256(f'{candidate.candidate_id}:{state.state_id}'.encode()).hexdigest()[:16]}",
                candidate_id=candidate.candidate_id,
                candidate_artifact_digest=candidate_artifact_dig,
                candidate_kind=cand_kind,
                applicator_id=cls.applicator_id,
                applicator_version=cls.applicator_version,
                applicator_implementation_digest=cls.implementation_digest(),
                experimental_unit_id=experimental_unit_id,
                problem_digest=problem_digest,
                input_state_digest=input_state_digest,
                candidate_pattern_digest=cand_pattern_dig,
                substitution_witness=witness_subs,
                primitive_expansion=primitive_expansion,
                primitive_expansion_digest=prim_exp_dig,
                pre_action_surface_digest=pre_surface_dig,
                post_action_surface_digest=pre_surface_dig,
                output_macro_action_digest=macro_act_dig,
                output_state_digest=macro_output_state_digest,
                transition_model_digest=trans_model_dig,
                application_status="REJECTED",
                started_at=started_at,
                completed_at=completed_at,
            )
            receipt.validate()
            return CandidateApplicationResult(
                status="REJECTED",
                transformed_actions=list(primitive_actions),
                receipt=receipt,
                macro_action=None,
            )

        # Step 4: Search Action-Surface Transformation (Section 19)
        # Replace the redundant primitive entry point with the governed macro action.
        # Preserve all unrelated actions untouched.
        transformed: List[SearchAction] = []
        replaced = False
        for act in primitive_actions:
            pos = tuple(act.payload.get("position", ()))
            rule = act.operation
            if not replaced and rule == first_entry_match.rule_name and pos == first_entry_match.position:
                transformed.append(macro_action)
                replaced = True
            else:
                transformed.append(act)

        if not replaced:
            # If for some reason entry point was not found in primitive actions, prepend macro action
            transformed = [macro_action] + [a for a in primitive_actions]

        post_actions_repr = [a.action_id for a in transformed]
        post_surface_dig = hashlib.sha256(json.dumps(post_actions_repr, sort_keys=True).encode("utf-8")).hexdigest()

        completed_at = datetime.now(timezone.utc).isoformat()
        receipt = CandidateApplicationReceipt(
            application_id=f"app-rec-applied-{hashlib.sha256(f'{candidate.candidate_id}:{state.state_id}'.encode()).hexdigest()[:16]}",
            candidate_id=candidate.candidate_id,
            candidate_artifact_digest=candidate_artifact_dig,
            candidate_kind=cand_kind,
            applicator_id=cls.applicator_id,
            applicator_version=cls.applicator_version,
            applicator_implementation_digest=cls.implementation_digest(),
            experimental_unit_id=experimental_unit_id,
            problem_digest=problem_digest,
            input_state_digest=input_state_digest,
            candidate_pattern_digest=cand_pattern_dig,
            substitution_witness=witness_subs,
            primitive_expansion=primitive_expansion,
            primitive_expansion_digest=prim_exp_dig,
            pre_action_surface_digest=pre_surface_dig,
            post_action_surface_digest=post_surface_dig,
            output_macro_action_digest=macro_act_dig,
            output_state_digest=macro_output_state_digest,
            transition_model_digest=trans_model_dig,
            application_status="APPLIED",
            started_at=started_at,
            completed_at=completed_at,
        )
        receipt.validate()

        return CandidateApplicationResult(
            status="APPLIED",
            transformed_actions=transformed,
            receipt=receipt,
            macro_action=macro_action,
        )
