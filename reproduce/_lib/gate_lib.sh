#!/usr/bin/env bash
# Shared helper sourced by every reproduce/<section>/run.sh.
#
# Keeps each run.sh thin: a run.sh just declares the gate id, whether it is
# full-replay-capable, the lite marker, and its test files, then calls
# run_gate. ALL receipt logic lives in reproduce/_lib/receipt_tools.py — this
# file only runs pytest and forwards the JUnit XML to that tool.
#
# Usage from a section run.sh:
#   source "<reproduce>/_lib/gate_lib.sh"
#   run_gate "<section-id>" <full_capable:0|1> "<lite-marker>" <file...>
#
# full_capable=1 means: when RUN_FULL_REPLAY=1 the lite marker is dropped so
# slow tests (real Lake builds) also run, and mode is reported as "full".

# Resolve repo root once (the dir holding reproduce/ + pyproject.toml).
_GATE_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$_GATE_LIB_DIR/../.." && pwd)"

run_gate() {
  local id="$1"; local full_capable="$2"; local marker="$3"; shift 3
  local files=("$@")

  local mode="lite"
  if [[ "$full_capable" == "1" && "${RUN_FULL_REPLAY:-0}" == "1" ]]; then
    marker=""          # run everything, including @pytest.mark.slow
    mode="full"
  fi

  local section_dir="$REPO_ROOT/reproduce/$id"
  local junit; junit="$(mktemp "${TMPDIR:-/tmp}/mft-${id}-junit.XXXXXXXX").xml"

  echo "== gate $id ($mode) =="

  # Thin pytest invocation. Marker applied only when non-empty.
  local pytest_args=(-q --junitxml="$junit")
  [[ -n "$marker" ]] && pytest_args+=(-m "$marker")

  local rc=0
  ( cd "$REPO_ROOT" && python3 -m pytest "${files[@]}" "${pytest_args[@]}" ) || rc=$?

  if [[ ! -s "$junit" ]]; then
    echo "ERROR: pytest produced no JUnit report (collection error?)" >&2
    rm -f "$junit"
    exit "$([[ $rc -ne 0 ]] && echo "$rc" || echo 1)"
  fi

  # Hand the run to the receipt tool: writes latest.json, compares to
  # canonical, prints MANIFEST_SUMMARY, and returns the authoritative exit code.
  local frc=0
  local finalize_args=(
    --section "$id"
    --section-dir "$section_dir"
    --junit "$junit"
    --files "${files[*]}"
    --gate-rc "$rc"
    --mode "$mode"
  )
  # The frozen canonical for section 04 is the lite claim surface. Full mode
  # adds slow Lake-build tests, so it is not digest-comparable to that lite
  # canonical until a separate full canonical is introduced.
  [[ "$mode" == "full" ]] && finalize_args+=(--skip-compare)

  python3 "$REPO_ROOT/reproduce/_lib/receipt_tools.py" finalize "${finalize_args[@]}" || frc=$?

  rm -f "$junit"
  exit "$frc"
}
