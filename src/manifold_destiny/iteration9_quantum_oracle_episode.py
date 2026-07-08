"""Iteration 9 quantum oracle discovery — episode builder from real IBM data.

This builds the discovery episode from the real ``ibm_marrakesh`` angle-sweep
measurements (``quantum-expanded-data.json``). It is the oracle counterpart of the
MVP episode (``iteration9_quantum_episode``), but where the MVP handed the carrier
a quantum correlation curve to fit, this episode hands it NOTHING but raw
correlators and the held-out geometry. The carrier must DISCOVER the invariance.

The split
---------
* ``model_visible_initial.world.settings`` — the carrier's visible training: the
  full Alice-angle-0 sweep (24 Bob settings, all at ``alpha = 0``). The carrier
  reads these correlators; it copies from them at transfer time. Because every
  visible setting shares one Alice angle, the candidates ``R_diff``, ``R_sum`` and
  ``R_beta`` induce the SAME partition here — the carrier cannot tell them apart
  from its own data. That degeneracy is what forces it to consult G.
* ``evidence_only.discovery_settings`` — the second Alice angle's sweep
  (``alpha = pi/4``) joined with the Alice-0 sweep. ONLY G reads this. It is what
  breaks the degeneracy: across two Alice angles, ``R_sum``/``R_beta``/``R_alpha``
  acquire anti-witnesses while ``R_diff``/``R_absdiff`` stay homogeneous.
* ``evidence_only.held_out_*`` — the held-out setting ``a1_b2 = (pi/4, 3pi/8)``.
  The carrier NEVER measured anything at Alice angle ``pi/4``; it predicts this
  correlator by transfer through the discovered invariance. Its level partner at
  ``R_diff`` value ``-pi/8`` is the visible Alice-0 setting at ``beta = pi/8``.
* ``evidence_only.chsh_*`` — the three other CHSH correlators (real measurements
  G holds) plus the sign table, so G can run the non-classicality tier on the
  carrier's transferred prediction.

The non-locality is real and physical: a held-out correlator at an Alice angle the
carrier never probed, predicted purely by transfer, lands the four-setting CHSH
sum above the classical bound.
"""

from __future__ import annotations

import math
from typing import Any

from manifold_destiny.iteration9_quantum_episode import (
    correlator_from_counts,
    shot_noise_se,
)


ITERATION9_QUANTUM_ORACLE_EPISODE_SCHEMA_VERSION = (
    "manifold-destiny-quantum-oracle-episode-v1"
)
ITERATION9_QUANTUM_ORACLE_CLAIM = (
    "ITERATION_9_QUANTUM_ORACLE_DISCOVERED_INVARIANCE_NON_LOCAL_TRANSFER"
)

# Real ibm_marrakesh angle conventions (radians), matching the data _metadata.
ALICE_ANGLES = (0.0, math.pi / 4)
BOB_SWEEP_STEP = math.pi / 24
BOB_SWEEP_COUNT = 24

# The four canonical CHSH settings as (alice_index, bob_sweep_index). b1 = pi/8 is
# Bob sweep index 3; b2 = 3pi/8 is Bob sweep index 9.
CHSH_SWEEP_INDEX = {
    "a0_b1": (0, 3),
    "a0_b2": (0, 9),
    "a1_b1": (1, 3),
    "a1_b2": (1, 9),
}

# CHSH combination S = E(a0_b1) - E(a0_b2) + E(a1_b1) + E(a1_b2). The held-out
# default is a1_b2, which enters with coefficient +1.
CHSH_SIGNS = {"a0_b1": +1, "a0_b2": -1, "a1_b1": +1, "a1_b2": +1}

# Classical (local-hidden-variable) CHSH bound. S > 2 certifies non-classicality.
CHSH_CLASSICAL_BOUND = 2.0

DEFAULT_HELD_OUT_SETTING = "a1_b2"
QUANTUM_ORACLE_MODES = ("eval", "adaptation")


class Iteration9QuantumOracleEpisodeError(ValueError):
    """Raised when the oracle episode contract is malformed."""


def _bob_angle(index: int) -> float:
    return index * BOB_SWEEP_STEP


def _setting_id(alice_index: int, bob_index: int) -> str:
    return f"a{alice_index}_b{bob_index:02d}"


def _sweep_record(
    data: dict[str, Any], alice_index: int, bob_index: int
) -> dict[str, Any]:
    """Build a setting record from one angle-sweep measurement.

    Carries the geometry ``(alpha, beta)``, the correlator recomputed from raw
    counts, the shot-noise standard error, and the shot total.
    """
    key = f"anglesweep_a{alice_index}_b{bob_index:02d}"
    record = data.get(key)
    if type(record) is not dict:
        raise Iteration9QuantumOracleEpisodeError(f"absent sweep record for {key!r}")
    counts = record.get("counts")
    if type(counts) is not dict:
        raise Iteration9QuantumOracleEpisodeError(f"record {key!r} has no counts")
    shots = int(record.get("shots", 0))
    correlator = correlator_from_counts(counts)
    return {
        "setting_id": _setting_id(alice_index, bob_index),
        "alpha": ALICE_ANGLES[alice_index],
        "beta": _bob_angle(bob_index),
        "E": correlator,
        "se": shot_noise_se(correlator, shots),
        "counts": dict(counts),
        "shots": shots,
    }


