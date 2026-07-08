"""Phase A unit tests: bounded grammar, receipt schemas, manifold store.

These are the substrate tests for the bounded-generation hardening. They
verify the shared machinery before any domain logic is layered on top:

  * Grammar enumeration is deterministic and bounded by depth.
  * Commutative operators canonicalize (u xor v == v xor u).
  * Missing operators genuinely shrink the enumerable set.
  * Receipts round-trip and hash stably (no path/time nondeterminism).
  * The manifold store dedupes by fiber, merges aliases, links patterns,
    and logs contract migrations without collapsing cross-domain records.
"""

from __future__ import annotations

import hashlib

import pytest

from manifold_destiny.iteration9_bounded_grammar import (
    SCHEMA_VERSION as GRAMMAR_SCHEMA,
    Grammar,
    atom,
    canonical_key,
    depth,
    expr_digest,
    expr_to_str,
    node,
)
from manifold_destiny.iteration9_bounded_generation_receipts import (
    SCHEMA_VERSION,
    BoundedGenerationReceiptV1,
    ControlResult,
    FiberSignature,
    GeneratedCandidate,
    GrammarConfig,
    evidence_hash,
    parse_receipt,
    verifier_contract_hash,
)
from manifold_destiny.iteration9_manifold_store import (
    PATTERN_NAME,
    PATTERN_SIGNATURE_HASH,
    ManifoldStore,
    VerifiedInformationQuotientV1,
    canonical_fiber_signature_from_partition,
)


# ---------------------------------------------------------------------------
# Grammar
# ---------------------------------------------------------------------------


