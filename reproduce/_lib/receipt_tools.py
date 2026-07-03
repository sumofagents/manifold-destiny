#!/usr/bin/env python3
"""Three-tier reproduction-receipt tooling for ``reproduce/``.

This module is the single owner of *all* receipt logic for the reproduction
area. The per-section ``run.sh`` scripts stay thin: they run pytest with the
right files + marker, then hand the JUnit XML to this tool. Nothing about a
receipt — its shape, its digest, what counts as the stable claim payload vs.
volatile metadata — is implemented in bash.

Three tiers (see ``reproduce/RECEIPT_SCHEMA.md``):

  * ``receipts/canonical.json`` — COMMITTED. The blessed receipt the paper
    cites. Frozen in Phase 6 from a clean source commit (carries
    ``source_commit``).
  * ``receipts/latest.json``   — GITIGNORED. What a reviewer's ``run.sh`` run
    produces on their machine.
  * digest diff               — ``compare`` recomputes the *stable digest* of
    each file's ``claim_payload`` and reports MATCH / MISMATCH / PENDING/ERROR.

Stable-digest rule (the whole point of the split): only ``claim_payload`` is
hashed. Everything environment- or run-dependent — wall-clock time, runtime
seconds, local paths, skip *messages*, host, python build, the per-run
``source_commit`` of a reviewer — lives under ``provenance`` and is NEVER
hashed. Two honest runs of the same frozen code therefore produce the same
``claim_digest`` even though their ``provenance`` blocks differ.

The canonical JSON encoding (sorted keys, compact separators, trailing
newline, sha256) is byte-for-byte identical to
``manifold_destiny.iteration9_bounded_generation_receipts.BoundedGenerationReceiptV1.to_json``
so a domain receipt embedded in ``claim_payload`` hashes consistently here and
in the package.

CLI::

    receipt_tools.py finalize --section ID --section-dir DIR --junit X.xml \
        --files "a.py b.py" --gate-rc N --mode lite|full
    receipt_tools.py freeze   --section-dir DIR     # Phase 6: latest.json -> canonical.json
    receipt_tools.py compare  --section-dir DIR     # or --canonical/--latest
    receipt_tools.py digest   --file FILE           # stable digest of claim_payload
    receipt_tools.py show     --file FILE           # pretty-print an envelope

``finalize`` always writes ``latest.json`` (even on gate failure, so the run is
inspectable) and prints a machine-readable ``MANIFEST_SUMMARY ...`` line that
``all.sh`` parses. Its exit code is authoritative for ``run.sh``:

  * gate failed (gate-rc != 0)            -> gate-rc          (gate failure dominates)
  * canonical missing / placeholder       -> 0  (PENDING is informational for future/unfrozen sections)
  * canonical real and digest MATCH       -> 0
  * canonical real and digest MISMATCH    -> 3
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

ENVELOPE_SCHEMA = "manifold-reproduce-receipt-v1"
MANIFEST_KIND = "gate_manifest_v1"
PLACEHOLDER_STATUS = "PLACEHOLDER_PENDING_PHASE6"
FROZEN_STATUS = "FROZEN"

# Domain receipt schema that each gate's claim corresponds to (informational;
# embedded in the manifest so the receipt lineage is self-describing).
SECTION_DOMAIN_SCHEMA: Dict[str, str] = {
    "01_synthetic_gf2": "manifold-destiny-bounded-generation-v1",
    "02_quantum": "manifold-destiny-bounded-generation-v1",
    "03_lean_generation": "manifold-destiny-bounded-generation-v1",
    "04_real_corpus_replay": "lean_github_replay_receipt_v1",
    "05_manifold_store": "manifold-destiny-bounded-generation-v1",
    "06_self_extending_grammar": "manifold-destiny-bounded-generation-v1",
}

# Quantum data location probed only for provenance (never hashed). Resolves
# via the same env vars as the test/module: MANIFOLD_QUANTUM_DATA first, then
# MANIFOLD_DATA_DIR root, then neutral default.
_q_data_root = os.path.expanduser(
    os.environ.get("MANIFOLD_DATA_DIR", str(Path.home() / ".manifold-destiny" / "data"))
)
_QUANTUM_DATA_PATH = Path(
    os.path.expanduser(
        os.environ.get(
            "MANIFOLD_QUANTUM_DATA",
            str(Path(_q_data_root) / "quantum-expanded-data.json"),
        )
    )
)


# --------------------------------------------------------------------------- #
# Canonical JSON + stable digest  (must match the package receipt encoder)
# --------------------------------------------------------------------------- #


def canonical_json(payload: Any) -> str:
    """Sorted keys, compact separators, trailing newline — deterministic.

    Byte-for-byte identical to ``BoundedGenerationReceiptV1.to_json``.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"


