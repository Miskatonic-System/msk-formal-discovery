"""Exact free-group words for WO-FORMAL-TOPOLOGICAL-GALOIS-SOURCE-REPRESENTATION-01A.

A word in F_n = <x_1, ..., x_n> is a tuple of letters (g, e) with g in 1..n and e in {+1, -1}.
Words are kept freely reduced, so equality of tuples is equality in the free group.
No Python object outside this module is ever compared for free-group equality.
"""
from __future__ import annotations

from typing import Iterable, Mapping, Tuple

Letter = Tuple[int, int]
Word = Tuple[Letter, ...]


def reduce_word(letters: Iterable[Letter]) -> Word:
    """Freely reduce: cancel adjacent (g, e)(g, -e) pairs until none remain."""
    out: list[Letter] = []
    for g, e in letters:
        if e not in (1, -1) or g < 1:
            raise ValueError(f"bad letter {(g, e)}")
        if out and out[-1][0] == g and out[-1][1] == -e:
            out.pop()
        else:
            out.append((g, e))
    return tuple(out)


def gen(i: int) -> Word:
    return ((i, 1),)


def inverse(w: Word) -> Word:
    return tuple((g, -e) for g, e in reversed(w))


def mul(*ws: Word) -> Word:
    letters: list[Letter] = []
    for w in ws:
        letters.extend(w)
    return reduce_word(letters)


def conj(a: Word, b: Word) -> Word:
    """a b a^{-1}."""
    return mul(a, b, inverse(a))


def word_str(w: Word) -> str:
    if not w:
        return "1"
    return " ".join(f"x{g}" if e == 1 else f"x{g}^-1" for g, e in w)


def parse(s: str) -> Word:
    """Parse the output format of word_str."""
    s = s.strip()
    if s == "1":
        return ()
    letters = []
    for tok in s.split():
        if not tok.startswith("x"):
            raise ValueError(tok)
        body = tok[1:]
        if body.endswith("^-1"):
            letters.append((int(body[:-3]), -1))
        else:
            letters.append((int(body), 1))
    return reduce_word(letters)


class Endo:
    """An endomorphism of F_n given by the images of the generators (exact substitution)."""

    def __init__(self, n: int, images: Mapping[int, Word]):
        self.n = n
        self.images = {i: reduce_word(images.get(i, gen(i))) for i in range(1, n + 1)}

    def __call__(self, w: Word) -> Word:
        letters: list[Letter] = []
        for g, e in w:
            img = self.images[g]
            letters.extend(img if e == 1 else inverse(img))
        return reduce_word(letters)

    def compose(self, other: "Endo") -> "Endo":
        """self o other  (apply other first)."""
        return Endo(self.n, {i: self(other.images[i]) for i in range(1, self.n + 1)})

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Endo) and self.n == other.n and self.images == other.images

    def is_identity(self) -> bool:
        return all(self.images[i] == gen(i) for i in range(1, self.n + 1))

    def abelianization_image(self) -> dict[int, dict[int, int]]:
        """Exponent-sum vector of each generator image (the induced map on Z^n)."""
        out = {}
        for i in range(1, self.n + 1):
            v = {j: 0 for j in range(1, self.n + 1)}
            for g, e in self.images[i]:
                v[g] += e
            out[i] = v
        return out

    def to_json(self) -> dict[str, str]:
        return {f"x{i}": word_str(self.images[i]) for i in range(1, self.n + 1)}
