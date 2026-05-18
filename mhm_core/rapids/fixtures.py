"""Executable neutral RAPIDS fixture helpers.

These helpers deliberately avoid CONNECT concepts. They stage a small
entity/group metric tree into the neutral external-data shape used to rehearse
the MHM RAPIDS module boundary before moving production RAPIDS code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import gzip
import json
import logging
from pathlib import Path
from typing import Iterable, Mapping


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
    staged_root.mkdir(parents=True, exist_ok=True)
    selected_entities = [str(entity).strip() for entity in (entities or entity_group_map.keys()) if str(entity).strip()]
    group_map = {
        str(entity).strip(): str(group).strip()
        for entity, group in entity_group_map.items()
        if str(entity).strip()
    }

    containers: dict[str, object] = {}
    input_files: dict[str, list[str]] = {}

    for sensor_key, sensor_inputs in inputs.items():
        sensor_name = _normalize_key(sensor_key)
        normalized_inputs = _normalize_sensor_inputs(sensor_inputs)
        sensor_containers: dict[str, str] = {}
        for platform, metric in normalized_inputs.items():
            sources = [
                source
                for entity in selected_entities
                if (source := _find_metric_file(root, entity=entity, group=group_map.get(entity, ""), metric=metric))
            ]
            input_files[metric] = [str(path) for path in sources]
            if not sources:
                log.warning("[rapids   ] no neutral metric files found for %s", metric)
                continue
            output_file = staged_root / f"{metric}.csv.gz"
            _concat_gzip_csv(sources, output_file)
            sensor_containers[_normalize_key(platform)] = output_file.name

        if not sensor_containers:
            continue
        if len(sensor_containers) == 1:
            containers[sensor_name] = next(iter(sensor_containers.values()))
        elif combine_multi_platform:
            combined_name = f"{sensor_name.lower()}.csv.gz"
            _concat_gzip_csv([staged_root / name for name in sensor_containers.values()], staged_root / combined_name)
            containers[sensor_name] = combined_name
        else:
            containers[sensor_name] = dict(sensor_containers)

    manifest_path = Path(staging_dir) / "rapids_fixture_manifest.json"
    manifest = {
        "module_id": "mhm.rapids",
        "contract_input": "entity_metric_tree",
        "entities": selected_entities,
        "entity_group_map": group_map,
        "containers": containers,
        "input_files": input_files,
        "staged_dir": str(staged_root),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return NeutralRapidsStageResult(
        staged_dir=staged_root,
        manifest_path=manifest_path,
        containers=containers,
        input_files=input_files,
        entity_group_map=group_map,
    )


def _normalize_sensor_inputs(value: object) -> dict[str, str]:
    if isinstance(value, str):
        return {"ALL": value}
    if not isinstance(value, Mapping):
        raise ValueError("RAPIDS fixture inputs must map sensors to metric names or platform mappings")
    return {
        str(platform).strip(): str(metric).strip()
        for platform, metric in value.items()
        if str(platform).strip() and str(metric).strip()
    }


def _normalize_key(value: object) -> str:
    return str(value).strip().replace("-", "_").replace(" ", "_").upper()


def _find_metric_file(root: Path, *, entity: str, group: str, metric: str) -> Path | None:
    candidates = []
    if group:
        candidates.append(root / group / entity / metric / f"{metric}.csv.gz")
    candidates.append(root / entity / metric / f"{metric}.csv.gz")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _concat_gzip_csv(files: Iterable[Path], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    wrote_header = False
    with gzip.open(output_file, "wt", encoding="utf-8") as out_fh:
        for source in files:
            with gzip.open(source, "rt", encoding="utf-8") as in_fh:
                header = in_fh.readline()
                if not header:
                    continue
                if not wrote_header:
                    out_fh.write(header)
                    wrote_header = True
                for line in in_fh:
                    out_fh.write(line)


__all__ = ["NeutralRapidsStageResult", "stage_entity_metric_tree_for_rapids"]
