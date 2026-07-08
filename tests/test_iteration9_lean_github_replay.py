"""Phase E tests: Lean-Github real-corpus replay gate.

Proves the verifier-mediated retention invariant holds on real published
mathematics from the internlm/Lean-Github corpus (218,866 rows). This is
corpus REPLAY, not generation: the candidate is the recorded tactic from the
dataset row, re-checked against the real Lean/Lake kernel with the real source
repo checked out.

Heavy dependencies skip cleanly: pyarrow, the 43MB parquet, checked-out source
repos, elan/lake with the pinned toolchain. Always-on unit tests validate
the machinery without building anything.

CRITICAL SCOPE: replay != generation != discovery. The candidate tactic came
from the dataset, not a grammar. The contribution is architecture validation:
the accept/reject mechanism behaves correctly on real-world Lean infrastructure.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from manifold_destiny.iteration9_lean_github_replay import (
    AXIOMATIC_CASE,
    FORBIDDEN_TOKENS,
    SCHEMA_VERSION,
    case_deps_available,
    forbidden_tokens_absent,
    make_replay_receipt,
    replay,
)


# ---------------------------------------------------------------------------
# Always-on unit tests (no heavy deps, no builds)
# ---------------------------------------------------------------------------


class TestForbiddenTokenScanner:
    """The sorry/admit/axiom/unsafe scanner is load-bearing."""

    def test_clean_proof_passes(self) -> None:
        clean = "theorem t : True := by\n  trivial"
        assert forbidden_tokens_absent(clean)

    def test_sorry_rejected(self) -> None:
        assert not forbidden_tokens_absent("theorem t : True := by\n  sorry")

    def test_admit_rejected(self) -> None:
        assert not forbidden_tokens_absent("theorem t : True := by\n  admit")

    def test_axiom_rejected(self) -> None:
        assert not forbidden_tokens_absent("axiom foo : True")

    def test_unsafe_rejected(self) -> None:
        assert not forbidden_tokens_absent("theorem t : True := by\n  unsafe_trivial")

    def test_scoped_to_proof_not_repo_names(self) -> None:
        """The token scan is on proof text, not repo/module names.

        A repo named 'lean4-axiomatic' is fine; 'axiom' in a proof block is not.
        The scanner operates on the candidate proof block string, so module
        names never trigger it.
        """
        proof = "theorem one_mul_one_eqv_one : (1 : ℤ) * 1 ≃ 1 := by\n  exact AA.identL"
        assert forbidden_tokens_absent(proof)


class TestReceiptStability:
    """Receipts are deterministic: no timestamps, stable hashes."""

    def test_receipt_record_hash_stable(self) -> None:
        """Same inputs -> same hash (cross-machine reproducibility)."""
        from manifold_destiny.iteration9_lean_github_replay import ReplayResult

        result = ReplayResult(
            case_full_name=AXIOMATIC_CASE.full_name,
            lean_version="Lean (version 4.10.0)",
            baseline_build_passed=True,
            good_candidate_accepted=True,
            bad_candidate_rejected=True,
            forbidden_tokens_absent=True,
            source_checkout_clean=True,
            variant_file_sha256="a" * 64,
            parquet_sha256="b" * 64,
            source_file_sha256_before="c" * 64,
        )
        r1 = make_replay_receipt(AXIOMATIC_CASE, result)
        r2 = make_replay_receipt(AXIOMATIC_CASE, result)
        assert r1["record_hash"] == r2["record_hash"]

    def test_receipt_has_no_timestamp(self) -> None:
        """Receipts must not embed wall-clock timestamps (non-deterministic).

        We check for timestamp-like KEYS, not substrings — 'candidate' contains
        'date' as a substring and is a legitimate field name.
        """
        from manifold_destiny.iteration9_lean_github_replay import ReplayResult

        result = ReplayResult(
            case_full_name=AXIOMATIC_CASE.full_name,
            lean_version="Lean (version 4.10.0)",
            baseline_build_passed=True,
            good_candidate_accepted=True,
            bad_candidate_rejected=True,
            forbidden_tokens_absent=True,
            source_checkout_clean=True,
            variant_file_sha256="a" * 64,
            parquet_sha256="b" * 64,
            source_file_sha256_before="c" * 64,
        )
        receipt = make_replay_receipt(AXIOMATIC_CASE, result)
        # No timestamp/date/time keys at any nesting level
        banned_keys = {"timestamp", "date", "time", "created_at", "generated_at"}
        keys_seen = set()

        def collect_keys(obj):
            if isinstance(obj, dict):
                keys_seen.update(obj.keys())
                for v in obj.values():
                    collect_keys(v)
            elif isinstance(obj, list):
                for item in obj:
                    collect_keys(item)

        collect_keys(receipt)
        assert not (keys_seen & banned_keys), (
            f"receipt contains time-dependent key(s): {keys_seen & banned_keys}"
        )

    def test_receipt_schema_version(self) -> None:
        assert SCHEMA_VERSION == "lean_github_replay_receipt_v1"

    def test_receipt_carries_non_claims(self) -> None:
        from manifold_destiny.iteration9_lean_github_replay import ReplayResult

        result = ReplayResult(
            case_full_name=AXIOMATIC_CASE.full_name,
            lean_version="Lean (version 4.10.0)",
            baseline_build_passed=True,
            good_candidate_accepted=True,
            bad_candidate_rejected=True,
            forbidden_tokens_absent=True,
            source_checkout_clean=True,
            variant_file_sha256="a" * 64,
            parquet_sha256="b" * 64,
            source_file_sha256_before="c" * 64,
        )
        receipt = make_replay_receipt(AXIOMATIC_CASE, result)
        assert "does not verify all Lean-Github rows" in receipt["non_claims"]
        assert "does not claim theorem discovery" in receipt["non_claims"]


class TestCaseProvenance:
    """The curated replay case has stable, verifiable provenance."""

    def test_axiomatic_case_provenance(self) -> None:
        assert AXIOMATIC_CASE.row_index == 69032
        assert AXIOMATIC_CASE.full_name == "Lean4Axiomatic.Integer.one_mul_one_eqv_one"
        assert AXIOMATIC_CASE.dataset_url == "https://github.com/cruhland/lean4-axiomatic.git"
        assert AXIOMATIC_CASE.toolchain == "leanprover/lean4:nightly-2024-06-08"

    def test_forbidden_tokens_constant(self) -> None:
        assert FORBIDDEN_TOKENS == ("sorry", "admit", "axiom", "unsafe")


class TestProofBlockMatching:
    """Exactly-one-match enforcement (review #L1)."""

    def test_zero_matches_raises(self, tmp_path) -> None:
        from manifold_destiny.iteration9_lean_github_replay import write_proof_variant

        f = tmp_path / "Test.lean"
        f.write_text("theorem t : True := by\n  trivial")
        with pytest.raises(RuntimeError, match="found 0"):
            write_proof_variant(tmp_path, "Test.lean", "NONEXISTENT BLOCK", "x")

    def test_two_matches_raises(self, tmp_path) -> None:
        from manifold_destiny.iteration9_lean_github_replay import write_proof_variant

        f = tmp_path / "Test.lean"
        f.write_text("foo\nfoo")  # two identical lines
        with pytest.raises(RuntimeError, match="found 2"):
            write_proof_variant(tmp_path, "Test.lean", "foo", "bar")

    def test_exactly_one_match_succeeds(self, tmp_path) -> None:
        from manifold_destiny.iteration9_lean_github_replay import write_proof_variant

        f = tmp_path / "Test.lean"
        f.write_text("theorem t : True := by\n  trivial")
        result = write_proof_variant(
            tmp_path, "Test.lean",
            "theorem t : True := by\n  trivial",
            "theorem t : True := by\n  sorry",
        )
        assert "source_file_sha256" in result


class TestCandidateProvenance:
    """The candidate tactic must be mechanically tied to the dataset row."""

    def test_verify_candidate_passes_when_tactic_present(self) -> None:
        from manifold_destiny.iteration9_lean_github_replay import verify_candidate_from_row

        row = {"tactic": "exact AA.identL"}
        # candidate contains the tactic -> passes
        verify_candidate_from_row(AXIOMATIC_CASE, row)

    def test_verify_candidate_fails_when_tactic_absent(self) -> None:
        from manifold_destiny.iteration9_lean_github_replay import verify_candidate_from_row

        row = {"tactic": "decide"}  # not in the candidate block
        with pytest.raises(RuntimeError, match="does not contain the recorded tactic"):
            verify_candidate_from_row(AXIOMATIC_CASE, row)

    def test_verify_candidate_fails_on_empty_tactic(self) -> None:
        from manifold_destiny.iteration9_lean_github_replay import verify_candidate_from_row

        row = {"tactic": ""}
        with pytest.raises(RuntimeError, match="no tactic field"):
            verify_candidate_from_row(AXIOMATIC_CASE, row)


# Commit verification (verify_cached_commit) is exercised end-to-end by the
# heavy integration test test_replay_passes_all_checks — if the cached repo
# were at the wrong commit, replay() would raise before any build.


# ---------------------------------------------------------------------------
# Heavy integration tests (skip-if-missing deps)
# ---------------------------------------------------------------------------


def _deps_or_skip(case=AXIOMATIC_CASE):
    available, missing = case_deps_available(case)
    if not available:
        pytest.skip(f"Lean-Github replay deps missing: {missing}")


@pytest.mark.slow
class TestSourceRepoReplay:
    """Full source-repo replay: real repo, real Lake build, real kernel.

    These build real Lean modules (minutes each). Skip if any dep is missing.
    """

    def test_replay_passes_all_checks(self) -> None:
        _deps_or_skip()
        result = replay(AXIOMATIC_CASE)
        assert result.baseline_build_passed, "baseline source build failed (sanity)"
        assert result.good_candidate_accepted, "good candidate not accepted by kernel"
        assert result.bad_candidate_rejected, "bad rfl-only control not rejected"
        assert result.forbidden_tokens_absent, "forbidden tokens present in candidate"
        assert result.source_checkout_clean, "source checkout was mutated"

    def test_baseline_build_passes(self) -> None:
        _deps_or_skip()
        result = replay(AXIOMATIC_CASE)
        assert result.baseline_build_passed

    def test_good_candidate_accepted(self) -> None:
        _deps_or_skip()
        result = replay(AXIOMATIC_CASE)
        assert result.good_candidate_accepted

    def test_bad_rfl_only_rejected(self) -> None:
        """The rfl-only control MUST fail the kernel build."""
        _deps_or_skip()
        result = replay(AXIOMATIC_CASE)
        assert result.bad_candidate_rejected

    def test_source_checkout_unmutated(self) -> None:
        """The cached source repo must never be mutated by the replay."""
        _deps_or_skip()
        result = replay(AXIOMATIC_CASE)
        assert result.source_checkout_clean

    def test_lean_version_captured(self) -> None:
        _deps_or_skip()
        result = replay(AXIOMATIC_CASE)
        assert "Lean" in result.lean_version
        # The version must be probed via the build's toolchain, not the system
        # default. The axiomatic case pins nightly-2024-06-08 (4.10 branch).
        # We don't assert the exact version string (elan output varies), but
        # it must NOT be the system default if that differs from the pin.
        assert result.lean_version != "unavailable"

    def test_receipt_from_real_replay(self) -> None:
        """A receipt produced from a real replay is well-formed and stable."""
        _deps_or_skip()
        result = replay(AXIOMATIC_CASE)
        receipt = make_replay_receipt(AXIOMATIC_CASE, result)
        assert receipt["schema"] == SCHEMA_VERSION
        assert receipt["domain"] == "lean_github_kernel_replay"
        assert receipt["verifier"]["good_candidate_accepted"]
        assert receipt["verifier"]["bad_rfl_only_candidate_rejected"]
        assert len(receipt["record_hash"]) == 64
