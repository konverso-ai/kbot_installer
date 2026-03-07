#!/usr/bin/env bash
# Register the merge driver for pyproject.toml (run once after clone).
# Run from repo root.

set -e
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
DRIVER_DIR="$ROOT/tools/merge-driver"
RUN_SCRIPT="$ROOT/tools/merge-driver/run_merge.py"
if [[ ! -f "$RUN_SCRIPT" ]]; then
  echo "Error: $RUN_SCRIPT not found. Run from repo root." >&2
  exit 1
fi
git config merge.pyproject-merge.name "Merge pyproject.toml (version + dependencies)"
git config merge.pyproject-merge.driver "uv run --project \"$DRIVER_DIR\" python \"$RUN_SCRIPT\" %O %A %B"
echo "Merge driver 'pyproject-merge' configured for this repo."
