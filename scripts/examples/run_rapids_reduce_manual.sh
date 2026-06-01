#!/usr/bin/env bash
# Run rapids_reduce with a manual reduce spec (overrides auto_from_run_spec).
set -euo pipefail

SPEC_PATH=${1:-specs/examples/full/rapids-reduce.yaml}
RAPIDS_DIR=${2:-/tmp/mhm-rapids-example/runs/REPLACE_RUN_ID/rapids}
OUTPUT_DIR=${3:-/tmp/mhm-rapids-example/runs/REPLACE_RUN_ID/combined}
ENTITIES=${4:-}

CMD=(python3 -m mhm_core.rapids.reduction --spec "$SPEC_PATH" --rapids-dir "$RAPIDS_DIR" --output-dir "$OUTPUT_DIR")
if [[ -n "$ENTITIES" ]]; then
  CMD+=(--entities "$ENTITIES")
fi

"${CMD[@]}"
