"""Iteration 9 the-learner-1.2 — richer-datum crossed-context gluing episode.

1.0 (Phase 9.0) carried exactly **1 bit** of non-local gluing datum
(``overlap_orientation ∈ {aligned, flipped}`` → 2 candidate repairs). 1.2 carries
``k`` bits (``2^k`` orientations) and asks whether the *same* non-local transfer
mechanism scales. **This module is the 3-bit (``k=3``) Stage 4 extension:** 8
orientations, 16-state world ``(x,u,v,w)``, 8 genuinely-distinct candidate
repairs, cold floor ``1/8 = 0.125`` — one rung past the banked 2-bit PASS.

THE FLIP TRAP (critical design note)
------------------------------------

The brief's hint "2 bits = (identity, flip_x, flip_u, flip_both)" is a TRAP.
Implemented naively as *coordinate flips*, the global objective G becomes
**vacuous**: partition-by-``(x,u)`` equals partition-by-``(x̄,u)`` equals
partition-by-``(x,ū)`` — flipping a coordinate relabels cells but yields the
**same partition**. All four "orientations" would collapse to one partition and
G could not discriminate (Theater Mode 11 — vacuous/code-only G).

The orientation must index **genuinely distinct partitions**. We use GF(2)
linear functionals. The world states carry an overlap bit ``x`` and three fine
bits ``u, v, w``. An orientation is an opaque 3-bit code indexing one of the
eight functionals ``{ℓ_0=0, ℓ_1=u, ℓ_2=v, ℓ_3=w, ℓ_4=u⊕v, ℓ_5=u⊕w, ℓ_6=v⊕w,
ℓ_7=u⊕v⊕w}``; the canonical repair ``R_i`` partitions the world by
``(x, ℓ_i(u, v, w))``:

    m="m000" → ℓ_0 = 0          → R_0 = partition by (x)       [coarse, 2 cells]
    m="m001" → ℓ_1 = u          → R_1 = partition by (x, u)    [= 2-bit R_a]
    m="m010" → ℓ_2 = v          → R_2 = partition by (x, v)    [= 2-bit R_b]
    m="m011" → ℓ_3 = w          → R_3 = partition by (x, w)    [the 3rd bit]
    m="m100" → ℓ_4 = u ⊕ v      → R_4 = partition by (x, u⊕v)
    m="m101" → ℓ_5 = u ⊕ w      → R_5 = partition by (x, u⊕w)
    m="m110" → ℓ_6 = v ⊕ w      → R_6 = partition by (x, v⊕w)
    m="m111" → ℓ_7 = u ⊕ v ⊕ w  → R_7 = partition by (x, u⊕v⊕w)

Because the 8 triples are the 8 distinct linear functionals on ``GF(2)^3`` (the
7 nonzero ones span ``GF(2)^3``, rank 3), the eight partitions are pairwise
distinct (a G-non-degeneracy gate asserts this). All eight are
``x``-homogeneous, so **all eight are locally valid** (every patch consumer
reads only the overlap coordinate ``x``); only G — reading the non-local datum
``M`` from ``evidence_only`` — accepts exactly one. The 2-bit stage is literally
the 4-of-8-functionals sub-case ``{R_0, R_1, R_2, R_4}`` restricted to
``{0,u,v,u⊕v}`` — maximal continuity.

Hardening posture
-----------------

  * Theater Mode 1 (attribute leakage) — eval exposes (x, u, v) on every state
    because that is the shared world. M is NEVER an attribute.
  * Theater Mode 9 (memory laundering) — ``evidence_only.overlap_orientation``
    is the only carrier of M; the model_visible payload is scanner-clean and
    free of every orientation-family token (incl. the four opaque codes).
  * Theater Mode 10 (adaptation = supervised labels) — orientation is never
    placed in a state, cell, or consumer field. The carrier is structural.
  * Theater Mode 11 (vacuous/code-only G) — the orientation indexes distinct
    *partitions*, asserted pairwise-distinct by the G-non-degeneracy gate.

This module ONLY builds the episode and owns the orientation→partition map (the
single source of truth). Local-env emission + global objective G are in
``iteration9_gluing_verifier``. No learner action queries G.
"""

