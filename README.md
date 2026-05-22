# MHM RAPIDS

Reusable/default RAPIDS adoption module for MHM pipeline profiles.

This repository contains neutral RAPIDS staging, reduction, combination, and
adoption-contract helpers. It is intended to make RAPIDS-compatible processing
usable from MHM pipeline profiles without making any one study profile part of
the reusable module.

## What This Package Owns

- RAPIDS input staging helpers
- reduced-output normalization helpers
- combined-output helpers
- adoption contracts for pipeline integration
- small fixtures for package-level checks

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
