"""First-order term representation, parsing, and substitution for anti-unification."""
from __future__ import annotations

import abc
import hashlib
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple


class Term(abc.ABC):
    """Abstract base class for structural terms."""

    @abc.abstractmethod
    def substitute(self, subst: Mapping[str, Term]) -> Term:
        """Apply variable substitution map."""

    @abc.abstractmethod
    def free_vars(self) -> Set[str]:
        """Return the set of free variable names."""

    @abc.abstractmethod
    def size(self) -> int:
        """Return the count of AST nodes."""

    @abc.abstractmethod
    def canonical_repr(self) -> str:
        """Return deterministic canonical string representation."""

    def digest(self) -> str:
        """Return SHA-256 digest of canonical representation."""
        return hashlib.sha256(self.canonical_repr().encode("utf-8")).hexdigest()

    def __str__(self) -> str:
        return self.canonical_repr()

    @classmethod
    def parse(cls, text: str) -> Term:
        """Parse a simple term expression like 'f(a, g(x))' or 'V1'."""
        tokens = cls._tokenize(text.strip())
        term, rest = cls._parse_tokens(tokens)
        if rest:
            raise ValueError(f"Unconsumed tokens after parsing term: {rest}")
        return term

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        # Tokenize identifiers, variables, commas, parentheses
        return re.findall(r"[A-Za-z0-9_#+*?-]+|\(|\)|,", text)

    @classmethod
    def _parse_tokens(cls, tokens: Sequence[str]) -> Tuple[Term, Sequence[str]]:
        if not tokens:
            raise ValueError("Unexpected end of tokens while parsing term")
        tok = tokens[0]
        rest = tokens[1:]

        # Check if next token is '(' -> function application
        if rest and rest[0] == "(":
            fn_name = tok
            rest = rest[1:]  # consume '('
            args: List[Term] = []
            if rest and rest[0] == ")":
                return App(fn_name, ()), rest[1:]
            while True:
                arg, rest = cls._parse_tokens(rest)
                args.append(arg)
                if not rest:
                    raise ValueError(f"Unterminated parenthesis in function application '{fn_name}'")
                if rest[0] == ",":
                    rest = rest[1:]
                    continue
                elif rest[0] == ")":
                    rest = rest[1:]
                    break
                else:
                    raise ValueError(f"Expected ',' or ')' after argument, got '{rest[0]}'")
            return App(fn_name, tuple(args)), rest

        # Variable (starts with V or ? or is explicitly a variable pattern)
        if tok.startswith("V") and len(tok) > 1 and tok[1:].isdigit():
            return Var(tok), rest
        if tok.startswith("?"):
            return Var(tok[1:]), rest

        # Constant / atom
        return Const(tok), rest


@dataclass(frozen=True)
class Const(Term):
    """Constant symbol."""
    name: str

    def substitute(self, subst: Mapping[str, Term]) -> Term:
        return self

    def free_vars(self) -> Set[str]:
        return set()

    def size(self) -> int:
        return 1

    def canonical_repr(self) -> str:
        return self.name

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Const) and self.name == other.name

    def __hash__(self) -> int:
        return hash(("Const", self.name))


@dataclass(frozen=True)
class Var(Term):
    """Variable symbol."""
    name: str

    def substitute(self, subst: Mapping[str, Term]) -> Term:
        return subst.get(self.name, self)

    def free_vars(self) -> Set[str]:
        return {self.name}

    def size(self) -> int:
        return 1

    def canonical_repr(self) -> str:
        return self.name

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Var) and self.name == other.name

    def __hash__(self) -> int:
        return hash(("Var", self.name))


@dataclass(frozen=True)
class App(Term):
    """Function application term."""
    fn: str
    args: Tuple[Term, ...]

    def substitute(self, subst: Mapping[str, Term]) -> Term:
        return App(self.fn, tuple(arg.substitute(subst) for arg in self.args))

    def free_vars(self) -> Set[str]:
        res: Set[str] = set()
        for a in self.args:
            res.update(a.free_vars())
        return res

    def size(self) -> int:
        return 1 + sum(a.size() for a in self.args)

    def canonical_repr(self) -> str:
        args_str = ", ".join(a.canonical_repr() for a in self.args)
        return f"{self.fn}({args_str})"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, App) and self.fn == other.fn and self.args == other.args

    def __hash__(self) -> int:
        return hash(("App", self.fn, self.args))
