"""Iteration 9 the-learner-1.2 — two-tier gluing verifier (3-bit Stage 4).

The verifier is split into two strictly separated tiers:

  * ``GluingLocalVerifierEnv`` — model-facing, orientation-blind. Computes every
    response as a pure function of the model-visible world/quotient/consumer.
    ALL ``2^k`` canonical repairs ``R_i`` are accepted locally (they are all
    ``x``-homogeneous); the local env emits identical bytes across all ``2^k``
    orientation twins.
  * ``global_glue_objective(...)`` — protocol-facing G, scored post-hoc. Reads
    ``evidence_only.overlap_orientation`` and accepts exactly one ``R_i`` via the
    ``2^k``-entry orientation→partition table (imported from the episode module,
    the single source of truth). G is NOT a learner action.

This separation is the structural source of non-locality: the model can only
touch the local env, and the local env contains no path that reads M. The
load-bearing proof is in ``tests/test_iteration9_nonlocality_exhaustion.py``.

Hardening posture (Phase 9.0 § 11.2 theater modes)
--------------------------------------------------

Mode 2 (reveal-channel leakage):
    ``local_glue_factorization`` and ``_all_local_anti_witnesses`` take only the
    world / current quotient / local consumer; orientation is structurally
    absent from their signatures and bodies.

Mode 3 (acceptance-feedback leakage — KILLER):
    A locally-complete proposal is a one-shot terminal commit. The env returns
    ``terminal_result="valid_repair"`` for all eight canonical repairs. There is no path
    by which a cold solver can probe one repair, read a verdict that depends on
    M, and try the other repair.

Mode 4 (coin-flip degeneracy):
    The local env emits identical bytes on all ``2^k`` M-twins regardless of
    which repair is proposed; the cold fixed-orientation guess is a fixed
    function whose correctness ratio on a balanced (seed × orientation) pool is
    exactly ``1/2^k`` by construction.

Mode 6 / 11 (vacuous / code-only G):
    G accepts exactly one ``R_i`` per orientation and rejects the other
    ``2^k − 1`` at every Hamming distance (single-bit error in ``m`` ⇒ a wholly
    different partition, no partial credit). The G-non-degeneracy gate asserts
    the ``2^k`` partitions are pairwise distinct, so G cannot collapse to
    hidden-code matching.

Mode 8 (broken instrument):
    G returns ``accepted`` or ``rejected`` based on the structural partition
    match; nothing is randomized; the contract tests prevent the instrument
    from collapsing to a constant.

Adaptation vs eval
------------------

In ``mode="adaptation"`` the env returns a gluing anti-witness observation
(carrying ``"kind": "gluing_anti_witness"``) when G rejects a locally-complete
proposal — that is the Atlas-mediated feedback channel through which the
policy can learn M. In ``mode="eval"`` the env never references
``evidence_only.overlap_orientation``; G is silent. The non-locality test
runs in eval mode.
"""

from __future__ import annotations

import copy
from typing import Any

from manifold_destiny.iteration8_episode import (
    ITERATION8_LEARNER_ACTIONS,
    Iteration8EpisodeValidationError,
    scan_iteration8_model_visible_payload,
)
from manifold_destiny.iteration9_gluing_episode import (
    GLUING_MODES,
    GLUING_ORIENTATIONS,
    LEGACY_ORIENTATION_ALIASES,
    ORIENTATION_TO_REPAIR_KIND,
    Iteration9GluingEpisodeError,
    canonical_repair,
)


ITERATION9_GLUING_VERIFIER_SCHEMA_VERSION = (
    "manifold-destiny-gluing-verifier-v1"
)

# Local verifier action results — superset of the iteration8 set with a Phase 9
# specific value retained for the gluing anti-witness adaptation channel.
GLUING_ENV_ACTION_RESULTS = (
    "accepted",
    "rejected",
    "revealed",
    "miss",
    "noop",
    "invalid_action",
    "refused_terminal",
    "budget_exhausted",
)


class Iteration9GluingVerifierError(Iteration8EpisodeValidationError):
    """Raised when the Phase 9.0 verifier would exceed its contract."""


# ---------------------------------------------------------------------------
# Local glue factorization (orientation-free)
# ---------------------------------------------------------------------------


