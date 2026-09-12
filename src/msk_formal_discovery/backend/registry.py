"""Registry of reasoning backends and authority enforcement."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import jsonschema

from msk_formal_discovery.backend.contract import (
    BackendFamily,
    LogicalAuthorityClass,
    ReasoningBackend,
)
from msk_formal_discovery.backend.lean4_adapter import Lean4Adapter
from msk_formal_discovery.backend.planned import PLANNED_BACKENDS
from msk_formal_discovery.backend.rocq_adapter import RocqAdapter
from msk_formal_discovery.backend.z3_adapter import Z3Adapter
from msk_formal_discovery.core.exceptions import AuthorityViolationError


class BackendRegistry:
    """Central registry of formal reasoning backend adapters."""

    def __init__(self, schema_path: Optional[Path] = None) -> None:
        self._backends: Dict[str, ReasoningBackend] = {}
        self._planned_descriptors: Dict[str, dict] = {}
        self._schema_path = schema_path

    def register(self, backend: ReasoningBackend) -> None:
        """Register a backend adapter, validating its descriptor and authority."""
        descriptor = backend.to_descriptor()
        if self._schema_path and self._schema_path.exists():
            schema_data = json.loads(self._schema_path.read_text(encoding="utf-8"))
            jsonschema.validate(descriptor, schema_data)

        # Enforce authority check
        if (
            backend.backend_family == BackendFamily.SMT_SOLVER
            and backend.logical_authority_class == LogicalAuthorityClass.DEDUCTIVE_PROOF_AUTHORITY
        ):
            raise AuthorityViolationError("SMT_SOLVER cannot claim DEDUCTIVE_PROOF_AUTHORITY")

        if (
            backend.backend_family == BackendFamily.MODEL_CHECKER
            and backend.logical_authority_class == LogicalAuthorityClass.DEDUCTIVE_PROOF_AUTHORITY
        ):
            raise AuthorityViolationError("MODEL_CHECKER cannot claim DEDUCTIVE_PROOF_AUTHORITY")

        self._backends[backend.backend_id] = backend

    def register_descriptor(self, descriptor: dict) -> None:
        """Register a planned backend descriptor."""
        if self._schema_path and self._schema_path.exists():
            schema_data = json.loads(self._schema_path.read_text(encoding="utf-8"))
            jsonschema.validate(descriptor, schema_data)
        self._planned_descriptors[descriptor["backend_id"]] = descriptor

    def get(self, backend_id: str) -> Optional[ReasoningBackend]:
        return self._backends.get(backend_id)

    def get_descriptor(self, backend_id: str) -> Optional[dict]:
        if backend_id in self._backends:
            return self._backends[backend_id].to_descriptor()
        return self._planned_descriptors.get(backend_id)

    def list_all(self) -> List[ReasoningBackend]:
        return list(self._backends.values())

    def list_by_family(self, family: BackendFamily) -> List[ReasoningBackend]:
        return [b for b in self._backends.values() if b.backend_family == family]

    def all_descriptors(self) -> Dict[str, dict]:
        res = {b_id: b.to_descriptor() for b_id, b in self._backends.items()}
        res.update(self._planned_descriptors)
        return res

    def __contains__(self, backend_id: str) -> bool:
        return backend_id in self._backends or backend_id in self._planned_descriptors

    @classmethod
    def create_default(cls, schema_path: Optional[Path] = None) -> BackendRegistry:
        """Construct a registry with active adapters and planned backend descriptors."""
        reg = cls(schema_path=schema_path)
        reg.register(Z3Adapter())
        reg.register(Lean4Adapter())
        reg.register(RocqAdapter())
        for desc in PLANNED_BACKENDS:
            reg.register_descriptor(desc)
        return reg