from __future__ import annotations

import json
import re
from typing import Any

from manifold_destiny.iteration8_episode import (
    ITERATION8_LEARNER_ACTIONS,
    Iteration8EpisodeValidationError,
    scan_iteration8_model_visible_payload,
)


ITERATION9_GLUING_EPISODE_SCHEMA_VERSION = (
    "manifold-destiny-gluing-episode-v1"
)
ITERATION9_PHASE90_CLAIM = (
    "ITERATION_9_PHASE_9_0_GLUING_TRANSFER_GATE_NON_LOCAL_ORIENTATION_TRANSFER"
)

# --- the-learner-1.2 Stage 4 richer datum: k = 3 bits ----------------------
# The number of non-local datum bits the orientation carries. 3 bits ⇒ 8
# orientations ⇒ 8 distinct partitions ⇒ cold floor 1/2^k = 0.125. Stage 4
# extends the banked 2-bit PASS one rung further (8 GF(2) functionals on
# (u,v,w)); everything structural is preserved and re-parameterized by k.
GLUING_K_BITS = 3

# The k=3 fine bits, in canonical order; ``len(GLUING_FINE_BITS) == GLUING_K_BITS``.
# These are the world's non-overlap coordinates (u, v, w). The orientation/datum
# size is fixed by this tuple; multi-patch composition (1.4) does NOT grow it.
GLUING_FINE_BITS = ("u", "v", "w")

# --- the-learner-1.4 multi-patch composition: N patches, fixed datum ---------
# 1.4 extends from 3 patches to N patches under a sheaf-style gluing-consistency
# obligation. DECOUPLED design (preferred): the orientation/datum size stays at
# ``GLUING_K_BITS = 3`` (8 functionals, 16-state world, cold floor 0.125) while
# ``GLUING_NUM_PATCHES = N`` may exceed ``k``. When ``N > k`` the patches beyond
# the first k SHARE a fine bit (cyclic over GLUING_FINE_BITS), so the overlap
# COVER is richer — more pairwise overlaps that must all glue — without enlarging
# the non-local datum. This isolates the COMPOSITION question ("does transfer
# glue across N overlaps?") from the richer-datum question (1.2's k-sweep): the
# datum, the cold floor, and the 24-cell pool are all unchanged, only the number
# of patch overlaps G must verify grows.
#
# The module default stays 3 so the zero-argument builder reproduces the 1.3
# fixture byte-for-byte (backward compatible; an existing test asserts exactly
# {patch_U, patch_V, patch_W}). N=4 / N=5 are exercised by passing ``num_patches``.
GLUING_NUM_PATCHES = 3


def _generate_orientation_codes(k: int) -> tuple[str, ...]:
    """Generate the ``2^k`` opaque orientation codes ``m<b0..b_{k-1}>``.

    Generated from ``k`` (R7 anti-regression) so the only hand-edited k-bound
    surfaces are ``GLUING_K_BITS``, the functional coefficient triples, the
    consumer patch list, and ``COLD_DEFAULT_ORIENTATION``. The integer value of
    a code's bits is its repair index: ``m000 → R_0`` … ``m111 → R_7``.
    """
    return tuple("m" + format(i, f"0{k}b") for i in range(2 ** k))


# Multi-patch gluing object.  Each patch declares an observable; the overlap is
# the coordinate they share (x in this fixture). At k=3 the world carries a
# third fine bit w, so the consumer also declares patch_W.
GLUING_PATCH_NAMES = ("patch_U", "patch_V", "patch_W")
GLUING_OVERLAP_OBSERVABLE = "x"


