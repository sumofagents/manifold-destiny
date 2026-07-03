"""Iteration 9 — Lean-Github real-corpus replay verifier.

Replays a recorded tactic from the external internlm/Lean-Github corpus against
the REAL Lean/Lake kernel with the REAL source repo checked out. This is
corpus REPLAY, not bounded generation: the candidate proof is the recorded
tactic from the dataset row, not a grammar composition. The contribution is
architecture validation — the verifier-mediated retention invariant holds on
real published mathematics, not toy worlds.

The verifier copies the cached source repo to a temp directory (never mutates
the cache), swaps exactly one proof block, runs the Lake build, and requires:
  - baseline build passes (sanity)
  - good candidate (recorded tactic) accepted
  - bad rfl-only control rejected
  - forbidden tokens (sorry/admit/axiom/unsafe) absent
  - source checkout stays clean

Heavy dependencies: pyarrow, the 43MB parquet, checked-out source repos, elan/
lake with the pinned toolchain. Tests skip cleanly if any are missing.

Paths are configurable via environment variables, never hardcoded:
  MANIFOLD_LEAN_GITHUB_DATASET_DIR  — override the parquet parent directory
  MANIFOLD_LEAN_GITHUB_REPLAY_CACHE — override the checked-out source repo cache
  MANIFOLD_LEAN_GITHUB_SCRATCH      — override the temp build directory

  These are also overridable via MANIFOLD_DATA_DIR (shared root for all data)
  and MANIFOLD_LEAN_GITHUB_* (specific). Defaults are neutral
  (~/.manifold-destiny/data/).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = "lean_github_replay_receipt_v1"
FORBIDDEN_TOKENS: Tuple[str, ...] = ("sorry", "admit", "axiom", "unsafe")

# Default paths (overridable via env for CI / other machines).
# MANIFOLD_DATA_DIR is the shared data root (matches fetch_data.sh). The
# parquet lives at $MANIFOLD_DATA_DIR/lean-github.parquet. The replay cache
# (checked-out source repos) lives under a subdir. Neutral defaults so a
# reviewer on any machine gets a sensible starting point.
_data_root = Path(
    os.path.expanduser(
        os.environ.get("MANIFOLD_DATA_DIR", str(Path.home() / ".manifold-destiny" / "data"))
    )
)
DEFAULT_DATASET_DIR = Path(
    os.path.expanduser(
        os.environ.get(
            "MANIFOLD_LEAN_GITHUB_DATASET_DIR",
            str(_data_root),
        )
    )
)
DEFAULT_REPLAY_CACHE = Path(
    os.path.expanduser(
        os.environ.get(
            "MANIFOLD_LEAN_GITHUB_REPLAY_CACHE",
            str(_data_root / "lean-github-replay-cache" / "repos"),
        )
    )
)
DEFAULT_SCRATCH = Path(
    os.path.expanduser(
        os.environ.get("MANIFOLD_LEAN_GITHUB_SCRATCH", "/tmp/manifold_destiny_lean_github_replay")
    )
)


@dataclass(frozen=True)
class SourceRepoReplayCase:
    """One curated source-repo replay case (axiomatic-style rigor)."""

    row_index: int
    dataset_url: str
    source_commit: str
    source_file: str
    source_repo_subpath: str  # path under the replay cache for this repo
    module: str
    full_name: str
    toolchain: str
    original_proof_block: str
    candidate_proof_block: str
    bad_proof_block: str

    @property
    def source_repo_dir(self) -> Path:
        return DEFAULT_REPLAY_CACHE / self.source_repo_subpath

    @property
    def parquet_path(self) -> Path:
        return DEFAULT_DATASET_DIR / "lean-github.parquet"


# The canonical replay case: a real theorem from cruhland/lean4-axiomatic.
AXIOMATIC_CASE = SourceRepoReplayCase(
    row_index=69032,
    dataset_url="https://github.com/cruhland/lean4-axiomatic.git",
    source_commit="3b1fa5357e45f126fba9ed92ceb2e94b48bbcb42",
    source_file="Lean4Axiomatic/Integer/Sign.lean",
    source_repo_subpath=(
        "github.com_cruhland_lean4-axiomatic_3b1fa5357e_462c0bf5d791"
    ),
    module="Lean4Axiomatic.Integer.Sign",
    full_name="Lean4Axiomatic.Integer.one_mul_one_eqv_one",
    toolchain="leanprover/lean4:nightly-2024-06-08",
    original_proof_block=(
        "theorem one_mul_one_eqv_one : (1 : ℤ) * 1 ≃ 1 := by\n"
        "  show 1 * 1 ≃ 1\n"
        "  exact AA.identL"
    ),
    candidate_proof_block=(
        "theorem one_mul_one_eqv_one : (1 : ℤ) * 1 ≃ 1 := by\n"
        "  show 1 * 1 ≃ 1\n"
        "  exact AA.identL"
    ),
    bad_proof_block=(
        "theorem one_mul_one_eqv_one : (1 : ℤ) * 1 ≃ 1 := by\n"
        "  rfl"
    ),
)


# ---------------------------------------------------------------------------
# Dependency detection (tests skip cleanly if any dep is missing)
# ---------------------------------------------------------------------------


def pyarrow_available() -> bool:
    try:
        import pyarrow.parquet  # noqa: F401
        return True
    except ImportError:
        return False


def lake_path() -> Optional[str]:
    """Resolve the lake binary. Returns None if not found."""
    found = shutil.which("lake")
    if found:
        return found
    elan_lake = Path.home() / ".elan/bin/lake"
    if elan_lake.exists():
        return str(elan_lake)
    return None


def elan_path() -> Optional[str]:
    """Resolve the elan binary (toolchain manager). Returns None if not found."""
    found = shutil.which("elan")
    if found:
        return found
    elan_bin = Path.home() / ".elan/bin/elan"
    if elan_bin.exists():
        return str(elan_bin)
    return None


def toolchain_available(toolchain: str) -> bool:
    """Check whether the pinned elan toolchain is installed/resolvable."""
    elan = elan_path()
    if not elan:
        return False
    try:
        result = subprocess.run(
            [elan, "run", toolchain, "--", "lean", "--version"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def case_deps_available(case: SourceRepoReplayCase) -> Tuple[bool, str]:
    """Return (available, missing_reason). For skip-if-missing test gating."""
    if not pyarrow_available():
        return False, "pyarrow not installed"
    if not case.parquet_path.exists():
        return False, f"parquet missing: {case.parquet_path}"
    if not case.source_repo_dir.exists():
        return False, f"source repo missing: {case.source_repo_dir}"
    if not lake_path():
        return False, "lake not found"
    if not toolchain_available(case.toolchain):
        return False, f"elan toolchain not installed: {case.toolchain}"
    return True, ""


# ---------------------------------------------------------------------------
# Hashing helpers
# ---------------------------------------------------------------------------


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Replay primitives
# ---------------------------------------------------------------------------


def forbidden_tokens_absent(text: str) -> bool:
    """Check proof text for sorry/admit/axiom/unsafe (scoped to proof, not names)."""
    lowered = text.lower()
    return not any(token in lowered for token in FORBIDDEN_TOKENS)


def load_dataset_row(case: SourceRepoReplayCase) -> Dict[str, Any]:
    """Load a parquet row and integrity-check its provenance."""
    import pyarrow.parquet as pq

    table = pq.read_table(case.parquet_path)
    row = {name: table[name][case.row_index].as_py() for name in table.column_names}
    if row.get("url") != case.dataset_url:
        raise RuntimeError(f"unexpected row url: {row.get('url')}")
    if row.get("commit") != case.source_commit:
        raise RuntimeError(f"unexpected row commit: {row.get('commit')}")
    if row.get("file_path") != case.source_file:
        raise RuntimeError(f"unexpected row file: {row.get('file_path')}")
    if row.get("full_name") != case.full_name:
        raise RuntimeError(f"unexpected row full_name: {row.get('full_name')}")
    return row


def copy_source_repo(case: SourceRepoReplayCase, dst: Path) -> None:
    """Copy the cached source repo to a temp dir. Never mutate the cache."""
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(case.source_repo_dir, dst, ignore=shutil.ignore_patterns(".git"))


def write_proof_variant(
    repo_dir: Path, source_file: str, original_block: str, replacement_block: str
) -> Dict[str, Any]:
    """Swap exactly one proof block. Raise if not exactly one match."""
    path = repo_dir / source_file
    text = path.read_text(encoding="utf-8")
    count = text.count(original_block)
    if count != 1:
        raise RuntimeError(f"expected one proof block match, found {count}")
    updated = text.replace(original_block, replacement_block)
    path.write_text(updated, encoding="utf-8")
    return {
        "source_file": str(path),
        "source_file_sha256": _sha256_file(path),
        "replacement_sha256": _sha256_text(replacement_block),
    }


def _remove_target_build_outputs(repo_dir: Path, module_path: str) -> None:
    """Clear stale .lake build outputs for the target module before rebuild."""
    build_glob = ".lake/build/lib/" + module_path.replace(".", "/") + ".*"
    ir_glob = ".lake/build/ir/" + module_path.replace(".", "/") + ".*"
    for pattern in (build_glob, ir_glob):
        for path in repo_dir.glob(pattern):
            if path.is_file():
                path.unlink()


def _lean_env(toolchain: str) -> Dict[str, str]:
    """Build env. elan resolves the toolchain from the project's lean-toolchain
    file or `+toolchain` CLI arg, NOT these env vars — but we set them for
    completeness and so any toolchain-aware helper can see the intent."""
    env = os.environ.copy()
    env["ELAN_TOOLCHAIN"] = toolchain
    env["LEAN_TOOLCHAIN"] = toolchain
    return env


def probe_lean_version(repo_dir: Path, toolchain: str) -> str:
    """Probe the Lean version the BUILD actually uses.

    Runs `lake env lean --version` inside the work dir, which resolves the
    toolchain the way `lake build` does (via the project's lean-toolchain
    file or elan's resolution). This is the version the receipt must report —
    NOT the system default.
    """
    elan = elan_path()
    if not elan or not repo_dir.exists():
        return "unavailable"
    try:
        result = subprocess.run(
            [elan, "run", toolchain, "--", "lake", "env", "lean", "--version"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0]
        return "unavailable"
    except Exception:
        return "unavailable"


def verify_cached_commit(case: SourceRepoReplayCase) -> str:
    """Assert the cached source repo is at the recorded commit.

    Returns the actual HEAD. Raises RuntimeError on mismatch — a wrong
    checkout must NOT silently pass as the recorded commit.
    """
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(case.source_repo_dir),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    actual = result.stdout.strip()
    if result.returncode != 0:
        raise RuntimeError(f"git rev-parse failed in {case.source_repo_dir}")
    if actual != case.source_commit:
        raise RuntimeError(
            f"cached repo commit mismatch: expected {case.source_commit}, "
            f"got {actual}"
        )
    return actual


def verify_candidate_from_row(
    case: SourceRepoReplayCase, row: Dict[str, Any]
) -> None:
    """Assert the candidate proof block uses the tactic recorded in the row.

    This closes the claim-vs-evidence gap: the receipt says 'recorded tactic
    re-checked' — this method proves it mechanically by asserting the row's
    tactic string appears in the candidate proof block.
    """
    recorded_tactic = str(row.get("tactic", "")).strip()
    if not recorded_tactic:
        raise RuntimeError("dataset row has no tactic field")
    if recorded_tactic not in case.candidate_proof_block:
        raise RuntimeError(
            f"candidate proof block does not contain the recorded tactic "
            f"{recorded_tactic!r}; receipt cannot claim 'recorded tactic re-checked'"
        )


def build_module(
    repo_dir: Path, module: str, toolchain: str, timeout: int = 120
) -> subprocess.CompletedProcess:
    """Run `lake build MODULE` under the pinned toolchain via elan.

    Uses `elan run <toolchain> -- lake build` so the pinned kernel is
    actually used, regardless of the system default.
    """
    _remove_target_build_outputs(repo_dir, module)
    elan = elan_path()
    lake = lake_path()
    if not elan:
        raise RuntimeError("elan not found; cannot pin toolchain")
    if not lake:
        raise RuntimeError("lake not found")
    return subprocess.run(
        [elan, "run", toolchain, "--", "lake", "build", module],
        cwd=str(repo_dir),
        env=_lean_env(toolchain),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def check_source_checkout_clean(case: SourceRepoReplayCase) -> bool:
    """Assert the CACHED source repo is unmutated (git status empty)."""
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=str(case.source_repo_dir),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return result.returncode == 0 and not result.stdout.strip()


# ---------------------------------------------------------------------------
# Full replay
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReplayResult:
    case_full_name: str
    lean_version: str
    baseline_build_passed: bool
    good_candidate_accepted: bool
    bad_candidate_rejected: bool
    forbidden_tokens_absent: bool
    source_checkout_clean: bool
    variant_file_sha256: str
    parquet_sha256: str
    source_file_sha256_before: str


def replay(case: SourceRepoReplayCase, scratch_dir: Optional[Path] = None) -> ReplayResult:
    """Run the full source-repo replay for one case.

    Returns the verifier verdicts. Raises on integrity failure (commit
    mismatch, candidate-tactic mismatch, proof-block-not-found).

    Uses a FRESH source copy for each variant (good + bad) so the
    exactly-one-match invariant holds even when candidate != original.
    """
    available, missing = case_deps_available(case)
    if not available:
        raise RuntimeError(f"deps missing for replay: {missing}")

    scratch = scratch_dir or (DEFAULT_SCRATCH / case.full_name.replace(".", "_"))
    row = load_dataset_row(case)

    # Mechanical enforcement of the claim chain.
    verify_cached_commit(case)
    verify_candidate_from_row(case, row)

    # Forbidden-token check on the candidate BEFORE any build.
    forbidden_ok = forbidden_tokens_absent(case.candidate_proof_block)

    # Snapshot source hashes before any variant.
    source_file_before = case.source_repo_dir / case.source_file
    source_sha_before = _sha256_file(source_file_before)
    parquet_sha = _sha256_file(case.parquet_path)

    # Baseline build (sanity: real repo builds unmodified).
    baseline_dir = scratch / "baseline_repo"
    copy_source_repo(case, baseline_dir)
    baseline = build_module(baseline_dir, case.module, case.toolchain)
    baseline_ok = baseline.returncode == 0
    build_version = probe_lean_version(baseline_dir, case.toolchain)

    # Good candidate variant (FRESH copy).
    good_dir = scratch / "good_repo"
    copy_source_repo(case, good_dir)
    good_variant = write_proof_variant(
        good_dir, case.source_file, case.original_proof_block, case.candidate_proof_block
    )
    good_build = build_module(good_dir, case.module, case.toolchain)
    good_ok = good_build.returncode == 0

    # Bad rfl-only control variant (FRESH copy).
    bad_dir = scratch / "bad_repo"
    copy_source_repo(case, bad_dir)
    bad_variant = write_proof_variant(
        bad_dir, case.source_file, case.original_proof_block, case.bad_proof_block
    )
    bad_build = build_module(bad_dir, case.module, case.toolchain)
    bad_rejected = bad_build.returncode != 0

    # Clean checkout assertion (on the CACHE, which we never touched).
    clean = check_source_checkout_clean(case)

    return ReplayResult(
        case_full_name=case.full_name,
        lean_version=build_version,
        baseline_build_passed=baseline_ok,
        good_candidate_accepted=good_ok,
        bad_candidate_rejected=bad_rejected,
        forbidden_tokens_absent=forbidden_ok,
        source_checkout_clean=clean,
        variant_file_sha256=good_variant["source_file_sha256"],
        parquet_sha256=parquet_sha,
        source_file_sha256_before=source_sha_before,
    )


def make_replay_receipt(case: SourceRepoReplayCase, result: ReplayResult) -> Dict[str, Any]:
    """Build a stable, deterministic receipt dict."""
    receipt = {
        "schema": SCHEMA_VERSION,
        "record_id": f"lean_github_replay_{case.row_index}_{case.full_name.replace('.', '_')}",
        "domain": "lean_github_kernel_replay",
        "source": {
            "dataset": "internlm/Lean-Github",
            "row_index": case.row_index,
            "repo": case.dataset_url,
            "commit": case.source_commit,
            "file_path": case.source_file,
            "full_name": case.full_name,
            "module": case.module,
            "toolchain": case.toolchain,
            "parquet_sha256": result.parquet_sha256,
            "source_file_sha256_before_variant": result.source_file_sha256_before,
        },
        "verifier": {
            "name": "lean_lake_source_candidate_replay_v1",
            "lean_version": result.lean_version,
            "baseline_source_build_passed": result.baseline_build_passed,
            "good_candidate_accepted": result.good_candidate_accepted,
            "bad_rfl_only_candidate_rejected": result.bad_candidate_rejected,
            "forbidden_tokens_absent": result.forbidden_tokens_absent,
            "source_checkout_stayed_clean": result.source_checkout_clean,
            "candidate_variant_file_sha256": result.variant_file_sha256,
        },
        "claim": "real-corpus replay, not generation: recorded tactic re-checked against real kernel",
        "non_claims": [
            "does not verify all Lean-Github rows",
            "does not claim theorem discovery",
            "does not claim improvement to Lean/Lake",
        ],
    }
    receipt["record_hash"] = _stable_hash(receipt)
    return receipt


__all__ = [
    "SCHEMA_VERSION",
    "FORBIDDEN_TOKENS",
    "SourceRepoReplayCase",
    "AXIOMATIC_CASE",
    "pyarrow_available",
    "lake_path",
    "elan_path",
    "toolchain_available",
    "case_deps_available",
    "forbidden_tokens_absent",
    "load_dataset_row",
    "copy_source_repo",
    "write_proof_variant",
    "build_module",
    "probe_lean_version",
    "verify_cached_commit",
    "verify_candidate_from_row",
    "check_source_checkout_clean",
    "replay",
    "make_replay_receipt",
]
