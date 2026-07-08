"""Phase D tests: Lean bounded generation gate.

Proves that a bounded grammar constructs a quotient absent from the restricted
demonstration catalog Q_0, and the Lean 4.31.0 kernel certifies both
admissibility (Adm) and semantic novelty (Not FiberEq). A bad candidate that
drops the consumer-preserving component is rejected (exit nonzero).

Self-contained: no mathlib. The source is pure kernel/subprocess. Skips
cleanly if the Lean kernel is not available.

CRITICAL SCOPE NOTE: Q_0 = {q0, qu, qv, qw} (each (x, single-field)) excludes
the generated target (x, bXor u v). Novelty is certified by the kernel via
Not FiberEq witness proofs.
"""

from __future__ import annotations

import pytest

from manifold_destiny.iteration9_bounded_grammar import atom, node
from manifold_destiny.iteration9_lean_bounded_generation import (
    LEAN_RESTRICTED_CATALOG_Q0,
    certify,
    emit_bad_source,
    emit_lean_source,
    lean_available,
    run_lean,
)

pytestmark = pytest.mark.skipif(
    not lean_available(), reason="Lean kernel not available"
)

TARGET_UV = node("xor", atom("u"), atom("v"))
TARGET_UW = node("xor", atom("u"), atom("w"))
TARGET_VW = node("xor", atom("v"), atom("w"))


class TestLeanAcceptance:
    """The kernel certifies the generated quotient is admissible + novel."""

    def test_generated_admissible_and_novel(self) -> None:
        """qgen=(x, bXor u v): Adm + 4x Not FiberEq all certified."""
        result = certify(TARGET_UV)
        assert result["exit_code"] == 0
        assert "Adm(qgen,c)" in result["certifies"]
        for name in LEAN_RESTRICTED_CATALOG_Q0:
            assert f"not FiberEq(qgen,{name})" in result["certifies"]

    def test_no_sorry_in_source(self) -> None:
        """The generated source must not contain sorry (no gaps)."""
        source, _ = emit_lean_source(TARGET_UV)
        assert "sorry" not in source

    def test_lean_version_captured_and_enforced(self) -> None:
        result = certify(TARGET_UV)
        assert result["lean_version"] != "unavailable"
        assert "4.31.0" in result["lean_version"]
        assert result.get("version_enforced") is True


class TestLeanParameterization:
    """Each pairwise xor target certifies admissibility + novelty."""

    @pytest.mark.parametrize(
        "target", [TARGET_UV, TARGET_UW, TARGET_VW], ids=["uv", "uw", "vw"]
    )
    def test_target_certified(self, target) -> None:
        result = certify(target)
        assert result["exit_code"] == 0
        assert len(result["certifies"]) == 5  # Adm + 4 Not FiberEq


class TestLeanControls:
    """Controls: bad candidate rejected, missing-operator, fixed-catalog-only."""

    def test_bad_candidate_rejected(self) -> None:
        """qbad drops x -> kernel cannot prove Adm -> exit nonzero."""
        result = run_lean(emit_bad_source())
        assert result["exit_code"] != 0

    def test_missing_operator_not_in_grammar(self) -> None:
        """Grammar without bXor cannot construct the target expression.

        We assert at the grammar level: the target node(xor, u, v) is not
        enumerable when xor is absent from ops.
        """
        from manifold_destiny.iteration9_bounded_grammar import Grammar, canonical_key

        grammar_no_xor = Grammar(atoms=("u", "v", "w"), ops=(), max_depth=2)
        exprs = grammar_no_xor.enumerate()
        target_key = canonical_key(TARGET_UV)
        assert not any(canonical_key(e) == target_key for e in exprs)

    def test_fixed_catalog_excludes_target(self) -> None:
        """Q_0 members are single-field; the target is a composition."""
        assert LEAN_RESTRICTED_CATALOG_Q0 == ("q0", "qu", "qv", "qw")
        # qgen = (x, bXor u v) is NOT a member of Q_0
        assert "qgen" not in LEAN_RESTRICTED_CATALOG_Q0


class TestLeanSourceEmission:
    """The emitted source is well-formed and parameterized correctly."""

    def test_source_contains_target_term(self) -> None:
        source, _ = emit_lean_source(TARGET_UV)
        assert "bXor s.u s.v" in source

    def test_source_contains_all_catalog_members(self) -> None:
        source, _ = emit_lean_source(TARGET_UV)
        for name in LEAN_RESTRICTED_CATALOG_Q0:
            assert f"def {name} " in source

    def test_source_contains_novelty_proofs(self) -> None:
        source, _ = emit_lean_source(TARGET_UV)
        for name in LEAN_RESTRICTED_CATALOG_Q0:
            assert f"qgen_not_fibereq_{name}" in source

    def test_proved_names_match_emitted_theorems(self) -> None:
        """Regression (review): certify reports ONLY emitted proofs.

        The old code hardcoded a 5-element certifies list. Now it derives from
        the actually-emitted theorem names. If a theorem is missing, certify
        must not claim it.
        """
        _, proved = emit_lean_source(TARGET_UV)
        # Must contain Adm + one per catalog member
        assert "Adm(qgen,c)" in proved
        for name in LEAN_RESTRICTED_CATALOG_Q0:
            assert f"not FiberEq(qgen,{name})" in proved
        assert len(proved) == 1 + len(LEAN_RESTRICTED_CATALOG_Q0)

    def test_non_novel_target_raises(self) -> None:
        """Regression (review): non-novel target must FAIL HARD.

        If the target is fiber-equivalent to a catalog member (e.g. target =
        atom('u') matches qu), no novelty witness exists. The emitter must
        raise ValueError, not silently skip the theorem and let the kernel
        exit 0 (which would be false certification).
        """
        # atom('u') is fiber-equivalent to qu=(x,u): both partition by (x,u).
        # There is no witness pair where qu agrees but target disagrees.
        from manifold_destiny.iteration9_bounded_grammar import atom

        with pytest.raises(ValueError, match="no novelty witness"):
            emit_lean_source(atom("u"))