def gluing_patch_fine_bit(index: int) -> str:
    """Fine bit read by patch ``index`` (0-based). Cyclic over GLUING_FINE_BITS.

    Patch 0→u, 1→v, 2→w, 3→u, 4→v, … so patches beyond the first k SHARE a fine
    bit. The shared bit is what makes the N>k cover richer without growing the
    datum (the orientation still indexes a functional on the k=3 fine bits).
    """
    return GLUING_FINE_BITS[index % GLUING_K_BITS]


def gluing_patch_name(index: int) -> str:
    """Deterministic, unique patch name for patch ``index`` (0-based).

    The first ``k`` patches are named for the fine bit they read
    (``patch_U``/``patch_V``/``patch_W``), so any ``N <= k`` reproduces the 1.3
    names exactly. Patches in later cycles reuse a fine bit and append the cycle
    number (``patch_U2`` reads ``u`` again, ``patch_V2`` reads ``v`` again), which
    keeps names unique and scanner-clean (no orientation-family token).
    """
    fine = gluing_patch_fine_bit(index)
    cycle = index // GLUING_K_BITS
    suffix = "" if cycle == 0 else str(cycle + 1)
    return f"patch_{fine.upper()}{suffix}"

# Orientation space: 2^k opaque codes "m<b0><b1><b2>", indexing the eight GF(2)
# functionals on (u,v,w). NOT "flip" labels (see THE FLIP TRAP above).
GLUING_ORIENTATIONS = _generate_orientation_codes(GLUING_K_BITS)
GLUING_MODES = ("adaptation", "eval")

# Orientation code → repair kind (single source of truth; imported by verifier,
# policy, evaluation — no module re-derives the canonical partition). Generated
# from the codes so it cannot drift out of sync with k (R7).
ORIENTATION_TO_REPAIR_KIND = {
    code: f"R_{index}" for index, code in enumerate(GLUING_ORIENTATIONS)
}
REPAIR_KIND_TO_ORIENTATION = {
    kind: code for code, kind in ORIENTATION_TO_REPAIR_KIND.items()
}

# Legacy 1.0/1.1 binary names retained as input aliases only.  They are not part
# of ``GLUING_ORIENTATIONS`` because the public contract is the k-bit code space.
# At any k, "aligned" = R_1 (partition by (x, u)) and "flipped" = R_2 (partition
# by (x, v)), which are GLUING_ORIENTATIONS[1] and [2] respectively.
LEGACY_ORIENTATION_ALIASES = {
    "aligned": GLUING_ORIENTATIONS[1],
    "flipped": GLUING_ORIENTATIONS[2],
}
LEGACY_REPAIR_KIND_ALIASES = {"R_a": "R_1", "R_b": "R_2"}

# Repair kind → GF(2) functional coefficients (c_u, c_v, c_w) with
# ℓ = c_u·u ⊕ c_v·v ⊕ c_w·w. THE GENUINE 3-bit math (hand-entered, R17). The 8
# triples are the 8 elements of GF(2)^3; the 7 nonzero triples are the standard
# basis plus its pairwise/triple sums and span GF(2)^3 (rank 3), so the 8
# induced partitions of the 16-state world are pairwise distinct.
REPAIR_KIND_TO_FUNCTIONAL_COEFFS = {
    "R_0": (0, 0, 0),  # ℓ_0 = 0           → partition by (x)        [coarse]
    "R_1": (1, 0, 0),  # ℓ_1 = u           → partition by (x, u)     [2-bit R_a]
    "R_2": (0, 1, 0),  # ℓ_2 = v           → partition by (x, v)     [2-bit R_b]
    "R_3": (0, 0, 1),  # ℓ_3 = w           → partition by (x, w)     [the 3rd bit]
    "R_4": (1, 1, 0),  # ℓ_4 = u ⊕ v       → partition by (x, u⊕v)
    "R_5": (1, 0, 1),  # ℓ_5 = u ⊕ w       → partition by (x, u⊕w)
    "R_6": (0, 1, 1),  # ℓ_6 = v ⊕ w       → partition by (x, v⊕w)
    "R_7": (1, 1, 1),  # ℓ_7 = u ⊕ v ⊕ w   → partition by (x, u⊕v⊕w)
}

