"""Iteration 9 quantum oracle discovery — lanes, falsifiers, verdict.

The adaptive lane must DISCOVER the invariance through G feedback and transfer the
held-out correlator; every falsifier lane must drop to failure. There is no
parameter to sweep — the carrier is a switchboard, one pass. The "sweep" is the
lane battery plus the entanglement ladder.

Lanes
-----
* ``adaptive`` — the carrier probes the catalog, G eliminates the wrong reductions,
  the survivors form ``M``, and the carrier transfers the held-out correlator
  through ``M``. Passes G (Tier A + transfer + Tier B).
* ``cold`` (``no_probe``) — the carrier commits a default reduction with NO probe.
  Its structural correctness is ``|surviving|/|catalog|`` (the floor), not 1.0.
* ``blank_data`` — strip G's discovery support; every probe returns ``no_data`` →
  nothing survives → the carrier abstains → fails. Probing is load-bearing.
* ``shuffle_settings`` — scramble the correlator↔geometry binding; every reduction
  acquires anti-witnesses → nothing survives → abstain → fails.
* ``classical_surrogate`` — local-realistic data (``S <= 2``). Tier A still passes
  (the triangle correlator is a function of ``|difference|``, so the structure is
  discovered) but Tier B reports ``classically_explicable`` → no certificate.
* ``entanglement_ladder`` — Tier B run across the real entanglement rungs; the
  certificate switches ON exactly where the measured ``S`` crosses ``2``.

Verdict: ``QUANTUM_ORACLE_DISCOVERY_VERIFIED`` iff adaptive passes and every
falsifier (blank, shuffle, classical surrogate) fails.
"""

from __future__ import annotations

import copy
from typing import Any

from manifold_destiny.iteration9_quantum_oracle_episode import (
    ALICE_ANGLES,
    BOB_SWEEP_COUNT,
    BOB_SWEEP_STEP,
    CHSH_SIGNS,
    CHSH_SWEEP_INDEX,
    ITERATION9_QUANTUM_ORACLE_CLAIM,
    build_quantum_oracle_episode,
    chsh_value,
)
from manifold_destiny.iteration9_quantum_oracle_reductions import (
    CATALOG_SIZE,
    REDUCTION_NAMES,
)
from manifold_destiny.iteration9_quantum_oracle_policy import (
    InvarianceDiscoveryCarrier,
    NoProbeColdCarrier,
)
from manifold_destiny.iteration9_quantum_oracle_verifier import (
    DELTA_MIN,
    GLUE_THROUGH,
    NON_CLASSICAL,
    quantum_oracle_objective,
    tier_a_probe,
    tier_b_nonclassicality,
)


ITERATION9_QUANTUM_ORACLE_EVALUATION_SCHEMA_VERSION = (
    "manifold-destiny-quantum-oracle-evaluation-v1"
)

ORACLE_ADAPTIVE_LANE = "adaptive"
ORACLE_FALSIFIER_LANES = ("blank_data", "shuffle_settings", "classical_surrogate")
ORACLE_LANE_ORDER = (ORACLE_ADAPTIVE_LANE,) + ORACLE_FALSIFIER_LANES

ORACLE_VERIFIED_VERDICT = "QUANTUM_ORACLE_DISCOVERY_VERIFIED"
ORACLE_NO_CLAIM_VERDICT = "QUANTUM_ORACLE_DISCOVERY_NO_CLAIM"


class Iteration9QuantumOracleEvaluationError(ValueError):
    """Raised when an evaluation boundary is violated."""


# ---------------------------------------------------------------------------
# G Tier A probe channel + true surviving class
# ---------------------------------------------------------------------------


def make_probe(episode: dict[str, Any]):
    """Return G's Tier A probe channel for ``episode``: name -> observation token.

    The carrier calls this and reads ONLY the token. The held-back discovery
    settings live behind it; the carrier never touches them.
    """
    settings = (episode.get("evidence_only", {}) or {}).get("discovery_settings", [])

    def probe(reduction_name: str) -> str:
        return tier_a_probe(reduction_name, settings)["kind"]

    return probe


def true_surviving_class(episode: dict[str, Any]) -> list[str]:
    """The reductions that actually glue through on the episode's real data."""
    settings = (episode.get("evidence_only", {}) or {}).get("discovery_settings", [])
    return [
        name
        for name in REDUCTION_NAMES
        if tier_a_probe(name, settings)["kind"] == GLUE_THROUGH
    ]


# ---------------------------------------------------------------------------
# Surrogate / shuffle data builders
# ---------------------------------------------------------------------------