class TestGrammarEnumeration:
    """Grammar enumeration is deterministic, bounded, and canonical."""

    def test_atoms_only_at_depth_zero(self) -> None:
        grammar = Grammar(atoms=("u", "v", "w"), ops=("xor",), max_depth=0)
        exprs = grammar.enumerate()
        assert len(exprs) == 3
        assert all(e.op == "atom" for e in exprs)
        assert {e.args[0] for e in exprs} == {"u", "v", "w"}

    def test_depth_one_adds_pairwise_xor(self) -> None:
        grammar = Grammar(atoms=("u", "v", "w"), ops=("xor",), max_depth=1)
        exprs = grammar.enumerate()
        # 3 atoms + 3 canonical xor pairs (u^v, u^w, v^w). Self-xor (u^u) is
        # canonicalized away? No — u^u is a valid distinct expr; but it has the
        # same canonical key only if we dedupe identical operands. We do NOT
        # collapse u^u (it is a distinct expression). Let's count:
        # atoms: 3. xor pairs: 3*3=9 raw, deduped by canonical key.
        # canonical keys: [u u],[u v],[u w],[v v],[v w],[w w] = 6 distinct.
        # total: 3 + 6 = 9.
        assert len(exprs) == 9

    def test_commutative_canonicalization(self) -> None:
        """u xor v and v xor u share one canonical key."""
        left = node("xor", atom("u"), atom("v"))
        right = node("xor", atom("v"), atom("u"))
        assert canonical_key(left) == canonical_key(right)
        assert expr_to_str(left) == expr_to_str(right)

    def test_noncommutative_preserves_order(self) -> None:
        """sub is not commutative: alpha-beta != beta-alpha."""
        left = node("sub", atom("alpha"), atom("beta"))
        right = node("sub", atom("beta"), atom("alpha"))
        assert canonical_key(left) != canonical_key(right)

    def test_enumeration_is_deterministic(self) -> None:
        grammar = Grammar(atoms=("u", "v", "w"), ops=("xor",), max_depth=2)
        first = grammar.enumerate()
        second = grammar.enumerate()
        assert [expr_to_str(e) for e in first] == [expr_to_str(e) for e in second]

    def test_enumeration_sorted_by_depth_then_key(self) -> None:
        grammar = Grammar(atoms=("u", "v"), ops=("xor",), max_depth=2)
        exprs = grammar.enumerate()
        depths = [depth(e) for e in exprs]
        assert depths == sorted(depths)
        # within each depth, keys are sorted
        for d in set(depths):
            level_keys = [
                canonical_key(e) for e in exprs if depth(e) == d
            ]
            assert level_keys == sorted(level_keys)

    def test_missing_operator_shrinks_set(self) -> None:
        """Grammar without xor cannot construct xor expressions."""
        with_xor = Grammar(atoms=("u", "v"), ops=("xor",), max_depth=1)
        without_xor = Grammar(atoms=("u", "v"), ops=(), max_depth=1)
        assert len(with_xor.enumerate()) > len(without_xor.enumerate())
        # without xor, only atoms are enumerable
        assert all(e.op == "atom" for e in without_xor.enumerate())

    def test_grammar_signature_is_stable(self) -> None:
        g1 = Grammar(atoms=("u", "v"), ops=("xor",), max_depth=2)
        g2 = Grammar(atoms=("u", "v"), ops=("xor",), max_depth=2)
        assert g1.signature == g2.signature

    def test_grammar_signature_changes_on_config_change(self) -> None:
        g1 = Grammar(atoms=("u", "v"), ops=("xor",), max_depth=2)
        g2 = Grammar(atoms=("u", "v"), ops=("xor",), max_depth=3)
        g3 = Grammar(atoms=("u", "v", "w"), ops=("xor",), max_depth=2)
        assert g1.signature != g2.signature
        assert g1.signature != g3.signature

    def test_has_op(self) -> None:
        grammar = Grammar(atoms=("u",), ops=("xor",), max_depth=1)
        assert grammar.has_op("xor")
        assert not grammar.has_op("sub")

    def test_expr_digest_stable(self) -> None:
        e = node("xor", atom("u"), atom("v"))
        assert expr_digest(e) == expr_digest(e)
        assert len(expr_digest(e)) == 64

    def test_mixed_depth_enumerated_at_depth_2(self) -> None:
        """Regression (review): mixed-depth expressions must be present.

        (u xor (v xor w)) has depth 2 with one child at depth 0 (u) and one
        at depth 1 (v xor w). The old enumerate() only composed level[-1] x
        level[-1] and missed this entire class.
        """
        grammar = Grammar(atoms=("u", "v", "w"), ops=("xor",), max_depth=2)
        exprs = grammar.enumerate()
        rendered = {expr_to_str(e) for e in exprs}
        # left-shallow: u xor (v xor w) -- canonical form after sort
        assert "(u xor (v xor w))" in rendered or "((v xor w) xor u)" in rendered, (
            f"mixed-depth not found in {rendered}"
        )
        # right-shallow: (u xor v) xor w -- must also appear
        assert "(w xor (u xor v))" in rendered or "((u xor v) xor w)" in rendered, (
            f"mixed-depth not found in {rendered}"
        )

    def test_triple_xor_enumerated_at_depth_3(self) -> None:
        """u xor v xor w (depth 3) must be enumerable for m111."""
        grammar = Grammar(atoms=("u", "v", "w"), ops=("xor",), max_depth=3)
        exprs = grammar.enumerate()
        # there must be at least one depth-3 expression
        assert any(depth(e) == 3 for e in exprs), "no depth-3 expression enumerated"

    def test_unary_op_enumerated(self) -> None:
        """Unary ops (arity 1) like 'abs' must enumerate correctly."""
        grammar = Grammar(
            atoms=("alpha",),
            ops=("abs",),
            max_depth=1,
            arities=(("abs", 1),),
        )
        exprs = grammar.enumerate()
        # alpha + (abs alpha)
        assert len(exprs) == 2
        rendered = {expr_to_str(e) for e in exprs}
        assert "(abs alpha)" in rendered

    def test_expr_to_str_renders_infix(self) -> None:
        """Receipts need infix notation: (u xor v), not postfix (u v xor)."""
        e = node("xor", atom("u"), atom("v"))
        assert expr_to_str(e) == "(u xor v)"
        s = node("sub", atom("alpha"), atom("beta"))
        assert expr_to_str(s) == "(alpha sub beta)"

    def test_invalid_grammar_rejected(self) -> None:
        with pytest.raises(ValueError):
            Grammar(atoms=(), ops=("xor",), max_depth=1)
        with pytest.raises(ValueError):
            Grammar(atoms=("u",), ops=("xor",), max_depth=-1)

    def test_schema_version_exported(self) -> None:
        assert GRAMMAR_SCHEMA == "manifold-destiny-bounded-grammar-v1"


# ---------------------------------------------------------------------------
# Receipt schemas
# ---------------------------------------------------------------------------


