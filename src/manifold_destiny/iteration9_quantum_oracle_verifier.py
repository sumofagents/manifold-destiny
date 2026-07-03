"""Iteration 9 quantum oracle discovery — the two-tier verifier G.

G never tells the carrier a number is wrong. It speaks only about STRUCTURE. There
are two tiers.

Tier A — collapse consistency (discovers the invariance)
--------------------------------------------------------
For a probed candidate ``R_i``, G bins every measurement setting it holds by the
``R_i`` value and asks whether each bin is HOMOGENEOUS in the correlator. If two
settings the carrier claims are equivalent (same ``R_i`` value) have correlators
that differ by more than ``K_SIGMA * (se1 + se2)``, that pair is an ANTI-WITNESS
and ``R_i`` is refuted (``anti_witness``). If every bin is homogeneous the
candidate survives (``glue_through``). G never says "your value is wrong"; it says
"settings you called equivalent are not", or "your invariance holds".

Tier B — non-classicality (the Bell load)
-----------------------------------------
Once Tier A pins the invariance and the carrier transfers a held-out correlator
through it, G assembles the four-setting CHSH sum from the three real correlators
it holds plus the carrier's transferred prediction, and computes ``S``. If
``S <= 2 + delta`` the structure is classically explicable — Tier B reports
``classically_explicable`` and NO certificate is issued. If ``S > 2 + delta`` the
local-hidden-variable account is refuted. Classical data passes Tier A (it has a
structure too) but fails Tier B; that is exactly the cut a Bell certificate makes.

There is no quantum formula here. Tier A is a homogeneity test on raw correlators;
Tier B is a polytope-bound check on a signed sum. No correlation curve, no
measurement postulate, no visibility parameter anywhere.
"""

from __future__ import annotations

from typing import Any

from manifold_destiny.iteration9_quantum_oracle_episode import (
    CHSH_CLASSICAL_BOUND,
    Iteration9QuantumOracleEpisodeError,
    chsh_value,
)
from manifold_destiny.iteration9_quantum_oracle_reductions import (
    level_sets,
    reduction_value,
)


ITERATION9_QUANTUM_ORACLE_VERIFIER_SCHEMA_VERSION = (
    "manifold-destiny-quantum-oracle-verifier-v1"
)

# Tier A homogeneity band: two settings in one level set are an anti-witness if
# their correlators differ by more than this many summed standard errors.
K_SIGMA = 3.0

# Tier B margin: S must clear 2 + DELTA_MIN, not merely 2, so a borderline
# classical dataset cannot squeak through on noise.
DELTA_MIN = 0.05

# Transfer accuracy band: the transferred prediction must land within this many
# shot-noise SEs of the real held-out correlator (the transfer is real).
ACCURACY_SIGMA = 4.0

# Transfer-consistency band: the predicted correlator must equal the correlator of
# a same-level-set visible setting (it is a COPY, not a fit). Allowed slack is the
# summed shot noise of the two correlators times this factor.
TRANSFER_CONSISTENCY_SIGMA = 4.0


# Tier A observation tokens.
GLUE_THROUGH = "glue_through"
ANTI_WITNESS = "anti_witness"
NO_DATA = "no_data"

# Tier B classification tokens.
CLASSICALLY_EXPLICABLE = "classically_explicable"
NON_CLASSICAL = "non_classical"


class Iteration9QuantumOracleVerifierError(ValueError):
    """Raised when G is handed a malformed oracle episode."""


def _discovery_settings(episode: dict[str, Any]) -> list[dict[str, Any]]:
    settings = (episode.get("evidence_only", {}) or {}).get("discovery_settings", [])
    return settings if type(settings) is list else []


