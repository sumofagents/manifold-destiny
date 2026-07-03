#!/usr/bin/env bash
# Gate 01 — synthetic GF(2) gluing: bounded-generation substrate + GF(2) claim.
# Thin: declare the gate, run pytest (lite), emit/compare the receipt.
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/_lib/gate_lib.sh"

run_gate "01_synthetic_gf2" 0 "not slow" \
  tests/test_iteration9_bounded_generation_phase_a.py \
  tests/test_iteration9_bounded_generation_gf2.py
