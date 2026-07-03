"""Iteration 9 — quantum bounded generation + scoped reduction registry.

Consumes the shared bounded grammar (``iteration9_bounded_grammar``) and the
existing quantum oracle verifier (``iteration9_quantum_oracle_verifier``).

The scratch probe monkeypatched the module-global ``REDUCTION_BY_NAME`` to
register a generated reduction. This module replaces that with an explicit,
scoped ``GeneratedReductionRegistry`` and a context manager that temporarily
extends the catalog and restores it on exit — so generated reductions cannot
leak across tests. The verifier itself is NOT edited.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from manifold_destiny.iteration9_bounded_grammar import (
    Expr,
    Grammar,
    canonical_key,
    expr_digest,
)
from manifold_destiny.iteration9_quantum_oracle_reductions import (
    REDUCTION_BY_NAME,
    REDUCTION_VALUE_DECIMALS,
    reduction_value,
)
from manifold_destiny.iteration9_quantum_oracle_verifier import (
    GLUE_THROUGH,
    tier_a_probe,
)

Reduction = Callable[[float, float], float]

# The restricted demonstration catalog: intentionally excludes R_diff and
# R_absdiff (the angle-difference survivors). This forces any pass to come from
# generation rather than selection.
RESTRICTED_CATALOG_Q0_QUANTUM: Tuple[str, ...] = (
    "R_sum",
    "R_alpha",
    "R_beta",
    "R_const",
    "R_prod",
)

# Verifier contract for receipts.
QUANTUM_VERIFIER_CONTRACT: Tuple[str, ...] = (
    "tier_a_level_set_homogeneity",
    "same_fiber_copy_transfer",
    "held_out_accuracy_within_shot_noise",
    "chsh_nonclassicality_above_margin",
    "v1",
)

# Default quantum-expanded data path (overridable via env). Honors
# MANIFOLD_QUANTUM_DATA first, then MANIFOLD_DATA_DIR root, then neutral
# default — matching the test's resolver so production/test behavior is unified.
_q_data_root = os.path.expanduser(
    os.environ.get("MANIFOLD_DATA_DIR", str(Path.home() / ".manifold-destiny" / "data"))
)
DEFAULT_QUANTUM_DATA = os.path.expanduser(
    os.environ.get(
        "MANIFOLD_QUANTUM_DATA",
        str(Path(_q_data_root) / "quantum-expanded-data.json"),
    )
)


class GeneratedReductionRegistry:
    """Explicit, instance-scoped registry of generated reductions.

    NOT global module state. A test constructs one, registers ``(name, fn)``
    pairs, and uses it inside ``with_generated_reductions(...)`` so the names
    are visible to ``reduction_value`` / ``tier_a_probe`` only for the duration
    of the context.
    """

    def __init__(self) -> None:
        self._entries: Dict[str, Reduction] = {}

    def register(self, name: str, fn: Reduction) -> None:
        if name in self._entries:
            raise ValueError(f"generated reduction already registered: {name!r}")
        self._entries[name] = fn

    def names(self) -> Tuple[str, ...]:
        return tuple(self._entries.keys())

    def get(self, name: str) -> Optional[Reduction]:
        return self._entries.get(name)

    def __len__(self) -> int:
        return len(self._entries)

    def __contains__(self, name: str) -> bool:
        return name in self._entries


@contextmanager
def with_generated_reductions(
    registry: GeneratedReductionRegistry,
) -> Iterator[None]:
    """Temporarily extend REDUCTION_BY_NAME with the registry's entries.

    On exit (including on exception), restores the catalog to its exact
    pre-context state by rebuilding from the snapshot — not by popping only
    the added keys. This guarantees no leak even if code inside the context
    mutated existing entries. Raises RuntimeError on drift (not a bare
    assert, so it survives ``python -O``).

    Name collisions are rejected: a generated reduction may not shadow a
    built-in catalog entry, otherwise tests would silently exercise selection
    rather than generation.
    """
    original = dict(REDUCTION_BY_NAME)
    for name in registry._entries:  # noqa: SLF001
        if name in original:
            raise ValueError(
                f"generated reduction {name!r} collides with built-in catalog entry; "
                "rename to avoid silently selecting the built-in"
            )
    try:
        for name, fn in registry._entries.items():  # noqa: SLF001
            REDUCTION_BY_NAME[name] = fn
        yield
    finally:
        # Restore EXACTLY from the snapshot. This handles mutations to
        # existing entries and added keys alike.
        REDUCTION_BY_NAME.clear()
        REDUCTION_BY_NAME.update(original)
        if dict(REDUCTION_BY_NAME) != original:
            raise RuntimeError(
                "REDUCTION_BY_NAME could not be restored to pre-context state"
            )


def _eval_quantum_expr(expr: Expr, alpha: float, beta: float) -> float:
    """Evaluate a grammar expression over quantum angle atoms."""
    if expr.op == "atom":
        label = str(expr.args[0])
        if label == "alpha":
            return float(alpha)
        if label == "beta":
            return float(beta)
        if label in ("0", "const0"):
            return 0.0
        if label in ("1", "const1"):
            return 1.0
        raise ValueError(f"unknown quantum atom: {label!r}")
    if expr.op == "sub":
        return _eval_quantum_expr(expr.args[0], alpha, beta) - _eval_quantum_expr(
            expr.args[1], alpha, beta
        )
    if expr.op == "add":
        return _eval_quantum_expr(expr.args[0], alpha, beta) + _eval_quantum_expr(
            expr.args[1], alpha, beta
        )
    if expr.op == "abs":
        return abs(_eval_quantum_expr(expr.args[0], alpha, beta))
    raise ValueError(f"unsupported quantum op: {expr.op!r}")


def expr_to_reduction(expr: Expr) -> Reduction:
    """Compile a grammar expression into a reduction callable."""
    return lambda alpha, beta: _eval_quantum_expr(expr, alpha, beta)


def register_generated_from_grammar(
    registry: GeneratedReductionRegistry,
    grammar: Grammar,
    prefix: str = "G",
) -> List[Tuple[str, Expr]]:
    """Register every grammar expression as a generated reduction.

    Returns a list of (registered_name, expr) pairs for inspection. Names are
    deterministic: ``G_<sha8>`` derived from the canonical key.
    """
    pairs: List[Tuple[str, Expr]] = []
    for expr in grammar.enumerate():
        key = canonical_key(expr)
        short = expr_digest(expr)[:8]
        name = f"{prefix}_{short}"
        if name not in registry:
            registry.register(name, expr_to_reduction(expr))
            pairs.append((name, expr))
    return pairs


def canonical_partition_signature(
    reduction_name: str,
    settings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Canonical hash of the fiber partition induced by a reduction."""
    import hashlib

    buckets: Dict[float, List[str]] = {}
    for rec in settings:
        value = reduction_value(reduction_name, rec["alpha"], rec["beta"])
        buckets.setdefault(value, []).append(str(rec["setting_id"]))
    canonical = [
        {
            "value": format(value, f".{REDUCTION_VALUE_DECIMALS}f"),
            "settings": sorted(ids),
        }
        for value, ids in sorted(buckets.items(), key=lambda item: item[0])
    ]
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return {
        "hash": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "cell_count": len(canonical),
    }