def tier_a_probe(
    reduction_name: str,
    settings: list[dict[str, Any]],
    k_sigma: float = K_SIGMA,
) -> dict[str, Any]:
    """Tier A: bin ``settings`` by ``reduction_name`` and test bin homogeneity.

    Returns a structured observation with ``kind`` in ``{glue_through,
    anti_witness, no_data}``. On ``anti_witness`` the offending pair is reported.
    """
    if len(settings) < 2:
        return {"kind": NO_DATA, "reduction": reduction_name}

    partition = level_sets(reduction_name, settings)
    for value, bucket in partition.items():
        for i in range(len(bucket)):
            for j in range(i + 1, len(bucket)):
                a, b = bucket[i], bucket[j]
                try:
                    ea, eb = float(a["E"]), float(b["E"])
                    sea, seb = float(a["se"]), float(b["se"])
                except (KeyError, TypeError, ValueError):
                    continue
                if abs(ea - eb) > k_sigma * (sea + seb):
                    return {
                        "kind": ANTI_WITNESS,
                        "reduction": reduction_name,
                        "level_value": value,
                        "anti_witness": {
                            "a": a.get("setting_id"),
                            "b": b.get("setting_id"),
                            "E_a": ea,
                            "E_b": eb,
                            "gap": abs(ea - eb),
                            "tolerance": k_sigma * (sea + seb),
                        },
                    }
    return {"kind": GLUE_THROUGH, "reduction": reduction_name}


def tier_b_nonclassicality(
    chsh_correlators: dict[str, float],
    held_out_setting: str,
    predicted_e: float,
    delta_min: float = DELTA_MIN,
) -> dict[str, Any]:
    """Tier B: assemble the CHSH sum and classify against the classical bound."""
    correlators = {k: float(v) for k, v in (chsh_correlators or {}).items()}
    correlators[held_out_setting] = float(predicted_e)
    try:
        s_value = chsh_value(correlators)
    except Iteration9QuantumOracleEpisodeError:
        return {"classification": CLASSICALLY_EXPLICABLE, "reason": "incomplete_chsh"}
    non_classical = abs(s_value) > CHSH_CLASSICAL_BOUND + delta_min
    return {
        "classification": NON_CLASSICAL if non_classical else CLASSICALLY_EXPLICABLE,
        "chsh_S": s_value,
        "bound": CHSH_CLASSICAL_BOUND + delta_min,
        "non_classical": non_classical,
    }


def _transfer_consistency(
    episode: dict[str, Any],
    transfer_reduction: str,
    predicted_e: float,
) -> dict[str, Any]:
    """Check the prediction is a COPY from a same-level-set visible setting.

    G recomputes the reduction value at the held-out geometry, finds the
    carrier-visible settings that share that value, and confirms the prediction
    equals one of their correlators (within shot noise). This is what enforces
    "applied invariance, not a fit": the predicted number must be a correlator the
    carrier literally read off an equivalent training setting.
    """
    evidence = episode.get("evidence_only", {}) or {}
    visible = (
        (episode.get("model_visible_initial", {}) or {}).get("world", {}) or {}
    ).get("settings", []) or []
    try:
        ho_alpha = float(evidence["held_out_alpha"])
        ho_beta = float(evidence["held_out_beta"])
    except (KeyError, TypeError, ValueError):
        return {"ok": False, "reason": "absent_held_out_geometry"}

    target_value = reduction_value(transfer_reduction, ho_alpha, ho_beta)
    partners = [
        rec
        for rec in visible
        if reduction_value(transfer_reduction, rec.get("alpha"), rec.get("beta"))
        == target_value
    ]
    if not partners:
        return {"ok": False, "reason": "no_level_partner_in_training"}

    best = None
    for rec in partners:
        try:
            e = float(rec["E"])
            se = float(rec["se"])
        except (KeyError, TypeError, ValueError):
            continue
        gap = abs(e - float(predicted_e))
        tol = TRANSFER_CONSISTENCY_SIGMA * (se + se)
        if best is None or gap < best["gap"]:
            best = {"gap": gap, "tolerance": tol, "partner": rec.get("setting_id")}
        if gap <= tol:
            return {"ok": True, "partner": rec.get("setting_id"), "gap": gap, "tolerance": tol}
    return {"ok": False, "reason": "prediction_not_a_copy", **(best or {})}