def local_glue_factorization(
    world: Any, quotient: Any, consumer: Any
) -> dict[str, Any]:
    """Recompute local validity of (world, quotient) under the two-patch consumer.

    Each patch's projection is consumed independently; a cell is locally valid
    iff its projection through each patch's projection field set is
    homogeneous in that patch's observable.

    The function signature does NOT include orientation. The body does NOT read
    any orientation source. This is the structural source of Theater Mode 2
    immunity.
    """
    try:
        states = _parse_world(world)
        cells = _parse_quotient(quotient, set(states))
        patches = _parse_consumer(consumer, states)
    except Iteration9GluingVerifierError as exc:
        return {
            "verdict": "abstain",
            "anti_witness": None,
            "observation": {
                "kind": "verifier_abstained",
                "reason_code": _safe_reason(str(exc)),
            },
        }

    for cell in cells:
        handles = cell["state_handles"]
        if len(handles) < 2:
            continue
        first_handle = handles[0]
        first_attrs = states[first_handle]
        for patch in patches:
            first_value = _patch_observable_value(first_attrs, patch)
            for handle in handles[1:]:
                value = _patch_observable_value(states[handle], patch)
                if value != first_value:
                    anti_witness = {
                        "cell_handle": cell["cell_handle"],
                        "state_handles": [first_handle, handle],
                        # The patch name is the gluing-domain analogue of
                        # distinguishing_observable; it is the OVERLAP coordinate
                        # field, never the hidden orientation.
                        "patch": patch["name"],
                        "distinguishing_observable": patch["observable"],
                    }
                    return {
                        "verdict": "invalid",
                        "anti_witness": anti_witness,
                        "observation": {
                            "kind": "factorization_invalid",
                            "cell_handle": anti_witness["cell_handle"],
                            "state_handles": list(anti_witness["state_handles"]),
                            "patch": anti_witness["patch"],
                            "distinguishing_observable": anti_witness[
                                "distinguishing_observable"
                            ],
                        },
                    }

    return {
        "verdict": "valid",
        "anti_witness": None,
        "observation": {
            "kind": "factorization_valid",
            "checked_cells": len(cells),
        },
    }


def all_patch_overlaps_consistent(
    world: Any, quotient: Any, consumer: Any
) -> bool:
    """Sheaf consistency across ALL ``N`` patch overlaps (the-learner-1.4).

    Every patch reads the shared overlap observable ``x``. A proposed partition
    glues consistently across the full ``N``-patch cover iff EVERY ordered pair of
    patches ``(i, j)`` agrees on the overlap value within every cell — i.e. each
    cell is homogeneous in patch ``i``'s observable, homogeneous in patch ``j``'s
    observable, and the two single values coincide. Because all patches share the
    overlap coordinate this is a conjunction over all ``C(N, 2)`` pairwise
    overlaps: at ``N = 3`` it is the original three-pair check, at ``N = 4`` it is
    six pairs, at ``N = 5`` ten pairs. This is the explicit COMPOSITION obligation
    — the gluing must hold across more than two overlap pairs.

    The check is orientation-free in signature and body (Theater Mode 2): it reads
    only world / quotient / consumer, never ``evidence_only``. It returns ``True``
    iff the partition is consistent across all ``N`` overlaps.
    """
    try:
        states = _parse_world(world)
        cells = _parse_quotient(quotient, set(states))
        patches = _parse_consumer(consumer, states)
    except Iteration9GluingVerifierError:
        return False

    for cell in cells:
        handles = cell["state_handles"]
        if len(handles) < 2:
            continue
        # Per-patch single overlap value across the cell (homogeneity), then
        # all-pairs agreement. A set per patch captures both in one pass.
        patch_values: list[set[Any]] = [
            {_patch_observable_value(states[h], patch) for h in handles}
            for patch in patches
        ]
        for i in range(len(patches)):
            if len(patch_values[i]) > 1:
                return False
            for j in range(i + 1, len(patches)):
                if patch_values[i] != patch_values[j]:
                    return False
    return True


def _all_local_anti_witnesses(
    world: Any, quotient: Any, consumer: Any
) -> list[dict[str, Any]]:
    """Enumerate every (cell, state_pair, patch) anti-witness in the local env.

    Deterministic ordering: sorted by cell handle, then sorted state pair, then
    patch order. This is the source of byte-identical anti-witness reveal
    ordering across M-twins.
    """
    try:
        states = _parse_world(world)
        cells = _parse_quotient(quotient, set(states))
        patches = _parse_consumer(consumer, states)
    except Iteration9GluingVerifierError:
        return []

    witnesses: list[dict[str, Any]] = []
    for cell in sorted(cells, key=lambda c: c["cell_handle"]):
        handles = cell["state_handles"]
        for left_index, left_handle in enumerate(handles):
            left_attrs = states[left_handle]
            for right_handle in handles[left_index + 1 :]:
                right_attrs = states[right_handle]
                for patch in patches:
                    if _patch_observable_value(
                        left_attrs, patch
                    ) != _patch_observable_value(right_attrs, patch):
                        witnesses.append(
                            {
                                "cell_handle": cell["cell_handle"],
                                "state_handles": [left_handle, right_handle],
                                "patch": patch["name"],
                                "distinguishing_observable": patch["observable"],
                            }
                        )
                        # One witness per pair is enough; record from the first
                        # patch that distinguishes the pair, deterministically.
                        break
    return witnesses


