"""Executable neutral RAPIDS fixture helpers.

These helpers stage a small entity/group metric tree into the neutral
external-data shape used to exercise the MHM RAPIDS module boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
from typing import Iterable, Mapping

from .staging import stage_rapids_metric_inputs


@dataclass(frozen=True)
class NeutralRapidsStageResult:
    staged_dir: Path
    manifest_path: Path
    containers: dict[str, object] = field(default_factory=dict)
    input_files: dict[str, list[str]] = field(default_factory=dict)
    entity_group_map: dict[str, str] = field(default_factory=dict)


def stage_entity_metric_tree_for_rapids(
    *,
    metric_tree_root: str | Path,
    staging_dir: str | Path,
    inputs: Mapping[str, object],
    entity_group_map: Mapping[str, str],
    entities: Iterable[str] | None = None,
    logger: logging.Logger | None = None,
    combine_multi_platform: bool = True,
) -> NeutralRapidsStageResult:
    """Stage a neutral entity/group metric tree as a RAPIDS input fixture.

    Expected input layout is either:

    - ``<root>/<group>/<entity>/<metric>/<metric>.csv.gz``; or
    - ``<root>/<entity>/<metric>/<metric>.csv.gz`` for group-free fixtures.
    """

    log = logger or logging.getLogger("mhm_core.rapids.fixtures")
    root = Path(metric_tree_root)
    staged_root = Path(staging_dir) / "data" / "external" / "mhm_entity_metric_tree" / "raw"
    selected_entities = [str(entity).strip() for entity in (entities or entity_group_map.keys()) if str(entity).strip()]
    group_map = {
        str(entity).strip(): str(group).strip()
        for entity, group in entity_group_map.items()
        if str(entity).strip()
    }
    staged = stage_rapids_metric_inputs(
        metric_tree_root=root,
        staged_root=staged_root,
        inputs=inputs,
        entity_group_map=group_map,
        entities=selected_entities,
        combine_multi_platform=combine_multi_platform,
        logger=log,
    )

    manifest_path = Path(staging_dir) / "rapids_fixture_manifest.json"
    manifest = {
        "module_id": "mhm.rapids",
        "contract_input": "entity_metric_tree",
        "entities": selected_entities,
        "entity_group_map": group_map,
        "containers": staged.containers,
        "input_files": staged.input_files,
        "staged_dir": str(staged.staged_dir),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return NeutralRapidsStageResult(
        staged_dir=staged.staged_dir,
        manifest_path=manifest_path,
        containers=staged.containers,
        input_files=staged.input_files,
        entity_group_map=group_map,
    )


__all__ = ["NeutralRapidsStageResult", "stage_entity_metric_tree_for_rapids"]
