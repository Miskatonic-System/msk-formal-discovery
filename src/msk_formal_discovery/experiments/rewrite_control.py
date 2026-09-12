"""Governed symbolic rewrite environment, primitive rules v0.1, and experimental substrate (WO-MATH-FORMAL-DISCOVERY-01B)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from msk_formal_discovery.backend.contract import ExecutionOrigin, LogicalAuthorityClass
from msk_formal_discovery.backend.z3_adapter import Z3Adapter
from msk_formal_discovery.core.exceptions import BackendUnavailableError
from msk_formal_discovery.core.terms import App, Const, Term, Var
from msk_formal_discovery.search.policy import SearchAction, SearchState
from msk_formal_discovery.trace.events import EventOrigin, ExecutionTraceEvent, TraceEventType
from msk_formal_discovery.trace.ir import ExecutionTrace

# Section 4: Primitive Rewrite Set v0.1
# R1: MUL_ONE_LEFT: mul(1, X) -> X
# R2: MUL_ONE_RIGHT: mul(X, 1) -> X
# R3: ADD_ZERO_LEFT: add(0, X) -> X
# R4: ADD_ZERO_RIGHT: add(X, 0) -> X
# R5: DOUBLE_NEG: neg(neg(X)) -> X
PRIMITIVE_RULES: Tuple[str, ...] = (
    "MUL_ONE_LEFT",
    "MUL_ONE_RIGHT",
    "ADD_ZERO_LEFT",
    "ADD_ZERO_RIGHT",
    "DOUBLE_NEG",
)


def compute_primitive_ruleset_digest() -> str:
    """Deterministic SHA-256 digest of primitive rewrite set v0.1 definitions."""
    rules_def = [
        {"id": "R1", "name": "MUL_ONE_LEFT", "pattern": "mul(1, X)", "replacement": "X"},
        {"id": "R2", "name": "MUL_ONE_RIGHT", "pattern": "mul(X, 1)", "replacement": "X"},
        {"id": "R3", "name": "ADD_ZERO_LEFT", "pattern": "add(0, X)", "replacement": "X"},
        {"id": "R4", "name": "ADD_ZERO_RIGHT", "pattern": "add(X, 0)", "replacement": "X"},
        {"id": "R5", "name": "DOUBLE_NEG", "pattern": "neg(neg(X))", "replacement": "X"},
    ]
    serialized = json.dumps(rules_def, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def get_rewrite_environment_implementation_digest() -> str:
    """SHA-256 of rewrite_control.py source code."""
    path = Path(__file__).resolve()
    return hashlib.sha256(path.read_bytes()).hexdigest()


# AST helper functions
def var(name: str) -> Var:
    return Var(name)


def const(val: Any) -> Const:
    return Const(str(val))


def add(e1: Term, e2: Term) -> App:
    return App("add", (e1, e2))


def mul(e1: Term, e2: Term) -> App:
    return App("mul", (e1, e2))


def neg(e: Term) -> App:
    return App("neg", (e,))


def get_subterm(term: Term, pos: Tuple[int, ...]) -> Term:
    """Retrieve subterm at given position path."""
    curr = term
    for idx in pos:
        if not isinstance(curr, App) or idx >= len(curr.args):
            raise IndexError(f"Position {pos} out of bounds for term {term}")
        curr = curr.args[idx]
    return curr


def replace_subterm(term: Term, pos: Tuple[int, ...], replacement: Term) -> Term:
    """Replace subterm at position path with replacement term."""
    if not pos:
        return replacement
    if not isinstance(term, App):
        raise ValueError(f"Cannot descend into non-App term {term} at position {pos}")
    idx = pos[0]
    rest = pos[1:]
    new_args = list(term.args)
    new_args[idx] = replace_subterm(new_args[idx], rest, replacement)
    return App(term.fn, tuple(new_args))


def match_primitive_rule(term: Term, rule_name: str) -> Optional[Tuple[Term, Dict[str, Term]]]:
    """Check if term matches primitive rule at root. Returns (replacement, substitutions) or None."""
    if not isinstance(term, App):
        return None

    if rule_name == "MUL_ONE_LEFT":
        if term.fn == "mul" and len(term.args) == 2:
            left, right = term.args
            if isinstance(left, Const) and left.name == "1":
                return right, {"X": right}
    elif rule_name == "MUL_ONE_RIGHT":
        if term.fn == "mul" and len(term.args) == 2:
            left, right = term.args
            if isinstance(right, Const) and right.name == "1":
                return left, {"X": left}
    elif rule_name == "ADD_ZERO_LEFT":
        if term.fn == "add" and len(term.args) == 2:
            left, right = term.args
            if isinstance(left, Const) and left.name == "0":
                return right, {"X": right}
    elif rule_name == "ADD_ZERO_RIGHT":
        if term.fn == "add" and len(term.args) == 2:
            left, right = term.args
            if isinstance(right, Const) and right.name == "0":
                return left, {"X": left}
    elif rule_name == "DOUBLE_NEG":
        if term.fn == "neg" and len(term.args) == 1:
            inner = term.args[0]
            if isinstance(inner, App) and inner.fn == "neg" and len(inner.args) == 1:
                return inner.args[0], {"X": inner.args[0]}
    return None


@dataclass(frozen=True)
class RewriteMatch:
    """A matched primitive rewrite at a specific AST position."""
    rule_name: str
    position: Tuple[int, ...]
    matched_term: Term
    replacement_term: Term
    substitutions: Dict[str, Term]


def find_applicable_rewrites(term: Term) -> List[RewriteMatch]:
    """Enumerate all applicable primitive rewrites across all subterm positions in deterministic order."""
    matches: List[RewriteMatch] = []

    def _traverse(curr: Term, pos: Tuple[int, ...]) -> None:
        for r in PRIMITIVE_RULES:
            res = match_primitive_rule(curr, r)
            if res is not None:
                rep, subst = res
                matches.append(
                    RewriteMatch(
                        rule_name=r,
                        position=pos,
                        matched_term=curr,
                        replacement_term=rep,
                        substitutions=subst,
                    )
                )
        if isinstance(curr, App):
            for i, arg in enumerate(curr.args):
                _traverse(arg, pos + (i,))

    _traverse(term, ())
    # Sort deterministically: innermost subterm first, then position, then rule priority
    matches.sort(key=lambda m: (-len(m.position), m.position, PRIMITIVE_RULES.index(m.rule_name)))
    return matches


@dataclass
class RewriteTransitionReceipt:
    """Observed transition evidence (WO-MATH-FORMAL-DISCOVERY-01B Section 7)."""
    input_state_digest: str
    action_id: str
    operation: str
    output_state_digest: str
    primitive_rule: str
    rewrite_position: List[int]
    matched_term_repr: str
    replacement_term_repr: str
    transition_implementation_digest: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_state_digest": self.input_state_digest,
            "action_id": self.action_id,
            "operation": self.operation,
            "output_state_digest": self.output_state_digest,
            "primitive_rule": self.primitive_rule,
            "rewrite_position": list(self.rewrite_position),
            "matched_term_repr": self.matched_term_repr,
            "replacement_term_repr": self.replacement_term_repr,
            "transition_implementation_digest": self.transition_implementation_digest,
        }

    def digest(self) -> str:
        serialized = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class RewriteSearchEnvironment:
    """Governed symbolic rewrite search environment (WO-MATH-FORMAL-DISCOVERY-01B Section 6 & 7)."""

    def __init__(
        self,
        problem_id: str,
        problem_digest: str,
        goal_expression: Term,
    ) -> None:
        self.environment_id = "miskatonic.rewrite-env.v0.1"
        self.environment_version = "0.1.0"
        self.problem_id = problem_id
        self.problem_digest = problem_digest
        self.goal_expression = goal_expression
        self._impl_digest = get_rewrite_environment_implementation_digest()

    @property
    def implementation_digest(self) -> str:
        return self._impl_digest

    def create_initial_state(self, initial_expr: Term) -> SearchState:
        """Create SearchState binding the full symbolic expression."""
        s_dig = initial_expr.digest()
        is_solved = (initial_expr == self.goal_expression)
        return SearchState(
            state_id=f"state-{s_dig[:12]}",
            goal=str(self.goal_expression),
            depth=0,
            path_cost=0.0,
            heuristic_value=float(initial_expr.size()),
            is_solved=is_solved,
            is_terminal=is_solved,
            context={
                "expression": initial_expr,
                "expression_str": initial_expr.canonical_repr(),
                "expression_digest": s_dig,
                "goal_expression": self.goal_expression,
            },
        )

    def actions(self, state: SearchState) -> List[SearchAction]:
        """Enumerate legal primitive rewrite actions from current state."""
        expr: Term = state.context["expression"]
        matches = find_applicable_rewrites(expr)
        actions: List[SearchAction] = []
        for idx, m in enumerate(matches):
            pos_str = "_".join(str(p) for p in m.position) if m.position else "root"
            action_id = f"act-{state.state_id}-{m.rule_name}-{pos_str}"
            actions.append(
                SearchAction(
                    action_id=action_id,
                    operation=m.rule_name,
                    payload={
                        "rule": m.rule_name,
                        "position": list(m.position),
                        "matched_term": m.matched_term.canonical_repr(),
                        "replacement_term": m.replacement_term.canonical_repr(),
                        "substitutions": {k: v.canonical_repr() for k, v in m.substitutions.items()},
                    },
                    prior_probability=1.0 / max(1, len(matches)),
                    estimated_cost=1.0,
                )
            )
        return actions

    def transition(self, state: SearchState, action: SearchAction) -> Tuple[SearchState, RewriteTransitionReceipt]:
        """Apply rewrite action to current state, producing new state and observed transition receipt."""
        expr: Term = state.context["expression"]
        input_digest = state.context.get("expression_digest", expr.digest())

        if action.operation.startswith("MACRO_") or action.payload.get("macro_type") == "TACTIC_MACRO":
            # Macro action: execute candidate primitive_expansion sequentially (Section 17)
            prim_exp = action.payload.get("primitive_expansion", [])
            curr_expr = expr
            for step_rule in prim_exp:
                matches = find_applicable_rewrites(curr_expr)
                step_match = next((m for m in matches if m.rule_name == step_rule), None)
                if not step_match:
                    raise ValueError(f"MACRO_EXECUTION_FAILURE: Step {step_rule} not applicable in {curr_expr}")
                curr_expr = replace_subterm(curr_expr, step_match.position, step_match.replacement_term)
            new_expr = curr_expr
            rule_label = f"MACRO({','.join(prim_exp)})"
            pos = action.payload.get("start_position", [])
            matched_repr = str(expr)
            rep_repr = str(new_expr)
        else:
            # Primitive rewrite
            pos = tuple(action.payload.get("position", ()))
            rule = action.operation
            matched_subterm = get_subterm(expr, pos)
            res = match_primitive_rule(matched_subterm, rule)
            if res is None:
                raise ValueError(f"ILLEGAL_REWRITE_ACTION: Rule {rule} does not match at position {pos} in {expr}")
            rep_term, _ = res
            new_expr = replace_subterm(expr, pos, rep_term)
            rule_label = rule
            matched_repr = matched_subterm.canonical_repr()
            rep_repr = rep_term.canonical_repr()

        output_digest = new_expr.digest()
        is_solved = (new_expr == self.goal_expression)

        receipt = RewriteTransitionReceipt(
            input_state_digest=input_digest,
            action_id=action.action_id,
            operation=action.operation,
            output_state_digest=output_digest,
            primitive_rule=rule_label,
            rewrite_position=list(pos),
            matched_term_repr=matched_repr,
            replacement_term_repr=rep_repr,
            transition_implementation_digest=self.implementation_digest,
        )

        new_state = SearchState(
            state_id=f"state-{output_digest[:12]}",
            goal=str(self.goal_expression),
            depth=state.depth + 1,
            parent_id=state.state_id,
            path_cost=state.path_cost + action.estimated_cost,
            heuristic_value=float(new_expr.size()),
            is_solved=is_solved,
            is_terminal=is_solved,
            context={
                "expression": new_expr,
                "expression_str": new_expr.canonical_repr(),
                "expression_digest": output_digest,
                "goal_expression": self.goal_expression,
                "last_transition_receipt": receipt.to_dict(),
            },
        )
        return new_state, receipt

    def goal_test(self, state: SearchState) -> bool:
        """Evaluate whether goal state has been reached."""
        return state.context.get("expression") == self.goal_expression


@dataclass
class RewriteProblem:
    """Problem definition for symbolic rewrite search."""
    problem_id: str
    problem_digest: str
    initial_expression: Term
    goal_expression: Term
    category: str  # "DISCOVERY", "HELD_OUT_POSITIVE", "HELD_OUT_NEGATIVE"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "problem_id": self.problem_id,
            "problem_digest": self.problem_digest,
            "initial_expression": self.initial_expression.canonical_repr(),
            "goal_expression": self.goal_expression.canonical_repr(),
            "category": self.category,
            "description": self.description,
        }


def _make_prob(pid: str, init_expr: Term, goal_expr: Term, category: str, desc: str = "") -> RewriteProblem:
    p_dig = hashlib.sha256(f"{pid}:{init_expr.canonical_repr()}->{goal_expr.canonical_repr()}".encode("utf-8")).hexdigest()
    return RewriteProblem(
        problem_id=pid,
        problem_digest=p_dig,
        initial_expression=init_expr,
        goal_expression=goal_expr,
        category=category,
        description=desc,
    )


# Section 9: Freeze exactly 8 Discovery Problems
def generate_discovery_corpus(seed: int = 42) -> List[RewriteProblem]:
    """Generate exactly 8 discovery problems with planted recurring motif (MUL_ONE_LEFT, ADD_ZERO_RIGHT)."""
    # Variation in variable names, surrounding expression contexts, and other applicable rules
    probs: List[RewriteProblem] = [
        # d1: add(mul(1, a), 0) -> a
        _make_prob("disc-01", add(mul(const(1), var("a")), const(0)), var("a"), "DISCOVERY", "core motif"),
        # d2: add(0, add(mul(1, b), 0)) -> b
        _make_prob("disc-02", add(const(0), add(mul(const(1), var("b")), const(0))), var("b"), "DISCOVERY", "outer add-zero-left"),
        # d3: mul(add(mul(1, c), 0), 1) -> c
        _make_prob("disc-03", mul(add(mul(const(1), var("c")), const(0)), const(1)), var("c"), "DISCOVERY", "outer mul-one-right"),
        # d4: neg(neg(add(mul(1, d), 0))) -> d
        _make_prob("disc-04", neg(neg(add(mul(const(1), var("d")), const(0)))), var("d"), "DISCOVERY", "outer double-neg"),
        # d5: add(add(mul(1, e), 0), 0) -> e
        _make_prob("disc-05", add(add(mul(const(1), var("e")), const(0)), const(0)), var("e"), "DISCOVERY", "outer add-zero-right"),
        # d6: mul(1, add(mul(1, f), 0)) -> f
        _make_prob("disc-06", mul(const(1), add(mul(const(1), var("f")), const(0))), var("f"), "DISCOVERY", "outer mul-one-left"),
        # d7: mul(add(mul(1, g), 0), neg(neg(1))) -> g
        _make_prob("disc-07", mul(add(mul(const(1), var("g")), const(0)), neg(neg(const(1)))), var("g"), "DISCOVERY", "compound right double-neg"),
        # d8: add(0, mul(add(mul(1, h), 0), 1)) -> h
        _make_prob("disc-08", add(const(0), mul(add(mul(const(1), var("h")), const(0)), const(1))), var("h"), "DISCOVERY", "nested compound"),
    ]
    assert len(probs) == 8, f"Expected exactly 8 discovery problems, got {len(probs)}"
    return probs


# Section 10: Freeze exactly 8 Held-Out Positive Problems
def generate_held_out_positive_corpus(seed: int = 1337) -> List[RewriteProblem]:
    """Generate exactly 8 held-out positive problems with unseen variable names and contexts."""
    if seed == 271828:
        # WO-MATH-FORMAL-DISCOVERY-01B-R1 Fresh Positive Held-Out Corpus (Section 12)
        probs = [
            _make_prob("qual-r1-pos-01", mul(const(1), add(mul(const(1), var("va")), const(0))), var("va"), "HELD_OUT_POSITIVE", "fresh va mul-one prefix"),
            _make_prob("qual-r1-pos-02", add(add(mul(const(1), var("vb")), const(0)), const(0)), var("vb"), "HELD_OUT_POSITIVE", "fresh vb add-zero suffix"),
            _make_prob("qual-r1-pos-03", neg(neg(add(mul(const(1), var("vc")), const(0)))), var("vc"), "HELD_OUT_POSITIVE", "fresh vc double-neg outer"),
            _make_prob("qual-r1-pos-04", mul(add(mul(const(1), var("vd")), const(0)), const(1)), var("vd"), "HELD_OUT_POSITIVE", "fresh vd mul-one suffix"),
            _make_prob("qual-r1-pos-05", add(const(0), add(mul(const(1), var("ve")), const(0))), var("ve"), "HELD_OUT_POSITIVE", "fresh ve add-zero prefix"),
            _make_prob("qual-r1-pos-06", mul(const(1), neg(neg(add(mul(const(1), var("vf")), const(0))))), var("vf"), "HELD_OUT_POSITIVE", "fresh vf compound"),
            _make_prob("qual-r1-pos-07", add(const(0), mul(add(mul(const(1), var("vg")), const(0)), const(1))), var("vg"), "HELD_OUT_POSITIVE", "fresh vg mixed"),
            _make_prob("qual-r1-pos-08", neg(neg(add(const(0), add(mul(const(1), var("vh")), const(0))))), var("vh"), "HELD_OUT_POSITIVE", "fresh vh nested"),
        ]
        assert len(probs) == 8, f"Expected exactly 8 positive held-out problems, got {len(probs)}"
        return probs

    # Historical 01B Positive Problems (seed=1337)
    # Unseen variables: u, v, w, x, y, z, p, q
    probs = [
        # q1: add(0, mul(1, add(mul(1, u), 0))) -> u
        _make_prob("qual-pos-01", add(const(0), mul(const(1), add(mul(const(1), var("u")), const(0)))), var("u"), "HELD_OUT_POSITIVE", "unseen u compound"),
        # q2: mul(add(mul(1, v), 0), mul(1, 1)) -> v
        _make_prob("qual-pos-02", mul(add(mul(const(1), var("v")), const(0)), mul(const(1), const(1))), var("v"), "HELD_OUT_POSITIVE", "unseen v mul-one"),
        # q3: neg(neg(mul(add(mul(1, w), 0), 1))) -> w
        _make_prob("qual-pos-03", neg(neg(mul(add(mul(const(1), var("w")), const(0)), const(1)))), var("w"), "HELD_OUT_POSITIVE", "unseen w double-neg outer"),
        # q4: add(0, neg(neg(add(mul(1, x), 0)))) -> x
        _make_prob("qual-pos-04", add(const(0), neg(neg(add(mul(const(1), var("x")), const(0))))), var("x"), "HELD_OUT_POSITIVE", "unseen x mixed"),
        # q5: mul(1, mul(1, add(mul(1, y), 0))) -> y
        _make_prob("qual-pos-05", mul(const(1), mul(const(1), add(mul(const(1), var("y")), const(0)))), var("y"), "HELD_OUT_POSITIVE", "unseen y double mul-one"),
        # q6: add(add(mul(1, z), 0), add(0, 0)) -> z
        _make_prob("qual-pos-06", add(add(mul(const(1), var("z")), const(0)), add(const(0), const(0))), var("z"), "HELD_OUT_POSITIVE", "unseen z add-zero sibling"),
        # q7: mul(neg(neg(const(1))), add(mul(1, p), 0)) -> p
        _make_prob("qual-pos-07", mul(neg(neg(const(1))), add(mul(const(1), var("p")), const(0))), var("p"), "HELD_OUT_POSITIVE", "unseen p prefix double-neg"),
        # q8: add(mul(add(mul(1, q), 0), 1), 0) -> q
        _make_prob("qual-pos-08", add(mul(add(mul(const(1), var("q")), const(0)), const(1)), const(0)), var("q"), "HELD_OUT_POSITIVE", "unseen q post add-zero"),
    ]
    assert len(probs) == 8, f"Expected exactly 8 positive held-out problems, got {len(probs)}"
    return probs


# Section 11: Freeze exactly 4 Held-Out Negative-Control Problems
def generate_held_out_negative_corpus(seed: int = 2026) -> List[RewriteProblem]:
    """Generate exactly 4 negative control problems lacking the candidate motif."""
    if seed == 314159:
        # WO-MATH-FORMAL-DISCOVERY-01B-R1 Fresh Negative-Control Corpus (Section 12)
        probs = [
            _make_prob("qual-r1-neg-01", mul(const(1), neg(neg(var("na")))), var("na"), "HELD_OUT_NEGATIVE", "fresh na double-neg"),
            _make_prob("qual-r1-neg-02", add(const(0), mul(var("nb"), const(1))), var("nb"), "HELD_OUT_NEGATIVE", "fresh nb mul-one"),
            _make_prob("qual-r1-neg-03", neg(neg(add(var("nc"), const(0)))), var("nc"), "HELD_OUT_NEGATIVE", "fresh nc add-zero"),
            _make_prob("qual-r1-neg-04", mul(const(1), add(const(0), var("nd"))), var("nd"), "HELD_OUT_NEGATIVE", "fresh nd add-zero prefix"),
        ]
        assert len(probs) == 4, f"Expected exactly 4 negative control problems, got {len(probs)}"
        return probs

    # Historical 01B Negative Problems (seed=2026)
    # These must NOT contain add(mul(1, X), 0)
    probs = [
        # n1: add(0, neg(neg(r))) -> r
        _make_prob("qual-neg-01", add(const(0), neg(neg(var("r")))), var("r"), "HELD_OUT_NEGATIVE", "negative control r"),
        # n2: mul(s, 1) -> s
        _make_prob("qual-neg-02", mul(var("s"), const(1)), var("s"), "HELD_OUT_NEGATIVE", "negative control s"),
        # n3: add(0, mul(t, 1)) -> t
        _make_prob("qual-neg-03", add(const(0), mul(var("t"), const(1))), var("t"), "HELD_OUT_NEGATIVE", "negative control t"),
        # n4: neg(neg(neg(neg(n)))) -> n
        _make_prob("qual-neg-04", neg(neg(neg(neg(var("n"))))), var("n"), "HELD_OUT_NEGATIVE", "negative control n quad neg"),
    ]
    assert len(probs) == 4, f"Expected exactly 4 negative control problems, got {len(probs)}"
    return probs


def run_discovery_episode(problem: RewriteProblem) -> ExecutionTrace:
    """Execute search on a discovery problem and produce an attested ExecutionTrace with RULE_APPLICATION events."""
    env = RewriteSearchEnvironment(
        problem_id=problem.problem_id,
        problem_digest=problem.problem_digest,
        goal_expression=problem.goal_expression,
    )
    initial_state = env.create_initial_state(problem.initial_expression)

    # Breadth-first exploration to find shortest rewrite path
    frontier: List[SearchState] = [initial_state]
    visited: Set[str] = {initial_state.context["expression_digest"]}
    parent_map: Dict[str, Tuple[SearchState, SearchAction, SearchState, RewriteTransitionReceipt]] = {}
    solved_state: Optional[SearchState] = None

    if initial_state.is_solved:
        solved_state = initial_state
    else:
        while frontier:
            curr = frontier.pop(0)
            actions = env.actions(curr)
            found_goal = False
            for act in actions:
                next_st, receipt = env.transition(curr, act)
                nxt_dig = next_st.context["expression_digest"]
                if nxt_dig not in visited:
                    visited.add(nxt_dig)
                    parent_map[next_st.state_id] = (curr, act, next_st, receipt)
                    if next_st.is_solved:
                        solved_state = next_st
                        found_goal = True
                        break
                    frontier.append(next_st)
            if found_goal:
                break

    if not solved_state:
        raise RuntimeError(f"Failed to solve discovery problem {problem.problem_id}")

    # Reconstruct winning path
    path: List[Tuple[SearchState, SearchAction, SearchState, RewriteTransitionReceipt]] = []
    curr_id = solved_state.state_id
    while curr_id in parent_map:
        item = parent_map[curr_id]
        path.append(item)
        curr_id = item[0].state_id
    path.reverse()

    # Construct ExecutionTrace with BACKEND_OBSERVED RULE_APPLICATION events (Section 8)
    trace = ExecutionTrace(
        trace_id=f"trace-{problem.problem_id}",
        problem_id=problem.problem_id,
        problem_digest=problem.problem_digest,
        backend_id="rewrite_environment",
        backend_version="0.1.0",
        execution_origin="EXECUTED_NATIVE",
        logical_authority_class="NONE",
        created_at=datetime.now(timezone.utc).isoformat(),
        terminal_verdict="PROVEN",
        wall_time_ms=5.0,
    )

    init_ev = trace.add_event(
        event_type=TraceEventType.INITIAL_PROBLEM,
        operation="init",
        state_digest=initial_state.context["expression_digest"],
        result_digest=initial_state.context["expression_digest"],
        payload={"problem_id": problem.problem_id, "expression": str(problem.initial_expression)},
        event_origin=EventOrigin.BACKEND_OBSERVED,
    )
    last_id = init_ev.event_id

    for st_in, act, st_out, rec in path:
        # Payload carries expression in form rule(RULE_NAME, var_name) for LGG anti-unification
        # Extract the variable from substitutions or term representation
        subterm = act.payload.get("matched_term", "")
        v_name = "V"
        for v in act.payload.get("substitutions", {}).values():
            v_name = v
            break

        ev = trace.add_event(
            event_type=TraceEventType.RULE_APPLICATION,
            operation=act.operation,
            state_digest=st_in.context["expression_digest"],
            result_digest=st_out.context["expression_digest"],
            parent_event_id=last_id,
            payload={
                "operation": act.operation,
                "expression": f"rule({act.operation}, {v_name})",
                "tactic": f"rule({act.operation}, {v_name})",
                "receipt": rec.to_dict(),
            },
            event_origin=EventOrigin.BACKEND_OBSERVED,
        )
        last_id = ev.event_id

    trace.add_event(
        event_type=TraceEventType.TERMINAL_VERDICT,
        operation="qed",
        state_digest=solved_state.context["expression_digest"],
        result_digest=solved_state.context["expression_digest"],
        parent_event_id=last_id,
        payload={"verdict": "PROVEN", "proof_complete": "PROVEN"},
        event_origin=EventOrigin.BACKEND_OBSERVED,
    )
    return trace


def term_to_smtlib(term: Term) -> str:
    """Convert symbolic Term to SMT-LIB2 integer arithmetic expression."""
    if isinstance(term, Var):
        return term.name
    elif isinstance(term, Const):
        try:
            val = int(term.name)
            return f"(- {abs(val)})" if val < 0 else str(val)
        except ValueError:
            return term.name
    elif isinstance(term, App):
        if term.fn == "add":
            return f"(+ {term_to_smtlib(term.args[0])} {term_to_smtlib(term.args[1])})"
        elif term.fn == "mul":
            return f"(* {term_to_smtlib(term.args[0])} {term_to_smtlib(term.args[1])})"
        elif term.fn == "neg":
            return f"(- {term_to_smtlib(term.args[0])})"
        else:
            raise ValueError(f"Unknown functor for SMT conversion: {term.fn}")
    raise ValueError(f"Unsupported term type for SMT conversion: {type(term)}")


def check_smt_equivalence(
    expr1: Term,
    expr2: Term,
    problem_id: str,
    adapter: Optional[Z3Adapter] = None,
) -> Tuple[bool, ExecutionTrace]:
    """Verify semantic equivalence of two symbolic expressions via native Z3 SMT check (Section 25).
    
    assert (not (= expr1 expr2))
    check-sat
    Expected: UNSAT (UNSAT_REFUTED) -> expressions are equivalent for all integers.
    """
    z3 = adapter or Z3Adapter()
    if not z3.z3_binary:
        raise BackendUnavailableError("Z3_UNAVAILABLE: Native Z3 binary not found on system path")

    free_vars = sorted(list(expr1.free_vars().union(expr2.free_vars())))
    smt_lines = ["; SMT Semantic Control (WO-MATH-FORMAL-DISCOVERY-01B Section 25)"]
    for v in free_vars:
        smt_lines.append(f"(declare-const {v} Int)")

    smt1 = term_to_smtlib(expr1)
    smt2 = term_to_smtlib(expr2)
    smt_lines.append(f"(assert (not (= {smt1} {smt2})))")
    smt_lines.append("(check-sat)")
    smt_script = "\n".join(smt_lines) + "\n"

    trace = z3.run_smt(
        problem_id=f"smt-{problem_id}",
        smtlib_script=smt_script,
        execution_mode="REAL",
    )

    # Require authentic native execution receipt and UNSAT verdict (Section 25)
    if trace.execution_origin != "EXECUTED_NATIVE":
        raise ValueError(f"SMT_CONTROL_NON_NATIVE_EXECUTION: origin '{trace.execution_origin}', simulated fallback prohibited")
    if trace.logical_authority_class != LogicalAuthorityClass.SOLVER_SAT_OR_UNSAT:
        raise ValueError(f"SMT_CONTROL_INVALID_AUTHORITY: {trace.logical_authority_class}")

    is_equiv = (trace.terminal_verdict == "UNSAT_REFUTED")
    return is_equiv, trace


def get_smt_control_implementation_digest() -> str:
    """SHA-256 digest of SMT control logic in rewrite_control.py."""
    path = Path(__file__).resolve()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_paired_terminal_smt_equivalence(
    baseline_bundle: Any,
    abstracted_bundle: Any,
    problem_id: str,
    adapter: Optional[Z3Adapter] = None,
) -> Tuple[bool, ExecutionTrace]:
    """Verify semantic equivalence of actual baseline vs actual abstracted terminal expressions via native Z3.

    Freeze invariant (WO-MATH-FORMAL-DISCOVERY-01B-R1 Sections 17 & 18):
    INITIAL_EXPRESSION_EQUIVALENT_TO_GOAL != PAIRED_TERMINAL_SEMANTIC_EQUIVALENCE.
    Actual baseline terminal must be compared directly to actual abstracted terminal.
    """
    baseline_term = getattr(baseline_bundle, "terminal_expression", None)
    if baseline_term is None and hasattr(baseline_bundle, "terminal_state") and baseline_bundle.terminal_state:
        baseline_term = baseline_bundle.terminal_state.context.get("expression")

    abstracted_term = getattr(abstracted_bundle, "terminal_expression", None)
    if abstracted_term is None and hasattr(abstracted_bundle, "terminal_state") and abstracted_bundle.terminal_state:
        abstracted_term = abstracted_bundle.terminal_state.context.get("expression")

    if baseline_term is None:
        raise ValueError(f"MISSING_BASELINE_TERMINAL: Problem {problem_id} search bundle lacks terminal expression")
    if abstracted_term is None:
        raise ValueError(f"MISSING_ABSTRACTED_TERMINAL: Problem {problem_id} search bundle lacks terminal expression")

    return check_smt_equivalence(baseline_term, abstracted_term, problem_id=f"paired-{problem_id}", adapter=adapter)

