"""Iteration 9 — verified-information quotient store.

A tiny in-memory store of verified abstractions. Each accepted bounded-
generation result is normalized into a ``VerifiedInformationQuotientV1`` record.
The store dedupes by fiber signature within a domain and links cross-domain
records under a shared pattern node without collapsing them.

The verifier is the truth boundary. This store checks existence, dedupe,
provenance, and cross-domain links. It never certifies on its own.

Keyed by: domain + consumer + fiber_signature_hash + verifier_contract_hash +
evidence_hash. A contract version change or evidence change forces a new record
(not a silent merge).
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = "verified_information_quotient_v1"

# The shared cross-domain pattern name for all bounded-generation accepted
# abstractions. Records from different domains with the same pattern signature
# link under one pattern node; their local records are never collapsed.
PATTERN_NAME = "bounded_generation_verified_retention_v1"

# Stable pattern signature: hashes the schema version + pattern name + the
# fixed retention contract (retain only V-accepted). It does NOT depend on the
# record content, so all records that share the same retention contract share
# the same pattern node.
_PATTERN_BLOB = (
    f'{{"schema":"{SCHEMA_VERSION}","pattern":"{PATTERN_NAME}",'
    '"contract":"retain_only_verifier_accepted"}}\n'
)
PATTERN_SIGNATURE_HASH = hashlib.sha256(_PATTERN_BLOB.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class VerifiedInformationQuotientV1:
    """One verified abstraction in the shared manifold."""

    domain: str
    world_chart: str
    consumer: str
    candidate: str
    fiber_signature_hash: str
    fiber_cell_count: int
    verifier_contract: Tuple[str, ...]
    verifier_contract_hash: str
    evidence_hash: str
    certificate: Tuple[Tuple[str, str], ...]  # ((key, value), ...) frozen
    provenance: Tuple[str, ...] = ()
    pattern_name: str = PATTERN_NAME
    pattern_signature_hash: str = PATTERN_SIGNATURE_HASH
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"schema_version mismatch: expected {SCHEMA_VERSION!r}, "
                f"got {self.schema_version!r}"
            )
        if not self.fiber_signature_hash:
            raise ValueError("fiber_signature_hash must be non-empty")
        if not self.verifier_contract_hash:
            raise ValueError("verifier_contract_hash must be non-empty")
        if not self.evidence_hash:
            raise ValueError("evidence_hash must be non-empty")

    def local_key(self) -> Tuple[str, ...]:
        """Dedupe key: same domain + consumer + fiber + contract + evidence.

        Two records with the same key are the SAME abstraction (merge
        provenance). A contract or evidence change changes the key, forcing a
        new record.
        """
        return (
            self.domain,
            self.consumer,
            self.fiber_signature_hash,
            self.verifier_contract_hash,
            self.evidence_hash,
        )


@dataclass(frozen=True)
class ContractMigration:
    """A logged contract version change (old record superseded by new)."""

    old_contract_hash: str
    new_contract_hash: str
    fiber_signature_hash: str
    domain: str
    old_record_id: str
    new_record_id: str


@dataclass
class InsertAction:
    """Result of inserting a record into the store."""

    action: str  # "retained_new" | "merged_duplicate" | "merged_alias"
    record_id: Optional[str] = None
    merged_into: Optional[str] = None
    aliases_added: Tuple[str, ...] = ()


class ManifoldStore:
    """In-memory store of verified-information quotient records."""

    def __init__(self) -> None:
        # local_key -> record (one canonical record per dedupe key)
        self._records: Dict[Tuple[str, ...], VerifiedInformationQuotientV1] = {}
        # record_id -> record (human-readable id for cross-referencing)
        self._by_id: Dict[str, VerifiedInformationQuotientV1] = {}
        # fiber_signature_hash -> list of record ids (for alias merge within domain)
        self._by_fiber: Dict[str, List[str]] = {}
        # pattern_signature_hash -> set of record ids
        self._by_pattern: Dict[str, set] = {}
        # migration log
        self._migrations: List[ContractMigration] = []
        # exact-dedupe counter (step-1 merges)
        self._exact_merge_count = 0
        self._next_id = 0

    def _new_id(self, domain: str) -> str:
        self._next_id += 1
        return f"{domain}_{self._next_id:04d}"

    def insert(
        self, record: VerifiedInformationQuotientV1
    ) -> InsertAction:
        """Insert a record, deduping by local key or fiber signature."""
        key = record.local_key()

        # 1. Exact dedupe: same domain+consumer+fiber+contract+evidence.
        if key in self._records:
            existing = self._records[key]
            existing_id = self._id_for(existing)
            # merge provenance
            merged = VerifiedInformationQuotientV1(
                domain=existing.domain,
                world_chart=existing.world_chart,
                consumer=existing.consumer,
                candidate=existing.candidate,
                fiber_signature_hash=existing.fiber_signature_hash,
                fiber_cell_count=existing.fiber_cell_count,
                verifier_contract=existing.verifier_contract,
                verifier_contract_hash=existing.verifier_contract_hash,
                evidence_hash=existing.evidence_hash,
                certificate=existing.certificate,
                provenance=tuple(
                    sorted(set(existing.provenance) | set(record.provenance))
                ),
                pattern_name=existing.pattern_name,
                pattern_signature_hash=existing.pattern_signature_hash,
            )
            self._records[key] = merged
            self._by_id[existing_id] = merged
            self._exact_merge_count += 1
            return InsertAction(
                action="merged_duplicate",
                merged_into=existing_id,
            )

        # 2. Fiber-signature alias: same domain + consumer + fiber signature but
        #    different contract or evidence -> merge provenance + alias, keep
        #    both records (they represent the same abstraction under different
        #    contracts/evidence).
        #
        #    Contract migration is logged ONLY when the evidence is the same:
        #    a contract bump on unchanged evidence is a genuine version upgrade.
        #    A contract change WITH an evidence change is a new independent
        #    record (not a migration of the old one).
        alias_ids: List[str] = []
        # Allocate the new record id ONCE so migration logs point at the real id.
        new_id = self._new_id(record.domain)
        for rid, existing in self._by_id.items():
            if (
                existing.domain == record.domain
                and existing.consumer == record.consumer
                and existing.fiber_signature_hash == record.fiber_signature_hash
                and (existing.verifier_contract_hash, existing.evidence_hash)
                != (record.verifier_contract_hash, record.evidence_hash)
            ):
                alias_ids.append(rid)
                # Migration: same fiber + same evidence, ONLY contract changed.
                if (
                    existing.verifier_contract_hash != record.verifier_contract_hash
                    and existing.evidence_hash == record.evidence_hash
                ):
                    self._migrations.append(
                        ContractMigration(
                            old_contract_hash=existing.verifier_contract_hash,
                            new_contract_hash=record.verifier_contract_hash,
                            fiber_signature_hash=record.fiber_signature_hash,
                            domain=record.domain,
                            old_record_id=rid,
                            new_record_id=new_id,
                        )
                    )

        # 3. Retain the new record.
        self._records[key] = record
        self._by_id[new_id] = record
        self._by_fiber.setdefault(
            record.fiber_signature_hash, []
        ).append(new_id)
        self._by_pattern.setdefault(
            record.pattern_signature_hash, set()
        ).add(new_id)

        if alias_ids:
            return InsertAction(
                action="merged_alias",
                record_id=new_id,
                aliases_added=tuple(sorted(alias_ids)),
            )
        return InsertAction(action="retained_new", record_id=new_id)

    def _id_for(self, record: VerifiedInformationQuotientV1) -> str:
        for rid, r in self._by_id.items():
            if r is record:
                return rid
        return ""

    @property
    def retained_local_record_count(self) -> int:
        return len(self._records)

    @property
    def merged_duplicate_count(self) -> int:
        """Exact-dedupe merges (same fiber + contract + evidence) + alias merges."""
        alias_count = 0
        for fiber, ids in self._by_fiber.items():
            if len(ids) > 1:
                alias_count += len(ids) - 1
        return self._exact_merge_count + alias_count

    @property
    def cross_domain_pattern_count(self) -> int:
        """Pattern nodes that link records from more than one domain."""
        count = 0
        for pattern_hash, ids in self._by_pattern.items():
            domains = {self._by_id[i].domain for i in ids if i in self._by_id}
            if len(domains) > 1:
                count += 1
        return count

    @property
    def pattern_domains(self) -> List[List[str]]:
        """List of domain-sets per cross-domain pattern node."""
        result: List[List[str]] = []
        for pattern_hash, ids in self._by_pattern.items():
            domains = sorted({self._by_id[i].domain for i in ids if i in self._by_id})
            if len(domains) > 1:
                result.append(domains)
        return result

    @property
    def migrations(self) -> Tuple[ContractMigration, ...]:
        return tuple(self._migrations)


def canonical_fiber_signature_from_partition(
    partition: Any,
) -> str:
    """Compute a stable fiber-signature hash from a partition structure.

    partition: an iterable of cells, each cell an iterable of state handles
    (strings). We sort within each cell and sort cells by their smallest
    member, then hash the canonical form.
    """
    cells_sorted: List[frozenset] = []
    for cell in partition:
        members = frozenset(str(h) for h in cell)
        cells_sorted.append(members)
    # canonical cell order: by smallest member
    cells_sorted.sort(key=lambda c: tuple(sorted(c)))
    canonical = " | ".join(
        " ".join(sorted(c)) for c in cells_sorted
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "SCHEMA_VERSION",
    "PATTERN_NAME",
    "PATTERN_SIGNATURE_HASH",
    "VerifiedInformationQuotientV1",
    "ContractMigration",
    "InsertAction",
    "ManifoldStore",
    "canonical_fiber_signature_from_partition",
]
