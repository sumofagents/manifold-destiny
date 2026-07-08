"""Iteration 9 quantum Bell certificate — episode builder from real IBM data.

This is the simplest **non-vacuous** quantum certificate adapter. Unlike the
synthetic gluing square (``iteration9_gluing_*``), the non-local datum here is a
real, physical fact measured on quantum hardware: the CHSH correlator of an
entangled pair at a measurement setting the carrier never sees.

THE OBJECT
----------
Four CHSH settings are measured on ``ibm_marrakesh`` for a Bell state (4000 shots
each). Three are TRAINING (model_visible): the carrier reads their correlators
``E``. One is HELD OUT (evidence_only): the carrier sees neither its correlator
nor its counts — only the verifier G does. The carrier must *extrapolate* the
quantum correlation curve ``E(θ_a, θ_b) = V·cos((θ_a − θ_b) − φ)`` to the held-out
setting and predict its correlator.

WHY THIS IS NON-VACUOUS
-----------------------
The held-out setting is **information-separated** from the carrier (it lives in
``evidence_only``, never in ``model_visible_initial``). To form a proposal the
carrier MUST read the training correlators and fit the curve — blank the training
data and it cannot fit (load-bearing). And the held-out correlator the hardware
measured (``E = +0.4035`` for Phi_plus a0_b2) lies **outside the local-hidden-
variable polytope** given the three training correlators: with the training
fixed, CHSH ``S ≤ 2`` forces ``E(a0_b2) ≥ +0.707``. The hardware measured
``+0.4035`` — ~21σ below the classical floor. So a classical (LHV-constrained)
carrier provably cannot reproduce the held-out value, and classical surrogate
data (any LHV model, ``S ≤ 2``) provably fails G's non-classicality conjunct.

This module only BUILDS the episode and owns the angle/CHSH-sign bookkeeping.
The verifier G is in ``iteration9_quantum_verifier``; the carrier in
``iteration9_quantum_policy``; lanes + verdict in ``iteration9_quantum_evaluation``.

The factor-of-2 note
--------------------
The redesign brief sketches the model as ``V·cos(2(θ_a − θ_b − φ))``. The real
ibm_marrakesh angle convention (Alice ∈ {0, π/4}, Bob ∈ {π/8, 3π/8}) already
bakes the doubling into the chosen angles, so the correlator the hardware
actually traces is ``E = V·cos((θ_a − θ_b) − φ)`` (verified against all four
measured correlators: the cosine fit reproduces them to within shot noise). We
fit the model the DATA follows, not a formula that would mispredict the sign of
the held-out point. The frequency is fixed to the physical value (1); only
``(V, φ)`` are free, so the carrier never over-fits 3 points.
"""

from __future__ import annotations

import math
from typing import Any


ITERATION9_QUANTUM_EPISODE_SCHEMA_VERSION = (
    "manifold-destiny-quantum-bell-certificate-episode-v1"
)
ITERATION9_QUANTUM_CLAIM = (
    "ITERATION_9_QUANTUM_BELL_CERTIFICATE_NON_LOCAL_CORRELATOR_TRANSFER"
)

# The four canonical CHSH settings and their (alpha, beta) measurement angles
# (radians). Matches quantum-chsh-data.json _metadata.settings exactly.
CHSH_SETTING_ANGLES = {
    "a0_b1": (0.0, math.pi / 8),
    "a0_b2": (0.0, 3 * math.pi / 8),
    "a1_b1": (math.pi / 4, math.pi / 8),
    "a1_b2": (math.pi / 4, 3 * math.pi / 8),
}

# CHSH combination S = E(a0_b1) − E(a0_b2) + E(a1_b1) + E(a1_b2). The single
# minus sign sits on the (a0, b2) term; the held-out MVP setting is a0_b2, so the
# held-out correlator enters S with coefficient −1 (low held-out E ⇒ large S).
CHSH_SIGNS = {"a0_b1": +1, "a0_b2": -1, "a1_b1": +1, "a1_b2": +1}

