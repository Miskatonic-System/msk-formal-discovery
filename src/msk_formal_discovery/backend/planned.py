"""Registration descriptors for planned reasoning backends (Section 2)."""
from __future__ import annotations

from typing import Any, Dict, List

from msk_formal_discovery.backend.contract import BackendFamily, LogicalAuthorityClass

PLANNED_BACKENDS: List[Dict[str, Any]] = [
    {
        "schema_version": "miskatonic.reasoning-backend.v0.1",
        "backend_id": "cvc5",
        "backend_family": BackendFamily.SMT_SOLVER.value,
        "backend_version": "1.1.2",
        "logical_authority_class": LogicalAuthorityClass.SOLVER_SAT_OR_UNSAT.value,
        "status": "PLANNED",
        "supported_operations": ["assert", "check_sat", "get_model", "get_proof"],
        "configuration": {},
        "adapter_identity": {
            "adapter_class": "Cvc5Adapter",
            "implementation_ref": "msk_formal_discovery.backend.planned.Cvc5Adapter",
            "is_reference_adapter": False,
        },
    },
    {
        "schema_version": "miskatonic.reasoning-backend.v0.1",
        "backend_id": "yices2",
        "backend_family": BackendFamily.SMT_SOLVER.value,
        "backend_version": "2.6.4",
        "logical_authority_class": LogicalAuthorityClass.SOLVER_SAT_OR_UNSAT.value,
        "status": "PLANNED",
        "supported_operations": ["assert", "check_sat", "get_model"],
        "configuration": {},
        "adapter_identity": {
            "adapter_class": "Yices2Adapter",
            "implementation_ref": "msk_formal_discovery.backend.planned.Yices2Adapter",
            "is_reference_adapter": False,
        },
    },
    {
        "schema_version": "miskatonic.reasoning-backend.v0.1",
        "backend_id": "bitwuzla",
        "backend_family": BackendFamily.SMT_SOLVER.value,
        "backend_version": "0.6.0",
        "logical_authority_class": LogicalAuthorityClass.SOLVER_SAT_OR_UNSAT.value,
        "status": "PLANNED",
        "supported_operations": ["assert", "check_sat", "get_model", "get_unsat_core"],
        "configuration": {},
        "adapter_identity": {
            "adapter_class": "BitwuzlaAdapter",
            "implementation_ref": "msk_formal_discovery.backend.planned.BitwuzlaAdapter",
            "is_reference_adapter": False,
        },
    },
    {
        "schema_version": "miskatonic.reasoning-backend.v0.1",
        "backend_id": "alloy",
        "backend_family": BackendFamily.MODEL_CHECKER.value,
        "backend_version": "6.1.0",
        "logical_authority_class": LogicalAuthorityClass.BOUNDED_EXHAUSTIVE_VERDICT.value,
        "status": "PLANNED",
        "supported_operations": ["check", "run", "get_instance"],
        "configuration": {},
        "adapter_identity": {
            "adapter_class": "AlloyAdapter",
            "implementation_ref": "msk_formal_discovery.backend.planned.AlloyAdapter",
            "is_reference_adapter": False,
        },
    },
    {
        "schema_version": "miskatonic.reasoning-backend.v0.1",
        "backend_id": "tlaplus",
        "backend_family": BackendFamily.MODEL_CHECKER.value,
        "backend_version": "1.8.0",
        "logical_authority_class": LogicalAuthorityClass.BOUNDED_EXHAUSTIVE_VERDICT.value,
        "status": "PLANNED",
        "supported_operations": ["model_check", "check_invariants", "find_counterexample"],
        "configuration": {},
        "adapter_identity": {
            "adapter_class": "TlaPlusAdapter",
            "implementation_ref": "msk_formal_discovery.backend.planned.TlaPlusAdapter",
            "is_reference_adapter": False,
        },
    },
    {
        "schema_version": "miskatonic.reasoning-backend.v0.1",
        "backend_id": "isabelle",
        "backend_family": BackendFamily.PROOF_ASSISTANT.value,
        "backend_version": "2024",
        "logical_authority_class": LogicalAuthorityClass.DEDUCTIVE_PROOF_AUTHORITY.value,
        "status": "PLANNED",
        "supported_operations": ["apply", "by", "sledgehammer", "nitpick"],
        "configuration": {},
        "adapter_identity": {
            "adapter_class": "IsabelleAdapter",
            "implementation_ref": "msk_formal_discovery.backend.planned.IsabelleAdapter",
            "is_reference_adapter": False,
        },
    },
    {
        "schema_version": "miskatonic.reasoning-backend.v0.1",
        "backend_id": "agda",
        "backend_family": BackendFamily.PROOF_ASSISTANT.value,
        "backend_version": "2.6.4",
        "logical_authority_class": LogicalAuthorityClass.DEDUCTIVE_PROOF_AUTHORITY.value,
        "status": "PLANNED",
        "supported_operations": ["typecheck", "case_split", "refine", "auto"],
        "configuration": {},
        "adapter_identity": {
            "adapter_class": "AgdaAdapter",
            "implementation_ref": "msk_formal_discovery.backend.planned.AgdaAdapter",
            "is_reference_adapter": False,
        },
    },
]
