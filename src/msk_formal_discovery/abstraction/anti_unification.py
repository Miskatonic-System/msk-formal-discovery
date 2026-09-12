"""Structural anti-unification, Least General Generalization (LGG), and admissibility guards (WO-MATH-FORMAL-DISCOVERY-01A-R1)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from msk_formal_discovery.core.exceptions import AntiUnificationError
from msk_formal_discovery.core.terms import App, Const, Term, Var

ANTI_UNIFICATION_ALGORITHM_VERSION = "miskatonic.structural-lgg-v0.1"
WRAPPER_FUNCTORS = frozenset({"seq", "list", "wrap", "wrapper", "transport", "identity", "step_wrapper", "tuple"})


class AdmissibilityStatus(str, Enum):
    """Admissibility classification for generalized patterns (WO-MATH-FORMAL-DISCOVERY-01A-R2)."""
    UNASSESSED = "UNASSESSED"
    ADMISSIBLE = "ADMISSIBLE"
    STRUCTURAL_GENERALIZATION_TRIVIAL = "STRUCTURAL_GENERALIZATION_TRIVIAL"
    TRIVIAL_OR_SEMANTICALLY_INCOMPATIBLE_GENERALIZATION = (
        "TRIVIAL_OR_SEMANTICALLY_INCOMPATIBLE_GENERALIZATION"
    )
    REQUIRES_BRANCH_GUARD = "REQUIRES_BRANCH_GUARD"
    NON_GLOBALIZABLE = "NON_GLOBALIZABLE"


def compute_shared_meaningful_constructors(term: Term) -> int:
    """Count non-wrapper constructor (App) applications in term."""
    if isinstance(term, (Var, Const)):
        return 0
    if isinstance(term, App):
        count = 1 if term.fn.lower() not in WRAPPER_FUNCTORS else 0
        for arg in term.args:
            count += compute_shared_meaningful_constructors(arg)
        return count
    return 0


from pathlib import Path
import re
import jsonschema
from msk_formal_discovery.core.exceptions import AntiUnificationError, ReceiptValidationError

HEX_64_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass
class AdmissibilityReceipt:
    """Deterministic admissibility assessment evidence (WO-MATH-FORMAL-DISCOVERY-01A-R3 Section 20)."""
    receipt_id: str
    algorithm_version: str
    source_trace_ids: List[str]
    source_trace_digests: List[str]
    discovery_problem_digests: List[str]
    source_term_digests: List[str]
    lgg_digest: str
    substitution_witness_digest: str
    branch_guards: List[str]
    semantic_domain_evidence: Dict[str, Any]
    meaningful_shared_constructor_count: int
    admissibility_status: AdmissibilityStatus
    receipt_digest: str = ""

    def __post_init__(self) -> None:
        if not self.receipt_digest:
            self.receipt_digest = self.compute_digest()

    @property
    def shared_meaningful_constructor_count(self) -> int:
        return self.meaningful_shared_constructor_count

    @property
    def semantic_domain_metadata(self) -> Dict[str, Any]:
        return self.semantic_domain_evidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "miskatonic.admissibility-receipt.v0.1",
            "receipt_id": self.receipt_id,
            "algorithm_version": self.algorithm_version,
            "source_trace_ids": list(self.source_trace_ids),
            "source_trace_digests": list(self.source_trace_digests),
            "discovery_problem_digests": list(self.discovery_problem_digests),
            "source_term_digests": list(self.source_term_digests),
            "lgg_digest": self.lgg_digest,
            "substitution_witness_digest": self.substitution_witness_digest,
            "branch_guards": list(self.branch_guards),
            "semantic_domain_evidence": self.semantic_domain_evidence,
            "meaningful_shared_constructor_count": self.meaningful_shared_constructor_count,
            "admissibility_status": (
                self.admissibility_status.value
                if isinstance(self.admissibility_status, AdmissibilityStatus)
                else str(self.admissibility_status)
            ),
            "receipt_digest": self.receipt_digest or self.compute_digest(),
        }

    def compute_digest(self) -> str:
        d = {
            "schema_version": "miskatonic.admissibility-receipt.v0.1",
            "receipt_id": self.receipt_id,
            "algorithm_version": self.algorithm_version,
            "source_trace_ids": list(self.source_trace_ids),
            "source_trace_digests": list(self.source_trace_digests),
            "discovery_problem_digests": list(self.discovery_problem_digests),
            "source_term_digests": list(self.source_term_digests),
            "lgg_digest": self.lgg_digest,
            "substitution_witness_digest": self.substitution_witness_digest,
            "branch_guards": list(self.branch_guards),
            "semantic_domain_evidence": self.semantic_domain_evidence,
            "meaningful_shared_constructor_count": self.meaningful_shared_constructor_count,
            "admissibility_status": (
                self.admissibility_status.value
                if isinstance(self.admissibility_status, AdmissibilityStatus)
                else str(self.admissibility_status)
            ),
        }
        serialized = json.dumps(d, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def digest(self) -> str:
        return self.receipt_digest or self.compute_digest()

    def validate(self, schema_path: Optional[Path] = None) -> None:
        if schema_path is None:
            default_path = Path(__file__).resolve().parents[3] / "schemas" / "admissibility-receipt.v0.1.schema.json"
            if default_path.exists():
                schema_path = default_path
        if schema_path and schema_path.exists():
            schema_data = json.loads(schema_path.read_text(encoding="utf-8"))
            try:
                jsonschema.validate(self.to_dict(), schema_data)
            except jsonschema.ValidationError as e:
                raise ReceiptValidationError(f"ADMISSIBILITY_RECEIPT_SCHEMA_ERROR: {e.message}") from e

        # Invariant: discovery problem digests must not be empty and must be hex
        if not self.discovery_problem_digests:
            raise ReceiptValidationError("ADMISSIBILITY_RECEIPT_EMPTY_PROBLEM_DIGESTS: discovery_problem_digests must not be empty")
        for pd in self.discovery_problem_digests:
            if not HEX_64_PATTERN.match(pd):
                raise ReceiptValidationError(f"INVALID_PROBLEM_DIGEST: '{pd}' is not a 64-char lowercase hex SHA-256")

        # Invariant: recomputed digest must match
        expected_digest = self.compute_digest()
        if self.receipt_digest != expected_digest:
            raise ReceiptValidationError(
                f"ADMISSIBILITY_RECEIPT_DIGEST_MISMATCH: receipt_digest '{self.receipt_digest}' != computed '{expected_digest}'"
            )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AdmissibilityReceipt:
        st_val = data["admissibility_status"]
        status = AdmissibilityStatus(st_val) if st_val in AdmissibilityStatus.__members__ else AdmissibilityStatus(st_val)
        return cls(
            receipt_id=data["receipt_id"],
            algorithm_version=data["algorithm_version"],
            source_trace_ids=list(data["source_trace_ids"]),
            source_trace_digests=list(data.get("source_trace_digests", [])),
            discovery_problem_digests=list(data.get("discovery_problem_digests", [])),
            source_term_digests=list(data["source_term_digests"]),
            lgg_digest=data["lgg_digest"],
            substitution_witness_digest=data.get("substitution_witness_digest", "0" * 64),
            branch_guards=list(data.get("branch_guards", [])),
            semantic_domain_evidence=data.get("semantic_domain_evidence") or data.get("semantic_domain_metadata", {}),
            meaningful_shared_constructor_count=data.get("meaningful_shared_constructor_count", data.get("shared_meaningful_constructor_count", 0)),
            admissibility_status=status,
            receipt_digest=data.get("receipt_digest", ""),
        )


def create_admissibility_receipt(
    terms: Sequence[Tuple[str, Term]],
    result: AntiUnificationResult,
    status: Optional[AdmissibilityStatus] = None,
    branch_guards: Optional[Sequence[str]] = None,
    discovery_problem_digests: Optional[Sequence[str]] = None,
    source_trace_digests: Optional[Sequence[str]] = None,
    semantic_domains: Optional[Dict[str, Any]] = None,
) -> AdmissibilityReceipt:
    """Create a validated AdmissibilityReceipt."""
    guards = list(branch_guards or [])
    if status is None:
        status = StructuralAntiUnifier.assess_admissibility(terms, result, branch_guards=guards)
    term_digests = [t[1].digest() for t in terms]
    trace_ids = [t[0] for t in terms]
    meaningful_count = compute_shared_meaningful_constructors(result.lgg_term)
    receipt_id = f"adm-rcpt-{result.deterministic_digest[:16]}"

    # Compute substitution witness digest
    raw_substs = {
        tid: {v: str(t_val) for v, t_val in subst.items()}
        for tid, subst in result.substitution_witnesses.items()
    }
    subst_dig = hashlib.sha256(json.dumps(raw_substs, sort_keys=True).encode("utf-8")).hexdigest()

    tr_digests = list(source_trace_digests or [hashlib.sha256(tid.encode("utf-8")).hexdigest() for tid in trace_ids])
    prob_digests = list(discovery_problem_digests or [])

    rcpt = AdmissibilityReceipt(
        receipt_id=receipt_id,
        algorithm_version=result.algorithm_version,
        source_trace_ids=trace_ids,
        source_trace_digests=tr_digests,
        discovery_problem_digests=prob_digests,
        source_term_digests=term_digests,
        lgg_digest=result.deterministic_digest,
        substitution_witness_digest=subst_dig,
        branch_guards=guards,
        semantic_domain_evidence=semantic_domains or {},
        meaningful_shared_constructor_count=meaningful_count,
        admissibility_status=status,
    )
    return rcpt


@dataclass(frozen=True)
class AntiUnificationResult:
    """Result of structural anti-unification over multiple source terms."""
    lgg_term: Term
    substitution_witnesses: Dict[str, Dict[str, Term]]  # trace_id -> {var_name: term}
    algorithm_version: str
    deterministic_digest: str

    @property
    def is_trivial_variable(self) -> bool:
        """Return True if the generalized term erased all structure down to a single variable."""
        return isinstance(self.lgg_term, Var)

    def verify_reconstruction(self, original_terms: Mapping[str, Term]) -> bool:
        """Verify that applying each witness substitution exactly reconstructs the original term."""
        for trace_id, orig_term in original_terms.items():
            subst = self.substitution_witnesses.get(trace_id, {})
            reconstructed = self.lgg_term.substitute(subst)
            if reconstructed != orig_term:
                return False
        return True


class StructuralAntiUnifier:
    """Deterministic structural anti-unifier computing least general generalizations."""

    def __init__(self, algorithm_version: str = ANTI_UNIFICATION_ALGORITHM_VERSION) -> None:
        self.algorithm_version = algorithm_version

    def anti_unify(self, terms: Sequence[Tuple[str, Term]]) -> AntiUnificationResult:
        """Compute the LGG for a sequence of (trace_id, Term) pairs.
        
        Must contain at least two terms.
        """
        if len(terms) < 2:
            raise AntiUnificationError("Anti-unification requires at least two terms to generalize")

        trace_ids = [t[0] for t in terms]
        term_instances = [t[1] for t in terms]

        # Map from tuple of subterms (t_1, ..., t_N) -> Var
        seen_tuples: Dict[Tuple[Term, ...], Var] = {}
        var_counter = 0

        def _lgg_recursive(subterms: Tuple[Term, ...]) -> Term:
            nonlocal var_counter

            # 1. If all subterms are identical, keep unchanged
            first = subterms[0]
            if all(t == first for t in subterms[1:]):
                return first

            # 2. If all subterms are function applications with matching functor and arity
            if all(isinstance(t, App) for t in subterms):
                app_first = subterms[0]
                assert isinstance(app_first, App)
                fn = app_first.fn
                arity = len(app_first.args)
                if all(isinstance(t, App) and t.fn == fn and len(t.args) == arity for t in subterms[1:]):
                    # Anti-unify arguments pairwise across all subterms
                    generalized_args: List[Term] = []
                    for arg_idx in range(arity):
                        arg_tuple = tuple(t.args[arg_idx] for t in subterms if isinstance(t, App))  # type: ignore
                        generalized_args.append(_lgg_recursive(arg_tuple))
                    return App(fn, tuple(generalized_args))

            # 3. Otherwise, check if we have already assigned a variable to this exact tuple
            if subterms in seen_tuples:
                return seen_tuples[subterms]

            # 4. Allocate a new deterministic variable V1, V2, ...
            var_counter += 1
            v = Var(f"V{var_counter}")
            seen_tuples[subterms] = v
            return v

        lgg = _lgg_recursive(tuple(term_instances))

        # Build substitution witnesses for each trace
        witnesses: Dict[str, Dict[str, Term]] = {tid: {} for tid in trace_ids}
        for subterm_tuple, var_node in seen_tuples.items():
            for i, tid in enumerate(trace_ids):
                witnesses[tid][var_node.name] = subterm_tuple[i]

        digest = lgg.digest()
        result = AntiUnificationResult(
            lgg_term=lgg,
            substitution_witnesses=witnesses,
            algorithm_version=self.algorithm_version,
            deterministic_digest=digest,
        )

        # Verify reconstruction invariant
        orig_map = dict(terms)
        if not result.verify_reconstruction(orig_map):
            raise AntiUnificationError("Generalization failed reconstruction verification invariant")

        return result

    @staticmethod
    def assess_admissibility(
        terms: Sequence[Tuple[str, Term]],
        result: AntiUnificationResult,
        branch_guards: Optional[Sequence[str]] = None,
    ) -> AdmissibilityStatus:
        """Assess candidate admissibility for lemma promotion (Sections 25, 28, 30)."""
        # 1. Check for conflicting branch guards (Section 30)
        if branch_guards:
            distinct_guards = set(branch_guards)
            if len(distinct_guards) > 1:
                return AdmissibilityStatus.REQUIRES_BRANCH_GUARD

        # 2. Check if LGG is a bare variable (trivial generalization)
        if result.is_trivial_variable:
            # Check for semantic domain / functor incompatibility (e.g. int_plus vs bool_xor)
            app_functors = {t.fn for _, t in terms if isinstance(t, App)}
            if len(app_functors) > 1:
                return AdmissibilityStatus.TRIVIAL_OR_SEMANTICALLY_INCOMPATIBLE_GENERALIZATION
            return AdmissibilityStatus.STRUCTURAL_GENERALIZATION_TRIVIAL

        # 3. Meaningful shared structure check (Section 28):
        # Wrapper-only nodes (such as seq(V1)) must not be admissible
        meaningful_count = compute_shared_meaningful_constructors(result.lgg_term)
        if meaningful_count == 0:
            # Check if inner functors differed across source terms
            inner_functors: Set[str] = set()
            for _, t in terms:
                if isinstance(t, App) and t.args:
                    for a in t.args:
                        if isinstance(a, App):
                            inner_functors.add(a.fn)
            if len(inner_functors) > 1:
                return AdmissibilityStatus.TRIVIAL_OR_SEMANTICALLY_INCOMPATIBLE_GENERALIZATION
            return AdmissibilityStatus.STRUCTURAL_GENERALIZATION_TRIVIAL

        # 4. Check if all structure is erased or too shallow (single node)
        if result.lgg_term.size() <= 1:
            return AdmissibilityStatus.STRUCTURAL_GENERALIZATION_TRIVIAL

        return AdmissibilityStatus.ADMISSIBLE
