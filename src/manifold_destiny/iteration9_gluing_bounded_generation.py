"""Iteration 9 — GF(2) bounded generation interpreter.

Consumes the shared bounded grammar (``iteration9_bounded_grammar``) and the
existing GF(2) gluing verifier (``iteration9_gluing_verifier``) WITHOUT editing
either. A generated expression is evaluated over the world states to produce a
quotient proposal; the existing verifier accepts or rejects it.

Multiple grammar expressions can map to the same partition (e.g.
``(u xor v)`` and ``((u xor v) xor (w xor w))`` are algebraically equivalent on
GF(2)). Accepted candidates are therefore deduplicated by FIBER SIGNATURE
(canonical partition), not by expression string. The result is a set of
distinct accepted abstractions, not a set of syntactically-different but
semantically-identical expressions.

The restricted demonstration catalog Q_0 = {0, u, v, w} is explicitly named.
The repo's full gluing catalog contains additional operators (e.g. R_4 = u⊕v);
novelty is asserted against Q_0, not against the full repo.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from manifold_destiny.iteration9_bounded_grammar import (
    Expr,
    Grammar,
    atom,
    canonical_key,
    depth,
    expr_digest,
    expr_to_str,
    node,
)
from manifold_destiny.iteration9_gluing_episode import build_crossed_context_episode
from manifold_destiny.iteration9_gluing_verifier import (
    global_glue_objective,
    validate_gluing_factorization,
)
from manifold_destiny.iteration9_manifold_store import (
    canonical_fiber_signature_from_partition,
)

# The restricted demonstration catalog. The repo's full gluing operator space
# is larger (it includes composed functionals like R_4 = u⊕v); novelty is
# asserted against THIS restricted set, not the full repo.
RESTRICTED_CATALOG_Q0: Tuple[str, ...] = ("0", "u", "v", "w")

# Verifier contract for receipts: the existing GF(2) gluing verifier pair.
GF2_VERIFIER_CONTRACT: Tuple[str, ...] = (
    "global_glue_objective",
    "validate_gluing_factorization",
    "v1",
)


def _eval_expr(expr: Expr, attrs: Dict[str, int]) -> int:
    """Evaluate a grammar expression over GF(2) bit attributes."""
    if expr.op == "atom":
        label = str(expr.args[0])
        if label == "0":
            return 0
        if label == "1":
            return 1
        return int(attrs[label]) & 1
    if expr.op == "xor":
        return _eval_expr(expr.args[0], attrs) ^ _eval_expr(expr.args[1], attrs)
    if expr.op == "and":
        return _eval_expr(expr.args[0], attrs) & _eval_expr(expr.args[1], attrs)
    if expr.op == "or":
        return _eval_expr(expr.args[0], attrs) | _eval_expr(expr.args[1], attrs)
    raise ValueError(f"unsupported GF(2) op: {expr.op!r}")


def _proposal_from_expr(episode: Dict[str, Any], expr: Expr) -> Dict[str, Any]:
    """Build a quotient proposal partitioning by (x, expr)."""
    states = episode["model_visible_initial"]["world"]["states"]
    groups: Dict[Tuple[int, int], List[str]] = {}
    for state in states:
        attrs = state["attributes"]
        key = (int(attrs["x"]) & 1, _eval_expr(expr, attrs))
        groups.setdefault(key, []).append(state["state_handle"])
    cells = []
    for idx, (_key, handles) in enumerate(sorted(groups.items())):
        cells.append(
            {"cell_handle": f"gen_cell_{idx}", "state_handles": list(handles)}
        )
    return {"repair_operator": "replace_partition", "cells": cells}


def _partition_cells(proposal: Dict[str, Any]) -> List[List[str]]:
    """Extract the list of cells (each a list of handles) from a proposal."""
    return [cell["state_handles"] for cell in proposal["cells"]]


def evaluate_generated_candidate(
    episode: Dict[str, Any], expr: Expr
) -> Dict[str, Any]:
    """Run the existing verifier on a single generated expression.

    Returns the G verdict, composite verdict, fiber signature, and cell count.
    Does NOT decide whether to retain — that is the caller's job.
    """
    proposal = _proposal_from_expr(episode, expr)
    g = global_glue_objective(episode, proposal)
    composite = validate_gluing_factorization(episode, proposal)
    cells = _partition_cells(proposal)
    fiber_hash = canonical_fiber_signature_from_partition(cells)
    return {
        "expr": expr,
        "expr_str": expr_to_str(expr),
        "canonical_key": canonical_key(expr),
        "digest": expr_digest(expr),
        "g_verdict": g["verdict"],
        "composite_verdict": composite["verdict"],
        "fiber_signature_hash": fiber_hash,
        "cell_count": len(cells),
        "proposal": proposal,
    }


def find_accepted_abstractions(
    episode: Dict[str, Any],
    grammar: Grammar,
) -> List[Dict[str, Any]]:
    """Enumerate grammar expressions and return distinct accepted abstractions.

    Deduplicates by fiber signature (semantic equivalence), not by expression
    string. Multiple expressions that induce the same partition collapse to
    one accepted abstraction. Within each fiber class, the SHALLOWEST
    expression is kept as the canonical representative.
    """
    all_exprs = grammar.enumerate()
    accepted_by_fiber: Dict[str, Dict[str, Any]] = {}
    for expr in all_exprs:
        result = evaluate_generated_candidate(episode, expr)
        if result["g_verdict"] != "accepted":
            continue
        if result["composite_verdict"] != "valid":
            continue
        fiber = result["fiber_signature_hash"]
        existing = accepted_by_fiber.get(fiber)
        if existing is None or depth(expr) < depth(existing["expr"]):
            accepted_by_fiber[fiber] = result
    return sorted(
        accepted_by_fiber.values(),
        key=lambda r: (depth(r["expr"]), r["canonical_key"]),
    )


def fixed_catalog_results(
    episode: Dict[str, Any],
    catalog: Tuple[str, ...] = RESTRICTED_CATALOG_Q0,
) -> List[Dict[str, Any]]:
    """Run the fixed demonstration catalog Q_0 through the same verifier."""
    results = []
    for label in catalog:
        expr = atom(label)
        result = evaluate_generated_candidate(episode, expr)
        results.append(
            {
                "expr_str": result["expr_str"],
                "g_verdict": result["g_verdict"],
                "composite_verdict": result["composite_verdict"],
                "fiber_signature_hash": result["fiber_signature_hash"],
            }
        )
    return results


def build_episode(orientation: str = "m100", variant: str = "bg") -> Dict[str, Any]:
    """Build a GF(2) gluing episode for bounded generation."""
    return build_crossed_context_episode(
        orientation=orientation, mode="eval", variant=variant
    )


__all__ = [
    "RESTRICTED_CATALOG_Q0",
    "GF2_VERIFIER_CONTRACT",
    "evaluate_generated_candidate",
    "find_accepted_abstractions",
    "fixed_catalog_results",
    "build_episode",
]