# Orientation-family tokens that must not appear in the model-visible payload.
# Scanner-clean is the baseline; this is the explicit gluing-domain extension,
# extended (R7) to the 1.2 lexicon: the eight opaque codes plus the functional
# vocabulary that could surface if a bit leaked.
ORIENTATION_FORBIDDEN_TOKENS = tuple(GLUING_ORIENTATIONS) + (
    "orientation",
    "overlap_orientation",
    "functional",
    "parity",
    "xor",
    "hamming",
)


class Iteration9GluingEpisodeError(Iteration8EpisodeValidationError):
    """Raised when the gluing episode contract leaks or is malformed."""


# ---------------------------------------------------------------------------
# Orientation bit helpers (opaque 2-bit codes)
# ---------------------------------------------------------------------------


def orientation_to_bits(orientation: str) -> tuple[int, ...]:
    """Return the opaque index bits of an orientation code.

    ``"m10" → (1, 0)``. The code is ``"m"`` followed by exactly ``k`` bits.
    """
    if (
        not isinstance(orientation, str)
        or len(orientation) != GLUING_K_BITS + 1
        or orientation[0] != "m"
        or any(ch not in "01" for ch in orientation[1:])
    ):
        raise Iteration9GluingEpisodeError(f"malformed orientation code: {orientation!r}")
    return tuple(int(ch) for ch in orientation[1:])


def bits_to_orientation(bits: tuple[int, ...]) -> str:
    """Inverse of :func:`orientation_to_bits`. ``(1, 0) → "m10"``."""
    if len(bits) != GLUING_K_BITS or any(b not in (0, 1) for b in bits):
        raise Iteration9GluingEpisodeError(f"malformed orientation bits: {bits!r}")
    return "m" + "".join(str(b) for b in bits)


# ---------------------------------------------------------------------------
# Episode builder
# ---------------------------------------------------------------------------


