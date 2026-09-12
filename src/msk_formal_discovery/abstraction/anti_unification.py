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


@dataclass(frozen=True)
class AdmissibilityReceipt:
    """Deterministic admissibility assessment evidence (Section 26)."""
    receipt_id: str
    algorithm_version: str
    source_trace_ids: List[str]
    discovery_problem_digests: List[str]
    source_term_digests: List[str]
    lgg_digest: str
    shared_meaningful_constructor_count: int
    branch_guards: List[str]
    semantic_domain_metadata: Dict[str, Any]
    admissibility_status: AdmissibilityStatus

    def to_dict(self) -> Dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "algorithm_version": self.algorithm_version,
            "source_trace_ids": self.source_trace_ids,
            "discovery_problem_digests": self.discovery_problem_digests,
            "source_term_digests": self.source_term_digests,
            "lgg_digest": self.lgg_digest,
            "shared_meaningful_constructor_count": self.shared_meaningful_constructor_count,
            "branch_guards": self.branch_guards,
            "semantic_domain_metadata": self.semantic_domain_metadata,
            "admissibility_status": (
                self.admissibility_status.value
                if isinstance(self.admissibility_status, AdmissibilityStatus)
                else str(self.admissibility_status)
            ),
        }

    def digest(self) -> str:
        serialized = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def create_admissibility_receipt(
    terms: Sequence[Tuple[str, Term]],
    result: AntiUnificationResult,
    status: Optional[AdmissibilityStatus] = None,
    branch_guards: Optional[Sequence[str]] = None,
    discovery_problem_digests: Optional[Sequence[str]] = None,
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
    return AdmissibilityReceipt(
        receipt_id=receipt_id,
        algorithm_version=result.algorithm_version,
        source_trace_ids=trace_ids,
        discovery_problem_digests=list(discovery_problem_digests or []),
        source_term_digests=term_digests,
        lgg_digest=result.deterministic_digest,
        shared_meaningful_constructor_count=meaningful_count,
        branch_guards=guards,
        semantic_domain_metadata=semantic_domains or {},
        admissibility_status=status,
    )


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