def stable_digest(claim_payload: Any) -> str:
    """``sha256:`` over the canonical JSON of *only* the claim payload.

    This is the single definition of "the digest". Volatile/provenance fields
    are not passed in and so cannot influence it.
    """
    blob = canonical_json(claim_payload).encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


# --------------------------------------------------------------------------- #
# JUnit XML parsing  -> stable claim surface + (volatile) outcomes
# --------------------------------------------------------------------------- #


def _testsuite(root: ET.Element) -> ET.Element:
    if root.tag == "testsuite":
        return root
    suite = root.find("testsuite")
    if suite is None:
        raise ValueError("no <testsuite> element in JUnit XML")
    return suite


def parse_junit(junit_path: Path) -> Dict[str, Any]:
    """Extract the *stable claim surface* and the *volatile outcomes*.

    The claim surface (``claim_tests``) is the sorted set of every collected
    test case's ``classname::name`` key. It is machine-independent: ``skipif``
    still *collects* a test (it reports as skipped, not deselected), so a
    reviewer without Lean / without the quantum data collects the same surface
    as a fully equipped machine. Only the *outcomes* differ, and outcomes are
    provenance, not claim.
    """
    suite = _testsuite(ET.parse(str(junit_path)).getroot())

    claim_tests: List[str] = []
    skipped: List[str] = []
    failed: List[str] = []
    errored: List[str] = []

    for tc in suite.findall("testcase"):
        key = f"{tc.get('classname', '')}::{tc.get('name', '')}"
        claim_tests.append(key)
        # A testcase carries at most one of these outcome children.
        if tc.find("skipped") is not None:
            skipped.append(key)
        if tc.find("failure") is not None:
            failed.append(key)
        if tc.find("error") is not None:
            errored.append(key)

    total = len(claim_tests)
    n_skip, n_fail, n_err = len(skipped), len(failed), len(errored)
    passed = total - n_skip - n_fail - n_err

    return {
        "claim_tests": sorted(claim_tests),
        "outcomes": {
            "total": total,
            "passed": passed,
            "skipped": n_skip,
            "failed": n_fail,
            "errors": n_err,
        },
        "skipped_tests": sorted(skipped),
        "failed_tests": sorted(failed + errored),
        "runtime_seconds": float(suite.get("time", "0") or "0"),
    }


# --------------------------------------------------------------------------- #
# Provenance probes (all NON-hashed)
# --------------------------------------------------------------------------- #


def _git_head(repo_root: Path) -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return None


def _git_dirty(repo_root: Path) -> Optional[bool]:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0:
            return bool(out.stdout.strip())
    except Exception:
        pass
    return None


def _pyarrow_available() -> bool:
    try:
        import pyarrow  # noqa: F401
        return True
    except Exception:
        return False


def detect_dependencies() -> Dict[str, Any]:
    """Environment capability tokens — provenance only, never hashed.

    A digest MISMATCH against canonical becomes diagnosable by reading these:
    e.g. ``lean_available=false`` explains why the Lean claims were skipped.
    """
    return {
        "lean_available": shutil.which("lean") is not None,
        "lake_available": shutil.which("lake") is not None,
        "quantum_data_present": _QUANTUM_DATA_PATH.exists(),
        "pyarrow_available": _pyarrow_available(),
    }


# --------------------------------------------------------------------------- #
# Envelope construction
# --------------------------------------------------------------------------- #


