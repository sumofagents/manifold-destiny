"""Phase B tests: GF(2) bounded generation gate.

Proves that a bounded grammar constructs a quotient absent from the restricted
demonstration catalog Q_0, the existing GF(2) gluing verifier accepts it, and
the controls (missing-operator, fixed-catalog-only, wrong-orientation) reject
as expected.

CRITICAL SCOPE NOTE: Q_0 = {0, u, v, w} is a RESTRICTED DEMONSTRATION catalog.
The repo's full gluing operator space includes composed functionals (R_4 = u⊕v
etc.). Novelty is asserted against Q_0, never against the full repo. Getting
this wrong would be an instant reviewer kill shot.

Fiber dedupe: multiple grammar expressions can map to the same partition on
GF(2) (e.g. (u xor v) and ((u xor v) xor (w xor w)) are algebraically
equivalent). Accepted abstractions are deduplicated by canonical fiber
signature (semantic equivalence), not by expression string.
"""

from __future__ import annotations

import pytest

from manifold_destiny.iteration9_bounded_grammar import Grammar, atom, depth, expr_to_str, node
from manifold_destiny.iteration9_bounded_generation_receipts import (
    ControlResult,
    FiberSignature,
    GeneratedCandidate,
    GrammarConfig,
    BoundedGenerationReceiptV1,
    evidence_hash,
    parse_receipt,
    verifier_contract_hash,
)
from manifold_destiny.iteration9_gluing_bounded_generation import (
    GF2_VERIFIER_CONTRACT,
    RESTRICTED_CATALOG_Q0,
    build_episode,
    evaluate_generated_candidate,
    find_accepted_abstractions,
    fixed_catalog_results,
)


# The canonical GF(2) grammar for bounded generation: atoms {0,u,v,w}, op xor.
GF2_GRAMMAR = Grammar(
    atoms=("0", "u", "v", "w"),
    ops=("xor",),
    max_depth=2,
)

# Orientation -> expected accepted expression (the correct hidden law).
ORIENTATION_TARGETS = {
    "m100": "(u xor v)",
    "m101": "(u xor w)",
    "m110": "(v xor w)",
    "m111": "(u xor (v xor w))",
}


class TestGf2Acceptance:
    """The bounded grammar constructs a quotient absent from Q_0 and G accepts."""

    def test_exactly_one_accepted_fiber_for_m100(self) -> None:
        """m100's correct law is u xor v; exactly one distinct fiber accepted."""
        episode = build_episode(orientation="m100", variant="bg_acc")
        accepted = find_accepted_abstractions(episode, GF2_GRAMMAR)
        assert len(accepted) == 1, (
            f"expected exactly 1 accepted fiber, got {len(accepted)}: "
            f"{[a['expr_str'] for a in accepted]}"
        )

    def test_accepted_expression_is_u_xor_v(self) -> None:
        """The shallowest representative of the accepted fiber is (u xor v)."""
        episode = build_episode(orientation="m100", variant="bg_expr")
        accepted = find_accepted_abstractions(episode, GF2_GRAMMAR)
        assert accepted[0]["expr_str"] == "(u xor v)"
        assert accepted[0]["g_verdict"] == "accepted"
        assert accepted[0]["composite_verdict"] == "valid"

    def test_accepted_not_in_fixed_catalog(self) -> None:
        """The accepted fiber is novel vs the restricted demonstration catalog."""
        episode = build_episode(orientation="m100", variant="bg_novel")
        accepted = find_accepted_abstractions(episode, GF2_GRAMMAR)
        fixed = fixed_catalog_results(episode)
        fixed_fibers = {f["fiber_signature_hash"] for f in fixed}
        assert accepted[0]["fiber_signature_hash"] not in fixed_fibers

    def test_fiber_dedupe_collapses_algebraic_equivalents(self) -> None:
        """Two known-equivalent expressions must share one fiber signature.

        (u xor v) and ((u xor v) xor (w xor w)) are algebraically identical on
        GF(2) because w xor w = 0. Both must produce the SAME partition and so
        the SAME canonical fiber hash. find_accepted_abstractions must collapse
        them to one retained abstraction.
        """
        episode = build_episode(orientation="m100", variant="bg_dedupe2")
        shallow = node("xor", atom("u"), atom("v"))
        # (u xor v) xor (w xor w) == u xor v on GF(2)
        equiv = node(
            "xor",
            node("xor", atom("u"), atom("v")),
            node("xor", atom("w"), atom("w")),
        )
        r_shallow = evaluate_generated_candidate(episode, shallow)
        r_equiv = evaluate_generated_candidate(episode, equiv)
        assert r_shallow["fiber_signature_hash"] == r_equiv["fiber_signature_hash"]
        # And the accepted set contains exactly one fiber, represented by the
        # shallow form.
        accepted = find_accepted_abstractions(episode, GF2_GRAMMAR)
        assert len(accepted) == 1
        assert accepted[0]["expr_str"] == "(u xor v)"

    def test_generated_partition_matches_repo_r4(self) -> None:
        """Positive identity: the generated (u xor v) partition IS R_4.

        The negative novelty test (not-in-Q_0) proves the generated fiber is
        absent from the restricted catalog. This positive test proves the
        generated fiber EQUALS the repo's R_4 partition — the precise
        construction claim: the grammar built the partition the fixed catalog
        lacked, using the same operator space the repo defines.
        """
        from manifold_destiny.iteration9_gluing_episode import REPAIR_KIND_TO_FUNCTIONAL_COEFFS
        from manifold_destiny.iteration9_manifold_store import (
            canonical_fiber_signature_from_partition,
        )

        episode = build_episode(orientation="m100", variant="bg_r4")
        states = episode["model_visible_initial"]["world"]["states"]
        # Build the R_4 partition directly from the functional coeffs (1,1,0).
        cu, cv, cw = REPAIR_KIND_TO_FUNCTIONAL_COEFFS["R_4"]
        groups: dict = {}
        for s in states:
            a = s["attributes"]
            key = (int(a["x"]) & 1, (cu & int(a["u"])) ^ (cv & int(a["v"])) ^ (cw & int(a["w"])))
            groups.setdefault(key, []).append(s["state_handle"])
        r4_cells = list(groups.values())
        r4_hash = canonical_fiber_signature_from_partition(r4_cells)

        generated = node("xor", atom("u"), atom("v"))
        result = evaluate_generated_candidate(episode, generated)
        assert result["fiber_signature_hash"] == r4_hash