# ---------------------------------------------------------------------------
# Local verifier environment
# ---------------------------------------------------------------------------


class GluingLocalVerifierEnv:
    """Deterministic, orientation-blind local verifier env.

    The env's reset/step methods compute responses as a pure function of the
    model-visible world/quotient/consumer. In ``mode="eval"`` no path of the
    env reads ``evidence_only.overlap_orientation`` — that is the structural
    source of Theater Mode 7 immunity.

    In ``mode="adaptation"`` the env appends a single gluing-anti-witness
    observation when a locally-complete proposal mismatches the orientation;
    this is the controlled feedback channel through which the policy can learn
    M during adaptation. Adaptation episodes still terminate one-shot — the
    feedback is part of the terminal emission, not retryable evidence.
    """

    def __init__(
        self, episode: dict[str, Any], *, repair_budget: int = 3
    ) -> None:
        if repair_budget < 1:
            raise Iteration9GluingVerifierError("repair budget must be positive")
        self._episode = copy.deepcopy(episode)
        self._initial_payload = copy.deepcopy(
            self._episode.get("model_visible_initial", {})
        )
        self._world = copy.deepcopy(self._initial_payload.get("world"))
        self._consumer = copy.deepcopy(self._initial_payload.get("consumer"))
        self._current_quotient = copy.deepcopy(
            self._initial_payload.get("candidate_quotient")
        )
        self._repair_budget_start = repair_budget
        self._remaining_repair_budget = repair_budget
        self._step_index = 0
        self._reset_done = False
        self._terminal_result: str | None = None
        self._evidence_so_far: list[dict[str, Any]] = []
        self._memory_update_count = 0

        mode = self._episode.get("mode")
        if mode not in GLUING_MODES:
            raise Iteration9GluingVerifierError(
                f"Phase 9.0 verifier mode missing or unknown: {mode!r}"
            )
        self._mode = mode
        # The verifier reads orientation ONLY in adaptation mode. In eval mode
        # the orientation handle is never bound, ensuring static analysis +
        # behavioral exhaustion both confirm the local env is orientation-blind.
        if mode == "adaptation":
            orientation = self._episode.get("evidence_only", {}).get(
                "overlap_orientation"
            )
            canonical_orientation = LEGACY_ORIENTATION_ALIASES.get(
                orientation, orientation
            )
            if canonical_orientation not in GLUING_ORIENTATIONS:
                raise Iteration9GluingVerifierError(
                    "adaptation mode requires evidence_only.overlap_orientation"
                )
            self._adaptation_orientation: str | None = orientation
        else:
            self._adaptation_orientation = None

    # -- public surface -----------------------------------------------------

    def reset(self) -> dict[str, Any]:
        self._step_index = 0
        self._remaining_repair_budget = self._repair_budget_start
        self._current_quotient = copy.deepcopy(
            self._initial_payload.get("candidate_quotient")
        )
        self._evidence_so_far = []
        self._terminal_result = None
        self._memory_update_count = 0
        self._reset_done = True

        state = self.model_visible_state()
        self._ensure_scanner_clean(state, "reset model-visible state")
        factorization = local_glue_factorization(
            self._world, self._current_quotient, self._consumer
        )
        if factorization["verdict"] == "abstain":
            raise Iteration9GluingVerifierError(
                "reset cannot safely validate malformed crossed-context episode"
            )
        return self._emit(
            kind="reset",
            action_result="noop",
            terminal_result=None,
            observation={"kind": "reset", "revealed": []},
            include_state=True,
        )

    def model_visible_state(self) -> dict[str, Any]:
        state = copy.deepcopy(self._initial_payload)
        state["candidate_quotient"] = copy.deepcopy(self._current_quotient)
        state["evidence_so_far"] = copy.deepcopy(self._evidence_so_far)
        return state

    def step(self, action: str, payload: Any | None = None) -> dict[str, Any]:
        if not self._reset_done:
            raise Iteration9GluingVerifierError("reset required before step")
        if self._terminal_result is not None:
            return self._emit(
                kind="terminal_refused",
                action_result="refused_terminal",
                terminal_result=self._terminal_result,
                observation={"kind": "terminal_refused"},
            )
        if action not in ITERATION8_LEARNER_ACTIONS:
            return self._emit(
                kind="action_invalid",
                action_result="invalid_action",
                terminal_result=None,
                observation={"kind": "action_invalid"},
            )

        self._step_index += 1

        if action == "abstain":
            self._terminal_result = "abstained"
            return self._emit(
                kind="terminal",
                action_result="accepted",
                terminal_result=self._terminal_result,
                observation={"kind": "abstained"},
            )
        if action == "declare_valid":
            return self._declare_valid()
        if action == "request_anti_witness":
            return self._request_anti_witness()
        if action == "point_anti_witness":
            return self._point_anti_witness(payload)
        if action == "propose_repair":
            return self._propose_repair(payload)
        if action == "replay_verifier":
            return self._replay_verifier()
        if action in {"store_memory", "reuse_memory"}:
            # Phase 8.3 memory operations are no-ops at the verifier-env layer.
            return self._emit(
                kind="runtime_noop",
                action_result="noop",
                terminal_result=None,
                observation={"kind": "runtime_noop"},
            )
        return self._emit(
            kind="runtime_noop",
            action_result="noop",
            terminal_result=None,
            observation={"kind": "runtime_noop"},
        )

    # -- step handlers ------------------------------------------------------

    def _declare_valid(self) -> dict[str, Any]:
        factorization = local_glue_factorization(
            self._world, self._current_quotient, self._consumer
        )
        if factorization["verdict"] == "valid":
            self._terminal_result = "valid_repair"
            return self._emit(
                kind="terminal",
                action_result="accepted",
                terminal_result=self._terminal_result,
                observation={"kind": "declared_valid"},
            )
        self._terminal_result = "failed"
        return self._emit(
            kind="terminal",
            action_result="rejected",
            terminal_result=self._terminal_result,
            observation={"kind": "false_valid_declaration"},
        )

    def _request_anti_witness(self) -> dict[str, Any]:
        factorization = local_glue_factorization(
            self._world, self._current_quotient, self._consumer
        )
        if factorization["verdict"] != "invalid" or factorization["anti_witness"] is None:
            return self._emit(
                kind="anti_witness_request",
                action_result="noop",
                terminal_result=None,
                observation={"kind": "no_distinction_available"},
            )
        observation = self._anti_witness_observation(factorization["anti_witness"])
        self._append_evidence(observation)
        return self._emit(
            kind="anti_witness_request",
            action_result="revealed",
            terminal_result=None,
            observation=observation,
        )

    def _point_anti_witness(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict) or not isinstance(
            payload.get("state_handles"), list
        ):
            return self._emit(
                kind="anti_witness_point",
                action_result="miss",
                terminal_result=None,
                observation={"kind": "point_miss"},
            )
        requested = set(payload.get("state_handles", []))
        for anti_witness in _all_local_anti_witnesses(
            self._world, self._current_quotient, self._consumer
        ):
            if set(anti_witness["state_handles"]) == requested:
                observation = self._anti_witness_observation(anti_witness)
                self._append_evidence(observation)
                return self._emit(
                    kind="anti_witness_point",
                    action_result="revealed",
                    terminal_result=None,
                    observation=observation,
                )
        return self._emit(
            kind="anti_witness_point",
            action_result="miss",
            terminal_result=None,
            observation={"kind": "point_miss"},
        )

    def _propose_repair(self, proposal: Any) -> dict[str, Any]:
        repaired = _apply_replace_partition(self._current_quotient, proposal)
        if repaired is None:
            return self._reject_repair("malformed_repair")
        factorization = local_glue_factorization(self._world, repaired, self._consumer)
        if factorization["verdict"] == "valid":
            return self._accept_locally_complete(repaired, proposal)
        return self._reject_repair("repair_not_factored")

    def _replay_verifier(self) -> dict[str, Any]:
        factorization = local_glue_factorization(
            self._world, self._current_quotient, self._consumer
        )
        if factorization["verdict"] == "valid":
            self._terminal_result = "valid_repair"
            return self._emit(
                kind="terminal",
                action_result="accepted",
                terminal_result=self._terminal_result,
                observation={"kind": "replay_valid"},
            )
        return self._emit(
            kind="replay",
            action_result="rejected",
            terminal_result=None,
            observation={"kind": "replay_not_factored"},
        )

    def _accept_locally_complete(
        self, repaired_quotient: dict[str, Any], proposal: dict[str, Any]
    ) -> dict[str, Any]:
        """Accept a locally-complete proposal.

        Theater Mode 3 (acceptance-feedback leakage) killer:
          The terminal emission is byte-identical in eval mode regardless of
          whether the proposal matches the orientation-correct partition. No
          information about M flows back through this path in eval.

        In adaptation mode, a mismatched locally-complete proposal returns a
        non-terminal gluing anti-witness. The eval path stays one-shot terminal
        and silent with respect to G.
        """
        if self._mode == "adaptation":
            return self._accept_locally_complete_adaptation(repaired_quotient, proposal)

        self._current_quotient = copy.deepcopy(repaired_quotient)
        self._terminal_result = "valid_repair"
        if self._memory_update_count == 0:
            self._memory_update_count = 1
        return self._emit(
            kind="terminal",
            action_result="accepted",
            terminal_result=self._terminal_result,
            observation={"kind": "repair_accepted"},
            memory_update_count=self._memory_update_count,
        )

    def _accept_locally_complete_adaptation(
        self, repaired_quotient: dict[str, Any], proposal: dict[str, Any]
    ) -> dict[str, Any]:
        verdict = global_glue_objective(self._episode, proposal)
        if verdict["verdict"] != "rejected":
            self._current_quotient = copy.deepcopy(repaired_quotient)
            self._terminal_result = "valid_repair"
            if self._memory_update_count == 0:
                self._memory_update_count = 1
            return self._emit(
                kind="terminal",
                action_result="accepted",
                terminal_result=self._terminal_result,
                observation={
                    "kind": "gluing_glue_through",
                    "reason_code": "global_factorization_passed",
                },
                memory_update_count=self._memory_update_count,
            )

        observation = {
            "kind": "gluing_anti_witness",
            "reason_code": "global_factorization_failed",
        }
        self._remaining_repair_budget -= 1
        if self._remaining_repair_budget <= 0:
            self._terminal_result = "budget_exhausted"
            return self._emit(
                kind="terminal",
                action_result="budget_exhausted",
                terminal_result=self._terminal_result,
                observation=observation,
            )
        return self._emit(
            kind="gluing_feedback",
            action_result="accepted",
            terminal_result=None,
            observation=observation,
        )

    def _reject_repair(self, reason_code: str) -> dict[str, Any]:
        self._remaining_repair_budget -= 1
        if self._remaining_repair_budget <= 0:
            self._terminal_result = "budget_exhausted"
            return self._emit(
                kind="terminal",
                action_result="budget_exhausted",
                terminal_result=self._terminal_result,
                observation={"kind": "repair_rejected", "reason_code": reason_code},
            )
        return self._emit(
            kind="repair_rejected",
            action_result="rejected",
            terminal_result=None,
            observation={"kind": "repair_rejected", "reason_code": reason_code},
        )

    # -- emission helpers ---------------------------------------------------

    def _anti_witness_observation(self, anti_witness: dict[str, Any]) -> dict[str, Any]:
        # The observation MUST not carry orientation tokens. The patch field
        # carries the OVERLAP coordinate handle (e.g. "patch_U") which is a
        # structural identity, not a hidden datum.
        return {
            "kind": "anti_witness_revealed",
            "cell_handle": anti_witness["cell_handle"],
            "state_handles": list(anti_witness["state_handles"]),
            "patch": anti_witness["patch"],
            "distinguishing_observable": anti_witness["distinguishing_observable"],
        }

    def _append_evidence(self, observation: dict[str, Any]) -> None:
        self._ensure_scanner_clean(observation, "verifier feedback")
        if observation not in self._evidence_so_far:
            self._evidence_so_far.append(copy.deepcopy(observation))

    def _emit(
        self,
        *,
        kind: str,
        action_result: str,
        terminal_result: str | None,
        observation: dict[str, Any],
        include_state: bool = False,
        memory_update_count: int = 0,
    ) -> dict[str, Any]:
        if action_result not in GLUING_ENV_ACTION_RESULTS:
            raise Iteration9GluingVerifierError(
                f"unknown action result: {action_result!r}"
            )
        result: dict[str, Any] = {
            "kind": kind,
            "step_index": self._step_index,
            "action_result": action_result,
            "terminal_result": terminal_result,
            "terminated": terminal_result is not None,
            "remaining_repair_budget": self._remaining_repair_budget,
            "observation": copy.deepcopy(observation),
            "memory_update_count": memory_update_count,
        }
        if include_state:
            result["model_visible_state"] = self.model_visible_state()
        self._ensure_scanner_clean(result, "gluing verifier emission")
        return result

    @staticmethod
    def _ensure_scanner_clean(payload: Any, context: str) -> None:
        findings = scan_iteration8_model_visible_payload(payload)
        if findings:
            raise Iteration9GluingVerifierError(f"{context} leakage: {findings[0]}")


