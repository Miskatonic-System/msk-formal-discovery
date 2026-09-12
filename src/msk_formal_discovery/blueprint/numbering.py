"""Central architecture numbering reconciliation for MATH tracks (Section 13)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Canonical architecture sequence for MATH-2A / MATH-3A onward
CANONICAL_MATH_TRACK_SEQUENCE: Tuple[str, ...] = (
    "MATH-00A",  # Baseline Definitional / Literature Reconstruction
    "MATH-00B",  # Governed Primary Manuscript Recovery / Intake
    "MATH-01A",  # Formal Discovery Engine Bootstrap & Abstraction Kernel
    "MATH-02A",  # Automated Search & Blueprint Expansion
    "MATH-03A",  # Cross-Backend Proof Synthesis & Verification
    "MATH-04A",  # Multi-Theory Library Refactoring & Compression
    "MATH-05A",  # Autonomous Verification & Long-Horizon Theorem Discovery
)

RE_MATH_ID = re.compile(r"^MATH-(\d{2}[A-Z])$")


@dataclass(frozen=True)
class ArchitectureTrackRecord:
    track_id: str
    phase_order: int
    title: str
    authority_ceiling: str


CANONICAL_TRACK_REGISTRY: Dict[str, ArchitectureTrackRecord] = {
    "MATH-00A": ArchitectureTrackRecord("MATH-00A", 0, "Literature Baseline & Definitional Firewall", "CONJECTURAL"),
    "MATH-00B": ArchitectureTrackRecord("MATH-00B", 1, "Governed Primary Manuscript Recovery & Custody", "SOURCE_IDENTITY_ONLY"),
    "MATH-01A": ArchitectureTrackRecord("MATH-01A", 2, "Formal Discovery Engine Bootstrap & Abstraction Kernel", "NONE"),
    "MATH-02A": ArchitectureTrackRecord("MATH-02A", 3, "Automated Search & Blueprint Expansion", "SEARCH_EXPLORATION_ONLY"),
    "MATH-03A": ArchitectureTrackRecord("MATH-03A", 4, "Cross-Backend Proof Synthesis & Verification", "DEDUCTIVE_VERIFIED_ONLY"),
    "MATH-04A": ArchitectureTrackRecord("MATH-04A", 5, "Multi-Theory Library Refactoring & Compression", "NON_AUTHORITATIVE_PROPOSAL"),
    "MATH-05A": ArchitectureTrackRecord("MATH-05A", 6, "Autonomous Verification & Long-Horizon Discovery", "KERNEL_QUALIFIED"),
}


def is_valid_math_sequence(tracks: List[str]) -> bool:
    """Verify that a sequence of tracks preserves the canonical order."""
    indices = []
    for t in tracks:
        if t not in CANONICAL_TRACK_REGISTRY:
            return False
        indices.append(CANONICAL_TRACK_REGISTRY[t].phase_order)
    return indices == sorted(indices)
