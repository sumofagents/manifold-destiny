"""Phase C tests: quantum bounded generation gate.

Proves that a bounded grammar constructs the angle-difference invariant
(alpha - beta), absent from the restricted demonstration catalog Q_0, and the
existing quantum oracle verifier accepts it. Controls: missing-operator,
fixed-catalog-only, classical surrogate, shuffled geometry.

CRITICAL SCOPE NOTE: Q_0 = {R_sum, R_alpha, R_beta, R_const, R_prod}
intentionally excludes R_diff and R_absdiff (the angle-difference survivors).
This forces any pass to come from generation rather than selection. The
repo's full reduction catalog DOES contain R_diff; novelty is against Q_0 only.

REGISTRY ISOLATION: generated reductions are registered via a scoped context
manager (with_generated_reductions). They must not leak across tests — the
module-global REDUCTION_BY_NAME is restored exactly on context exit.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from manifold_destiny.iteration9_bounded_grammar import (
    Grammar,
    atom,
    canonical_key,
    expr_digest,
    node,
)
from manifold_destiny.iteration9_quantum_oracle_bounded_generation import (
    RESTRICTED_CATALOG_Q0_QUANTUM,
    GeneratedReductionRegistry,
    canonical_partition_signature,
    expr_to_reduction,
    find_transfer_partner,
    fixed_catalog_tier_a,
    proposal_for_generated,
    register_generated_from_grammar,
    with_generated_reductions,
)
from manifold_destiny.iteration9_quantum_oracle_episode import build_quantum_oracle_episode
from manifold_destiny.iteration9_quantum_oracle_evaluation import (
    build_classical_surrogate_data,
    shuffle_settings_data,
)
from manifold_destiny.iteration9_quantum_oracle_reductions import REDUCTION_BY_NAME
from manifold_destiny.iteration9_quantum_oracle_verifier import (
    GLUE_THROUGH,
    quantum_oracle_objective,
    tier_a_probe,
)

# Quantum data path: env-configurable via MANIFOLD_QUANTUM_DATA, or under
# MANIFOLD_DATA_DIR root. Neutral default so a reviewer on any machine gets
# a sensible starting point.
_quantum_data_root = os.path.expanduser(
    os.environ.get("MANIFOLD_DATA_DIR", str(Path.home() / ".manifold-destiny" / "data"))
)
DATA_PATH = Path(
    os.path.expanduser(
        os.environ.get(
            "MANIFOLD_QUANTUM_DATA",
            str(Path(_quantum_data_root) / "quantum-expanded-data.json"),
        )
    )
)

# The canonical quantum grammar: atoms {alpha, beta}, op sub.
QUANTUM_GRAMMAR = Grammar(atoms=("alpha", "beta"), ops=("sub",), max_depth=1)

TARGET_EXPR = node("sub", atom("alpha"), atom("beta"))


def _load_data():
    if not DATA_PATH.exists():
        pytest.skip(f"real quantum data not found at {DATA_PATH}")
    return json.loads(DATA_PATH.read_text())


def _register_target(registry: GeneratedReductionRegistry) -> str:
    """Register the alpha-beta reduction and return its generated name."""
    name = f"G_{expr_digest(TARGET_EXPR)[:8]}"
    if name not in registry:
        registry.register(name, expr_to_reduction(TARGET_EXPR))
    return name


@pytest.fixture(scope="module")
def expanded_data():
    return _load_data()


@pytest.fixture
def episode(expanded_data):
    return build_quantum_oracle_episode(expanded_data, "a1_b2", "eval")


class TestQuantumAcceptance:
    """The bounded grammar constructs alpha-beta and the verifier accepts."""

    def test_fixed_catalog_all_fail_tier_a(self, episode) -> None:
        """Q_0 (no R_diff/R_absdiff) -> every member refuted by anti-witness."""
        disc = episode["evidence_only"]["discovery_settings"]
        fixed = fixed_catalog_tier_a(disc)
        assert len(fixed) == len(RESTRICTED_CATALOG_Q0_QUANTUM)
        assert all(f["tier_a"] != GLUE_THROUGH for f in fixed)
        assert all(f["tier_a"] == "anti_witness" for f in fixed)

    def test_generated_alpha_minus_beta_passes_tier_a(self, episode) -> None:
        disc = episode["evidence_only"]["discovery_settings"]
        registry = GeneratedReductionRegistry()
        name = _register_target(registry)
        with with_generated_reductions(registry):
            result = tier_a_probe(name, disc)
        assert result["kind"] == GLUE_THROUGH

    def test_generated_fiber_matches_builtin_r_diff(self, episode) -> None:
        """Generated alpha-beta shares the SAME fiber signature as R_diff."""
        disc = episode["evidence_only"]["discovery_settings"]
        registry = GeneratedReductionRegistry()
        name = _register_target(registry)
        with with_generated_reductions(registry):
            gen_sig = canonical_partition_signature(name, disc)
        builtin_sig = canonical_partition_signature("R_diff", disc)
        assert gen_sig["hash"] == builtin_sig["hash"]
        assert gen_sig["cell_count"] == builtin_sig["cell_count"]

    def test_generated_novel_vs_q0(self, episode) -> None:
        """The generated fiber is absent from the restricted catalog Q_0."""
        disc = episode["evidence_only"]["discovery_settings"]
        registry = GeneratedReductionRegistry()
        name = _register_target(registry)
        with with_generated_reductions(registry):
            gen_sig = canonical_partition_signature(name, disc)
        q0_sigs = {
            canonical_partition_signature(n, disc)["hash"]
            for n in RESTRICTED_CATALOG_Q0_QUANTUM
        }
        assert gen_sig["hash"] not in q0_sigs


class TestQuantumFullVerifier:
    """End-to-end: the full quantum_oracle_objective (G) accepts a generated name.

    This is the load-bearing proof — the whole point of the experiment is that
    G accepts the generated reduction, not just that Tier A structure is
    consistent. A regression in transfer consistency or Tier B lookup for
    generated names would be caught ONLY by these tests.
    """

    def test_generated_accepted_by_full_g(self, episode) -> None:
        registry = GeneratedReductionRegistry()
        name = _register_target(registry)
        with with_generated_reductions(registry):
            proposal = proposal_for_generated(episode, name, "alpha - beta")
            assert not proposal["abstained"], "transfer partner not found"
            result = quantum_oracle_objective(episode, proposal)
        assert result["verdict"] == "accepted"

    def test_generated_held_out_accuracy_within_tolerance(self, episode) -> None:
        """The generated reduction's prediction matches measured E within shot noise."""
        registry = GeneratedReductionRegistry()
        name = _register_target(registry)
        with with_generated_reductions(registry):
            proposal = proposal_for_generated(episode, name, "alpha - beta")
            result = quantum_oracle_objective(episode, proposal)
        acc = result["accuracy"]
        assert abs(acc["residual"]) <= acc["tolerance"]

    def test_generated_chsh_above_margin(self, episode) -> None:
        """The generated reduction yields a CHSH S above the verifier margin."""
        registry = GeneratedReductionRegistry()
        name = _register_target(registry)
        with with_generated_reductions(registry):
            proposal = proposal_for_generated(episode, name, "alpha - beta")
            result = quantum_oracle_objective(episode, proposal)
        tier_b = result["tier_b"]
        assert tier_b.get("chsh_S", 0) > tier_b.get("bound", 2.05)


