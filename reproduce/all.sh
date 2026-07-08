#!/usr/bin/env bash
# Run every lite reproduction gate and print a PASS/FAIL summary table.
#
#   bash reproduce/all.sh                 # lite: all six reproduction gates, < 60s
#   RUN_FULL_REPLAY=1 bash reproduce/all.sh   # also runs section 04's Lake build
#
# Each gate's run.sh prints a machine-readable "MANIFEST_SUMMARY ..." line which
# this script parses. Exit code is non-zero iff any gate FAILED (skips due to
# missing optional deps — Lean, quantum data, pyarrow — are NOT failures).
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECTIONS=(01_synthetic_gf2 02_quantum 03_lean_generation 04_real_corpus_replay 05_manifold_store 06_self_extending_grammar)

declare -a ROWS=()
any_fail=0

for s in "${SECTIONS[@]}"; do
  out="$(bash "$HERE/$s/run.sh" 2>&1)" || true
  summary="$(printf '%s\n' "$out" | grep '^MANIFEST_SUMMARY ' | tail -1 || true)"

  if [[ -z "$summary" ]]; then
    ROWS+=("$s|ERROR|-|-|-|no MANIFEST_SUMMARY (collection error)")
    any_fail=1
    printf '%s\n' "$out" | sed 's/^/    /'
    continue
  fi

  # Parse "key=val" tokens.
  gate="" ; passed="" ; skipped="" ; failed="" ; digest="" ; mode=""
  for tok in $summary; do
    case "$tok" in
      gate=*)    gate="${tok#gate=}" ;;
      passed=*)  passed="${tok#passed=}" ;;
      skipped=*) skipped="${tok#skipped=}" ;;
      failed=*)  failed="${tok#failed=}" ;;
      digest=*)  digest="${tok#digest=}" ;;
      mode=*)    mode="${tok#mode=}" ;;
    esac
  done

  [[ "$gate" == "PASS" ]] || any_fail=1
  # Digest MISMATCH or ERROR is a failure even if the gate passed.
  [[ "$digest" == "MISMATCH" || "$digest" == "ERROR" ]] && any_fail=1
  ROWS+=("$s|$gate|$mode|${passed}p/${skipped}s/${failed}f|$digest|")
done

echo
echo "================================ REPRODUCTION SUMMARY ================================"
printf "%-24s %-6s %-5s %-12s %-9s\n" "SECTION" "GATE" "MODE" "P/S/F" "DIGEST"
printf "%-24s %-6s %-5s %-12s %-9s\n" "------------------------" "------" "-----" "------------" "---------"
for row in "${ROWS[@]}"; do
  IFS='|' read -r sec gate mode psf digest extra <<<"$row"
  printf "%-24s %-6s %-5s %-12s %-9s %s\n" "$sec" "$gate" "$mode" "$psf" "$digest" "$extra"
done
echo "====================================================================================="
echo "P/S/F = passed / skipped / failed.  Skips (missing Lean, quantum data, or pyarrow)"
echo "are expected on a bare machine and do NOT fail a gate."
echo "DIGEST: MATCH = latest claim surface matches frozen canonical; FULL = full mode not compared; MISMATCH/ERROR fails."

if [[ "$any_fail" -ne 0 ]]; then
  echo "RESULT: FAIL (one or more gates failed)"
  exit 1
fi
echo "RESULT: PASS (all gates green)"
exit 0