def _sample_receipt() -> BoundedGenerationReceiptV1:
    grammar = GrammarConfig(
        atoms=("u", "v", "w"),
        ops=("xor",),
        max_depth=2,
        signature="a" * 64,
    )
    generated = GeneratedCandidate(
        expression="(u xor v)",
        registered_name="gen_u_xor_v",
        canonical_key="[xor @u @v]",
        digest="b" * 64,
    )
    fiber = FiberSignature(
        hash="c" * 64,
        cell_count=4,
        canonical_partition="cell0|cell1",
    )
    controls = (
        ControlResult("missing_operator", "not_enumerable", "grammar lacks xor"),
        ControlResult("fixed_catalog_only", "rejected", "all Q_0 rejected"),
        ControlResult("falsifier", "rejected", "wrong orientation"),
    )
    return BoundedGenerationReceiptV1(
        schema_version=SCHEMA_VERSION,
        domain="gf2_gluing",
        grammar=grammar,
        fixed_catalog=("0", "u", "v", "w"),
        generated=generated,
        verifier_contract=("global_glue_objective", "v1"),
        verifier_contract_hash=verifier_contract_hash(
            ("global_glue_objective", "v1")
        ),
        evidence_hash=evidence_hash({"orientation": "m100"}),
        fiber_signature=fiber,
        certificate={"g_verdict": "accepted", "composite_verdict": "valid"},
        controls=controls,
        verdict="PASS",
    )


class TestReceipts:
    """Receipts round-trip and hash deterministically."""

    def test_round_trip(self) -> None:
        receipt = _sample_receipt()
        blob = receipt.to_json()
        import json

        parsed = parse_receipt(json.loads(blob))
        assert parsed.domain == receipt.domain
        assert parsed.verdict == receipt.verdict
        assert parsed.fiber_signature.hash == receipt.fiber_signature.hash

    def test_digest_stable(self) -> None:
        receipt = _sample_receipt()
        assert receipt.digest() == receipt.digest()

    def test_digest_changes_on_change(self) -> None:
        receipt = _sample_receipt()
        import dataclasses

        altered = dataclasses.replace(
            receipt, verdict="FAIL"
        )
        assert receipt.digest() != altered.digest()

    def test_no_timestamp_in_json(self) -> None:
        receipt = _sample_receipt()
        blob = receipt.to_json()
        assert "timestamp" not in blob.lower()
        assert "date" not in blob.lower()

    def test_verifier_contract_hash_stable(self) -> None:
        c1 = ("global_glue_objective", "v1")
        c2 = ("global_glue_objective", "v1")
        assert verifier_contract_hash(c1) == verifier_contract_hash(c2)

    def test_evidence_hash_changes_on_input_change(self) -> None:
        h1 = evidence_hash({"orientation": "m100"})
        h2 = evidence_hash({"orientation": "m101"})
        assert h1 != h2

    def test_parse_rejects_bad_schema_version(self) -> None:
        import json

        blob = _sample_receipt().to_json()
        payload = json.loads(blob)
        payload["schema_version"] = "wrong"
        with pytest.raises(ValueError):
            parse_receipt(payload)

    def test_parse_rejects_bad_domain(self) -> None:
        import json

        blob = _sample_receipt().to_json()
        payload = json.loads(blob)
        payload["domain"] = "not_a_domain"
        with pytest.raises(ValueError):
            parse_receipt(payload)


# ---------------------------------------------------------------------------
# Manifold store
# ---------------------------------------------------------------------------


def _make_record(
    domain: str = "gf2_gluing",
    consumer: str = "gluing_consumer",
    fiber_hash: str = "f" * 64,
    contract: tuple = ("global_glue_objective", "v1"),
    evidence: str = "e" * 64,
    candidate: str = "(u xor v)",
    provenance: tuple = ("bounded_generation_probe",),
) -> VerifiedInformationQuotientV1:
    return VerifiedInformationQuotientV1(
        domain=domain,
        world_chart="states(x,u,v,w)",
        consumer=consumer,
        candidate=candidate,
        fiber_signature_hash=fiber_hash,
        fiber_cell_count=4,
        verifier_contract=contract,
        verifier_contract_hash=verifier_contract_hash(contract),
        evidence_hash=evidence,
        certificate=(("g_verdict", "accepted"),),
        provenance=provenance,
    )


