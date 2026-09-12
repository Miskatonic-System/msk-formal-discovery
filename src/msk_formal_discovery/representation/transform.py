"""Deterministic Representation Transformations for WO-MATH-FORMAL-DISCOVERY-01C."""
from __future__ import annotations

import hashlib
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from msk_formal_discovery.core.terms import App, Const, Term, Var
from msk_formal_discovery.experiments.rewrite_control import RewriteProblem, _make_prob


class RepresentationStratum(str, Enum):
    R0_CANONICAL_CONTROL = "R0_CANONICAL_CONTROL"
    R1_ALPHA_RENAMED = "R1_ALPHA_RENAMED"
    R2_ASSOCIATIVE_REGROUPED = "R2_ASSOCIATIVE_REGROUPED"
    R3_COMMUTATIVE_MIRROR = "R3_COMMUTATIVE_MIRROR"


def get_transform_implementation_digest() -> str:
    """SHA-256 digest of transform.py source bytes."""
    path = Path(__file__).resolve()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_leaves_in_order(term: Term) -> List[str]:
    """Retrieve leaf names in strict left-to-right order."""
    leaves: List[str] = []

    def _traverse(t: Term) -> None:
        if isinstance(t, (Var, Const)):
            leaves.append(t.name)
        elif isinstance(t, App):
            for arg in t.args:
                _traverse(arg)

    _traverse(term)
    return leaves


def alpha_rename_term(term: Term, bijection: Dict[str, str]) -> Term:
    """Apply bijective variable renaming to an AST term.
    
    Validates:
    - Bijective: 1-to-1 (injective) and covers all free variables in term.
    """
    targets = list(bijection.values())
    if len(set(targets)) != len(targets):
        raise ValueError("NON_BIJECTIVE_ALPHA_RENAME: Bijection has duplicate target names (not injective)")

    free_vars = term.free_vars()
    missing = free_vars - set(bijection.keys())
    if missing:
        raise ValueError(f"NON_BIJECTIVE_ALPHA_RENAME: Free variables {missing} not in bijection")

    def _rename(t: Term) -> Term:
        if isinstance(t, Var):
            return Var(bijection[t.name])
        elif isinstance(t, Const):
            return Const(t.name)
        elif isinstance(t, App):
            return App(t.fn, tuple(_rename(a) for a in t.args))
        return t

    return _rename(term)


def associative_regroup_term(term: Term) -> Term:
    """Apply semantics-preserving associative regrouping without commutative reordering.
    
    Reassociates eligible subtrees:
    - (A + B) + C <-> A + (B + C)
    - (A * B) * C <-> A * (B * C)
    
    Guarantees leaf order is strictly preserved.
    """
    if not isinstance(term, App):
        return term

    new_args = tuple(associative_regroup_term(a) for a in term.args)

    if term.fn == "add" and len(new_args) == 2:
        left, right = new_args
        # (A + B) + C -> A + (B + C)
        if isinstance(left, App) and left.fn == "add" and len(left.args) == 2:
            a, b = left.args
            c = right
            res = App("add", (a, App("add", (b, c))))
            # Verify leaf order preservation
            if get_leaves_in_order(res) != get_leaves_in_order(App(term.fn, new_args)):
                raise ValueError("UNAPPROVED_COMMUTATIVE_TRANSFORMATION: Associative regroup altered leaf order")
            return res
        # A + (B + C) -> (A + B) + C
        elif isinstance(right, App) and right.fn == "add" and len(right.args) == 2:
            a = left
            b, c = right.args
            res = App("add", (App("add", (a, b)), c))
            if get_leaves_in_order(res) != get_leaves_in_order(App(term.fn, new_args)):
                raise ValueError("UNAPPROVED_COMMUTATIVE_TRANSFORMATION: Associative regroup altered leaf order")
            return res

    elif term.fn == "mul" and len(new_args) == 2:
        left, right = new_args
        # (A * B) * C -> A * (B * C)
        if isinstance(left, App) and left.fn == "mul" and len(left.args) == 2:
            a, b = left.args
            c = right
            res = App("mul", (a, App("mul", (b, c))))
            if get_leaves_in_order(res) != get_leaves_in_order(App(term.fn, new_args)):
                raise ValueError("UNAPPROVED_COMMUTATIVE_TRANSFORMATION: Associative regroup altered leaf order")
            return res
        # A * (B * C) -> (A * B) * C
        elif isinstance(right, App) and right.fn == "mul" and len(right.args) == 2:
            a = left
            b, c = right.args
            res = App("mul", (App("mul", (a, b)), c))
            if get_leaves_in_order(res) != get_leaves_in_order(App(term.fn, new_args)):
                raise ValueError("UNAPPROVED_COMMUTATIVE_TRANSFORMATION: Associative regroup altered leaf order")
            return res

    return App(term.fn, new_args)