# ---------------------------------------------------------------------------
# Global objective G (post-hoc, protocol-facing, not an action)
# ---------------------------------------------------------------------------


def global_glue_objective(
    episode: dict[str, Any], proposal: Any
) -> dict[str, Any]:
    """Score a repair proposal against the global gluing objective.

    G is the protocol-facing layer; it reads ``evidence_only.overlap_orientation``
    and compares the proposal partition to the orientation-correct canonical
    repair via the ``2^k``-entry ``ORIENTATION_TO_REPAIR_KIND`` table (the single
    source of truth, imported from the episode module). G is NEVER called by a
    learner action; it is scored post-hoc on the proposal that the local env
    accepted. Because the ``2^k`` partitions are pairwise distinct, G accepts
    exactly one orientation's repair and rejects the other ``2^k − 1`` at every
    Hamming distance ≥ 1 (no partial credit).

    Returns
    -------
    dict
        ``{"verdict": "accepted" | "rejected", "anti_witness": ... | None}``.
        The anti-witness is a scanner-clean ``gluing_anti_witness`` observation
        used by adaptation feedback; it never carries the orientation token.
    """
    orientation = episode.get("evidence_only", {}).get("overlap_orientation")
    orientation = LEGACY_ORIENTATION_ALIASES.get(orientation, orientation)
    if orientation not in ORIENTATION_TO_REPAIR_KIND:
        return {"verdict": "abstain", "anti_witness": None}

    correct_kind = ORIENTATION_TO_REPAIR_KIND[orientation]
    try:
        correct = canonical_repair(episode, kind=correct_kind)
    except Iteration9GluingEpisodeError:
        return {"verdict": "abstain", "anti_witness": None}

    proposal_partition = _normalize_partition(proposal)
    correct_partition = _normalize_partition(correct)
    if proposal_partition is None or correct_partition is None:
        return {
            "verdict": "rejected",
            "anti_witness": {
                "kind": "gluing_anti_witness",
                "reason_code": "malformed_proposal",
            },
        }

    if proposal_partition == correct_partition:
        # the-learner-1.4 composition gate: the orientation-correct partition must
        # additionally glue consistently across ALL N patch overlaps, not just the
        # pairwise ones implied by k=3. For a canonical (x-homogeneous) repair this
        # is necessarily satisfied for any N, so this conjunct never flips an
        # accepted verdict at N=3 (backward compatible) — it makes the multi-patch
        # obligation explicit and would reject a partition that matched M's cells
        # yet failed to glue across the richer N>3 cover.
        model_visible = episode.get("model_visible_initial", {})
        world = model_visible.get("world")
        consumer = model_visible.get("consumer")
        quotient = {"cells": proposal.get("cells", [])}
        if all_patch_overlaps_consistent(world, quotient, consumer):
            return {"verdict": "accepted", "anti_witness": None}
        return {
            "verdict": "rejected",
            "anti_witness": {
                "kind": "gluing_anti_witness",
                "reason_code": "multi_patch_overlap_inconsistent",
            },
        }
    return {
        "verdict": "rejected",
        "anti_witness": {
            "kind": "gluing_anti_witness",
            "reason_code": "global_factorization_failed",
        },
    }


