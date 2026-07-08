"""Iteration 9 — Lean bounded generation interpreter.

Consumes the shared bounded grammar and the Lean 4.31.0 kernel (via subprocess)
as the verifier. Emits a self-contained Lean source defining a finite world W,
a consumer c, a restricted demonstration catalog Q_0, and a generated quotient
qgen built from the grammar. The kernel certifies admissibility (Adm) and
semantic novelty (Not FiberEq) vs every Q_0 member.

No mathlib required. The source is pure kernel/subprocess. A bad generated
candidate (one that drops the consumer-preserving component) must be rejected
by the kernel — exit nonzero.

Witness states for the Not FiberEq proofs are computed in Python from the
Boolean world, not hand-authored, so the emitter generalizes across target
expressions (u xor v, u xor w, v xor w, u xor v xor w).
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from manifold_destiny.iteration9_bounded_grammar import Expr, atom, expr_to_str, node

LEAN = Path.home() / ".elan/bin/lean"

# The restricted demonstration catalog Q_0 for the Lean domain.
# Each member is (x, <single-field>): q0=(x,false), qu=(x,u), qv=(x,v), qw=(x,w).
# The target qgen=(x, bXor u v) is absent from Q_0.
LEAN_RESTRICTED_CATALOG_Q0: Tuple[str, ...] = ("q0", "qu", "qv", "qw")

LEAN_VERIFIER_CONTRACT: Tuple[str, ...] = (
    "lean_kernel_4_31_0",
    "admissibility_check",
    "novelty_not_fibereq",
    "v1",
)

LEAN_SCHEMA_VERSION = "lean_bounded_generation_v1"


def lean_available() -> bool:
    """Is the Lean kernel available on this machine?"""
    return LEAN.exists()


def _lean_version() -> str:
    """Capture the Lean version string for receipts."""
    if not lean_available():
        return "unavailable"
    try:
        result = subprocess.run(
            [str(LEAN), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip().split("\n")[0]
    except Exception:
        return "unknown"


def _field_vars(expr: Expr) -> List[str]:
    """Extract the field variables referenced in an expression."""
    if expr.op == "atom":
        label = str(expr.args[0])
        if label in ("u", "v", "w"):
            return [label]
        return []
    result: List[str] = []
    for child in expr.args:
        for v in _field_vars(child):
            if v not in result:
                result.append(v)
    return result


def _expr_to_lean_term(expr: Expr) -> str:
    """Render a grammar expression as a Lean term over s : W."""
    if expr.op == "atom":
        label = str(expr.args[0])
        if label in ("u", "v", "w"):
            return f"s.{label}"
        if label in ("0", "false"):
            return "false"
        if label in ("1", "true"):
            return "true"
        return label
    if expr.op == "xor":
        return f"bXor {_expr_to_lean_term(expr.args[0])} {_expr_to_lean_term(expr.args[1])}"
    raise ValueError(f"unsupported Lean grammar op: {expr.op}")


def _bool_str(b: bool) -> str:
    return "true" if b else "false"


def _state_lean(x: bool, u: bool, v: bool, w: bool) -> str:
    return f"{{ x := {_bool_str(x)}, u := {_bool_str(u)}, v := {_bool_str(v)}, w := {_bool_str(w)} }}"


def _find_novelty_witness(
    target_fn, catalog_fn
) -> Optional[Tuple[Tuple, Tuple]]:
    """Find two states where catalog agrees but target disagrees.

    Returns (state_a, state_b) or None if no witness exists.
    """
    import itertools

    states = list(itertools.product(*[(False, True)] * 4))
    for a in states:
        for b in states:
            if a == b:
                continue
            xa, ua, va, wa = a
            xb, ub, vb, wb = b
            if catalog_fn(xa, ua, va, wa) == catalog_fn(xb, ub, vb, wb):
                if target_fn(xa, ua, va, wa) != target_fn(xb, ub, vb, wb):
                    return (a, b)
    return None


def _eval_xor_expr(expr: Expr, x: bool, u: bool, v: bool, w: bool) -> bool:
    """Evaluate a grammar xor expression over Boolean fields (Python side)."""
    if expr.op == "atom":
        label = str(expr.args[0])
        if label == "u":
            return u
        if label == "v":
            return v
        if label == "w":
            return w
        if label in ("0", "false"):
            return False
        if label in ("1", "true"):
            return True
        raise ValueError(f"unknown atom: {label}")
    if expr.op == "xor":
        return _eval_xor_expr(expr.args[0], x, u, v, w) ^ _eval_xor_expr(
            expr.args[1], x, u, v, w
        )
    raise ValueError(f"unsupported op: {expr.op}")


def emit_lean_source(
    target_expr: Expr,
    catalog_members: Tuple[str, ...] = LEAN_RESTRICTED_CATALOG_Q0,
) -> Tuple[str, Tuple[str, ...]]:
    """Emit a self-contained Lean source for the given target expression.

    Returns (source, proved_theorem_names) where proved_theorem_names is the
    exact list of theorem names emitted. This lets certify() report ONLY what
    was actually proved, not a hardcoded list.

    The source defines W, c, Adm, FiberEq, Q_0, qgen, the admissibility proof,
    and a Not FiberEq proof per catalog member (witnesses computed in Python).

    Raises ValueError if a novelty witness cannot be found for any catalog
    member — this means the target is fiber-equivalent to that member, so the
    generated quotient is NOT novel and must not be silently certified.
    """
    target_term = _expr_to_lean_term(target_expr)
    target_fn = lambda x, u, v, w: _eval_xor_expr(target_expr, x, u, v, w)

    catalog_fns = {
        "q0": lambda x, u, v, w: (x, False),
        "qu": lambda x, u, v, w: (x, u),
        "qv": lambda x, u, v, w: (x, v),
        "qw": lambda x, u, v, w: (x, w),
    }
    catalog_def_templates = {
        "q0": "def q0 (s : W) : Bool × Bool := (s.x, false)",
        "qu": "def qu (s : W) : Bool × Bool := (s.x, s.u)",
        "qv": "def qv (s : W) : Bool × Bool := (s.x, s.v)",
        "qw": "def qw (s : W) : Bool × Bool := (s.x, s.w)",
    }
    catalog_defs = [catalog_def_templates[name] for name in catalog_members]

    # Build novelty proofs with Python-computed witnesses. FAIL HARD if any
    # catalog member has no witness — that means the target is NOT novel vs
    # that member, and claiming it would be false certification.
    novelty_proofs = []
    proved_names: List[str] = ["Adm(qgen,c)"]
    for name in catalog_members:
        witness = _find_novelty_witness(target_fn, catalog_fns[name])
        if witness is None:
            raise ValueError(
                f"no novelty witness for {name!r}: target is fiber-equivalent "
                "to this catalog member, so it cannot be certified as novel"
            )
        (xa, ua, va, wa), (xb, ub, vb, wb) = witness
        sa = _state_lean(xa, ua, va, wa)
        sb = _state_lean(xb, ub, vb, wb)
        theorem_name = f"qgen_not_fibereq_{name}"
        novelty_proofs.append(
            f"""theorem {theorem_name} : Not (FiberEq qgen {name}) := by
  intro h
  have hcat : {name} {sa} = {name} {sb} := by rfl
  have hgen : qgen {sa} = qgen {sb} := (h {sa} {sb}).2 hcat
  cases hgen"""
        )
        proved_names.append(f"not FiberEq(qgen,{name})")

    novelty_block = "\n\n".join(novelty_proofs)
    catalog_block = "\n".join(catalog_defs)

    source = f"""structure W where
  x : Bool
  u : Bool
  v : Bool
  w : Bool
