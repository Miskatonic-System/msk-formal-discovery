"""Representation Transform Receipt for WO-MATH-FORMAL-DISCOVERY-01C."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import jsonschema

from msk_formal_discovery.core.exceptions import ReceiptValidationError, AuthorityViolationError

RECEIPT_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "schemas" / "representation-transform-receipt.v0.1.schema.json"
)


@dataclass
class RepresentationTransformReceipt:
    """Attested receipt certifying semantic equivalence between canonical and transformed representation."""
    receipt_id: str
    family_id: str
    stratum: str
    source_expression: str
    transformed_expression: str
    source_expression_digest: str
    transformed_expression_digest: str
    variable_bijection: Dict[str, str]
    transform_implementation_digest: str
    smt_certificate_ref: str
    smt_certificate_digest: str
    smt_verdict: str = "UNSAT_REFUTED"
    semantic_equivalence_certified: bool = True
    authority: str = "NONE"
    schema_version: str = "miskatonic.representation-transform-receipt.v0.1"
    receipt_digest: str = ""

    def __post_init__(self) -> None:
        if not self.receipt_digest:
            self.receipt_digest = self.compute_digest()

    def compute_digest(self) -> str:
        d = {k: v for k, v in self.to_dict().items() if k != "receipt_digest"}
        serialized = json.dumps(d, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "family_id": self.family_id,
            "stratum": self.stratum,
            "source_expression": self.source_expression,
            "transformed_expression": self.transformed_expression,
            "source_expression_digest": self.source_expression_digest,
            "transformed_expression_digest": self.transformed_expression_digest,
            "variable_bijection": dict(self.variable_bijection),
            "transform_implementation_digest": self.transform_implementation_digest,
            "smt_certificate_ref": self.smt_certificate_ref,
            "smt_certificate_digest": self.smt_certificate_digest,
            "smt_verdict": self.smt_verdict,
            "semantic_equivalence_certified": self.semantic_equivalence_certified,
            "authority": self.authority,
            "receipt_digest": self.receipt_digest,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RepresentationTransformReceipt:
        return cls(
            schema_version=data.get("schema_version", "miskatonic.representation-transform-receipt.v0.1"),
            receipt_id=data["receipt_id"],
            family_id=data["family_id"],
            stratum=data["stratum"],
            source_expression=data["source_expression"],
            transformed_expression=data["transformed_expression"],
            source_expression_digest=data["source_expression_digest"],
            transformed_expression_digest=data["transformed_expression_digest"],
            variable_bijection=dict(data.get("variable_bijection", {})),
            transform_implementation_digest=data["transform_implementation_digest"],
            smt_certificate_ref=data["smt_certificate_ref"],
            smt_certificate_digest=data["smt_certificate_digest"],
            smt_verdict=data.get("smt_verdict", "UNSAT_REFUTED"),
            semantic_equivalence_certified=data.get("semantic_equivalence_certified", True),
            authority=data.get("authority", "NONE"),
            receipt_digest=data.get("receipt_digest", ""),
        )

    def validate(self) -> None:
        if self.authority != "NONE":
            raise AuthorityViolationError(f"AUTHORITY_VIOLATION: authority must be 'NONE', got '{self.authority}'")
        if not self.semantic_equivalence_certified:
            raise ReceiptValidationError("SEMANTIC_EQUIVALENCE_FAILED: semantic_equivalence_certified must be true")
        if self.smt_verdict != "UNSAT_REFUTED":
            raise ReceiptValidationError(f"INVALID_SMT_VERDICT: expected 'UNSAT_REFUTED', got '{self.smt_verdict}'")

        if RECEIPT_SCHEMA_PATH.is_file():
            schema_data = json.loads(RECEIPT_SCHEMA_PATH.read_text(encoding="utf-8"))
            try:
                jsonschema.validate(self.to_dict(), schema_data)
            except jsonschema.exceptions.ValidationError as e:
                raise ReceiptValidationError(f"REPRESENTATION_TRANSFORM_RECEIPT_SCHEMA_ERROR: {e.message}") from e

        computed = self.compute_digest()
        if self.receipt_digest != computed:
            raise ReceiptValidationError(
                f"RECEIPT_DIGEST_MISMATCH: Computed {computed} != {self.receipt_digest}"
            )
