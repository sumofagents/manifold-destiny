"""Iteration 9 — bounded-generation receipt schemas and hash helpers.

One shared receipt envelope with per-domain certificate payloads. Receipts are
emitted by the receipt-generation CLI and round-trip validated in pytest.

Receipts are deterministic: sorted JSON keys, compact separators, no
timestamps, no machine-local paths. A receipt that depends on where the test
ran is not a receipt.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Tuple

SCHEMA_VERSION = "manifold-destiny-bounded-generation-v1"

DOMAINS = ("gf2_gluing", "quantum_oracle", "lean_kernel")


@dataclass(frozen=True)
class GrammarConfig:
    """Snapshot of a grammar for receipt reproducibility."""

    atoms: Tuple[str, ...]
    ops: Tuple[str, ...]
    max_depth: int
    signature: str
    arities: Tuple[Tuple[str, int], ...] = ()


@dataclass(frozen=True)
class GeneratedCandidate:
    """The generated expression that crossed the fixed-catalog ceiling."""

    expression: str
    registered_name: str
    canonical_key: str
    digest: str


@dataclass(frozen=True)
class ControlResult:
    """Verdict for a single control (missing-operator, fixed-catalog-only, falsifier)."""

    name: str
    verdict: str  # "rejected" | "accepted" | "not_enumerable"
    detail: str = ""


@dataclass(frozen=True)
class FiberSignature:
    """Canonical fiber/partition signature of the accepted abstraction."""

    hash: str
    cell_count: int
    canonical_partition: str


@dataclass(frozen=True)
class BoundedGenerationReceiptV1:
    """Shared receipt envelope for all three domains."""

    schema_version: str
    domain: str
    grammar: GrammarConfig
    fixed_catalog: Tuple[str, ...]
    generated: GeneratedCandidate
    verifier_contract: Tuple[str, ...]
    verifier_contract_hash: str
    evidence_hash: str
    fiber_signature: FiberSignature
    certificate: Dict[str, Any]
    controls: Tuple[ControlResult, ...]
    verdict: str  # "PASS" | "FAIL"

    def to_json(self) -> str:
        """Stable canonical JSON: sorted keys, compact separators, trailing newline."""
        payload = _to_serializable(self)
        return json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"

    def digest(self) -> str:
        """SHA-256 over the canonical JSON form."""
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()


def _to_serializable(obj: Any) -> Any:
    """Recursively convert dataclasses/tuples to JSON-serializable structures."""
    if isinstance(obj, tuple):
        return [_to_serializable(x) for x in obj]
    if isinstance(obj, list):
        return [_to_serializable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _to_serializable(v) for k, v in sorted(obj.items())}
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _to_serializable(v) for k, v in asdict(obj).items()}
    return obj


def verifier_contract_hash(contract: Tuple[str, ...]) -> str:
    """Hash a frozen verifier-contract tuple (e.g. ('global_glue_objective', 'v1'))."""
    blob = json.dumps(list(contract), sort_keys=True, separators=(",", ":")) + "\n"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def evidence_hash(inputs: Dict[str, Any]) -> str:
    """Hash over episode/data inputs that anchor reproducibility.

    Pass only stable, serializable inputs (orientation codes, data file
    digests, lean version). Never pass machine-local paths or timestamps.
    """
    blob = json.dumps(
        _to_serializable(inputs), sort_keys=True, separators=(",", ":")
    ) + "\n"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def parse_receipt(payload: Dict[str, Any]) -> BoundedGenerationReceiptV1:
    """Parse a JSON-decoded payload back into a typed receipt.

    Raises ValueError if the payload does not match the schema.
    """
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"schema_version mismatch: expected {SCHEMA_VERSION!r}, "
            f"got {payload.get('schema_version')!r}"
        )
    domain = payload.get("domain")
    if domain not in DOMAINS:
        raise ValueError(f"unknown domain {domain!r}; expected one of {DOMAINS}")

    grammar = GrammarConfig(
        atoms=tuple(payload["grammar"]["atoms"]),
        ops=tuple(payload["grammar"]["ops"]),
        max_depth=int(payload["grammar"]["max_depth"]),
        signature=str(payload["grammar"]["signature"]),
        arities=tuple(
            (str(k), int(v))
            for k, v in payload["grammar"].get("arities", [])
        ),
    )
    generated = GeneratedCandidate(
        expression=str(payload["generated"]["expression"]),
        registered_name=str(payload["generated"]["registered_name"]),
        canonical_key=str(payload["generated"]["canonical_key"]),
        digest=str(payload["generated"]["digest"]),
    )
    fiber = FiberSignature(
        hash=str(payload["fiber_signature"]["hash"]),
        cell_count=int(payload["fiber_signature"]["cell_count"]),
        canonical_partition=str(payload["fiber_signature"]["canonical_partition"]),
    )
    controls = tuple(
        ControlResult(
            name=str(c["name"]),
            verdict=str(c["verdict"]),
            detail=str(c.get("detail", "")),
        )
        for c in payload["controls"]
    )
    return BoundedGenerationReceiptV1(
        schema_version=str(payload["schema_version"]),
        domain=domain,
        grammar=grammar,
        fixed_catalog=tuple(payload["fixed_catalog"]),
        generated=generated,
        verifier_contract=tuple(payload["verifier_contract"]),
        verifier_contract_hash=str(payload["verifier_contract_hash"]),
        evidence_hash=str(payload["evidence_hash"]),
        fiber_signature=fiber,
        certificate=dict(payload["certificate"]),
        controls=controls,
        verdict=str(payload["verdict"]),
    )


__all__ = [
    "SCHEMA_VERSION",
    "DOMAINS",
    "GrammarConfig",
    "GeneratedCandidate",
    "ControlResult",
    "FiberSignature",
    "BoundedGenerationReceiptV1",
    "verifier_contract_hash",
    "evidence_hash",
    "parse_receipt",
]