# Classical (local-hidden-variable) CHSH bound. S > 2 certifies non-classicality.
CHSH_CLASSICAL_BOUND = 2.0

QUANTUM_MODES = ("eval", "adaptation")


class Iteration9QuantumEpisodeError(ValueError):
    """Raised when the quantum Bell episode contract is malformed."""


def correlator_from_counts(counts: dict[str, Any]) -> float:
    """E = (N00 + N11 − N01 − N10) / N_total from joint measurement counts.

    This is the operational definition of the CHSH correlator: the expectation of
    the product of the two ±1 outcomes. Recomputed from raw counts so the carrier
    and G read the same physical quantity the hardware produced.
    """
    n00 = float(counts.get("00", 0))
    n01 = float(counts.get("01", 0))
    n10 = float(counts.get("10", 0))
    n11 = float(counts.get("11", 0))
    total = n00 + n01 + n10 + n11
    if total <= 0:
        raise Iteration9QuantumEpisodeError("counts must contain at least one shot")
    return (n00 + n11 - n01 - n10) / total


def shot_noise_se(correlator: float, shots: int) -> float:
    """Shot-noise standard error of a correlator estimate: sqrt((1 − E²) / N).

    This is the binomial standard error of the ±1 product expectation under N
    shots — the tolerance band G allows the carrier's prediction.
    """
    if shots <= 0:
        raise Iteration9QuantumEpisodeError("shots must be positive")
    variance = max(0.0, 1.0 - correlator * correlator)
    return math.sqrt(variance / shots)


def _setting_record(data: dict[str, Any], bell_state: str, setting_id: str) -> dict[str, Any]:
    key = f"{bell_state}_{setting_id}"
    record = data.get(key)
    if not isinstance(record, dict):
        raise Iteration9QuantumEpisodeError(
            f"missing measurement record for {key!r} in data"
        )
    counts = record.get("counts")
    if not isinstance(counts, dict):
        raise Iteration9QuantumEpisodeError(f"record {key!r} missing counts")
    shots = int(record.get("shots", 0))
    alpha, beta = CHSH_SETTING_ANGLES[setting_id]
    return {
        "setting_id": setting_id,
        "alpha": alpha,
        "beta": beta,
        # E is recomputed from counts (the physical correlator), not trusted from
        # the JSON's cached "E" field.
        "E": correlator_from_counts(counts),
        "counts": dict(counts),
        "shots": shots,
    }


