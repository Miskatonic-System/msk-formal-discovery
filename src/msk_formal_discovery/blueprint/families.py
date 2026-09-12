"""Blueprint object families (Section 13)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class BlueprintObjectFamily(str, Enum):
    """Canonical Blueprint object families for mathematical formal discovery."""
    MICRO_LEMMA = "MICRO_LEMMA"
    HIDDEN_PRECONDITION = "HIDDEN_PRECONDITION"
    TYPECLASS_REQUIREMENT = "TYPECLASS_REQUIREMENT"
    NORMALIZATION_LEMMA = "NORMALIZATION_LEMMA"
    LIBRARY_BRIDGE = "LIBRARY_BRIDGE"
    FORMAL_DEPENDENCY = "FORMAL_DEPENDENCY"
    AMBIGUITY = "AMBIGUITY"
    UNRESOLVED_SYMBOL = "UNRESOLVED_SYMBOL"


@dataclass
class BlueprintNode:
    """A node in the mathematical discovery blueprint."""
    node_id: str
    family: BlueprintObjectFamily
    title: str
    statement: str
    dependencies: List[str]
    metadata: Dict[str, Any]
