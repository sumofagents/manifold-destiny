#!/usr/bin/env bash
# Gate 03 — Lean kernel certification of a generated abstraction.
# The Lean 4.31.0 kernel certifies Adm(qgen,c) + novelty; a bad candidate is
# rejected. Skips cleanly if the Lean toolchain is not on PATH.
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/_lib/gate_lib.sh"

run_gate "03_lean_generation" 0 "not slow" \
  tests/test_iteration9_bounded_generation_lean.py