def build_quantum_bell_episode(
    data: dict[str, Any],
    bell_state: str = "Phi_plus",
    held_out_setting: str = "a0_b2",
    mode: str = "eval",
) -> dict[str, Any]:
    """Build a quantum Bell certificate episode from real IBM CHSH data.

    Parameters
    ----------
    data : dict
        The parsed ``quantum-chsh-data.json`` (keys like ``"Phi_plus_a0_b1"``).
    bell_state : str
        Which Bell state's correlators to use (e.g. ``"Phi_plus"``).
    held_out_setting : str
        The CHSH setting whose correlator the carrier must predict (default
        ``"a0_b2"``, the MVP held-out point). Its counts live in
        ``evidence_only``; the carrier never sees them.
    mode : str
        ``"eval"`` (G silent) or ``"adaptation"`` (G feedback channel available).

    Returns
    -------
    dict
        Episode with ``model_visible_initial`` (3 training settings' correlators)
        and ``evidence_only`` (held-out setting's angles + raw counts).
    """
    if held_out_setting not in CHSH_SETTING_ANGLES:
        raise Iteration9QuantumEpisodeError(f"unknown held_out_setting: {held_out_setting!r}")
    if mode not in QUANTUM_MODES:
        raise Iteration9QuantumEpisodeError(f"unknown mode: {mode!r}")

    training_ids = [s for s in CHSH_SETTING_ANGLES if s != held_out_setting]
    training_settings = [
        _setting_record(data, bell_state, setting_id) for setting_id in training_ids
    ]
    # The training payload the carrier reads: the correlator and the geometry, no
    # held-out information whatsoever.
    visible_settings = [
        {
            "setting_id": rec["setting_id"],
            "alpha": rec["alpha"],
            "beta": rec["beta"],
            "E": rec["E"],
            "shots": rec["shots"],
        }
        for rec in training_settings
    ]

    held_out = _setting_record(data, bell_state, held_out_setting)
    held_out_alpha, held_out_beta = CHSH_SETTING_ANGLES[held_out_setting]

    model_visible_initial: dict[str, Any] = {
        "bell_state": bell_state,
        "world": {"settings": visible_settings},
        "consumer": {"name": "chsh_correlation_consumer"},
        # The held-out ANGLES are public (the carrier must know where to
        # extrapolate); only the held-out correlator/counts are hidden.
        "held_out_query": {
            "setting_id": held_out_setting,
            "alpha": held_out_alpha,
            "beta": held_out_beta,
        },
    }

    evidence_only: dict[str, Any] = {
        "held_out_setting": held_out_setting,
        "held_out_alpha": held_out_alpha,
        "held_out_beta": held_out_beta,
        "held_out_counts": held_out["counts"],
        "held_out_shots": held_out["shots"],
        "held_out_E_measured": held_out["E"],
        "bell_state": bell_state,
    }

    return {
        "schema_version": ITERATION9_QUANTUM_EPISODE_SCHEMA_VERSION,
        "mode": mode,
        "model_visible_initial": model_visible_initial,
        "evidence_only": evidence_only,
    }


def chsh_value(correlators: dict[str, float]) -> float:
    """Signed CHSH S over the four settings using ``CHSH_SIGNS``.

    ``correlators`` maps setting_id → E for all four settings. Returns the signed
    S; ``S > 2`` (CHSH_CLASSICAL_BOUND) certifies the correlations are outside the
    LHV polytope.
    """
    missing = set(CHSH_SIGNS) - set(correlators)
    if missing:
        raise Iteration9QuantumEpisodeError(f"chsh_value missing settings: {sorted(missing)}")
    return sum(CHSH_SIGNS[s] * float(correlators[s]) for s in CHSH_SIGNS)


def lhv_bound_on_held_out(training: dict[str, float], held_out_setting: str) -> float:
    """Minimum held-out correlator consistent with the LHV polytope (S ≤ 2).

    Given the three training correlators fixed, ``S = Σ signs·E ≤ 2`` rearranges
    to a one-sided bound on the held-out correlator. For ``held_out = a0_b2``
    (sign −1), ``S = T − E(a0_b2) ≤ 2`` ⇒ ``E(a0_b2) ≥ T − 2`` where ``T`` is the
    signed training sum. A classical carrier cannot predict below this floor.
    """
    sign = CHSH_SIGNS[held_out_setting]
    training_sum = sum(
        CHSH_SIGNS[s] * float(e) for s, e in training.items() if s != held_out_setting
    )
    # S = training_sum + sign * E_ho ≤ 2  ⇒  bound on E_ho.
    if sign < 0:
        # E_ho ≥ training_sum − 2
        return training_sum - CHSH_CLASSICAL_BOUND
    # sign > 0: E_ho ≤ 2 − training_sum (upper bound); return it for symmetry.
    return CHSH_CLASSICAL_BOUND - training_sum


__all__ = [
    "ITERATION9_QUANTUM_EPISODE_SCHEMA_VERSION",
    "ITERATION9_QUANTUM_CLAIM",
    "CHSH_SETTING_ANGLES",
    "CHSH_SIGNS",
    "CHSH_CLASSICAL_BOUND",
    "QUANTUM_MODES",
    "Iteration9QuantumEpisodeError",
    "correlator_from_counts",
    "shot_noise_se",
    "build_quantum_bell_episode",
    "chsh_value",
    "lhv_bound_on_held_out",
]
