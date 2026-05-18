"""Reusable RAPIDS staging helpers for entity metric trees."""

from __future__ import annotations

from dataclasses import dataclass, field
import gzip
import logging
from pathlib import Path
from typing import Iterable, Mapping


@dataclass(frozen=True)
class RapidsMetricStageResult:
    containers: dict[str, object]
    staged_dir: Path
    input_files: dict[str, list[str]] = field(default_factory=dict)


def normalize_sensor_key(value: object) -> str:
    return str(value).strip().replace("-", "_").replace(" ", "_").upper()


def normalize_platform_key(value: object) -> str:
    return str(value).strip().upper()


def normalize_os_key(value: object) -> str:
    return normalize_platform_key(value)


def normalize_sensor_inputs(value: object) -> dict[str, str]:
    if isinstance(value, str):
        return {"ALL": value}
    if not isinstance(value, Mapping):
        raise ValueError("RAPIDS inputs must map sensors to metric names or platform mappings")
    return {
        str(platform).strip(): str(metric).strip()
        for platform, metric in value.items()
        if str(platform).strip() and str(metric).strip()
    }


def find_entity_metric_file(
    metric_tree_root: str | Path,
    *,
    entity_id: str,
    metric: str,
    group: str = "",
    allow_group_scan: bool = True,
) -> Path | None:
    """Find ``<metric>.csv.gz`` in a neutral group/entity metric tree."""

    root = Path(metric_tree_root)
    candidates: list[Path] = []
    if group:
        candidates.append(root / group / entity_id / metric / f"{metric}.csv.gz")
    candidates.append(root / entity_id / metric / f"{metric}.csv.gz")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    if allow_group_scan and root.exists():
        for group_dir in root.iterdir():
            if not group_dir.is_dir():
                continue
            candidate = group_dir / entity_id / metric / f"{metric}.csv.gz"
            if candidate.exists():
                return candidate
    return None


def gather_entity_metric_files(
    metric_tree_root: str | Path,
    *,
    entities: Iterable[str],
    metric: str,
    entity_group_map: Mapping[str, str] | None = None,
    allow_group_scan: bool = True,
) -> list[Path]:
    group_map = entity_group_map or {}
    files: list[Path] = []
    for entity_id in entities:
        source = find_entity_metric_file(
            metric_tree_root,
            entity_id=str(entity_id),
            group=str(group_map.get(str(entity_id), "")),
            metric=metric,
            allow_group_scan=allow_group_scan,
        )
        if source:
            files.append(source)
    return files


def concat_gzip_csv(files: Iterable[Path], output_file: Path, *, logger: logging.Logger | None = None) -> None:
    """Concatenate gzip CSV files, keeping the first header only."""

    log = logger or logging.getLogger("mhm_core.rapids.staging")
    files = list(files)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    wrote_header = False
    with gzip.open(output_file, "wt", encoding="utf-8") as out_fh:
        for idx, source in enumerate(files, start=1):
            log.info("[rapids   ] staging %s (%d/%d)", source, idx, len(files))
            try:
                with gzip.open(source, "rt", encoding="utf-8") as in_fh:
                    header = in_fh.readline()
                    if not header:
                        continue
                    if not wrote_header:
                        out_fh.write(header)
                        wrote_header = True
                    for line in in_fh:
                        out_fh.write(line)
            except Exception as exc:  # noqa: BLE001
                log.warning("[rapids   ] failed to read %s: %s", source, exc)
    if not wrote_header:
        log.warning("[rapids   ] no rows written to %s (all sources empty?)", output_file)


def stage_rapids_metric_inputs(
    *,
    metric_tree_root: str | Path,
    staged_root: str | Path,
    inputs: Mapping[str, object],
    entity_group_map: Mapping[str, str],
    entities: Iterable[str],
    platform_filter: str | None = None,
    combine_multi_platform: bool = True,
    overwrite: bool = True,
    logger: logging.Logger | None = None,
) -> RapidsMetricStageResult:
    """Stage configured sensor inputs from an entity metric tree."""

    log = logger or logging.getLogger("mhm_core.rapids.staging")
    root = Path(metric_tree_root)
    staged_dir = Path(staged_root)
    staged_dir.mkdir(parents=True, exist_ok=True)
    selected_entities = [str(entity).strip() for entity in entities if str(entity).strip()]
    group_map = {str(entity): str(group) for entity, group in entity_group_map.items()}
    platform_filter_norm = normalize_platform_key(platform_filter) if platform_filter else None
    containers: dict[str, object] = {}
    input_files: dict[str, list[str]] = {}

    for sensor_key, sensor_inputs in inputs.items():
        sensor_name = normalize_sensor_key(sensor_key)
        normalized_inputs = normalize_sensor_inputs(sensor_inputs)
        sensor_containers: dict[str, str] = {}
        for platform, metric in normalized_inputs.items():
            if platform_filter_norm and normalize_platform_key(platform) != platform_filter_norm:
                continue
            metric_files = gather_entity_metric_files(
                root,
                entities=selected_entities,
                metric=metric,
                entity_group_map=group_map,
            )
            input_files[metric] = [str(path) for path in metric_files]
            if not metric_files:
                log.warning("[rapids   ] no merged files found for metric %s", metric)
                continue
            output_file = staged_dir / f"{metric}.csv.gz"
            if output_file.exists() and not overwrite:
                log.info("[rapids   ] keeping existing staged file %s", output_file)
            else:
                concat_gzip_csv(metric_files, output_file, logger=log)
            sensor_containers[normalize_platform_key(platform)] = output_file.name

        if not sensor_containers:
            continue
        if len(sensor_containers) == 1:
            containers[sensor_name] = next(iter(sensor_containers.values()))
        elif combine_multi_platform:
            combined_name = f"{sensor_name.lower()}.csv.gz"
            concat_gzip_csv([staged_dir / name for name in sensor_containers.values()], staged_dir / combined_name, logger=log)
            containers[sensor_name] = combined_name
        else:
            containers[sensor_name] = dict(sensor_containers)

    return RapidsMetricStageResult(
        containers=containers,
        staged_dir=staged_dir,
        input_files=input_files,
    )


__all__ = [
    "RapidsMetricStageResult",
    "concat_gzip_csv",
    "find_entity_metric_file",
    "gather_entity_metric_files",
    "normalize_os_key",
    "normalize_platform_key",
    "normalize_sensor_inputs",
    "normalize_sensor_key",
    "stage_rapids_metric_inputs",
]