def build_envelope(
    section: str,
    junit: Dict[str, Any],
    test_files: List[str],
    mode: str,
    gate_rc: int,
    repo_root: Path,
) -> Dict[str, Any]:
    """Assemble a ``manifold-reproduce-receipt-v1`` envelope.

    ``claim_payload`` (HASHED) holds only the machine-independent claim surface.
    ``provenance`` (NOT HASHED) holds everything run/environment dependent.
    """
    claim_payload = {
        "kind": MANIFEST_KIND,
        "section": section,
        "domain_receipt_schema": SECTION_DOMAIN_SCHEMA.get(section, "unknown"),
        "test_files": sorted(test_files),
        "claim_tests": junit["claim_tests"],
        # Future schemas may embed rich per-domain receipts here under a
        # "domain_receipts" key; the digest/compare contract is agnostic to
        # claim_payload's internal shape.
    }

    provenance: Dict[str, Any] = {
        "mode": mode,
        "gate_exit_code": gate_rc,
        "outcomes": junit["outcomes"],
        # Which claims this particular run could NOT verify (env-dependent).
        # Diagnostic only — kept out of the hashed payload on purpose.
        "skipped_tests": junit["skipped_tests"],
        "failed_tests": junit["failed_tests"],
        "dependencies": detect_dependencies(),
        "runtime_seconds": junit["runtime_seconds"],
        "python_version": platform.python_version(),
        "platform": f"{platform.system().lower()}-{platform.machine()}",
        # Informational for latest.json: the commit the reviewer ran against.
        # canonical.json's source_commit is the FROZEN generation commit and is
        # set by the Phase 6 promotion step, not here.
        "source_commit": _git_head(repo_root),
        "working_tree_dirty": _git_dirty(repo_root),
    }

    claim_digest = stable_digest(claim_payload)
    return {
        "schema": ENVELOPE_SCHEMA,
        "section": section,
        "claim_payload": claim_payload,
        "claim_digest": claim_digest,
        "provenance": provenance,
    }


# --------------------------------------------------------------------------- #
# Compare
# --------------------------------------------------------------------------- #


def is_placeholder(envelope: Optional[Dict[str, Any]]) -> bool:
    if envelope is None:
        return True
    if envelope.get("status") == PLACEHOLDER_STATUS:
        return True
    return envelope.get("claim_payload") is None


def _load(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def compare_envelopes(
    canonical: Optional[Dict[str, Any]],
    latest: Optional[Dict[str, Any]],
) -> Tuple[str, str]:
    """Return ``(verdict, detail)``.

    verdict in {MATCH, MISMATCH, PENDING, ERROR}.
    PENDING  = canonical absent or an unfrozen placeholder (informational).
    ERROR    = latest missing/unreadable (an infrastructure problem).
    """
    if latest is None or latest.get("claim_payload") is None:
        return "ERROR", "latest.json missing or has no claim_payload"
    if is_placeholder(canonical):
        return "PENDING", "canonical.json is missing or not yet frozen"

    d_can = stable_digest(canonical["claim_payload"])
    d_lat = stable_digest(latest["claim_payload"])
    if d_can == d_lat:
        return "MATCH", d_lat
    return "MISMATCH", f"canonical={d_can} latest={d_lat}"


# --------------------------------------------------------------------------- #
# CLI commands
# --------------------------------------------------------------------------- #


def _repo_root_from(start: Path) -> Path:
    """Walk up to the repository root (the dir holding ``reproduce/``)."""
    cur = start.resolve()
    for cand in [cur, *cur.parents]:
        if (cand / "reproduce").is_dir() and (cand / "pyproject.toml").exists():
            return cand
    return start.resolve()


def cmd_finalize(args: argparse.Namespace) -> int:
    section_dir = Path(args.section_dir).resolve()
    repo_root = _repo_root_from(section_dir)
    receipts_dir = section_dir / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)

    junit = parse_junit(Path(args.junit))
    test_files = [f for f in (args.files or "").split() if f]
    envelope = build_envelope(
        section=args.section,
        junit=junit,
        test_files=test_files,
        mode=args.mode,
        gate_rc=args.gate_rc,
        repo_root=repo_root,
    )

    latest_path = receipts_dir / "latest.json"
    latest_path.write_text(canonical_json(envelope))

    if getattr(args, "skip_compare", False):
        # Full mode: compare against canonical_full.json if it exists
        full_canonical_path = receipts_dir / "canonical_full.json"
        if full_canonical_path.exists() and args.mode == "full":
            canonical = _load(full_canonical_path)
            verdict, detail = compare_envelopes(canonical, envelope)
        else:
            canonical = None
            verdict, detail = "FULL", "full-mode run; no canonical_full.json to compare"
    else:
        canonical = _load(receipts_dir / "canonical.json")
        verdict, detail = compare_envelopes(canonical, envelope)

    oc = junit["outcomes"]
    gate_result = "PASS" if args.gate_rc == 0 else "FAIL"

    # Human-readable block.
    print(f"  receipt    : {latest_path.relative_to(repo_root)}")
    print(f"  claim_digest: {envelope['claim_digest']}")
    print(f"  vs canonical: {verdict}" + (f"  ({detail})" if detail else ""))

    # Machine-readable summary consumed by all.sh.
    print(
        "MANIFEST_SUMMARY "
        f"section={args.section} gate={gate_result} mode={args.mode} "
        f"passed={oc['passed']} skipped={oc['skipped']} failed={oc['failed']} "
        f"errors={oc['errors']} digest={verdict}"
    )

    # Exit policy: gate failure dominates; otherwise a real mismatch fails.
    if args.gate_rc != 0:
        return args.gate_rc
    if verdict == "MISMATCH":
        return 3
    if verdict == "ERROR":
        return 4
    return 0