def build_crossed_context_episode(
    *,
    orientation: str = "m010",
    mode: str = "eval",
    variant: str = "default",
    num_patches: int = GLUING_NUM_PATCHES,
) -> dict[str, Any]:
    """Build a crossed-context gluing episode.

    Parameters
    ----------
    orientation : str
        The hidden ``k``-bit gluing datum ``M`` ∈ ``GLUING_ORIENTATIONS``
        (``{"m000",…,"m111"}``). Lives in ``evidence_only`` only; the
        model-visible payload is byte-identical across all ``2^k`` orientation
        values.
    mode : str
        Either ``"adaptation"`` (G feedback channel) or ``"eval"`` (G silent).
    variant : str
        Handle-prefix variant for namespacing across pool seeds and lanes.
    num_patches : int
        The number of patches ``N`` in the cover (1.4 multi-patch composition).
        The world (16 states), the datum (8 orientations), and the cold floor
        (0.125) are independent of ``N`` — only the consumer's patch list and the
        joint patch-projection map grow. When ``N > k`` the extra patches reuse a
        fine bit (see :func:`gluing_patch_fine_bit`). Defaults to
        ``GLUING_NUM_PATCHES`` (3) so the zero-argument call is the 1.3 fixture.

    Notes
    -----
    The eval episode is the hardening surface: it must be a pure function of
    ``model_visible_initial`` only. The local env never reads
    ``evidence_only.overlap_orientation`` in eval mode.

    All ``2^k`` canonical repairs ``R_i`` partition by ``(x, ℓ_i(u, v, w))`` and
    are therefore ``x``-homogeneous → locally accepted under c_U = c_V = c_W = x.
    The global objective G discriminates by reading ``M`` from ``evidence_only``.
    Cold cannot recover ``M`` from any in-episode probe at any budget → ``1/2^k``.
    """
    canonical_orientation = LEGACY_ORIENTATION_ALIASES.get(orientation, orientation)
    if canonical_orientation not in GLUING_ORIENTATIONS:
        raise Iteration9GluingEpisodeError(f"unknown orientation: {orientation!r}")
    if mode not in GLUING_MODES:
        raise Iteration9GluingEpisodeError(f"unknown mode: {mode!r}")
    if not isinstance(num_patches, int) or num_patches < 1:
        raise Iteration9GluingEpisodeError(
            f"num_patches must be a positive integer, got {num_patches!r}"
        )
    if not isinstance(variant, str) or not variant:
        raise Iteration9GluingEpisodeError("variant must be a non-empty string")
    # Variant strings flow into state-handle and cell-handle prefixes, which are
    # serialized into model_visible. Reject variants that would leak orientation
    # tokens through that channel. (Theater Mode 5 — back-channel matching via
    # handle structure; Theater Mode 1 — attribute leakage by name.)
    lowered_variant = variant.lower()
    if not re.fullmatch(r"[a-zA-Z0-9_]+", variant):
        raise Iteration9GluingEpisodeError(
            "variant must contain only [A-Za-z0-9_] characters"
        )
    for token in ORIENTATION_FORBIDDEN_TOKENS:
        if token in lowered_variant:
            raise Iteration9GluingEpisodeError(
                f"variant {variant!r} contains orientation-family token {token!r}"
            )

    states = _build_states(variant)
    quotient = _build_initial_quotient(states, variant)
    consumer = _build_local_consumer(num_patches)

    model_visible_initial: dict[str, Any] = {
        "world": {"states": states},
        "candidate_quotient": quotient,
        "consumer": consumer,
        "allowed_actions": list(ITERATION8_LEARNER_ACTIONS),
        "prior_actions": [],
        "evidence_so_far": [],
        "quotient_memory": [],
    }

    # Both projections are PUBLIC in the core variant: only the orientation is
    # hidden. Hiding the projections is deferred to Phase 9.1.
    model_visible_initial["patch_projections"] = _build_patch_projections(num_patches)

    evidence_only: dict[str, Any] = {
        "overlap_orientation": orientation,
        # The patch projection map is also recorded in evidence_only for audit;
        # it is structurally redundant with model_visible (core variant only).
        "u_projection": "x_and_u",
        "v_projection": "x_and_v",
        "w_projection": "x_and_w",
        # The G-correct partition for this orientation; consumed only by G
        # (global_glue_objective), never read by the local env in eval mode.
        "g_correct_repair_kind": ORIENTATION_TO_REPAIR_KIND[canonical_orientation],
    }

    episode: dict[str, Any] = {
        "schema_version": ITERATION9_GLUING_EPISODE_SCHEMA_VERSION,
        "mode": mode,
        "model_visible_initial": model_visible_initial,
        "evidence_only": evidence_only,
        "audit_sidecar": {},
        "evidence_timeline": [],
    }

    findings = scan_iteration8_model_visible_payload(model_visible_initial)
    if findings:
        raise Iteration9GluingEpisodeError(
            f"crossed-context episode scanner findings: {findings}"
        )
    _scan_for_orientation_family_tokens(model_visible_initial)
    return episode


# ---------------------------------------------------------------------------
# State / quotient / consumer construction (deterministic, scanner-clean)
# ---------------------------------------------------------------------------


def _build_states(variant: str) -> list[dict[str, Any]]:
    """Build the 16 binary-attribute states.

    Each state has attributes ``x``, ``u``, ``v``, ``w`` ∈ {0, 1}. Handle is
    ``<variant>_s_xuvw`` so partitions over the pool have independent
    namespaces — Theater Mode 5 (back-channel matching) is killed by handle
    namespace partitioning.
    """
    handles: list[dict[str, Any]] = []
    for x in (0, 1):
        for u in (0, 1):
            for v in (0, 1):
                for w in (0, 1):
                    handles.append(
                        {
                            "state_handle": f"{variant}_s_{x}{u}{v}{w}",
                            "attributes": {"x": x, "u": u, "v": v, "w": w},
                        }
                    )
    return handles