deriving DecidableEq

def bXor : Bool -> Bool -> Bool
| false, false => false
| false, true => true
| true, false => true
| true, true => false

def c (s : W) : Bool := s.x

def Adm {{A : Type}} (q : W -> A) : Prop :=
  forall a b : W, q a = q b -> c a = c b

def FiberEq {{A B : Type}} (q : W -> A) (r : W -> B) : Prop :=
  forall a b : W, q a = q b <-> r a = r b

-- Restricted fixed catalog Q_0 (excludes the generated target).
{catalog_block}

-- Generated by bounded grammar.
def qgen (s : W) : Bool × Bool := (s.x, {target_term})

-- Verifier certificate: generated quotient preserves the consumer.
theorem qgen_admissible : Adm qgen := by
  intro a b h
  simpa [qgen, c] using congrArg Prod.fst h

{novelty_block}
"""
    return source, tuple(proved_names)


def emit_bad_source() -> str:
    """Emit a source with a bad candidate that drops x (must be rejected)."""
    return """structure W where
  x : Bool
  u : Bool
  v : Bool
  w : Bool
deriving DecidableEq

def bXor : Bool -> Bool -> Bool
| false, false => false
| false, true => true
| true, false => true
| true, true => false

def c (s : W) : Bool := s.x

def Adm {A : Type} (q : W -> A) : Prop :=
  forall a b : W, q a = q b -> c a = c b