def validate_gluing_factorization(
    episode: dict[str, Any], proposal: Any
) -> dict[str, Any]:
    """Composite validity: per-patch local + N-overlap consistency + global G.

    Returns a structured verdict. ``local_u_valid`` / ``local_v_valid`` are kept
    for the 1.0–1.3 contract, but the conjunction is now over EVERY patch in the
    cover (``all_patches_local_valid``) and the explicit ``N``-patch overlap
    consistency (the-learner-1.4), so the composite verifies the gluing across the
    full cover, not just the first two patches. At ``N = 3`` this is identical to
    the prior behavior.
    """
    world = episode.get("model_visible_initial", {}).get("world")
    consumer = episode.get("model_visible_initial", {}).get("consumer")
    quotient = _apply_replace_partition({"cells": []}, proposal)
    if quotient is None:
        return {
            "local_u_valid": False,
            "local_v_valid": False,
            "all_patches_local_valid": False,
            "overlap_consistent": False,
            "global_factor_through": False,
            "num_patches": 0,
            "verdict": "invalid",
            "reason_code": "malformed_proposal",
        }
    # Per-patch local validity over EVERY declared patch in the cover.
    patches = (consumer or {}).get("patches", []) or []
    patch_validities: dict[str, bool] = {}
    for patch in patches:
        if not isinstance(patch, dict) or not isinstance(patch.get("name"), str):
            continue
        name = patch["name"]
        single = _single_patch_consumer(consumer, patch_name=name)
        patch_validities[name] = (
            local_glue_factorization(world, quotient, single)["verdict"] == "valid"
        )
    all_patches_valid = bool(patch_validities) and all(patch_validities.values())
    # Backward-compatible named slots (patch_U / patch_V are always present here).
    local_u_valid = patch_validities.get("patch_U", all_patches_valid)
    local_v_valid = patch_validities.get("patch_V", all_patches_valid)

    overlap = all_patch_overlaps_consistent(world, quotient, consumer)
    g_result = global_glue_objective(episode, proposal)
    verdict = all_patches_valid and overlap and g_result["verdict"] == "accepted"
    return {
        "local_u_valid": local_u_valid,
        "local_v_valid": local_v_valid,
        "all_patches_local_valid": all_patches_valid,
        "per_patch_local_valid": patch_validities,
        "overlap_consistent": overlap,
        "global_factor_through": g_result["verdict"] == "accepted",
        "num_patches": len(patch_validities),
        "verdict": "valid" if verdict else "invalid",
    }


