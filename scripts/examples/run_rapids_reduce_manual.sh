#!/usr/bin/env bash
# Run rapids_reduce with a manual reduce spec (overrides auto_from_run_spec).
set -euo pipefail

SPEC_PATH=${1:-specs/examples/full/rapids-reduce.yaml}
RAPIDS_DIR=${2:-/mnt/connect/workdir/runs/REPLACE_RUN_ID/rapids}
OUTPUT_DIR=${3:-/mnt/connect/workdir/runs/REPLACE_RUN_ID/combined}
PARTICIPANTS=${4:-}

CMD=(python3 mhm_core/reduce_rapids_features.py --spec "$SPEC_PATH" --rapids-dir "$RAPIDS_DIR" --output-dir "$OUTPUT_DIR")
if [[ -n "$PARTICIPANTS" ]]; then
  CMD+=(--participants "$PARTICIPANTS")
fi

"${CMD[@]}"