-- Bad candidate: drops x, so it cannot preserve consumer c.
def qbad (s : W) : Bool × Bool := (bXor s.u s.v, false)

-- This proof attempt should fail.
theorem qbad_admissible_badproof : Adm qbad := by
  intro a b h
  simpa [qbad, c] using congrArg Prod.fst h
"""


def run_lean(source: str, prefix: str = "manifold_destiny_lean_bg_") -> Dict[str, Any]:
    """Write source to a temp file and run the Lean kernel on it."""
    if not lean_available():
        return {
            "available": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": "lean kernel not available",
        }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".lean", delete=False, prefix=prefix, dir="/tmp"
    ) as handle:
        handle.write(source)
        path = handle.name
    try:
        result = subprocess.run(
            [str(LEAN), path], capture_output=True, text=True, timeout=30
        )
        return {
            "available": True,
            "path": path,
            "exit_code": result.returncode,
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:2000],
        }
    except subprocess.TimeoutExpired:
        return {
            "available": True,
            "path": path,
            "exit_code": -1,
            "stdout": "",
            "stderr": "lean kernel timed out",
        }
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def certify(target_expr: Expr) -> Dict[str, Any]:
    """Run the full Lean certification for a generated target expression.

    Returns the exit code, stderr, and the list of propositions ACTUALLY
    certified (derived from emitted theorem names, not hardcoded).

    Enforces the Lean version matches the declared contract. Returns an error
    result (exit_code=-1, certifies=[]) if the installed Lean version differs
    from 4.31.0 (the version this gate was authored and tested against).
    """
    source, proved_names = emit_lean_source(target_expr)
    result = run_lean(source)

    observed_version = _lean_version()
    # Enforce exact version match so the contract tuple cannot mislabel the
    # verifier. The contract says lean_kernel_4_31_0; the kernel must be that.
    if result.get("available") and "4.31.0" not in observed_version:
        return {
            "lean_version": observed_version,
            "exit_code": -1,
            "stderr": (
                f"Lean version mismatch: contract requires 4.31.0, "
                f"observed {observed_version!r}"
            ),
            "certifies": [],
            "available": True,
            "version_enforced": True,
        }

    # Only report certification if the kernel accepted (exit 0, no stderr).
    certifies = list(proved_names) if result["exit_code"] == 0 else []
    return {
        "lean_version": observed_version,
        "exit_code": result["exit_code"],
        "stderr": result.get("stderr", ""),
        "certifies": certifies,
        "available": result.get("available", True),
        "version_enforced": result.get("available", False),
    }


__all__ = [
    "LEAN",
    "LEAN_RESTRICTED_CATALOG_Q0",
    "LEAN_VERIFIER_CONTRACT",
    "LEAN_SCHEMA_VERSION",
    "lean_available",
    "emit_lean_source",
    "emit_bad_source",
    "run_lean",
    "certify",
]