class TestQuantumControls:
    """Controls: missing-operator, classical surrogate, shuffled geometry."""

    def test_missing_operator_no_glue_through(self, episode) -> None:
        """Grammar without sub cannot construct alpha-beta -> no glue_through."""
        disc = episode["evidence_only"]["discovery_settings"]
        registry = GeneratedReductionRegistry()
        # Wider negative grammar: add + abs (non-sub constructions). Even with
        # these, nothing can reach R_diff's fiber.
        grammar_no_sub = Grammar(
            atoms=("alpha", "beta"), ops=("add", "abs"), max_depth=2,
            arities=(("abs", 1),),
        )
        register_generated_from_grammar(registry, grammar_no_sub)
        assert len(registry) > 0, "grammar must enumerate at least one candidate"
        with with_generated_reductions(registry):
            results = [
                tier_a_probe(name, disc)["kind"] for name in registry.names()
            ]
        assert len(results) > 0
        assert GLUE_THROUGH not in results

    def test_fixed_catalog_only_no_glue_through(self, episode) -> None:
        """Using ONLY Q_0 (no generation) -> none glue_through."""
        disc = episode["evidence_only"]["discovery_settings"]
        fixed = fixed_catalog_tier_a(disc)
        assert all(f["tier_a"] != GLUE_THROUGH for f in fixed)

    def test_classical_surrogate_rejected_by_full_g(self) -> None:
        """End-to-end: classical surrogate passes Tier A but G rejects on Tier B.

        The generated reduction's structure is consistent (Tier A glue_through),
        but the surrogate data is classically explicable — Tier B non-classicality
        rejects it. This is the full-verifier rejection, not just Tier A.
        """
        classical_ep = build_quantum_oracle_episode(
            build_classical_surrogate_data(), "a1_b2", "eval"
        )
        registry = GeneratedReductionRegistry()
        name = _register_target(registry)
        with with_generated_reductions(registry):
            proposal = proposal_for_generated(classical_ep, name, "alpha - beta")
            result = quantum_oracle_objective(classical_ep, proposal)
        assert result["verdict"] == "rejected"

    def test_shuffled_geometry_rejected(self, expanded_data) -> None:
        """Shuffled settings geometry -> Tier A refutes before full acceptance."""
        shuffled_ep = build_quantum_oracle_episode(
            shuffle_settings_data(expanded_data), "a1_b2", "eval"
        )
        disc = shuffled_ep["evidence_only"]["discovery_settings"]
        registry = GeneratedReductionRegistry()
        name = _register_target(registry)
        with with_generated_reductions(registry):
            tier_a = tier_a_probe(name, disc)
        assert tier_a["kind"] != GLUE_THROUGH


