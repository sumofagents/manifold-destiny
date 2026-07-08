"""Iteration 9 quantum oracle discovery — the carrier (a dumb switchboard).

``InvarianceDiscoveryCarrier`` is NOT a model. It has no weights, no forward pass,
no generation, no reasoning. It does three things, exactly like the synthetic
``GluingAdaptivePolicy._infer_gluing`` it is copied from:

  1. PROBE   — try a candidate reduction from the fixed catalog, in catalog order.
  2. REMEMBER — G answers ``glue_through`` or ``anti_witness``.
  3. ELIMINATE — discard the refuted candidates; keep the survivors.

What survives is the discovered invariance class ``M``. There is NO supplied
functional form: the carrier is never handed a correlation curve, a measurement postulate, or
a visibility parameter. It is handed a yes/no feedback channel and a menu of
generic algebraic candidates, and it discovers which ones are right by elimination.

Prediction is APPLIED INVARIANCE, never a fit. To predict the held-out correlator
the carrier maps the held-out geometry through the discovered reduction to its
level value, finds a visible training setting at that same level value, and COPIES
that setting's measured correlator. No interpolation, no curve, no parameters.

Why the probe is load-bearing
-----------------------------
The carrier's visible training is recorded at one Alice angle. On that data,
``R_diff``, ``R_sum`` and ``R_beta`` induce the identical partition — the carrier
cannot tell them apart from what it reads. Only G's feedback (which folds in the
second Alice angle the carrier never measured) separates them. Deny the probe
(``no_probe`` cold lane) and the carrier must commit a candidate blind; its
expected correctness is then only ``|surviving| / |catalog|``, the structural
floor. Blank the data and every probe returns ``no_data``; the carrier abstains.
"""

from __future__ import annotations

from typing import Any, Callable

from manifold_destiny.iteration9_quantum_oracle_reductions import (
    REDUCTION_NAMES,
    reduction_value,
)
from manifold_destiny.iteration9_quantum_oracle_verifier import (
    ANTI_WITNESS,
    GLUE_THROUGH,
)


ITERATION9_QUANTUM_ORACLE_POLICY_SCHEMA_VERSION = (
    "manifold-destiny-quantum-oracle-policy-v1"
)

# Deterministic blind commit for the no-probe cold lane. A fixed candidate so the
# |surviving|/|catalog| floor is structural, not drawn at random.
COLD_DEFAULT_REDUCTION = REDUCTION_NAMES[0]

# Probe order is catalog order; the transferred reduction is the first survivor in
# this order, so the choice is deterministic.
PROBE_ORDER = REDUCTION_NAMES


ProbeFn = Callable[[str], str]