def _counts_for_correlator(correlator: float, shots: int = 4000) -> dict[str, int]:
    """Synthesize counts whose recovered correlator is ``correlator``."""
    correlator = max(-1.0, min(1.0, correlator))
    n_same = round(shots * (1.0 + correlator) / 2.0)
    n_diff = shots - n_same
    n00 = n_same // 2
    n11 = n_same - n00
    n01 = n_diff // 2
    n10 = n_diff - n01
    return {"00": int(n00), "11": int(n11), "01": int(n01), "10": int(n10)}


def _triangle_lhv_correlator(alpha: float, beta: float) -> float:
    """Optimal local-realistic correlator: a tent in ``|difference|``.

    ``E = 1 - (2/pi)*|wrapped difference|`` traces the local-hidden-variable
    polytope boundary; it gives CHSH ``S = 2`` exactly on the Bell angles — the
    most a classical account can do. It is a function of ``|alpha - beta|`` only,
    so it has structure (Tier A passes) yet is classically explicable (Tier B
    fails). No quantum curve is involved.
    """
    import math

    delta = abs(alpha - beta) % (2 * math.pi)
    if delta > math.pi:
        delta = 2 * math.pi - delta
    return 1.0 - (2.0 / math.pi) * delta


def build_classical_surrogate_data(shots: int = 4000) -> dict[str, Any]:
    """Build a fully local-realistic angle-sweep dataset (``S <= 2``).

    Both Alice angles' sweeps follow the triangle correlator, so the structure is
    real (a function of ``|difference|``) and the carrier discovers it, but the
    four-setting CHSH sum never clears the classical bound.
    """
    data: dict[str, Any] = {}
    for alice_index, alpha in enumerate(ALICE_ANGLES):
        for j in range(BOB_SWEEP_COUNT):
            beta = j * BOB_SWEEP_STEP
            e = _triangle_lhv_correlator(alpha, beta)
            data[f"anglesweep_a{alice_index}_b{j:02d}"] = {
                "counts": _counts_for_correlator(e, shots),
                "shots": shots,
            }
    return data


# Deterministic coprime stride for the scramble permutation. 7 is coprime to the
# 48-setting grid, so ``i -> (i*7 + 1) mod 48`` is a genuine permutation with no
# algebraic relation to the geometry; it refutes every reduction (verified).
SHUFFLE_STRIDE = 7


def shuffle_settings_data(data: dict[str, Any]) -> dict[str, Any]:
    """Scramble the correlator↔geometry binding via a coprime-stride permutation.

    The geometry stays keyed by index in the episode builder, but each key now
    carries a different setting's counts, so every reduction's level sets become
    inhomogeneous — anti-witnesses everywhere, nothing survives, the carrier
    abstains.
    """
    shuffled = copy.deepcopy(data)
    keys = [
        f"anglesweep_a{a}_b{j:02d}"
        for a in range(len(ALICE_ANGLES))
        for j in range(BOB_SWEEP_COUNT)
    ]
    originals = [data[k] for k in keys]
    n = len(keys)
    for i, k in enumerate(keys):
        shuffled[k] = copy.deepcopy(originals[(i * SHUFFLE_STRIDE + 1) % n])
    return shuffled


# ---------------------------------------------------------------------------
# Lane execution
# ---------------------------------------------------------------------------


def _run_lane(lane: str, data: dict[str, Any], held_out_setting: str) -> dict[str, Any]:
    if lane == "blank_data":
        episode = build_quantum_oracle_episode(data, held_out_setting, "eval")
        episode["evidence_only"]["discovery_settings"] = []
        episode["model_visible_initial"]["world"]["settings"] = []
        carrier = InvarianceDiscoveryCarrier()
    elif lane == "shuffle_settings":
        episode = build_quantum_oracle_episode(
            shuffle_settings_data(data), held_out_setting, "eval"
        )
        carrier = InvarianceDiscoveryCarrier()
    elif lane == "classical_surrogate":
        episode = build_quantum_oracle_episode(
            build_classical_surrogate_data(), held_out_setting, "eval"
        )
        carrier = InvarianceDiscoveryCarrier()
    else:  # adaptive
        episode = build_quantum_oracle_episode(data, held_out_setting, "eval")
        carrier = InvarianceDiscoveryCarrier()

    proposal = carrier.propose(episode, make_probe(episode))
    g_result = quantum_oracle_objective(episode, proposal)
    return {
        "lane": lane,
        "passed": g_result["verdict"] == "accepted",
        "proposal": proposal,
        "g_result": g_result,
    }


def run_cold_lane(data: dict[str, Any], held_out_setting: str) -> dict[str, Any]:
    """No-probe cold lane: blind commit; correctness = |surviving|/|catalog|."""
    episode = build_quantum_oracle_episode(data, held_out_setting, "eval")
    carrier = NoProbeColdCarrier()
    proposal = carrier.propose(episode, make_probe(episode))
    g_result = quantum_oracle_objective(episode, proposal)
    survivors = true_surviving_class(episode)
    correctness = len(survivors) / CATALOG_SIZE
    return {
        "lane": "no_probe",
        "passed": g_result["verdict"] == "accepted",
        "structural_correctness": correctness,
        "surviving_class": survivors,
        "catalog_size": CATALOG_SIZE,
        "proposal": proposal,
        "g_result": g_result,
    }


