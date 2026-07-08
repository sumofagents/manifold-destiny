#!/usr/bin/env bash
# Gate 06 — self-extending grammar (bootstrapped primitives, the self-extending theorem).
# A retained, verifier-certified quotient is promoted to a new typed atom; the
# enumerate -> verify -> retain -> promote loop grows the grammar while every
# promoted atom stays V-certified. Pure Python — no heavy deps.
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/_lib/gate_lib.sh"

run_gate "06_self_extending_grammar" 0 "not slow" \
  tests/test_iteration9_self_extending_grammar.py \
  tests/test_iteration9_lean_self_extending.py