def commutative_mirror_term(term: Term) -> Term:
    """Commutatively mirror identity-bearing subtrees.
    
    Mirrors:
    - add(0, X) <-> add(X, 0)
    - mul(1, X) <-> mul(X, 1)
    """
    if not isinstance(term, App):
        return term

    new_args = tuple(commutative_mirror_term(a) for a in term.args)

    if term.fn == "add" and len(new_args) == 2:
        l, r = new_args
        if isinstance(l, Const) and l.name == "0":
            return App("add", (r, l))
        elif isinstance(r, Const) and r.name == "0":
            return App("add", (r, l))
    elif term.fn == "mul" and len(new_args) == 2:
        l, r = new_args
        if isinstance(l, Const) and l.name == "1":
            return App("mul", (r, l))
        elif isinstance(r, Const) and r.name == "1":
            return App("mul", (r, l))

    return App(term.fn, new_args)


def apply_transform(
    problem: RewriteProblem,
    stratum: RepresentationStratum,
    variable_bijection: Optional[Dict[str, str]] = None,
    r2_initial_expression: Optional[Term] = None,
) -> Tuple[RewriteProblem, Dict[str, str]]:
    """Transform an R0 canonical problem into the specified representation stratum."""
    s_val = stratum.value if isinstance(stratum, RepresentationStratum) else stratum

    if s_val == RepresentationStratum.R0_CANONICAL_CONTROL.value:
        bijection = {v: v for v in problem.initial_expression.free_vars()}
        prob_id = f"{problem.problem_id}-r0"
        trans_prob = _make_prob(
            pid=prob_id,
            init_expr=problem.initial_expression,
            goal_expr=problem.goal_expression,
            category=problem.category,
            desc=f"{problem.description} [R0_CANONICAL_CONTROL]",
        )
        return trans_prob, bijection

    elif s_val == RepresentationStratum.R1_ALPHA_RENAMED.value:
        if variable_bijection is None:
            bijection = {v: f"alpha_{v}" for v in problem.initial_expression.free_vars()}
        else:
            bijection = dict(variable_bijection)

        new_init = alpha_rename_term(problem.initial_expression, bijection)
        new_goal = alpha_rename_term(problem.goal_expression, bijection)
        prob_id = f"{problem.problem_id}-r1"
        trans_prob = _make_prob(
            pid=prob_id,
            init_expr=new_init,
            goal_expr=new_goal,
            category=problem.category,
            desc=f"{problem.description} [R1_ALPHA_RENAMED]",
        )
        return trans_prob, bijection

    elif s_val == RepresentationStratum.R2_ASSOCIATIVE_REGROUPED.value:
        bijection = {v: v for v in problem.initial_expression.free_vars()}
        if r2_initial_expression is not None:
            new_init = r2_initial_expression
            # Verify leaf order matches R0
            if get_leaves_in_order(new_init) != get_leaves_in_order(problem.initial_expression):
                raise ValueError("UNAPPROVED_COMMUTATIVE_TRANSFORMATION: R2 initial expression altered leaf order")
        else:
            new_init = associative_regroup_term(problem.initial_expression)

        prob_id = f"{problem.problem_id}-r2"
        trans_prob = _make_prob(
            pid=prob_id,
            init_expr=new_init,
            goal_expr=problem.goal_expression,
            category=problem.category,
            desc=f"{problem.description} [R2_ASSOCIATIVE_REGROUPED]",
        )
        return trans_prob, bijection

    elif s_val == RepresentationStratum.R3_COMMUTATIVE_MIRROR.value:
        bijection = {v: v for v in problem.initial_expression.free_vars()}
        new_init = commutative_mirror_term(problem.initial_expression)
        prob_id = f"{problem.problem_id}-r3"
        trans_prob = _make_prob(
            pid=prob_id,
            init_expr=new_init,
            goal_expr=problem.goal_expression,
            category=problem.category,
            desc=f"{problem.description} [R3_COMMUTATIVE_MIRROR]",
        )
        return trans_prob, bijection

    else:
        raise ValueError(f"UNKNOWN_REPRESENTATION_STRATUM: {stratum}")