class TestManifoldStore:
    """Store dedupes, merges aliases, links patterns, logs migrations."""

    def test_insert_new_record(self) -> None:
        store = ManifoldStore()
        action = store.insert(_make_record())
        assert action.action == "retained_new"
        assert action.record_id is not None
        assert store.retained_local_record_count == 1

    def test_exact_duplicate_merges(self) -> None:
        store = ManifoldStore()
        store.insert(_make_record(provenance=("source_a",)))
        action = store.insert(_make_record(provenance=("source_b",)))
        assert action.action == "merged_duplicate"
        assert store.retained_local_record_count == 1

    def test_same_fiber_alias_merges(self) -> None:
        """Same domain+consumer+fiber but different candidate name -> alias."""
        store = ManifoldStore()
        store.insert(_make_record(candidate="(u xor v)"))
        action = store.insert(
            _make_record(candidate="gen_alias_u_xor_v", provenance=("alias",))
        )
        # same fiber, same contract, same evidence, different candidate label
        # -> exact dedupe (the candidate label is not in the dedupe key)
        assert action.action == "merged_duplicate"

    def test_contract_change_creates_migration(self) -> None:
        store = ManifoldStore()
        store.insert(_make_record(contract=("global_glue_objective", "v1")))
        action = store.insert(
            _make_record(contract=("global_glue_objective", "v2"))
        )
        # different contract -> different dedupe key -> new record + migration
        assert action.action in ("retained_new", "merged_alias")
        assert len(store.migrations) >= 1
        assert store.migrations[0].old_contract_hash != store.migrations[0].new_contract_hash

    def test_migration_new_record_id_is_lookupable(self) -> None:
        """Regression (review): migration.new_record_id must exist.

        The old code called _new_id() twice, so the migration log pointed at an
        id that was never stored. The inserted record got a different id.
        """
        store = ManifoldStore()
        store.insert(_make_record(contract=("global_glue_objective", "v1")))
        store.insert(_make_record(contract=("global_glue_objective", "v2")))
        assert len(store.migrations) >= 1
        mig = store.migrations[0]
        # the new_record_id must be a real id in the store
        assert mig.new_record_id in [
            rid for rid in store._by_id  # noqa: SLF001 — test-only introspection
        ]

    def test_contract_and_evidence_change_is_not_migration(self) -> None:
        """Regression (review): contract+evidence both changed = new record.

        Migration is ONLY logged when the contract changed but evidence is the
        same. If evidence also changed, it is a new independent record, not a
        version upgrade of the old one.
        """
        store = ManifoldStore()
        store.insert(
            _make_record(contract=("v", "1"), evidence="e" * 64)
        )
        store.insert(
            _make_record(contract=("v", "2"), evidence="d" * 64)
        )
        assert len(store.migrations) == 0
        assert store.retained_local_record_count == 2

    def test_exact_duplicate_merges_and_counts(self) -> None:
        """Regression (review): exact dedupe must increment the counter."""
        store = ManifoldStore()
        store.insert(_make_record(provenance=("source_a",)))
        store.insert(_make_record(provenance=("source_b",)))
        assert store.retained_local_record_count == 1
        assert store.merged_duplicate_count >= 1

    def test_evidence_change_forces_new_record(self) -> None:
        store = ManifoldStore()
        store.insert(_make_record(evidence="e" * 64))
        store.insert(_make_record(evidence="d" * 64))
        assert store.retained_local_record_count == 2

    def test_cross_domain_pattern_links(self) -> None:
        store = ManifoldStore()
        store.insert(_make_record(domain="gf2_gluing", fiber_hash="a" * 64))
        store.insert(_make_record(domain="lean_kernel", fiber_hash="b" * 64))
        store.insert(_make_record(domain="quantum_oracle", fiber_hash="c" * 64))
        assert store.retained_local_record_count == 3
        assert store.cross_domain_pattern_count == 1
        domains = store.pattern_domains[0]
        assert set(domains) == {"gf2_gluing", "lean_kernel", "quantum_oracle"}

    def test_pattern_constants_stable(self) -> None:
        assert PATTERN_NAME == "bounded_generation_verified_retention_v1"
        assert len(PATTERN_SIGNATURE_HASH) == 64

    def test_fiber_signature_from_partition(self) -> None:
        partition = [{"a", "b"}, {"c", "d"}]
        h1 = canonical_fiber_signature_from_partition(partition)
        # reorder cells -> same hash
        h2 = canonical_fiber_signature_from_partition([{"c", "d"}, {"a", "b"}])
        assert h1 == h2
        # different partition -> different hash
        h3 = canonical_fiber_signature_from_partition([{"a", "c"}, {"b", "d"}])
        assert h1 != h3