class TestRegistryIsolation:
    """Generated reductions do not leak across contexts or tests."""

    def test_restoration_after_context_exit(self, episode) -> None:
        """REDUCTION_BY_NAME restored exactly after context exit."""
        disc = episode["evidence_only"]["discovery_settings"]
        original = dict(REDUCTION_BY_NAME)
        registry = GeneratedReductionRegistry()
        name = _register_target(registry)
        with with_generated_reductions(registry):
            assert name in REDUCTION_BY_NAME
        assert name not in REDUCTION_BY_NAME
        assert dict(REDUCTION_BY_NAME) == original

    def test_registry_instance_scoped(self) -> None:
        """Two registries are independent; names don't collide."""
        reg_a = GeneratedReductionRegistry()
        reg_b = GeneratedReductionRegistry()
        reg_a.register("G_test_a", lambda a, b: a - b)
        reg_b.register("G_test_b", lambda a, b: a + b)
        assert "G_test_a" in reg_a
        assert "G_test_a" not in reg_b
        assert "G_test_b" in reg_b
        assert "G_test_b" not in reg_a

    def test_duplicate_registration_rejected(self) -> None:
        registry = GeneratedReductionRegistry()
        registry.register("G_dup", lambda a, b: a - b)
        with pytest.raises(ValueError):
            registry.register("G_dup", lambda a, b: a + b)

    def test_restoration_on_exception(self, episode) -> None:
        """Regression (review): finally block restores even on exception."""
        disc = episode["evidence_only"]["discovery_settings"]
        original = dict(REDUCTION_BY_NAME)
        registry = GeneratedReductionRegistry()
        name = _register_target(registry)
        with pytest.raises(RuntimeError):
            with with_generated_reductions(registry):
                assert name in REDUCTION_BY_NAME
                raise RuntimeError("boom")
        # Must be restored despite the exception
        assert name not in REDUCTION_BY_NAME
        assert dict(REDUCTION_BY_NAME) == original

    def test_drift_detected_if_body_mutates_catalog(self, episode) -> None:
        """Regression (review): mutation inside context is detected.

        If code inside the context mutates an existing catalog entry, the
        exit-time restoration rebuilds from snapshot and the drift assertion
        confirms restoration succeeded. (The restore-from-snapshot logic means
        even mutations are undone.)
        """
        original = dict(REDUCTION_BY_NAME)
        registry = GeneratedReductionRegistry()
        name = _register_target(registry)
        with with_generated_reductions(registry):
            # Simulate hostile mutation: overwrite a built-in
            REDUCTION_BY_NAME["R_diff"] = lambda a, b: 999.0
        # Restored: R_diff back to original function object
        assert dict(REDUCTION_BY_NAME) == original

    def test_collision_with_builtin_rejected(self) -> None:
        """Regression (review): cannot shadow a built-in name.

        If a generated reduction registers 'R_diff', the context would silently
        use the built-in — tests would exercise selection not generation. This
        must be rejected at context entry.
        """
        registry = GeneratedReductionRegistry()
        registry.register("R_diff", lambda a, b: a - b)
        with pytest.raises(ValueError, match="collides with built-in"):
            with with_generated_reductions(registry):
                pass


class TestQuantumGrammar:
    """Grammar enumeration over quantum atoms."""

    def test_grammar_enumerates_alpha_minus_beta(self) -> None:
        exprs = QUANTUM_GRAMMAR.enumerate()
        target_key = canonical_key(TARGET_EXPR)
        assert any(canonical_key(e) == target_key for e in exprs)

    def test_grammar_signature_stable(self) -> None:
        g1 = Grammar(atoms=("alpha", "beta"), ops=("sub",), max_depth=1)
        g2 = Grammar(atoms=("alpha", "beta"), ops=("sub",), max_depth=1)
        assert g1.signature == g2.signature

    def test_expr_to_reduction_correct(self) -> None:
        fn = expr_to_reduction(TARGET_EXPR)
        assert fn(0.5, 0.3) == pytest.approx(0.2)
        assert fn(1.0, 0.0) == pytest.approx(1.0)
        assert fn(0.0, 1.0) == pytest.approx(-1.0)


class TestQuantumRestrictionGuard:
    """Q_0 is the restricted demonstration catalog, not the full repo."""

    def test_q0_excludes_diff_survivors(self) -> None:
        """R_diff and R_absdiff are NOT in Q_0 (they are the targets)."""
        assert "R_diff" not in RESTRICTED_CATALOG_Q0_QUANTUM
        assert "R_absdiff" not in RESTRICTED_CATALOG_Q0_QUANTUM

    def test_q0_is_five_members(self) -> None:
        assert len(RESTRICTED_CATALOG_Q0_QUANTUM) == 5
        assert RESTRICTED_CATALOG_Q0_QUANTUM == (
            "R_sum",
            "R_alpha",
            "R_beta",
            "R_const",
            "R_prod",
        )

    def test_builtin_r_diff_exists_in_repo(self) -> None:
        """The repo's full catalog DOES contain R_diff — novelty is vs Q_0 only."""
        assert "R_diff" in REDUCTION_BY_NAME