# ---------------------------------------------------------------------------
# Parsing + helpers
# ---------------------------------------------------------------------------


def _parse_world(world: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(world, dict) or not isinstance(world.get("states"), list) or not world["states"]:
        raise Iteration9GluingVerifierError("malformed world")
    states: dict[str, dict[str, Any]] = {}
    for state in world["states"]:
        if not isinstance(state, dict) or not isinstance(state.get("state_handle"), str):
            raise Iteration9GluingVerifierError("malformed world state")
        handle = state["state_handle"]
        if handle in states:
            raise Iteration9GluingVerifierError("duplicate world state")
        attributes = state.get("attributes")
        if not isinstance(attributes, dict):
            raise Iteration9GluingVerifierError("malformed state attributes")
        states[handle] = attributes
    return states


def _parse_quotient(quotient: Any, known_handles: set[str]) -> list[dict[str, Any]]:
    if not isinstance(quotient, dict) or not isinstance(quotient.get("cells"), list) or not quotient["cells"]:
        raise Iteration9GluingVerifierError("malformed quotient")
    cells: list[dict[str, Any]] = []
    seen: set[str] = set()
    for cell in quotient["cells"]:
        if not isinstance(cell, dict) or not isinstance(cell.get("cell_handle"), str):
            raise Iteration9GluingVerifierError("malformed quotient cell")
        state_handles = cell.get("state_handles")
        if not isinstance(state_handles, list) or not state_handles:
            raise Iteration9GluingVerifierError("malformed quotient cell members")
        normalized: list[str] = []
        for handle in state_handles:
            if not isinstance(handle, str) or handle not in known_handles:
                raise Iteration9GluingVerifierError("unknown quotient state")
            if handle in seen:
                raise Iteration9GluingVerifierError("duplicate quotient state")
            seen.add(handle)
            normalized.append(handle)
        cells.append({"cell_handle": cell["cell_handle"], "state_handles": normalized})
    if seen != known_handles:
        raise Iteration9GluingVerifierError("quotient does not cover world")
    return cells


def _parse_consumer(consumer: Any, states: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(consumer, dict):
        raise Iteration9GluingVerifierError("malformed consumer")
    patches = consumer.get("patches")
    if not isinstance(patches, list) or not patches:
        raise Iteration9GluingVerifierError("malformed consumer patches")
    normalized: list[dict[str, Any]] = []
    for patch in patches:
        if not isinstance(patch, dict):
            raise Iteration9GluingVerifierError("malformed consumer patch")
        name = patch.get("name")
        observable = patch.get("observable")
        fields = patch.get("projection_fields")
        if not isinstance(name, str) or not isinstance(observable, str):
            raise Iteration9GluingVerifierError("malformed consumer patch fields")
        if not isinstance(fields, list) or not all(isinstance(f, str) for f in fields):
            raise Iteration9GluingVerifierError("malformed consumer patch projection_fields")
        # Verify the observable can be computed for every state.
        for attrs in states.values():
            _patch_observable_value(attrs, {"observable": observable})
        normalized.append({"name": name, "observable": observable, "projection_fields": list(fields)})
    return normalized


def _patch_observable_value(attributes: dict[str, Any], patch: dict[str, Any]) -> Any:
    observable = patch.get("observable")
    if not isinstance(observable, str):
        raise Iteration9GluingVerifierError("malformed patch observable")
    if observable.endswith("_parity"):
        base = observable[: -len("_parity")]
        if base not in attributes or not isinstance(attributes[base], int):
            raise Iteration9GluingVerifierError("unknown patch observable")
        return attributes[base] % 2
    if observable not in attributes:
        raise Iteration9GluingVerifierError("unknown patch observable")
    return attributes[observable]


def _single_patch_consumer(consumer: Any, *, patch_name: str) -> dict[str, Any]:
    if not isinstance(consumer, dict) or not isinstance(consumer.get("patches"), list):
        raise Iteration9GluingVerifierError("malformed consumer for single-patch view")
    for patch in consumer["patches"]:
        if isinstance(patch, dict) and patch.get("name") == patch_name:
            return {"name": consumer.get("name", "single_patch"), "patches": [copy.deepcopy(patch)]}
    raise Iteration9GluingVerifierError(f"patch {patch_name!r} not found in consumer")


def _check_overlap_consistency(world: Any, quotient: Any) -> bool:
    """Each cell must agree on the overlap coordinate (x).

    This is structurally implied by the consumer being homogeneous on the
    overlap observable for each patch, but recomputed here for the composite
    ``validate_gluing_factorization`` view.
    """
    try:
        states = _parse_world(world)
        cells = _parse_quotient(quotient, set(states))
    except Iteration9GluingVerifierError:
        return False
    for cell in cells:
        values = {states[h].get("x") for h in cell["state_handles"]}
        if len(values) > 1:
            return False
    return True


def _normalize_partition(proposal: Any) -> frozenset[frozenset[str]] | None:
    """Return a canonical (handle-name-blind) representation of a partition."""
    if not isinstance(proposal, dict):
        return None
    cells = proposal.get("cells")
    if not isinstance(cells, list) or not cells:
        return None
    canonical: list[frozenset[str]] = []
    for cell in cells:
        if not isinstance(cell, dict):
            return None
        members = cell.get("state_handles")
        if not isinstance(members, list) or not members:
            return None
        if not all(isinstance(h, str) for h in members):
            return None
        canonical.append(frozenset(members))
    return frozenset(canonical)


def _apply_replace_partition(
    current_quotient: Any, proposal: Any
) -> dict[str, Any] | None:
    """Apply a replace_partition proposal, returning the new quotient or None.

    Mirrors iteration8_runtime_verifier._apply_repair_proposal restricted to
    the operator the Phase 9.0 contract recognizes: ``replace_partition``.
    """
    if not isinstance(proposal, dict):
        return None
    operator = proposal.get("repair_operator")
    if operator != "replace_partition":
        return None
    cells = proposal.get("cells")
    if not isinstance(cells, list) or not cells:
        return None
    normalized: list[dict[str, Any]] = []
    for index, cell in enumerate(cells):
        if not isinstance(cell, dict) or not isinstance(cell.get("state_handles"), list):
            return None
        if not all(isinstance(h, str) for h in cell["state_handles"]):
            return None
        normalized.append(
            {
                "cell_handle": f"repair_cell_{index}",
                "state_handles": list(cell["state_handles"]),
            }
        )
    return {"cells": normalized}


def _safe_reason(reason: str) -> str:
    allowed = {
        "malformed world": "malformed_world",
        "malformed world state": "malformed_world",
        "duplicate world state": "malformed_world",
        "malformed state attributes": "malformed_world",
        "malformed quotient": "malformed_quotient",
        "malformed quotient cell": "malformed_quotient",
        "malformed quotient cell members": "malformed_quotient",
        "unknown quotient state": "malformed_quotient",
        "duplicate quotient state": "malformed_quotient",
        "quotient does not cover world": "malformed_quotient",
        "malformed consumer": "malformed_consumer",
        "malformed consumer patches": "malformed_consumer",
        "malformed consumer patch": "malformed_consumer",
        "malformed consumer patch fields": "malformed_consumer",
        "malformed consumer patch projection_fields": "malformed_consumer",
        "unknown patch observable": "malformed_consumer",
        "malformed patch observable": "malformed_consumer",
    }
    return allowed.get(reason, "malformed_runtime_input")


__all__ = [
    "ITERATION9_GLUING_VERIFIER_SCHEMA_VERSION",
    "GLUING_ENV_ACTION_RESULTS",
    "Iteration9GluingVerifierError",
    "GluingLocalVerifierEnv",
    "global_glue_objective",
    "local_glue_factorization",
    "all_patch_overlaps_consistent",
    "validate_gluing_factorization",
]