def _build_initial_quotient(states: list[dict[str, Any]], variant: str) -> dict[str, Any]:
    """The initial quotient bundles all 16 states into one cell — locally invalid
    under every patch consumer because x differs across states."""
    handles = [s["state_handle"] for s in states]
    return {
        "cells": [
            {"cell_handle": f"{variant}_qcell_global", "state_handles": handles}
        ]
    }


def _build_local_consumer(num_patches: int = GLUING_NUM_PATCHES) -> dict[str, Any]:
    """Declare the ``N``-patch consumer (patch_U, patch_V, patch_W, …).

    Every patch's consumer reads the overlap coordinate ``x``; its declared
    projection is ``(x, b_i)`` where ``b_i`` is the (possibly shared) fine bit
    patch ``i`` reads. The hardening posture is unchanged: orientation cannot be
    recovered from the consumer declaration because each patch is a pure function
    of ``(x, b_i)`` — none encodes M. At ``N = 3`` this is byte-identical to the
    1.3 fixture (patch_U/(x,u), patch_V/(x,v), patch_W/(x,w)). For ``N > 3`` the
    extra patches reuse a fine bit, enriching the overlap cover G must verify
    without naming the datum (Mode 19 — every fine bit stays symmetric in the
    consumer family).
    """
    patches = []
    for index in range(num_patches):
        patches.append(
            {
                "name": gluing_patch_name(index),
                "observable": GLUING_OVERLAP_OBSERVABLE,
                "projection_fields": ["x", gluing_patch_fine_bit(index)],
            }
        )
    return {"name": "multi_patch_gluing_consumer", "patches": patches}


def _build_patch_projections(num_patches: int = GLUING_NUM_PATCHES) -> dict[str, Any]:
    projections: dict[str, Any] = {}
    for index in range(num_patches):
        name = gluing_patch_name(index)
        projections[name] = {"name": name, "fields": ["x", gluing_patch_fine_bit(index)]}
    return projections


# ---------------------------------------------------------------------------
# Canonical repairs (R_i for each orientation code) — single source of truth
# ---------------------------------------------------------------------------


def canonical_repair(episode: dict[str, Any], *, kind: str) -> dict[str, Any]:
    """Return the canonical repair proposal for the given kind.

    ``kind`` is one of ``REPAIR_KIND_TO_FUNCTIONAL_COEFFS`` (``"R_0"`` …
    ``"R_7"``). The repair partitions the world by ``(x, ℓ(u, v, w))`` where
    ``ℓ = c_u·u ⊕ c_v·v ⊕ c_w·w`` for the kind's GF(2) coefficients
    ``(c_u, c_v, c_w)``.

    The repair is a ``replace_partition`` proposal with stable, kind-prefixed
    cell handles. Handle prefixes carry no orientation information that reaches
    model_visible — G compares partitions handle-blind.
    """
    kind = LEGACY_REPAIR_KIND_ALIASES.get(kind, kind)
    coeffs = REPAIR_KIND_TO_FUNCTIONAL_COEFFS.get(kind)
    if coeffs is None:
        raise Iteration9GluingEpisodeError(f"unknown canonical repair kind: {kind!r}")
    c_u, c_v, c_w = coeffs
    states = episode["model_visible_initial"]["world"]["states"]

    groups: dict[tuple[int, int], list[str]] = {}
    for s in states:
        attrs = s["attributes"]
        ell = (c_u & attrs["u"]) ^ (c_v & attrs["v"]) ^ (c_w & attrs["w"])
        key = (attrs["x"], ell)
        groups.setdefault(key, []).append(s["state_handle"])

    cells: list[dict[str, Any]] = []
    for idx, (_, members) in enumerate(sorted(groups.items())):
        cells.append(
            {
                "cell_handle": f"{kind}_cell_{idx}",
                "state_handles": list(members),
            }
        )
    return {"repair_operator": "replace_partition", "cells": cells}


