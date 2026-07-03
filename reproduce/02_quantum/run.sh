#!/usr/bin/env bash
# Gate 02 — quantum oracle: grammar constructs alpha-beta absent from the
# restricted catalog; CHSH violation certificate; fiber matches built-in R_diff.
# Uses the quantum data file bundled in this directory (quantum-expanded-data.json).
# Skips cleanly if the data file is absent (e.g. on a checkout that excludes it).
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/_lib/gate_lib.sh"

# Point at the repo-bundled quantum data if present (shipped with the repo).
_GATE02_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$_GATE02_DIR/quantum-expanded-data.json" ]]; then
  export MANIFOLD_QUANTUM_DATA="$_GATE02_DIR/quantum-expanded-data.json"
fi

run_gate "02_quantum" 0 "not slow" \
  tests/test_iteration9_bounded_generation_quantum.py