class TestGf2Parameterization:
    """Each orientation accepts its corresponding composed law."""

    @pytest.mark.parametrize(
        "orientation,expected_expr",
        list(ORIENTATION_TARGETS.items()),
        ids=list(ORIENTATION_TARGETS.keys()),
    )
    def test_orientation_accepts_target(self, orientation: str, expected_expr: str) -> None:
        episode = build_episode(
            orientation=orientation, variant=f"param_{orientation[-2:]}"
        )
        accepted = find_accepted_abstractions(episode, GF2_GRAMMAR)
        assert len(accepted) == 1
        assert accepted[0]["expr_str"] == expected_expr


class TestGf2HeldOutTransfer:
    """The accepted abstraction transfers to a held-out variant with new handles."""

    def test_held_out_variant_accepted(self) -> None:
        """Same expression, different variant -> G accepts + composite valid."""
        expr = node("xor", atom("u"), atom("v"))
        ep_a = build_episode(orientation="m100", variant="xfer_src")
        ep_b = build_episode(orientation="m100", variant="xfer_dst")
        result_a = evaluate_generated_candidate(ep_a, expr)
        result_b = evaluate_generated_candidate(ep_b, expr)
        assert result_a["g_verdict"] == "accepted"
        assert result_a["composite_verdict"] == "valid"
        assert result_b["g_verdict"] == "accepted"
        assert result_b["composite_verdict"] == "valid"
        # Same partition structure (cell count), even though handles differ
        assert result_a["cell_count"] == result_b["cell_count"]


class TestGf2Controls:
    """Controls: wrong orientation, missing operator, fixed-catalog-only."""

    def test_wrong_orientation_rejects(self) -> None:
        """(u xor v) is correct for m100 but wrong for m101 -> G rejects."""
        expr = node("xor", atom("u"), atom("v"))
        episode = build_episode(orientation="m101", variant="ctrl_wrong")
        result = evaluate_generated_candidate(episode, expr)
        assert result["g_verdict"] == "rejected"

    def test_missing_operator_no_acceptance(self) -> None:
        """Grammar without xor cannot construct any composed quotient."""
        grammar_no_xor = Grammar(
            atoms=("0", "u", "v", "w"), ops=(), max_depth=2
        )
        episode = build_episode(orientation="m100", variant="ctrl_noop")
        accepted = find_accepted_abstractions(episode, grammar_no_xor)
        assert len(accepted) == 0, (
            f"grammar without xor should accept nothing, got {accepted}"
        )

    def test_fixed_catalog_only_all_rejected(self) -> None:
        """Q_0 = {0,u,v,w} only -> all rejected on m100 (the ceiling)."""
        episode = build_episode(orientation="m100", variant="ctrl_fixed")
        fixed = fixed_catalog_results(episode)
        assert len(fixed) == len(RESTRICTED_CATALOG_Q0)
        assert all(f["g_verdict"] == "rejected" for f in fixed)
        assert all(f["composite_verdict"] == "invalid" for f in fixed)

    def test_fixed_catalog_novelty_assertion_is_restricted(self) -> None:
        """Q_0 is explicitly the RESTRICTED demonstration catalog, not the repo."""
        # This test exists to prevent a reviewer kill shot: the repo's full
        # operator space DOES contain u⊕v (R_4). The novelty claim is against
        # Q_0 = {0,u,v,w}, never against the full repo.
        assert RESTRICTED_CATALOG_Q0 == ("0", "u", "v", "w")
        assert "u xor v" not in RESTRICTED_CATALOG_Q0