# ---------------------------------------------------------------------------
# Entanglement ladder
# ---------------------------------------------------------------------------


def _ladder_tag(theta: float) -> str:
    return f"t{int(theta * 1000):04d}"


def run_entanglement_ladder(data: dict[str, Any]) -> dict[str, Any]:
    """Run Tier B across the real entanglement rungs.

    For each rung the four CHSH correlators are read directly from the
    ``entangle_t*_s*`` records (s0..s3 = a0_b1, a0_b2, a1_b1, a1_b2). The held-out
    is ``a1_b2`` (its measured correlator stands in for the transferred one). The
    certificate switches ON exactly where the measured ``S`` clears ``2``.
    """
    from manifold_destiny.iteration9_quantum_episode import correlator_from_counts

    meta = data.get("_metadata", {}) or {}
    thetas = sorted(meta.get("entanglement_thetas", []) or [])
    slot_to_setting = ["a0_b1", "a0_b2", "a1_b1", "a1_b2"]
    rungs = []
    for theta in thetas:
        tag = _ladder_tag(theta)
        correlators: dict[str, float] = {}
        ok = True
        for slot, sid in enumerate(slot_to_setting):
            rec = data.get(f"entangle_{tag}_s{slot}")
            if type(rec) is not dict or "counts" not in rec:
                ok = False
                break
            correlators[sid] = correlator_from_counts(rec["counts"])
        if not ok:
            continue
        held_out = "a1_b2"
        known = {k: v for k, v in correlators.items() if k != held_out}
        tier_b = tier_b_nonclassicality(known, held_out, correlators[held_out])
        s_value = chsh_value(correlators)
        rungs.append({
            "theta": theta,
            "chsh_S": s_value,
            "certificate_on": tier_b["classification"] == NON_CLASSICAL,
            "classification": tier_b["classification"],
        })
    # The switch is monotone: find the boundary theta where it turns ON.
    switch_on_theta = next((r["theta"] for r in rungs if r["certificate_on"]), None)
    return {
        "schema_version": ITERATION9_QUANTUM_ORACLE_EVALUATION_SCHEMA_VERSION,
        "rungs": rungs,
        "switch_on_theta": switch_on_theta,
        "bound": 2.0 + DELTA_MIN,
    }


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------


def run_quantum_oracle_evaluation(
    data: dict[str, Any], held_out_setting: str = "a1_b2"
) -> dict[str, Any]:
    """Run the adaptive lane and every falsifier, then render the verdict."""
    lanes = {
        lane: _run_lane(lane, data, held_out_setting) for lane in ORACLE_LANE_ORDER
    }
    cold = run_cold_lane(data, held_out_setting)

    adaptive_passed = lanes[ORACLE_ADAPTIVE_LANE]["passed"]
    falsifiers_failed = {
        lane: (not lanes[lane]["passed"]) for lane in ORACLE_FALSIFIER_LANES
    }
    all_falsifiers_failed = all(falsifiers_failed.values())
    verified = adaptive_passed and all_falsifiers_failed

    return {
        "schema_version": ITERATION9_QUANTUM_ORACLE_EVALUATION_SCHEMA_VERSION,
        "claim": ITERATION9_QUANTUM_ORACLE_CLAIM if verified else None,
        "held_out_setting": held_out_setting,
        "lane_order": list(ORACLE_LANE_ORDER),
        "lanes": lanes,
        "cold": cold,
        "adaptive_passed": adaptive_passed,
        "falsifiers_failed": falsifiers_failed,
        "all_falsifiers_failed": all_falsifiers_failed,
        "verdict": ORACLE_VERIFIED_VERDICT if verified else ORACLE_NO_CLAIM_VERDICT,
    }


__all__ = [
    "ITERATION9_QUANTUM_ORACLE_EVALUATION_SCHEMA_VERSION",
    "ORACLE_ADAPTIVE_LANE",
    "ORACLE_FALSIFIER_LANES",
    "ORACLE_LANE_ORDER",
    "ORACLE_VERIFIED_VERDICT",
    "ORACLE_NO_CLAIM_VERDICT",
    "Iteration9QuantumOracleEvaluationError",
    "make_probe",
    "true_surviving_class",
    "build_classical_surrogate_data",
    "shuffle_settings_data",
    "run_cold_lane",
    "run_entanglement_ladder",
    "run_quantum_oracle_evaluation",
]
