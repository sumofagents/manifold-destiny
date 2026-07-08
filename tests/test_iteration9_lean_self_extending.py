"""Lean self-extending grammar tests.

Tests the self-extending grammar mechanism in the Lean domain: the grammar
constructs a candidate quotient, the Lean 4.31.0 kernel verifies it (Adm +
novelty), and the retained quotient is promoted to a new grammar atom. The
grown grammar can then express deeper compositions that the seed grammar
could not reach at the same depth.

These tests use the Lean kernel as the verifier — not a mock, not a proxy.
The kernel either accepts or rejects; the verdict is binary and exact.
"""

from __future__ import annotations

import pytest

from manifold_destiny.iteration9_bounded_grammar import (
    Grammar,
    atom,
    canonical_key,
    expand_grammar,
    expr_to_str,
    node,
    promoted_atom_label,
    self_extend_step,
)
from manifold_destiny.iteration9_lean_bounded_generation import (
    emit_lean_source,
    lean_available,
    run_lean,
)

pytestmark = pytest.mark.skipif(
    not lean_available(),
    reason="Lean kernel not available — skipping Lean self-extension tests",
)

# The seed grammar for Lean: atoms are the GF(2) variables, op is xor.
LEAN_G0 = Grammar(
    atoms=("x", "u", "v", "w"),
    ops=("xor",),
    max_depth=2,
    arities=(("xor", 2),),
)

# The GF(2) expression u xor v — the first retained quotient to promote.
LEAN_UV = node("xor", atom("u"), atom("v"))


def _lean_verify(expr) -> bool:
    """Use the Lean 4.31.0 kernel as the verifier for a candidate expression."""
    try:
        source, proved = emit_lean_source(expr)
    except ValueError:
        # Candidate is fiber-equivalent to a catalog member — NOT novel. Reject.
        return False
    if not proved:
        return False
    result = run_lean(source, prefix="lean_selfext_")
    return result.get("exit_code") == 0


class TestLeanSelfExtension:
    """The self-extending grammar mechanism works in the Lean domain."""

    def test_lean_seed_grammar_enumerates(self) -> None:
        """G0 has a finite, non-empty candidate set."""
        candidates = LEAN_G0.enumerate()
        assert len(candidates) > 0

    def test_lean_kernel_verifies_candidate(self) -> None:
        """The Lean kernel accepts the u xor v candidate as c-admissible + novel."""
        assert _lean_verify(LEAN_UV), (
            "Lean kernel must accept u xor v as Adm + novel vs Q_0"
        )

    def test_lean_promote_retained_quotient(self) -> None:
        """A kernel-accepted quotient promotes to a new typed atom."""
        g1 = expand_grammar(LEAN_G0, LEAN_UV)
        assert len(g1.atoms) > len(LEAN_G0.atoms)
        label = promoted_atom_label(LEAN_UV)
        assert label in g1.atoms

    def test_lean_grown_grammar_expresses_more(self) -> None:
        """G1 (after promotion) can express more compositions than G0."""
        g1 = expand_grammar(LEAN_G0, LEAN_UV)
        assert len(g1.enumerate()) > len(LEAN_G0.enumerate())

    def test_lean_self_extend_step_with_kernel(self) -> None:
        """One round of self-extending enumeration + Lean verification + retention.

        The grammar enumerates candidates, the Lean kernel verifies each,
        retained quotients are promoted to atoms, and the grammar grows.
        """
        # Use a small subset of candidates to keep the Lean kernel calls bounded.
        # We only test u xor v (the known-accepted quotient).
        def limited_enumerate(grammar):
            candidates = grammar.enumerate()
            # Focus on depth-1 xor expressions (the constructible quotients)
            return [c for c in candidates if _expr_depth(c) == 1 and c.op == "xor"]

        step = self_extend_step(
            LEAN_G0,
            enumerate_fn=limited_enumerate,
            verify_fn=_lean_verify,
        )
        # At least one candidate (u xor v) should be retained and promoted.
        assert len(step.retained) >= 1
        assert step.grew
        assert len(step.grown_grammar.atoms) > len(LEAN_G0.atoms)

    def test_lean_definitions_preserved_across_promotion(self) -> None:
        """The promoted atom's definition is preserved in grammar.definitions."""
        g1 = expand_grammar(LEAN_G0, LEAN_UV)
        label = promoted_atom_label(LEAN_UV)
        defs = dict(g1.definitions)
        assert label in defs
        assert canonical_key(defs[label]) == canonical_key(LEAN_UV)


def _expr_depth(expr) -> int:
    """Depth of an expression (atom = 0)."""
    if expr.op == "atom":
        return 0
    return 1 + max(_expr_depth(a) for a in expr.args)