def quantum_oracle_objective(episode: dict[str, Any], proposal: Any) -> dict[str, Any]:
    """Score a carrier proposal under the conjunction of the two tiers.

    The proposal carries ``discovered_class`` (the carrier's surviving reductions),
    ``transfer_reduction`` (the survivor it transferred through), and
    ``predicted_E`` (the transferred correlator). G re-verifies every claimed
    survivor at Tier A (the carrier cannot claim a refuted structure), confirms the
    prediction is a real copy through that invariance and matches the held-out
    within shot noise, and finally runs Tier B.
    """
    if type(proposal) is not dict or proposal.get("predicted_E") is None:
        return _reject("abstained_or_malformed_proposal")

    evidence = episode.get("evidence_only", {}) or {}
    held_out_setting = evidence.get("held_out_setting")
    signs = evidence.get("chsh_signs", {}) or {}
    if held_out_setting not in signs:
        return _reject("unknown_held_out_setting")

    try:
        predicted_e = float(proposal["predicted_E"])
    except (TypeError, ValueError):
        return _reject("malformed_prediction")

    discovered_class = list(proposal.get("discovered_class") or [])
    transfer_reduction = proposal.get("transfer_reduction")

    # --- Tier A: re-verify every claimed survivor ----------------------------
    settings = _discovery_settings(episode)
    tier_a_detail: dict[str, str] = {}
    all_survive = bool(discovered_class)
    for name in discovered_class:
        obs = tier_a_probe(name, settings)
        tier_a_detail[name] = obs["kind"]
        if obs["kind"] != GLUE_THROUGH:
            all_survive = False
    transfer_ok = (
        transfer_reduction in discovered_class
        and tier_a_detail.get(transfer_reduction) == GLUE_THROUGH
    )
    tier_a_ok = all_survive and transfer_ok

    # --- transfer consistency: the prediction is a copy through the invariance -
    consistency = (
        _transfer_consistency(episode, transfer_reduction, predicted_e)
        if transfer_reduction
        else {"ok": False, "reason": "no_transfer_reduction"}
    )

    # --- accuracy: the transferred value matches the real held-out ------------
    try:
        from manifold_destiny.iteration9_quantum_episode import (
            correlator_from_counts,
            shot_noise_se,
        )

        measured_e = correlator_from_counts(evidence["held_out_counts"])
        shots = int(evidence["held_out_shots"])
        se = shot_noise_se(measured_e, shots)
    except (KeyError, TypeError, ValueError, Iteration9QuantumOracleEpisodeError):
        return _reject("malformed_held_out_evidence")
    accuracy_tol = ACCURACY_SIGMA * se
    accuracy_residual = abs(predicted_e - measured_e)
    accuracy_ok = accuracy_residual <= accuracy_tol

    # --- Tier B: non-classicality --------------------------------------------
    tier_b = tier_b_nonclassicality(
        evidence.get("chsh_correlators", {}), held_out_setting, predicted_e
    )
    tier_b_ok = tier_b.get("non_classical", False)

    verdict_bool = tier_a_ok and bool(consistency.get("ok")) and accuracy_ok and tier_b_ok
    return {
        "verdict": "accepted" if verdict_bool else "rejected",
        "tier_a": {
            "ok": tier_a_ok,
            "survivors": tier_a_detail,
            "transfer_reduction": transfer_reduction,
            "transfer_survives": transfer_ok,
        },
        "transfer_consistency": consistency,
        "accuracy": {
            "ok": accuracy_ok,
            "predicted_E": predicted_e,
            "measured_E": measured_e,
            "residual": accuracy_residual,
            "tolerance": accuracy_tol,
        },
        "tier_b": tier_b,
    }


def _reject(reason_code: str) -> dict[str, Any]:
    return {
        "verdict": "rejected",
        "reason_code": reason_code,
        "tier_a": {"ok": False},
        "transfer_consistency": {"ok": False},
        "accuracy": {"ok": False},
        "tier_b": {"classification": CLASSICALLY_EXPLICABLE, "non_classical": False},
    }


__all__ = [
    "ITERATION9_QUANTUM_ORACLE_VERIFIER_SCHEMA_VERSION",
    "K_SIGMA",
    "DELTA_MIN",
    "ACCURACY_SIGMA",
    "TRANSFER_CONSISTENCY_SIGMA",
    "GLUE_THROUGH",
    "ANTI_WITNESS",
    "NO_DATA",
    "CLASSICALLY_EXPLICABLE",
    "NON_CLASSICAL",
    "Iteration9QuantumOracleVerifierError",
    "tier_a_probe",
    "tier_b_nonclassicality",
    "quantum_oracle_objective",
]
