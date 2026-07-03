#!/usr/bin/env bash
# Fetch + verify the 43MB Lean/GitHub corpus parquet for the FULL replay.
#
# The lite gate (default `bash run.sh`) does NOT need this file — it is only
# required for the full `RUN_FULL_REPLAY=1` Lake build. The parquet is not
# committed (no Git LFS — quota); it is fetched on demand and SHA256-verified.
#
#   MANIFOLD_DATA_DIR=/path bash fetch_data.sh   # default: ~/.manifold-destiny/data
#
# Source: internlm/Lean-Github on Hugging Face (see
# the Gate 04 receipt metadata).
#
# The module (src/manifold_destiny/iteration9_lean_github_replay.py) reads
# MANIFOLD_DATA_DIR by default, so fetch_data.sh + the replay gate are aligned:
# running this script places the parquet where the gate expects it.
set -euo pipefail

DATA_DIR="${MANIFOLD_DATA_DIR:-$HOME/.manifold-destiny/data}"
URL="https://huggingface.co/datasets/internlm/Lean-Github/resolve/main/lean-github.parquet"
SHA256="849076288d96d06f68deb5ebcbf65aefba8939fc31b6db897225ea8df26133cb"
OUT="$DATA_DIR/lean-github.parquet"

mkdir -p "$DATA_DIR"

verify() {
  local file="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    echo "$SHA256  $file" | sha256sum -c - >/dev/null 2>&1
  elif command -v shasum >/dev/null 2>&1; then
    [[ "$(shasum -a 256 "$file" | awk '{print $1}')" == "$SHA256" ]]
  else
    echo "WARN: no sha256sum/shasum; cannot verify $file" >&2
    return 0
  fi
}

if [[ -f "$OUT" ]] && verify "$OUT"; then
  echo "OK: already present and SHA256-verified: $OUT"
  exit 0
fi

echo "Fetching $URL"
echo "  -> $OUT"
if command -v curl >/dev/null 2>&1; then
  curl -fL --retry 3 -o "$OUT" "$URL"
elif command -v wget >/dev/null 2>&1; then
  wget -O "$OUT" "$URL"
else
  echo "ERROR: need curl or wget to fetch the parquet." >&2
  exit 1
fi

if verify "$OUT"; then
  echo "OK: fetched and SHA256-verified ($SHA256)"
else
  echo "ERROR: SHA256 mismatch for $OUT (expected $SHA256)" >&2
  exit 1
fi