def _visible_record(rec: dict[str, Any]) -> dict[str, Any]:
    """The carrier-visible projection of a setting (geometry + correlator)."""
    return {
        "setting_id": rec["setting_id"],
        "alpha": rec["alpha"],
        "beta": rec["beta"],
        "E": rec["E"],
        "se": rec["se"],
        "shots": rec["shots"],
    }


def build_quantum_oracle_episode(
    data: dict[str, Any],
    held_out_setting: str = DEFAULT_HELD_OUT_SETTING,
    mode: str = "eval",
) -> dict[str, Any]:
    """Build the oracle discovery episode from real angle-sweep data.

    Parameters
    ----------
    data : dict
        Parsed ``quantum-expanded-data.json`` (angle-sweep keys).
    held_out_setting : str
        The CHSH setting the carrier transfers to (default ``"a1_b2"``).
    mode : str
        ``"eval"`` or ``"adaptation"``.
    """
    if held_out_setting not in CHSH_SWEEP_INDEX:
        raise Iteration9QuantumOracleEpisodeError(
            f"unknown held_out_setting: {held_out_setting!r}"
        )
    if mode not in QUANTUM_ORACLE_MODES:
        raise Iteration9QuantumOracleEpisodeError(f"unknown mode: {mode!r}")

    # Carrier-visible training: the full Alice-0 sweep (one Alice angle only).
    visible_sweep = [_sweep_record(data, 0, j) for j in range(BOB_SWEEP_COUNT)]
    visible_settings = [_visible_record(rec) for rec in visible_sweep]

    # G's discovery support: both Alice angles' sweeps. Only G reads this; it is
    # what breaks the one-Alice-angle degeneracy at Tier A.
    discovery_settings: list[dict[str, Any]] = []
    for alice_index in (0, 1):
        for j in range(BOB_SWEEP_COUNT):
            discovery_settings.append(_visible_record(_sweep_record(data, alice_index, j)))

    # The held-out setting: an Alice angle the carrier never probed.
    ho_alice_index, ho_bob_index = CHSH_SWEEP_INDEX[held_out_setting]
    held_out = _sweep_record(data, ho_alice_index, ho_bob_index)

    # The three other CHSH correlators G holds for the non-classicality tier.
    chsh_correlators: dict[str, float] = {}
    for sid, (a_idx, b_idx) in CHSH_SWEEP_INDEX.items():
        if sid == held_out_setting:
            continue
        rec = _sweep_record(data, a_idx, b_idx)
        chsh_correlators[sid] = rec["E"]

    model_visible_initial: dict[str, Any] = {
        "world": {"settings": visible_settings},
        "consumer": {"name": "chsh_correlation_consumer"},
        "held_out_query": {
            "setting_id": held_out_setting,
            "alpha": held_out["alpha"],
            "beta": held_out["beta"],
        },
    }

    evidence_only: dict[str, Any] = {
        "discovery_settings": discovery_settings,
        "held_out_setting": held_out_setting,
        "held_out_alpha": held_out["alpha"],
        "held_out_beta": held_out["beta"],
        "held_out_counts": held_out["counts"],
        "held_out_shots": held_out["shots"],
        "held_out_E_measured": held_out["E"],
        "chsh_correlators": chsh_correlators,
        "chsh_signs": dict(CHSH_SIGNS),
    }

    return {
        "schema_version": ITERATION9_QUANTUM_ORACLE_EPISODE_SCHEMA_VERSION,
        "mode": mode,
        "held_out_setting": held_out_setting,
        "model_visible_initial": model_visible_initial,
        "evidence_only": evidence_only,
    }


def chsh_value(correlators: dict[str, float]) -> float:
    """Signed CHSH S over the four settings via ``CHSH_SIGNS``."""
    absent = set(CHSH_SIGNS) - set(correlators)
    if absent:
        raise Iteration9QuantumOracleEpisodeError(
            f"chsh_value absent settings: {sorted(absent)}"
        )
    return sum(CHSH_SIGNS[s] * float(correlators[s]) for s in CHSH_SIGNS)


__all__ = [
    "ITERATION9_QUANTUM_ORACLE_EPISODE_SCHEMA_VERSION",
    "ITERATION9_QUANTUM_ORACLE_CLAIM",
    "ALICE_ANGLES",
    "BOB_SWEEP_STEP",
    "BOB_SWEEP_COUNT",
    "CHSH_SWEEP_INDEX",
    "CHSH_SIGNS",
    "CHSH_CLASSICAL_BOUND",
    "DEFAULT_HELD_OUT_SETTING",
    "QUANTUM_ORACLE_MODES",
    "Iteration9QuantumOracleEpisodeError",
    "build_quantum_oracle_episode",
    "chsh_value",
]
