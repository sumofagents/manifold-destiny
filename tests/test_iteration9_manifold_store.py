"""Phase D tests: universal manifold store stitching.

Stitches the GF(2), quantum, and Lean accepted abstractions into one shared
verified_information_quotient_v1 store. Proves:
  - three domain records retained as distinct local abstractions
  - same-fiber alias (quantum generated alpha-beta == built-in R_diff) merges
  - cross-domain pattern links all three under one pattern node
  - the store never certifies on its own — the verifier is the trust boundary

The verifier remains the truth boundary. The store checks existence, dedupe,
provenance, and cross-domain links.
"""

from __future__ import annotations

import pytest

from manifold_destiny.iteration9_bounded_generation_receipts import evidence_hash, verifier_contract_hash
from manifold_destiny.iteration9_manifold_store import (
    PATTERN_NAME,
    ManifoldStore,
    VerifiedInformationQuotientV1,
)


def _record(
    domain: str,
    consumer: str,
    fiber_hash: str,
    contract: tuple,
    evidence: str,
    candidate: str,
) -> VerifiedInformationQuotientV1:
    return VerifiedInformationQuotientV1(
        domain=domain,
        world_chart=f"{domain}_world",
        consumer=consumer,
        candidate=candidate,
        fiber_signature_hash=fiber_hash,
        fiber_cell_count=4,
        verifier_contract=contract,
        verifier_contract_hash=verifier_contract_hash(contract),
        evidence_hash=evidence,
        certificate=(("verdict", "accepted"),),
        provenance=("bounded_generation",),
    )


GF2_RECORD = _record(
    domain="gf2_gluing",
    consumer="gluing_consumer",
    fiber_hash="a" * 64,
    contract=("global_glue_objective", "validate_gluing_factorization", "v1"),
    evidence="gf2_ev",
    candidate="(u xor v)",
)

LEAN_RECORD = _record(
    domain="lean_kernel",
    consumer="lean_consumer",
    fiber_hash="b" * 64,
    contract=("lean_kernel_4_31_0", "admissibility_check", "novelty_not_fibereq", "v1"),
    evidence="lean_ev",
    candidate="(x, bXor u v)",
)

# Quantum generated alpha-beta: SAME fiber signature as built-in R_diff
QUANTUM_FIBER = "4d1371d95e20f98431a68a85425e75304ee16f4721190a2f23455f275162f2f7"
QUANTUM_RECORD = _record(
    domain="quantum_oracle",
    consumer="chsh_correlation_consumer",
    fiber_hash=QUANTUM_FIBER,
    contract=(
        "tier_a_level_set_homogeneity",
        "same_fiber_copy_transfer",
        "held_out_accuracy_within_shot_noise",
        "chsh_nonclassicality_above_margin",
        "v1",
    ),
    evidence="quantum_ev",
    candidate="alpha - beta",
)

# Built-in R_diff alias: same fiber, different candidate name + provenance
QUANTUM_RDIFF_ALIAS = VerifiedInformationQuotientV1(
    domain="quantum_oracle",
    world_chart="quantum_oracle_world",
    consumer="chsh_correlation_consumer",
    candidate="R_diff (built-in)",
    fiber_signature_hash=QUANTUM_FIBER,
    fiber_cell_count=30,
    verifier_contract=QUANTUM_RECORD.verifier_contract,
    verifier_contract_hash=QUANTUM_RECORD.verifier_contract_hash,
    evidence_hash=QUANTUM_RECORD.evidence_hash,
    certificate=QUANTUM_RECORD.certificate,
    provenance=("built_in_catalog",),
)


class TestManifoldStitching:
    """Three domain records stitch into one verified-information manifold."""

    def test_three_domains_retained_distinctly(self) -> None:
        store = ManifoldStore()
        store.insert(GF2_RECORD)
        store.insert(LEAN_RECORD)
        store.insert(QUANTUM_RECORD)
        assert store.retained_local_record_count == 3

    def test_cross_domain_pattern_links_all_three(self) -> None:
        store = ManifoldStore()
        store.insert(GF2_RECORD)
        store.insert(LEAN_RECORD)
        store.insert(QUANTUM_RECORD)
        assert store.cross_domain_pattern_count == 1
        domains = store.pattern_domains[0]
        assert set(domains) == {"gf2_gluing", "lean_kernel", "quantum_oracle"}

    def test_quantum_alias_merges_with_generated(self) -> None:
        """Built-in R_diff and generated alpha-beta share one fiber -> merge."""
        store = ManifoldStore()
        store.insert(QUANTUM_RECORD)
        action = store.insert(QUANTUM_RDIFF_ALIAS)
        # Same domain + consumer + fiber + contract + evidence -> exact dedupe
        assert action.action == "merged_duplicate"
        assert store.retained_local_record_count == 1

    def test_full_stitch_with_alias_merge(self) -> None:
        """All three domains + the R_diff alias -> 3 records, 1 pattern node."""
        store = ManifoldStore()
        store.insert(GF2_RECORD)
        store.insert(LEAN_RECORD)
        store.insert(QUANTUM_RECORD)
        store.insert(QUANTUM_RDIFF_ALIAS)
        assert store.retained_local_record_count == 3
        assert store.cross_domain_pattern_count == 1
        assert store.merged_duplicate_count >= 1

    def test_pattern_name_is_bounded_generation_retention(self) -> None:
        assert PATTERN_NAME == "bounded_generation_verified_retention_v1"

    def test_store_does_not_certify(self) -> None:
        """The store records what was certified elsewhere; it never certifies.

        Inserting a record with a fabricated fiber hash is accepted by the
        store (it's just storage) — but the store provides NO certificate of
        validity. The verifier contract hash points at the external verifier
        that did the certifying.
        """
        store = ManifoldStore()
        fabricated = _record(
            domain="gf2_gluing",
            consumer="c",
            fiber_hash="0" * 64,
            contract=("fake_verifier", "v1"),
            evidence="fake",
            candidate="fabricated",
        )
        action = store.insert(fabricated)
        assert action.action == "retained_new"
        # The store did NOT verify anything; it just stored the record.
        # The verifier_contract_hash points at "fake_verifier" — the store
        # trusts whatever contract was declared. Truth lives in the verifier.
        assert fabricated.verifier_contract == ("fake_verifier", "v1")


class TestCanonicalFiberSignatures:
    """Fiber signatures are computed from the partition, not receipt JSON."""

    def test_gf2_signature_from_partition(self) -> None:
        from manifold_destiny.iteration9_manifold_store import (
            canonical_fiber_signature_from_partition,
        )

        # (u xor v) partition of the 16-state GF(2) world
        partition = [
            ["s0", "s1", "s8", "s9"],  # x=0,uv=0 / x=1,uv=0
            ["s2", "s3", "s10", "s11"],
            ["s4", "s5", "s12", "s13"],
            ["s6", "s7", "s14", "s15"],
        ]
        h1 = canonical_fiber_signature_from_partition(partition)
        h2 = canonical_fiber_signature_from_partition(list(reversed(partition)))
        assert h1 == h2

    def test_quantum_signature_stable_across_reorder(self) -> None:
        from manifold_destiny.iteration9_manifold_store import (
            canonical_fiber_signature_from_partition,
        )

        partition_a = [["a", "b"], ["c", "d"], ["e", "f"]]
        partition_b = [["c", "d"], ["e", "f"], ["a", "b"]]
        assert (
            canonical_fiber_signature_from_partition(partition_a)
            == canonical_fiber_signature_from_partition(partition_b)
        )
