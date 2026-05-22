# MHM RAPIDS

Python helpers for RAPIDS-compatible sensor-data processing.

Use this package to stage external data for RAPIDS, normalize RAPIDS outputs,
combine reduced metric outputs, and expose module metadata for pipeline
configuration.

## What You Can Do

- stage RAPIDS input trees
- normalize reduced RAPIDS outputs
- combine per-metric outputs
- inspect the RAPIDS module contract
- run small fixture-based checks

## Install

```sh
python -m venv .venv
. .venv/bin/activate
pip install -e .
python - <<'PYCODE'
from mhm_core.rapids.adoption import rapids_module_contract
print(rapids_module_contract().module_id)
PYCODE
```
