#!/usr/bin/env bash
# Gate 05 — verified-information manifold store.
# Three domains (GF(2), quantum, Lean) stitch into one manifold; aliases merge;
# the store records but never itself certifies. Pure Python — no heavy deps.
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/_lib/gate_lib.sh"

run_gate "05_manifold_store" 0 "not slow" \
  tests/test_iteration9_manifold_store.py
