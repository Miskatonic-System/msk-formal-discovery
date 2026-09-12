"""Structural anti-unification, Least General Generalization (LGG), and admissibility guards (WO-MATH-FORMAL-DISCOVERY-01A-R1)."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from msk_formal_discovery.core.exceptions import AntiUnificationError
from msk_formal_discovery.core.terms import App, Const, Term, Var

ANTI_UNIFICATION_ALGORITHM_VERSION = "miskatonic.structural-lgg-v0.1"


class AdmissibilityStatus(str, Enum):
    """Admissibility classification for generalized patterns."""
    ADMISSIBLE = "ADMISSIBLE"
    STRUCTURAL_GENERALIZATION_TRIVIAL = "STRUCTURAL_GENERALIZATION_TRIVIAL"
    TRIVIAL_OR_SEMANTICALLY_INCOMPATIBLE_GENERALIZATION = (
        "TRIVIAL_OR_SEMANTICALLY_INCOMPATIBLE_GENERALIZATION"
    )
    REQUIRES_BRANCH_GUARD = "REQUIRES_BRANCH_GUARD"
    NON_GLOBALIZABLE = "NON_GLOBALIZABLE"


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
        """Assess candidate admissibility for lemma promotion (Sections 18, 19, 20)."""
        # 1. Check for conflicting branch guards
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

        # 3. Check if all structure is erased or too shallow (single node)
        if result.lgg_term.size() <= 1:
            return AdmissibilityStatus.STRUCTURAL_GENERALIZATION_TRIVIAL

        return AdmissibilityStatus.ADMISSIBLE
