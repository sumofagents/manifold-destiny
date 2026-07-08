#!/usr/bin/env bash
# Gate 04 — real Lean/GitHub corpus replay.
#
#   Lite (default):       -m "not slow"  — always-on unit tests, <1s, no heavy
#                         deps. This is what the lite reproduction asserts.
#   Full (RUN_FULL_REPLAY=1): also runs the @slow tests that drive a real Lake
#                         build of Lean4Axiomatic.Integer.one_mul_one_eqv_one.
#                         Requires: pyarrow + the 43MB parquet (fetch_data.sh),
#                         a checked-out source repo, and elan/lake with the
#                         pinned toolchain (leanprover/lean4:nightly-2024-06-08).
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/_lib/gate_lib.sh"

if [[ "${RUN_FULL_REPLAY:-0}" == "1" ]]; then
  echo "RUN_FULL_REPLAY=1 -> full mode: real Lake build."
  echo "  Needs parquet (reproduce/04_real_corpus_replay/fetch_data.sh),"
  echo "  source checkout, and elan/lake @ leanprover/lean4:nightly-2024-06-08."
fi

# full_capable=1 -> when RUN_FULL_REPLAY=1 the lite marker is dropped.
run_gate "04_real_corpus_replay" 1 "not slow" \
  tests/test_iteration9_lean_github_replay.py
