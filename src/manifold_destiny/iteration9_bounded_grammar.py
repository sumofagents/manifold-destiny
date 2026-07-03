"""Iteration 9 — bounded typed grammar of abstraction expressions.

Shared substrate for the bounded-generation probes. A bounded grammar produces
a *finite* set of typed expressions from a small set of atoms and operators,
bounded by a maximum expression depth. Each domain (GF(2), quantum, Lean)
provides its own interpreter; this module owns only the expression type,
grammar configuration, canonicalization, and deterministic enumeration.

The grammar is deliberately tiny: the goal is to show that a generated
candidate absent from the restricted demonstration catalog can be constructed
and accepted by the EXISTING domain verifier, not to solve open-ended program
synthesis. Enumeration is deterministic and commutative operators are
canonicalized so that two equivalent expressions share one canonical key.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Tuple

SCHEMA_VERSION = "manifold-destiny-bounded-grammar-v1"

# Operators that are commutative: their argument order is normalized so that
# two structurally equivalent expressions canonicalize to one key. This keeps
# enumeration, dedupe, and hashing stable.
COMMUTATIVE_OPS: frozenset[str] = frozenset({"xor", "add", "mul", "and", "or"})


@dataclass(frozen=True)
class Expr:
    """A single typed abstraction expression.

    Leaves: op == "atom", args == (name,) where name is an atom label
            (e.g. "u", "alpha", "0").
    Nodes:  op is an operator label (e.g. "xor", "sub"), args is the tuple of
            child Expr operands.
    """

    op: str
    args: Tuple[Any, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.op, str) or not self.op:
            raise ValueError(f"Expr.op must be a non-empty str, got {self.op!r}")
        if not isinstance(self.args, tuple):
            raise ValueError(f"Expr.args must be a tuple, got {type(self.args)}")
        if self.op == "atom":
            if len(self.args) != 1:
                raise ValueError(f"atom Expr needs exactly one arg, got {self.args}")
        else:
            if len(self.args) < 1:
                raise ValueError(f"node Expr needs >=1 args, got {self.args}")
            for child in self.args:
                if not isinstance(child, Expr):
                    raise TypeError(f"node Expr arg must be Expr, got {type(child)}")


def atom(name: str) -> Expr:
    """Construct an atom (leaf) expression."""
    return Expr("atom", (str(name),))


def node(op: str, *operands: Expr) -> Expr:
    """Construct an operator node expression."""
    return Expr(op, tuple(operands))


def expand_grammar(grammar: Grammar, accepted_expr: Expr) -> Grammar:
    """Promote a retained (verifier-accepted) quotient to a new typed atom.

    This is the self-extending grammar mechanism (the self-extending theorem in the paper): every
    retained abstraction becomes a new composition atom, so the grammar grows
    monotonically as the system learns. The new atom's label is derived from the
    accepted expression's canonical key, so promotion is deterministic and
    idempotent (accepting the same fiber twice does not duplicate the atom).

    The promoted atom is a *typed* atom: its definition (the originating Expr)
    is recorded in ``grammar.definitions``, so downstream interpreters can
    resolve ``s_<hash>`` back to the certified expression. Soundness is
    preserved by induction because every promoted atom was verifier-accepted at
    retention time, and composition over certified atoms stays sound assuming
    the verifier is compositional (if q_1 is c-admissible and q_2 is
    c-admissible on the fibers of q_1, then the composed quotient is
    c-admissible — this is what the verifier checks at the next stage).

    Returns a new Grammar (Grammar is frozen). If the accepted_expr's canonical
    key is already an atom in the grammar, the grammar is returned unchanged
    (idempotent promotion).
    """
    if accepted_expr.op == "atom" and accepted_expr.args[0] in grammar.atoms:
        # Already a base atom — no growth needed.
        return grammar
    label = _promoted_atom_label(accepted_expr)
    if label in grammar.atoms:
        # Already promoted (idempotent).
        return grammar
    new_atoms = tuple(list(grammar.atoms) + [label])
    new_defs = tuple(list(grammar.definitions) + [(label, accepted_expr)])
    return Grammar(
        atoms=new_atoms,
        ops=grammar.ops,
        max_depth=grammar.max_depth,
        arities=grammar.arities,
        definitions=new_defs,
    )


def _promoted_atom_label(accepted_expr: Expr) -> str:
    """Deterministic label for a promoted atom, derived from canonical key."""
    key = canonical_key(accepted_expr)
    short = hashlib.sha256(key.encode("utf-8")).hexdigest()[:8]
    return f"s_{short}"


# Public alias (kept under _ for internal use, exported via __all__).
promoted_atom_label = _promoted_atom_label


def self_extend_step(
    grammar: Grammar,
    enumerate_fn,
    verify_fn,
) -> "SelfExtendResult":
    """One round of self-extending enumeration + verification + retention.

    enumerate_fn(grammar) -> list[Expr]: domain-specific enumeration (usually
        grammar.enumerate(), but domains may filter).
    verify_fn(expr) -> bool: domain-specific verifier (accept/reject).

    Returns the retained expressions (verifier-accepted) and the grown grammar
    with each retained quotient promoted to a new atom.

    This is the primitive that the self-extending loop calls. The loop itself
    (run until fixed-point or max rounds) is `self_extend_loop`.
    """
    candidates = enumerate_fn(grammar)
    retained = [e for e in candidates if verify_fn(e)]
    grown = grammar
    for e in retained:
        grown = expand_grammar(grown, e)
    # Derive new_atoms from the actual atom-set diff (not from retained list),
    # to avoid duplicate counting when commutative equivalents are both retained.
    base_atom_set = set(grammar.atoms)
    new_atoms = tuple(
        a for a in grown.atoms if a not in base_atom_set
    )
    return SelfExtendResult(
        base_grammar=grammar,
        grown_grammar=grown,
        candidates=candidates,
        retained=retained,
        new_atoms=new_atoms,
    )


@dataclass(frozen=True)
class SelfExtendResult:
    """One step of the self-extending grammar loop."""

    base_grammar: Grammar
    grown_grammar: Grammar
    candidates: "list[Expr]"
    retained: "list[Expr]"
    new_atoms: Tuple[str, ...]

    @property
    def grew(self) -> bool:
        """True if this step added at least one new atom to the grammar."""
        return len(self.new_atoms) > 0 or len(self.grown_grammar.atoms) > len(self.base_grammar.atoms)


def self_extend_loop(
    seed_grammar: Grammar,
    enumerate_fn,
    verify_fn,
    max_rounds: int = 10,
    stop_on_no_growth: bool = True,
) -> "list[SelfExtendResult]":
    """Run the self-extending grammar loop until fixed-point or max_rounds.

    Each round:
      1. Enumerate the current grammar.
      2. Verify each candidate; retain the accepted ones.
      3. Promote each retained quotient to a new atom.
      4. If the grammar grew, repeat. If not (fixed-point), stop.

    This constructs the grammar hierarchy {G_0, G_1, G_2, ...} where each
    G_{n+1} = expand(G_n, retained(G_n)). The union of retained sets across
    all rounds is the self-extending completeness result (the self-extending theorem in the
    paper).

    stop_on_no_growth=True terminates when a round adds no new atoms (the
    grammar has saturated for the given verifier and depth). Set False to
    always run max_rounds (useful for testing termination claims).
    """
    if max_rounds < 1:
        raise ValueError("max_rounds must be >= 1")
    results: "list[SelfExtendResult]" = []
    current = seed_grammar
    for _ in range(max_rounds):
        step = self_extend_step(current, enumerate_fn, verify_fn)
        results.append(step)
        if stop_on_no_growth and not step.grew:
            break
        current = step.grown_grammar
    return results


def expr_to_str(expr: Expr) -> str:
    """Render an expression to a stable, canonical string.

    Binary ops render infix: (u xor v). Unary ops render prefix: (abs alpha).
    Commutative operators have their operands sorted by canonical key so that
    (u xor v) and (v xor u) render identically. This makes the string form
    stable for receipts.
    """
    if expr.op == "atom":
        return str(expr.args[0])
    operands = (
        sorted(expr.args, key=canonical_key)
        if expr.op in COMMUTATIVE_OPS
        else expr.args
    )
    if len(operands) == 1:
        return f"({expr.op} {expr_to_str(operands[0])})"
    inner = f" {expr.op} ".join(expr_to_str(a) for a in operands)
    return f"({inner})"


def canonical_key(expr: Expr) -> str:
    """Stable canonical key for dedupe and hashing.

    Commutative operators have their operands sorted by rendered string so that
    (u xor v) and (v xor u) share one key. Non-commutative operators preserve
    argument order.
    """
    if expr.op == "atom":
        return f"@{expr.args[0]}"
    if expr.op in COMMUTATIVE_OPS:
        child_keys = sorted(canonical_key(a) for a in expr.args)
        return f"[{expr.op} {' '.join(child_keys)}]"
    child_keys = [canonical_key(a) for a in expr.args]
    return f"[{expr.op} {' '.join(child_keys)}]"


def depth(expr: Expr) -> int:
    """Depth of an expression (atom depth = 0)."""
    if expr.op == "atom":
        return 0
    return 1 + max(depth(a) for a in expr.args)


@dataclass(frozen=True)
class Grammar:
    """A bounded typed grammar.

    atoms    : tuple of atom labels that may appear as leaves (nullary).
    ops      : tuple of operator labels that may appear as internal nodes.
    arities  : optional mapping op->arity. Ops not listed default to arity 2.
               arity 1 = unary (abs, not), arity 2 = binary (xor, sub, add).
               Nullary constants are modeled as atoms, not ops.
    max_depth: maximum expression depth. depth 0 = atoms only.
    definitions: mapping from promoted-atom label to the originating Expr.
               Seed atoms have no definition (they are primitive). Promoted
               atoms (added via expand_grammar) carry their provenance here,
               so downstream interpreters can resolve s_<hash> back to the
               certified expression. This is the semantic payload that makes
               bootstrapped primitives sound (the self-extending theorem).
    """

    atoms: Tuple[str, ...]
    ops: Tuple[str, ...]
    max_depth: int = 2
    arities: Tuple[Tuple[str, int], ...] = ()
    definitions: Tuple[Tuple[str, "Expr"], ...] = ()

    def _arity(self, op: str) -> int:
        for label, arity in self.arities:
            if label == op:
                return arity
        return 2

    def __post_init__(self) -> None:
        if not isinstance(self.atoms, tuple) or not self.atoms:
            raise ValueError("Grammar.atoms must be a non-empty tuple")
        if not isinstance(self.ops, tuple):
            raise ValueError("Grammar.ops must be a tuple")
        if self.max_depth < 0:
            raise ValueError("Grammar.max_depth must be >= 0")
        if not isinstance(self.arities, tuple):
            raise ValueError("Grammar.arities must be a tuple")
        for label, arity in self.arities:
            if arity not in (1, 2):
                raise ValueError(
                    f"arity for {label!r} must be 1 or 2, got {arity}"
                )

    @property
    def signature(self) -> str:
        """Stable signature for receipts: hashes the frozen grammar config."""
        payload = {
            "schema": SCHEMA_VERSION,
            "atoms": list(self.atoms),
            "ops": list(self.ops),
            "max_depth": self.max_depth,
            "arities": [[k, v] for k, v in self.arities],
        }
        blob = _canonical_json(payload)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def has_op(self, op: str) -> bool:
        return op in self.ops

    def enumerate(self) -> list[Expr]:
        """Deterministically enumerate all expressions up to max_depth.

        Returns a de-duplicated list ordered by (depth, canonical_key). Atoms
        come first (depth 0), then all depth-1 nodes, then depth-2, etc.

        At depth d, an expression has max(child depths) == d-1. We compose
        from ALL prior levels (not just the previous one) so that mixed-depth
        expressions like (u xor (v xor w)) are included.
        """
        seen: dict[str, Expr] = {}
        # depth 0: atoms only
        current: list[Expr] = []
        for label in self.atoms:
            expr = atom(label)
            key = canonical_key(expr)
            if key not in seen:
                seen[key] = expr
                current.append(expr)
        # levels[d] = list of all expressions at exactly depth d
        levels: list[list[Expr]] = [current]
        # all_prior[d-1] = list of all expressions at depth <= d-1
        all_prior: list[list[Expr]] = [list(current)]

        for target_depth in range(1, self.max_depth + 1):
            next_level: list[Expr] = []
            shallower = all_prior[target_depth - 1]  # depth <= target-1
            exactly_prev = levels[target_depth - 1]  # depth == target-1
            for op in self.ops:
                arity = self._arity(op)
                if arity == 1:
                    # unary: child must be at exactly target-1 so the node is
                    # at the target depth (not shallower)
                    for child in exactly_prev:
                        candidate = node(op, child)
                        key = canonical_key(candidate)
                        if key not in seen:
                            seen[key] = candidate
                            next_level.append(candidate)
                else:
                    # binary: at least one child at exactly target-1
                    for left in shallower:
                        left_d = depth(left)
                        for right in shallower:
                            if max(left_d, depth(right)) != target_depth - 1:
                                continue
                            candidate = node(op, left, right)
                            key = canonical_key(candidate)
                            if key not in seen:
                                seen[key] = candidate
                                next_level.append(candidate)
            if not next_level:
                break
            levels.append(next_level)
            all_prior.append(all_prior[-1] + next_level)

        all_exprs: list[Expr] = []
        for level_exprs in levels:
            all_exprs.extend(level_exprs)
        all_exprs.sort(key=lambda e: (depth(e), canonical_key(e)))
        return all_exprs


def _canonical_json(payload: Any) -> str:
    """Canonical JSON for hashing: sorted keys, compact separators, trailing newline."""
    import json

    return json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"


def expr_digest(expr: Expr) -> str:
    """SHA-256 digest of an expression's canonical key."""
    blob = canonical_key(expr)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


__all__ = [
    "SCHEMA_VERSION",
    "COMMUTATIVE_OPS",
    "Expr",
    "atom",
    "node",
    "expr_to_str",
    "canonical_key",
    "depth",
    "Grammar",
    "expr_digest",
    "expand_grammar",
    "self_extend_step",
    "self_extend_loop",
    "SelfExtendResult",
    "promoted_atom_label",
]
