"""Deterministic candidate selector and candidate selection ledger (WO-MATH-FORMAL-DISCOVERY-01B-R1 Sections 8-11)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from msk_formal_discovery.abstraction.anti_unification import (
    AdmissibilityStatus,
    compute_shared_meaningful_constructors,
)
from msk_formal_discovery.abstraction.candidate import (
    AbstractionCandidate,
    AbstractionKind,
    CandidateFactory,
)
from msk_formal_discovery.abstraction.subtrace_miner import RecurringSubtracePattern


def get_selector_implementation_digest() -> str:
    """SHA-256 digest of selector.py file bytes."""
    path = Path(__file__).resolve()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def derive_candidate_id_from_operations(operations: Sequence[str]) -> str:
    """Deterministically derive candidate ID from operation sequence."""
    tokens = []
    for op in operations:
        clean = op.lower().replace("_left", "").replace("_right", "")
        tokens.append(clean)
    return f"macro_{'_'.join(tokens)}"


def select_candidate(
    patterns: Sequence[RecurringSubtracePattern],
    candidate_kind: AbstractionKind = AbstractionKind.TACTIC_MACRO,
) -> Tuple[AbstractionCandidate, Dict[str, Any]]:
    """Select the winning candidate using the four-level deterministic comparator (Section 8).

    Ordering:
    1. Highest distinct-trace support (descending)
    2. Longest primitive operation sequence (descending)
    3. Highest meaningful shared-constructor count (descending)
    4. Lexical deterministic candidate artifact/pattern digest tie-break (ascending)

    Returns:
        (selected_candidate, candidate_selection_ledger_dict)
    """
    if not patterns:
        raise ValueError("CANDIDATE_DISCOVERY_FAILED: No subtrace patterns provided for candidate selection")

    candidate_records: List[Dict[str, Any]] = []

    for pattern in patterns:
        if not pattern.anti_unification_result:
            continue

        cid = derive_candidate_id_from_operations(pattern.operations)
        candidate = CandidateFactory.from_pattern(
            pattern,
            candidate_kind=candidate_kind,
            candidate_id=cid,
        )

        # Only admissible candidates are eligible for selection
        if candidate.admissibility_status != AdmissibilityStatus.ADMISSIBLE:
            continue

        distinct_support = len({occ[0] for occ in pattern.occurrences})
        op_seq_len = len(pattern.operations)
        meaningful_constructors = compute_shared_meaningful_constructors(
            pattern.anti_unification_result.lgg_term
        )
        art_dig = candidate.artifact_digest()

        # Sort key: (-support, -length, -constructors, artifact_digest)
        sort_tuple = (
            -distinct_support,
            -op_seq_len,
            -meaningful_constructors,
            art_dig,
        )

        candidate_records.append({
            "candidate": candidate,
            "candidate_id": cid,
            "source_trace_ids": list(candidate.discovery_set_trace_ids),
            "distinct_support": distinct_support,
            "operation_sequence": list(pattern.operations),
            "operation_sequence_length": op_seq_len,
            "meaningful_shared_constructor_count": meaningful_constructors,
            "deterministic_digest": art_dig,
            "sort_key_tuple": sort_tuple,
            "sort_key_repr": f"(-{distinct_support}, -{op_seq_len}, -{meaningful_constructors}, {art_dig})",
        })

    if not candidate_records:
        raise ValueError("CANDIDATE_DISCOVERY_FAILED: No admissible candidates could be constructed from patterns")

    # Sort deterministically; completely independent of input insertion order
    candidate_records.sort(key=lambda r: r["sort_key_tuple"])

    for idx, r in enumerate(candidate_records):
        r["rank"] = idx + 1

    winning_record = candidate_records[0]
    selected_candidate = winning_record["candidate"]

    # Verify that the selected candidate meets the contract (Section 10)
    if not selected_candidate.primitive_expansion:
        raise ValueError("CANDIDATE_DISCOVERY_FAILED: Selected candidate lacks primitive_expansion")

    ledger: Dict[str, Any] = {
        "schema_version": "miskatonic.candidate-selection-ledger.v0.1",
        "total_patterns_evaluated": len(patterns),
        "admissible_candidate_count": len(candidate_records),
        "candidate_records": [
            {
                "candidate_id": r["candidate_id"],
                "source_trace_ids": r["source_trace_ids"],
                "distinct_support": r["distinct_support"],
                "operation_sequence": r["operation_sequence"],
                "operation_sequence_length": r["operation_sequence_length"],
                "meaningful_shared_constructor_count": r["meaningful_shared_constructor_count"],
                "deterministic_digest": r["deterministic_digest"],
                "final_sort_key": r["sort_key_repr"],
                "rank": r["rank"],
            }
            for r in candidate_records
        ],
        "selected_candidate": {
            "candidate_id": selected_candidate.candidate_id,
            "candidate_kind": (
                selected_candidate.candidate_kind.value
                if hasattr(selected_candidate.candidate_kind, "value")
                else str(selected_candidate.candidate_kind)
            ),
            "primitive_expansion": list(selected_candidate.primitive_expansion),
            "artifact_digest": selected_candidate.artifact_digest(),
            "rank": 1,
        },
        "selector_implementation_digest": get_selector_implementation_digest(),
    }

    return selected_candidate, ledger