class InvarianceDiscoveryCarrier:
    """Dumb switchboard: probe candidates, remember G's yes/no, eliminate."""

    schema_version = ITERATION9_QUANTUM_ORACLE_POLICY_SCHEMA_VERSION

    def discover(self, probe: ProbeFn) -> dict[str, Any]:
        """Probe each candidate; keep the ``glue_through`` survivors.

        ``probe(name)`` is G's Tier A channel: it returns ``glue_through`` (the
        invariance holds), ``anti_witness`` (refuted), or ``no_data`` (nothing to
        test). The carrier reads ONLY this token — never the held-back data behind
        it. If no probe yields any usable signal (all ``no_data``), the carrier has
        learned nothing and the surviving class is empty.
        """
        survivors: list[str] = []
        trace: list[dict[str, str]] = []
        any_signal = False
        for name in PROBE_ORDER:
            token = probe(name)
            trace.append({"reduction": name, "observation": token})
            if token == GLUE_THROUGH:
                survivors.append(name)
                any_signal = True
            elif token == ANTI_WITNESS:
                any_signal = True
        if not any_signal:
            survivors = []
        return {
            "discovered_class": survivors,
            "probe_trace": trace,
            "probes_spent": len(trace),
        }

    def predict(
        self,
        visible_settings: list[dict[str, Any]],
        held_out_angles: tuple[float, float],
        transfer_reduction: str,
    ) -> tuple[float | None, str | None]:
        """Apply the discovered invariance: copy an equivalent setting's correlator.

        Map the held-out geometry through ``transfer_reduction`` to its level
        value, find a visible training setting at that same value, and copy its
        correlator. Returns ``(predicted_E, source_setting_id)`` or ``(None, None)``
        if no equivalent training setting exists or the data is blank.
        """
        alpha, beta = held_out_angles
        target = reduction_value(transfer_reduction, alpha, beta)
        for rec in visible_settings or []:
            try:
                value = reduction_value(transfer_reduction, rec["alpha"], rec["beta"])
                e = float(rec["E"])
            except (KeyError, TypeError, ValueError):
                continue
            if value == target:
                return e, rec.get("setting_id")
        return None, None

    def propose(self, episode: dict[str, Any], probe: ProbeFn) -> dict[str, Any]:
        """Discover the invariance through G, then transfer to the held-out.

        Abstains (``predicted_E = None``) if nothing survives or no equivalent
        training setting backs the transfer — the two load-bearing failure paths.
        """
        discovery = self.discover(probe)
        survivors = discovery["discovered_class"]
        model_visible = episode.get("model_visible_initial", {}) or {}
        query = model_visible.get("held_out_query", {}) or {}
        visible_settings = (model_visible.get("world", {}) or {}).get("settings", []) or []

        if not survivors:
            return {
                "predicted_E": None,
                "discovered_class": [],
                "transfer_reduction": None,
                "transfer_source_setting_id": None,
                "abstained": True,
                "reason": "no_structure_discovered",
                "probe_trace": discovery["probe_trace"],
                "probes_spent": discovery["probes_spent"],
            }

        transfer_reduction = survivors[0]
        try:
            held_out_angles = (float(query["alpha"]), float(query["beta"]))
        except (KeyError, TypeError, ValueError):
            held_out_angles = None

        predicted_e, source = (
            self.predict(visible_settings, held_out_angles, transfer_reduction)
            if held_out_angles is not None
            else (None, None)
        )
        if predicted_e is None:
            return {
                "predicted_E": None,
                "discovered_class": survivors,
                "transfer_reduction": transfer_reduction,
                "transfer_source_setting_id": None,
                "abstained": True,
                "reason": "no_transfer_partner",
                "probe_trace": discovery["probe_trace"],
                "probes_spent": discovery["probes_spent"],
            }

        return {
            "predicted_E": predicted_e,
            "discovered_class": survivors,
            "transfer_reduction": transfer_reduction,
            "transfer_source_setting_id": source,
            "abstained": False,
            "probe_trace": discovery["probe_trace"],
            "probes_spent": discovery["probes_spent"],
        }


class NoProbeColdCarrier(InvarianceDiscoveryCarrier):
    """Cold foil: commits a fixed candidate blind, with no G feedback.

    It never probes. It declares ``COLD_DEFAULT_REDUCTION`` as its sole survivor
    and transfers through it. Its discovery is unverified — the structural
    correctness of a blind commit over the catalog is ``|surviving|/|catalog|``,
    computed in the evaluation, not 1.0. This is the no-probe floor.
    """

    def propose(self, episode: dict[str, Any], probe: ProbeFn) -> dict[str, Any]:
        model_visible = episode.get("model_visible_initial", {}) or {}
        query = model_visible.get("held_out_query", {}) or {}
        visible_settings = (model_visible.get("world", {}) or {}).get("settings", []) or []
        transfer_reduction = COLD_DEFAULT_REDUCTION
        try:
            held_out_angles = (float(query["alpha"]), float(query["beta"]))
        except (KeyError, TypeError, ValueError):
            held_out_angles = None
        predicted_e, source = (
            self.predict(visible_settings, held_out_angles, transfer_reduction)
            if held_out_angles is not None
            else (None, None)
        )
        return {
            "predicted_E": predicted_e,
            "discovered_class": [transfer_reduction],
            "transfer_reduction": transfer_reduction,
            "transfer_source_setting_id": source,
            "abstained": predicted_e is None,
            "no_probe": True,
            "probes_spent": 0,
        }


__all__ = [
    "ITERATION9_QUANTUM_ORACLE_POLICY_SCHEMA_VERSION",
    "COLD_DEFAULT_REDUCTION",
    "PROBE_ORDER",
    "InvarianceDiscoveryCarrier",
    "NoProbeColdCarrier",
]