def canonical_repair_for_orientation(
    episode: dict[str, Any], *, orientation: str
) -> dict[str, Any]:
    """Convenience: the canonical repair for an orientation code."""
    orientation = LEGACY_ORIENTATION_ALIASES.get(orientation, orientation)
    if orientation not in ORIENTATION_TO_REPAIR_KIND:
        raise Iteration9GluingEpisodeError(f"unknown orientation: {orientation!r}")
    return canonical_repair(episode, kind=ORIENTATION_TO_REPAIR_KIND[orientation])


# ---------------------------------------------------------------------------
# Scanner extension for orientation-family tokens
# ---------------------------------------------------------------------------


def _scan_for_orientation_family_tokens(payload: Any) -> None:
    """Scan a payload for orientation-family tokens.

    This is the gluing-domain extension to the Phase 8.1 scanner — it
    specifically rejects the orientation lexicon (incl. the 2^k opaque codes) so
    an accidental leak of the hidden datum is caught at build time.
    """
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).lower()
    for token in ORIENTATION_FORBIDDEN_TOKENS:
        if re.search(rf"\b{re.escape(token)}\b", serialized):
            raise Iteration9GluingEpisodeError(
                f"orientation-family token {token!r} leaked into model-visible payload"
            )


# ---------------------------------------------------------------------------
# Validation helpers used by tests + downstream policy code
# ---------------------------------------------------------------------------


def validate_crossed_context_episode(episode: dict[str, Any]) -> dict[str, Any]:
    if episode.get("schema_version") != ITERATION9_GLUING_EPISODE_SCHEMA_VERSION:
        raise Iteration9GluingEpisodeError("gluing episode schema mismatch")
    mode = episode.get("mode")
    if mode not in GLUING_MODES:
        raise Iteration9GluingEpisodeError("gluing episode mode missing or unknown")
    model_visible = episode.get("model_visible_initial")
    if not isinstance(model_visible, dict):
        raise Iteration9GluingEpisodeError("gluing episode missing model_visible_initial")
    findings = scan_iteration8_model_visible_payload(model_visible)
    if findings:
        raise Iteration9GluingEpisodeError(f"gluing model_visible leakage: {findings[0]}")
    _scan_for_orientation_family_tokens(model_visible)
    evidence_only = episode.get("evidence_only", {})
    if not isinstance(evidence_only, dict):
        raise Iteration9GluingEpisodeError("gluing episode missing evidence_only")
    evidence_orientation = evidence_only.get("overlap_orientation")
    canonical_orientation = LEGACY_ORIENTATION_ALIASES.get(
        evidence_orientation, evidence_orientation
    )
    if canonical_orientation not in GLUING_ORIENTATIONS:
        raise Iteration9GluingEpisodeError(
            "evidence_only.overlap_orientation must be one of GLUING_ORIENTATIONS"
        )
    states = model_visible.get("world", {}).get("states", [])
    if len(states) != 16:
        raise Iteration9GluingEpisodeError("gluing world must have exactly 16 states")
    return {"status": "pass", "state_count": len(states)}


__all__ = [
    "ITERATION9_GLUING_EPISODE_SCHEMA_VERSION",
    "ITERATION9_PHASE90_CLAIM",
    "GLUING_K_BITS",
    "GLUING_FINE_BITS",
    "GLUING_NUM_PATCHES",
    "GLUING_PATCH_NAMES",
    "gluing_patch_name",
    "gluing_patch_fine_bit",
    "GLUING_OVERLAP_OBSERVABLE",
    "GLUING_ORIENTATIONS",
    "GLUING_MODES",
    "ORIENTATION_TO_REPAIR_KIND",
    "REPAIR_KIND_TO_ORIENTATION",
    "REPAIR_KIND_TO_FUNCTIONAL_COEFFS",
    "ORIENTATION_FORBIDDEN_TOKENS",
    "Iteration9GluingEpisodeError",
    "orientation_to_bits",
    "bits_to_orientation",
    "build_crossed_context_episode",
    "canonical_repair",
    "canonical_repair_for_orientation",
    "validate_crossed_context_episode",
]