def cmd_freeze(args: argparse.Namespace) -> int:
    """Phase 6 promotion: freeze a section's ``latest.json`` into ``canonical.json``.

    Reads the section's ``latest.json`` (produced by a fresh ``run.sh``), stamps
    the current ``git HEAD`` as the frozen ``source_commit`` (the commit the
    receipt was generated FROM — the canonical file itself lands in a follow-up
    commit, so it never hashes a tree containing itself), marks
    ``status=FROZEN``, and writes ``canonical.json`` with the same canonical
    encoding as every other receipt.

    ``claim_payload`` and ``claim_digest`` are carried over **verbatim** from
    ``latest.json`` so the frozen digest is byte-for-byte the one the generating
    run produced — only ``status`` and ``provenance.source_commit`` change.

    Refuses to freeze (exit 1) if:

    * ``latest.json`` is missing / has no ``claim_payload``
    * the recorded ``gate_exit_code`` is not exactly ``0``
    * ``claim_digest`` does not match a recomputation over ``claim_payload``
    * the working tree is dirty (use ``--allow-dirty`` to override)
    * ``canonical.json`` is already frozen (use ``--force`` to re-freeze)
    * ``git HEAD`` is unresolvable

    Exit 0 on success.
    """
    section_dir = Path(args.section_dir).resolve()
    repo_root = _repo_root_from(section_dir)
    receipts_dir = section_dir / "receipts"
    latest_path = receipts_dir / "latest.json"
    canonical_path = receipts_dir / "canonical.json"

    latest = _load(latest_path)
    if latest is None or latest.get("claim_payload") is None:
        print(
            f"ERROR: {latest_path} missing or has no claim_payload "
            "(run the gate's run.sh first)",
            file=sys.stderr,
        )
        return 1

    # Never freeze a receipt from a failed or missing gate run.
    gate_rc = (latest.get("provenance") or {}).get("gate_exit_code")
    if gate_rc != 0:
        print(
            f"ERROR: latest.json records gate_exit_code={gate_rc} "
            "(must be exactly 0) — refusing to freeze",
            file=sys.stderr,
        )
        return 1

    # Re-validate digest integrity: the stored claim_digest must match a fresh
    # recomputation over claim_payload. Catches stale or edited latest.json.
    recomputed = stable_digest(latest["claim_payload"])
    if recomputed != latest.get("claim_digest"):
        print(
            f"ERROR: latest.json digest mismatch — stored "
            f"claim_digest={latest.get('claim_digest')} "
            f"recomputed={recomputed} — refusing to freeze inconsistent receipt",
            file=sys.stderr,
        )
        return 1

    # Refuse dirty working tree unless explicitly overridden.
    prov = latest.get("provenance") or {}
    is_dirty = prov.get("working_tree_dirty", False)
    if is_dirty and not getattr(args, "allow_dirty", False):
        print(
            "ERROR: latest.json records working_tree_dirty=True — source_commit "
            "would point at HEAD while claims may have come from uncommitted code. "
            "Re-run the gate from a clean tree, or use --allow-dirty to override.",
            file=sys.stderr,
        )
        return 1

    # Refuse to re-freeze an already-frozen canonical unless --force.
    existing = _load(canonical_path)
    if existing is not None and existing.get("status") == FROZEN_STATUS:
        if not getattr(args, "force", False):
            print(
                f"ERROR: {canonical_path} is already FROZEN (source_commit="
                f"{(existing.get('provenance') or {}).get('source_commit', '?')[:8]}). "
                "Use --force to re-freeze.",
                file=sys.stderr,
            )
            return 1

    source_commit = _git_head(repo_root)
    if not source_commit:
        print("ERROR: could not resolve git HEAD for source_commit", file=sys.stderr)
        return 1

    # Promote: start from the exact latest envelope, mark it FROZEN, and stamp
    # the generation commit. claim_payload / claim_digest are preserved as-is.
    canonical = dict(latest)
    canonical["status"] = FROZEN_STATUS
    provenance = dict(canonical.get("provenance") or {})
    provenance["source_commit"] = source_commit
    canonical["provenance"] = provenance

    canonical_path.write_text(canonical_json(canonical))

    digest = canonical.get("claim_digest", "") or ""
    sha8 = digest.split(":")[-1][:8] if digest else "????????"
    section = canonical.get("section", section_dir.name)
    print(f"[{section}] FROZEN source_commit={source_commit} digest={sha8}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    if args.section_dir:
        rd = Path(args.section_dir).resolve() / "receipts"
        canonical_path, latest_path = rd / "canonical.json", rd / "latest.json"
    else:
        canonical_path, latest_path = Path(args.canonical), Path(args.latest)

    latest = _load(latest_path)

    # Full-mode: compare against canonical_full.json if it exists
    if latest is not None and (latest.get("provenance") or {}).get("mode") == "full":
        rd_canonical = canonical_path.parent
        full_canonical = rd_canonical / "canonical_full.json"
        if full_canonical.exists():
            canonical = _load(full_canonical)
            verdict, detail = compare_envelopes(canonical, latest)
            print(f"{verdict}" + (f"  {detail}" if detail else ""))
            return 0 if verdict == "MATCH" else 1
        else:
            print("FULL  full-mode latest.json; no canonical_full.json to compare")
            return 0

    canonical = _load(canonical_path)
    verdict, detail = compare_envelopes(canonical, latest)
    print(f"{verdict}" + (f"  {detail}" if detail else ""))
    return {"MATCH": 0, "PENDING": 0, "MISMATCH": 3, "ERROR": 4}[verdict]


def cmd_digest(args: argparse.Namespace) -> int:
    env = _load(Path(args.file))
    if env is None or env.get("claim_payload") is None:
        print("ERROR: no claim_payload", file=sys.stderr)
        return 4
    print(stable_digest(env["claim_payload"]))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    env = _load(Path(args.file))
    if env is None:
        print("ERROR: unreadable", file=sys.stderr)
        return 4
    print(json.dumps(env, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("finalize", help="write latest.json from a JUnit run and compare to canonical")
    f.add_argument("--section", required=True)
    f.add_argument("--section-dir", required=True)
    f.add_argument("--junit", required=True)
    f.add_argument("--files", default="", help="space-separated test files the gate ran")
    f.add_argument("--gate-rc", type=int, default=0)
    f.add_argument("--mode", default="lite", choices=["lite", "full"])
    f.add_argument(
        "--skip-compare",
        action="store_true",
        help="write latest.json but do not compare against canonical (used for full mode when only a lite canonical is frozen)",
    )
    f.set_defaults(func=cmd_finalize)

    fr = sub.add_parser(
        "freeze",
        help="Phase 6: promote a section's latest.json into a FROZEN canonical.json",
    )
    fr.add_argument("--section-dir", required=True)
    fr.add_argument(
        "--allow-dirty",
        action="store_true",
        help="allow freezing even if working_tree_dirty=True",
    )
    fr.add_argument(
        "--force",
        action="store_true",
        help="re-freeze even if canonical.json is already FROZEN",
    )
    fr.set_defaults(func=cmd_freeze)

    c = sub.add_parser("compare", help="compare canonical vs latest stable digests")
    c.add_argument("--section-dir")
    c.add_argument("--canonical")
    c.add_argument("--latest")
    c.set_defaults(func=cmd_compare)

    d = sub.add_parser("digest", help="print the stable digest of an envelope's claim_payload")
    d.add_argument("--file", required=True)
    d.set_defaults(func=cmd_digest)

    s = sub.add_parser("show", help="pretty-print an envelope")
    s.add_argument("--file", required=True)
    s.set_defaults(func=cmd_show)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
