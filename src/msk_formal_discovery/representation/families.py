"""Semantic Family Generator and Representation Orbit Instantiation (WO-MATH-FORMAL-DISCOVERY-01C)."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from msk_formal_discovery.core.terms import App, Const, Term, Var
from msk_formal_discovery.experiments.rewrite_control import (
    RewriteProblem,
    _make_prob,
    add,
    const,
    generate_discovery_corpus,
    generate_held_out_negative_corpus,
    generate_held_out_positive_corpus,
    mul,
    var,
)
from msk_formal_discovery.representation.transform import (
    RepresentationStratum,
    apply_transform,
)

POSITIVE_FAMILY_SEED = 161803
NEGATIVE_FAMILY_SEED = 141421


def get_families_implementation_digest() -> str:
    """SHA-256 digest of families.py source bytes."""
    path = Path(__file__).resolve()
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class SemanticFamily:
    """An independent unit of inference generating 4 representation strata (Section 5)."""
    family_id: str
    category: str  # HELD_OUT_POSITIVE or HELD_OUT_NEGATIVE
    canonical_variable: str
    r0_problem: RewriteProblem
    r2_initial_expression: Term
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "family_id": self.family_id,
            "category": self.category,
            "canonical_variable": self.canonical_variable,
            "r0_initial_expression": self.r0_problem.initial_expression.canonical_repr(),
            "r2_initial_expression": self.r2_initial_expression.canonical_repr(),
            "goal_expression": self.r0_problem.goal_expression.canonical_repr(),
            "description": self.description,
        }


def _X1(v: str) -> Term:
    """Canonical 01B inner motif: add(mul(1, V), 0)."""
    return add(mul(const(1), var(v)), const(0))


def _X2(v: str) -> Term:
    """Canonical 01B outer motif: mul(1, add(V, 0))."""
    return mul(const(1), add(var(v), const(0)))


def generate_semantic_families(
    pos_seed: int = POSITIVE_FAMILY_SEED,
    neg_seed: int = NEGATIVE_FAMILY_SEED,
) -> List[SemanticFamily]:
    """Generate the 12 semantic families (8 positive, 4 negative) frozen for WO-MATH-FORMAL-DISCOVERY-01C."""
    assert pos_seed == POSITIVE_FAMILY_SEED, f"Invalid positive seed: {pos_seed}"
    assert neg_seed == NEGATIVE_FAMILY_SEED, f"Invalid negative seed: {neg_seed}"

    families: List[SemanticFamily] = []

    # 8 Positive Families (ka .. kh)
    # 1. Left-associative add outer zeros
    v1 = "ka"
    r0_1 = add(add(_X1(v1), const(0)), const(0))
    r2_1 = add(_X1(v1), add(const(0), const(0)))
    families.append(
        SemanticFamily(
            family_id="fam-pos-01",
            category="HELD_OUT_POSITIVE",
            canonical_variable=v1,
            r0_problem=_make_prob("fam-pos-01", r0_1, var(v1), "HELD_OUT_POSITIVE", "left-associative add zeros"),
            r2_initial_expression=r2_1,
            description="Positive family 1: add-zero suffix left-to-right associative regrouping",
        )
    )

    # 2. Right-associative add outer zeros
    v2 = "kb"
    r0_2 = add(const(0), add(const(0), _X1(v2)))
    r2_2 = add(add(const(0), const(0)), _X1(v2))
    families.append(
        SemanticFamily(
            family_id="fam-pos-02",
            category="HELD_OUT_POSITIVE",
            canonical_variable=v2,
            r0_problem=_make_prob("fam-pos-02", r0_2, var(v2), "HELD_OUT_POSITIVE", "right-associative add zeros"),
            r2_initial_expression=r2_2,
            description="Positive family 2: add-zero prefix right-to-left associative regrouping",
        )
    )

    # 3. Double mul-one prefix
    v3 = "kc"
    r0_3 = mul(const(1), mul(const(1), _X1(v3)))
    r2_3 = mul(mul(const(1), const(1)), _X1(v3))
    families.append(
        SemanticFamily(
            family_id="fam-pos-03",
            category="HELD_OUT_POSITIVE",
            canonical_variable=v3,
            r0_problem=_make_prob("fam-pos-03", r0_3, var(v3), "HELD_OUT_POSITIVE", "mul-one prefix chain"),
            r2_initial_expression=r2_3,
            description="Positive family 3: mul-one prefix right-to-left associative regrouping",
        )
    )

    # 4. Double mul-one suffix
    v4 = "kd"
    r0_4 = mul(mul(_X1(v4), const(1)), const(1))
    r2_4 = mul(_X1(v4), mul(const(1), const(1)))
    families.append(
        SemanticFamily(
            family_id="fam-pos-04",
            category="HELD_OUT_POSITIVE",
            canonical_variable=v4,
            r0_problem=_make_prob("fam-pos-04", r0_4, var(v4), "HELD_OUT_POSITIVE", "mul-one suffix chain"),
            r2_initial_expression=r2_4,
            description="Positive family 4: mul-one suffix left-to-right associative regrouping",
        )
    )

    # 5. Outer mul-add-zero with left add
    v5 = "ke"
    r0_5 = add(add(_X2(v5), const(0)), const(0))
    r2_5 = add(_X2(v5), add(const(0), const(0)))
    families.append(
        SemanticFamily(
            family_id="fam-pos-05",
            category="HELD_OUT_POSITIVE",
            canonical_variable=v5,
            r0_problem=_make_prob("fam-pos-05", r0_5, var(v5), "HELD_OUT_POSITIVE", "mul-prefix add-suffix left-assoc"),
            r2_initial_expression=r2_5,
            description="Positive family 5: X2 left-to-right associative regrouping",
        )
    )

    # 6. Outer mul-add-zero with right add
    v6 = "kf"
    r0_6 = add(const(0), add(const(0), _X2(v6)))
    r2_6 = add(add(const(0), const(0)), _X2(v6))
    families.append(
        SemanticFamily(
            family_id="fam-pos-06",
            category="HELD_OUT_POSITIVE",
            canonical_variable=v6,
            r0_problem=_make_prob("fam-pos-06", r0_6, var(v6), "HELD_OUT_POSITIVE", "mul-prefix add-prefix right-assoc"),
            r2_initial_expression=r2_6,
            description="Positive family 6: X2 right-to-left associative regrouping",
        )
    )

    # 7. Outer mul-add-zero with prefix mul chain
    v7 = "kg"
    r0_7 = mul(const(1), mul(const(1), _X2(v7)))
    r2_7 = mul(mul(const(1), const(1)), _X2(v7))
    families.append(
        SemanticFamily(
            family_id="fam-pos-07",
            category="HELD_OUT_POSITIVE",
            canonical_variable=v7,
            r0_problem=_make_prob("fam-pos-07", r0_7, var(v7), "HELD_OUT_POSITIVE", "mul-prefix chain"),
            r2_initial_expression=r2_7,
            description="Positive family 7: X2 prefix mul right-to-left associative regrouping",
        )
    )

    # 8. Outer mul-add-zero with suffix mul chain
    v8 = "kh"
    r0_8 = mul(mul(_X2(v8), const(1)), const(1))
    r2_8 = mul(_X2(v8), mul(const(1), const(1)))
    families.append(
        SemanticFamily(
            family_id="fam-pos-08",
            category="HELD_OUT_POSITIVE",
            canonical_variable=v8,
            r0_problem=_make_prob("fam-pos-08", r0_8, var(v8), "HELD_OUT_POSITIVE", "mul-suffix chain"),
            r2_initial_expression=r2_8,
            description="Positive family 8: X2 suffix mul left-to-right associative regrouping",
        )
    )

    # 4 Negative Control Families (qa .. qd)
    # 9. Add zero prefix chain (no candidate motif)
    v9 = "qa"
    r0_9 = add(const(0), add(const(0), var(v9)))
    r2_9 = add(add(const(0), const(0)), var(v9))
    families.append(
        SemanticFamily(
            family_id="fam-neg-01",
            category="HELD_OUT_NEGATIVE",
            canonical_variable=v9,
            r0_problem=_make_prob("fam-neg-01", r0_9, var(v9), "HELD_OUT_NEGATIVE", "negative control add zeros prefix"),
            r2_initial_expression=r2_9,
            description="Negative family 1: zero prefix without mul motif",
        )
    )

    # 10. Mul one prefix chain (no candidate motif)
    v10 = "qb"
    r0_10 = mul(const(1), mul(const(1), var(v10)))
    r2_10 = mul(mul(const(1), const(1)), var(v10))
    families.append(
        SemanticFamily(
            family_id="fam-neg-02",
            category="HELD_OUT_NEGATIVE",
            canonical_variable=v10,
            r0_problem=_make_prob("fam-neg-02", r0_10, var(v10), "HELD_OUT_NEGATIVE", "negative control mul ones prefix"),
            r2_initial_expression=r2_10,
            description="Negative family 2: one prefix without add motif",
        )
    )

    # 11. Add zero suffix chain (no candidate motif)
    v11 = "qc"
    r0_11 = add(add(var(v11), const(0)), const(0))
    r2_11 = add(var(v11), add(const(0), const(0)))
    families.append(
        SemanticFamily(
            family_id="fam-neg-03",
            category="HELD_OUT_NEGATIVE",
            canonical_variable=v11,
            r0_problem=_make_prob("fam-neg-03", r0_11, var(v11), "HELD_OUT_NEGATIVE", "negative control add zeros suffix"),
            r2_initial_expression=r2_11,
            description="Negative family 3: zero suffix without mul motif",
        )
    )

    # 12. Mul one suffix chain (no candidate motif)
    v12 = "qd"
    r0_12 = mul(mul(var(v12), const(1)), const(1))
    r2_12 = mul(var(v12), mul(const(1), const(1)))
    families.append(
        SemanticFamily(
            family_id="fam-neg-04",
            category="HELD_OUT_NEGATIVE",
            canonical_variable=v12,
            r0_problem=_make_prob("fam-neg-04", r0_12, var(v12), "HELD_OUT_NEGATIVE", "negative control mul ones suffix"),
            r2_initial_expression=r2_12,
            description="Negative family 4: one suffix without add motif",
        )
    )

    assert len(families) == 12, f"Expected 12 semantic families, got {len(families)}"
    return families


def get_prior_experimental_units() -> Tuple[Set[str], Set[str]]:
    """Collect canonical representations and digests for all 32 prior experimental units."""
    prior_exprs: Set[str] = set()
    prior_digests: Set[str] = set()

    for fn_call in [
        lambda: generate_discovery_corpus(42),
        lambda: generate_held_out_positive_corpus(1337),
        lambda: generate_held_out_negative_corpus(2026),
        lambda: generate_held_out_positive_corpus(271828),
        lambda: generate_held_out_negative_corpus(314159),
    ]:
        for p in fn_call():
            prior_exprs.add(p.initial_expression.canonical_repr())
            prior_digests.add(p.problem_digest)

    assert len(prior_exprs) == 32, f"Expected 32 prior expressions, got {len(prior_exprs)}"
    assert len(prior_digests) == 32, f"Expected 32 prior digests, got {len(prior_digests)}"
    return prior_exprs, prior_digests


def assert_disjoint_from_prior_corpora(
    represented_problems: Dict[str, Dict[RepresentationStratum, Tuple[RewriteProblem, Dict[str, str]]]],
) -> None:
    """Verify that all 48 represented problems are strictly disjoint from all 32 prior units."""
    prior_exprs, prior_digests = get_prior_experimental_units()

    all_current_exprs: Set[str] = set()
    all_current_digests: Set[str] = set()

    for fid, strata_dict in represented_problems.items():
        for stratum, (prob, _) in strata_dict.items():
            c_repr = prob.initial_expression.canonical_repr()
            p_dig = prob.problem_digest

            if c_repr in prior_exprs:
                raise ValueError(
                    f"CORPUS_COLLISION_WITH_PRIOR_UNIT: Family {fid} stratum {stratum} has expression '{c_repr}' matching prior unit"
                )
            if p_dig in prior_digests:
                raise ValueError(
                    f"CORPUS_COLLISION_WITH_PRIOR_UNIT: Family {fid} stratum {stratum} has digest '{p_dig}' matching prior unit"
                )

            all_current_exprs.add(c_repr)
            all_current_digests.add(p_dig)

    if len(all_current_exprs) != 48:
        raise ValueError(
            f"INTERNAL_REPRESENTATION_COLLISION: Expected 48 unique expressions, got {len(all_current_exprs)}"
        )
    if len(all_current_digests) != 48:
        raise ValueError(
            f"INTERNAL_PROBLEM_DIGEST_COLLISION: Expected 48 unique digests, got {len(all_current_digests)}"
        )


def generate_all_represented_problems(
    families: List[SemanticFamily],
) -> Dict[str, Dict[RepresentationStratum, Tuple[RewriteProblem, Dict[str, str]]]]:
    """Generate all 48 represented problems across the 12 semantic families and 4 strata."""
    results: Dict[str, Dict[RepresentationStratum, Tuple[RewriteProblem, Dict[str, str]]]] = {}

    for fam in families:
        fam_dict: Dict[RepresentationStratum, Tuple[RewriteProblem, Dict[str, str]]] = {}
        for s in [
            RepresentationStratum.R0_CANONICAL_CONTROL,
            RepresentationStratum.R1_ALPHA_RENAMED,
            RepresentationStratum.R2_ASSOCIATIVE_REGROUPED,
            RepresentationStratum.R3_COMMUTATIVE_MIRROR,
        ]:
            prob, bijection = apply_transform(
                problem=fam.r0_problem,
                stratum=s,
                r2_initial_expression=fam.r2_initial_expression,
            )
            fam_dict[s] = (prob, bijection)

        results[fam.family_id] = fam_dict

    assert_disjoint_from_prior_corpora(results)
    return results