def fixed_catalog_tier_a(
    discovery_settings: List[Dict[str, Any]],
    catalog: Tuple[str, ...] = RESTRICTED_CATALOG_Q0_QUANTUM,
) -> List[Dict[str, Any]]:
    """Run the fixed demonstration catalog through Tier A."""
    return [
        {"name": name, "tier_a": tier_a_probe(name, discovery_settings)["kind"]}
        for name in catalog
    ]


def find_transfer_partner(
    episode: Dict[str, Any],
    reduction_name: str,
) -> Tuple[Optional[float], Optional[str]]:
    """Copy the visible correlator with the same generated reduction value.

    Finds the visible measurement setting whose reduction value equals the
    held-out setting's reduction value, and returns its correlator E and id.
    This is the transfer step: the generated reduction predicts the held-out
    correlator by copying the matching visible one.
    """
    evidence = episode["evidence_only"]
    visible = episode["model_visible_initial"]["world"]["settings"]
    target = reduction_value(
        reduction_name,
        evidence["held_out_alpha"],
        evidence["held_out_beta"],
    )
    for rec in visible:
        value = reduction_value(reduction_name, rec["alpha"], rec["beta"])
        if value == target:
            return float(rec["E"]), str(rec["setting_id"])
    return None, None


def proposal_for_generated(
    episode: Dict[str, Any],
    generated_name: str,
    expression: str,
) -> Dict[str, Any]:
    """Build a verifier proposal carrying the generated reduction.

    The existing quantum_oracle_objective reads ``transfer_reduction`` to
    copy the correlator and ``predicted_E`` for the held-out accuracy check.
    This proposal shape is what G consumes end-to-end.
    """
    predicted_e, transfer_source = find_transfer_partner(episode, generated_name)
    return {
        "discovered_class": [generated_name],
        "transfer_reduction": generated_name,
        "predicted_E": predicted_e,
        "transfer_source_setting_id": transfer_source,
        "abstained": predicted_e is None,
        "generated_expression": expression,
    }


__all__ = [
    "RESTRICTED_CATALOG_Q0_QUANTUM",
    "QUANTUM_VERIFIER_CONTRACT",
    "DEFAULT_QUANTUM_DATA",
    "GeneratedReductionRegistry",
    "with_generated_reductions",
    "expr_to_reduction",
    "register_generated_from_grammar",
    "canonical_partition_signature",
    "fixed_catalog_tier_a",
    "find_transfer_partner",
    "proposal_for_generated",
]
