# MHM RAPIDS

Reusable/default RAPIDS adoption module for MHM pipeline profiles.

This repository contains neutral RAPIDS staging, reduction, combination, and
adoption-contract helpers. CONNECT-specific RAPIDS mappings and profiles live
in `ConnectDigitalStudy/connect-rapids`.

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

This branch was extracted from
`connect-summary@011391223d0acaa28eb4c19ad5cd3e8f3e022d0b`.
