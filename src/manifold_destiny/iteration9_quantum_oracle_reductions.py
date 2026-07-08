"""Iteration 9 quantum oracle discovery — the reduction catalog.

This is the physics-agnostic menu of candidate STRUCTURES the carrier probes. It
is the analog of the eight GF(2) functionals in the synthetic gluing framework:
a fixed, pre-enumerated list of generic algebraic combinations of the two
measurement angles ``(alpha, beta)``. NONE of them is a quantum formula — there is
no trigonometric correlation curve, no measurement postulate, no visibility model anywhere.
They are plain arithmetic candidates.

Each candidate ``R_i`` induces a PARTITION of measurement settings into LEVEL
SETS: two settings ``(a1, b1)`` and ``(a2, b2)`` land in the same level set iff
``R_i(a1, b1) == R_i(a2, b2)``. The structural claim "the correlator E is a
function of ``R_i``" is then exactly "every level set is homogeneous in E".

The carrier never knows which candidate is correct. It discovers the answer by
probing each one and keeping only the ones the verifier G fails to refute (the
``glue_through`` survivors). What survives is what it discovered.

The discovery is genuinely load-bearing because the carrier's own visible data is
recorded at one Alice angle. With Alice held fixed, ``R_diff``, ``R_sum`` and
``R_beta`` all induce the IDENTICAL partition of the visible settings — the carrier
provably cannot tell them apart from what it can read. Only G, which holds the
held-back second-Alice-angle measurements, can break the degeneracy. So the
carrier must consult G; structure alone (no probe) cannot identify the invariance.
"""

from __future__ import annotations

from typing import Any, Callable


ITERATION9_QUANTUM_ORACLE_REDUCTIONS_SCHEMA_VERSION = (
    "manifold-destiny-quantum-oracle-reductions-v1"
)

# Float rounding for level-set membership (settings whose reduction value agrees
# to this many decimals share a level set). The measurement grid is spaced by
# pi/24 ~ 0.13 rad, far coarser than this, so rounding never merges grid points
# that the physical geometry keeps apart.
REDUCTION_VALUE_DECIMALS = 9

Reduction = Callable[[float, float], float]

# The fixed, physics-agnostic catalog. Catalog ORDER is the deterministic probe
# order; it is also the tie-break order the carrier uses to pick a survivor for
# the transfer (the first survivor in this order). NONE of these is a quantum
# correlation curve — they are generic algebraic candidates only.
REDUCTION_CATALOG: list[tuple[str, Reduction]] = [
    ("R_diff", lambda alpha, beta: alpha - beta),       # E depends on the angle difference
    ("R_absdiff", lambda alpha, beta: abs(alpha - beta)),  # E depends on |difference|
    ("R_sum", lambda alpha, beta: alpha + beta),        # E depends on the sum
    ("R_alpha", lambda alpha, beta: alpha),             # E depends on Alice only
    ("R_beta", lambda alpha, beta: beta),               # E depends on Bob only
    ("R_const", lambda alpha, beta: 0.0),               # E is constant
    ("R_prod", lambda alpha, beta: alpha * beta),       # E depends on the product
]

REDUCTION_NAMES: tuple[str, ...] = tuple(name for name, _ in REDUCTION_CATALOG)
REDUCTION_BY_NAME: dict[str, Reduction] = {name: fn for name, fn in REDUCTION_CATALOG}
CATALOG_SIZE = len(REDUCTION_CATALOG)


class Iteration9QuantumOracleReductionError(ValueError):
    """Raised when a reduction is asked for by an unknown name."""


def reduction_value(name: str, alpha: float, beta: float) -> float:
    """Evaluate the named reduction at ``(alpha, beta)``, rounded for binning."""
    fn = REDUCTION_BY_NAME.get(name)
    if fn is None:
        raise Iteration9QuantumOracleReductionError(f"unknown reduction: {name!r}")
    return round(fn(float(alpha), float(beta)), REDUCTION_VALUE_DECIMALS)


def level_sets(name: str, settings: list[dict[str, Any]]) -> dict[float, list[dict[str, Any]]]:
    """Partition ``settings`` into level sets keyed by the reduction value.

    Each entry in ``settings`` must carry ``alpha`` and ``beta``. Returns a map
    from the (rounded) reduction value to the list of settings at that value.
    """
    partition: dict[float, list[dict[str, Any]]] = {}
    for rec in settings or []:
        try:
            alpha = float(rec["alpha"])
            beta = float(rec["beta"])
        except (KeyError, TypeError, ValueError):
            continue
        value = reduction_value(name, alpha, beta)
        partition.setdefault(value, []).append(rec)
    return partition


__all__ = [
    "ITERATION9_QUANTUM_ORACLE_REDUCTIONS_SCHEMA_VERSION",
    "REDUCTION_VALUE_DECIMALS",
    "REDUCTION_CATALOG",
    "REDUCTION_NAMES",
    "REDUCTION_BY_NAME",
    "CATALOG_SIZE",
    "Iteration9QuantumOracleReductionError",
    "reduction_value",
    "level_sets",
]