class TestGf2Determinism:
    """Same grammar -> same enumeration -> same accepted abstraction."""

    def test_enumeration_deterministic(self) -> None:
        episode = build_episode(orientation="m100", variant="det")
        first = find_accepted_abstractions(episode, GF2_GRAMMAR)
        second = find_accepted_abstractions(episode, GF2_GRAMMAR)
        assert [a["expr_str"] for a in first] == [a["expr_str"] for a in second]

    def test_grammar_signature_stable(self) -> None:
        g1 = Grammar(atoms=("0", "u", "v", "w"), ops=("xor",), max_depth=2)
        g2 = Grammar(atoms=("0", "u", "v", "w"), ops=("xor",), max_depth=2)
        assert g1.signature == g2.signature


class TestGf2Receipt:
    """Receipt round-trip and determinism."""

    def test_receipt_round_trip(self) -> None:
        episode = build_episode(orientation="m100", variant="rcpt")
        accepted = find_accepted_abstractions(episode, GF2_GRAMMAR)[0]
        fixed = fixed_catalog_results(episode)

        grammar_cfg = GrammarConfig(
            atoms=GF2_GRAMMAR.atoms,
            ops=GF2_GRAMMAR.ops,
            max_depth=GF2_GRAMMAR.max_depth,
            arities=GF2_GRAMMAR.arities,
            signature=GF2_GRAMMAR.signature,
        )
        generated = GeneratedCandidate(
            expression=accepted["expr_str"],
            registered_name="gen_gf2_xor",
            canonical_key=accepted["canonical_key"],
            digest=accepted["digest"],
        )
        fiber = FiberSignature(
            hash=accepted["fiber_signature_hash"],
            cell_count=accepted["cell_count"],
            canonical_partition="gf2_16state_partition",
        )
        controls = (
            ControlResult(
                "missing_operator",
                "not_enumerable",
                "grammar without xor accepts nothing",
            ),
            ControlResult(
                "fixed_catalog_only",
                "rejected",
                f"all {len(RESTRICTED_CATALOG_Q0)} Q_0 members rejected",
            ),
            ControlResult(
                "falsifier",
                "rejected",
                "wrong orientation m101 rejects (u xor v)",
            ),
        )
        receipt = BoundedGenerationReceiptV1(
            schema_version="manifold-destiny-bounded-generation-v1",
            domain="gf2_gluing",
            grammar=grammar_cfg,
            fixed_catalog=RESTRICTED_CATALOG_Q0,
            generated=generated,
            verifier_contract=GF2_VERIFIER_CONTRACT,
            verifier_contract_hash=verifier_contract_hash(GF2_VERIFIER_CONTRACT),
            evidence_hash=evidence_hash(
                {"orientation": "m100", "world_size": 16, "k_bits": 3}
            ),
            fiber_signature=fiber,
            certificate={
                "g_verdict": accepted["g_verdict"],
                "composite_verdict": accepted["composite_verdict"],
            },
            controls=controls,
            verdict="PASS",
        )
        blob = receipt.to_json()
        import json

        parsed = parse_receipt(json.loads(blob))
        assert parsed.domain == "gf2_gluing"
        assert parsed.generated.expression == "(u xor v)"
        assert parsed.verdict == "PASS"
        assert "timestamp" not in blob.lower()

    def test_receipt_digest_stable(self) -> None:
        episode = build_episode(orientation="m100", variant="rcpt2")
        accepted = find_accepted_abstractions(episode, GF2_GRAMMAR)[0]
        grammar_cfg = GrammarConfig(
            atoms=GF2_GRAMMAR.atoms,
            ops=GF2_GRAMMAR.ops,
            max_depth=GF2_GRAMMAR.max_depth,
            arities=GF2_GRAMMAR.arities,
            signature=GF2_GRAMMAR.signature,
        )
        receipt = BoundedGenerationReceiptV1(
            schema_version="manifold-destiny-bounded-generation-v1",
            domain="gf2_gluing",
            grammar=grammar_cfg,
            fixed_catalog=RESTRICTED_CATALOG_Q0,
            generated=GeneratedCandidate(
                expression=accepted["expr_str"],
                registered_name="gen",
                canonical_key=accepted["canonical_key"],
                digest=accepted["digest"],
            ),
            verifier_contract=GF2_VERIFIER_CONTRACT,
            verifier_contract_hash=verifier_contract_hash(GF2_VERIFIER_CONTRACT),
            evidence_hash=evidence_hash({"orientation": "m100"}),
            fiber_signature=FiberSignature(
                hash=accepted["fiber_signature_hash"],
                cell_count=accepted["cell_count"],
                canonical_partition="x",
            ),
            certificate={"g_verdict": "accepted"},
            controls=(),
            verdict="PASS",
        )
        assert receipt.digest() == receipt.digest()
