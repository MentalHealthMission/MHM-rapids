#!/usr/bin/env python3
"""Reduce RAPIDS feature outputs across multiple inputs per entity."""
from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd
import yaml


logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

DEFAULT_TIME_COLS = [
    "local_segment",
    "local_segment_label",
    "local_segment_start_datetime",
    "local_segment_end_datetime",
]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reduce RAPIDS features across multiple inputs.")
    parser.add_argument("--spec", required=True, type=Path, help="YAML spec describing reductions")
    parser.add_argument("--rapids-dir", required=True, type=Path, help="RAPIDS run directory (contains data/processed)")
    parser.add_argument("--output-dir", required=True, type=Path, help="Output directory for reduced features")
    parser.add_argument("--entities", type=str, help="Comma-separated entity IDs to include")
    parser.add_argument("--participants", type=str, help="Compatibility alias for --entities")
    return parser


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _iter_entities(rapids_dir: Path, entities: Optional[List[str]]) -> List[str]:
    if entities:
        return entities
    features_root = rapids_dir / "data" / "processed" / "features"
    if not features_root.exists():
        raise FileNotFoundError(f"RAPIDS features dir not found: {features_root}")
    entity_ids: List[str] = []
    for child in features_root.iterdir():
        if child.is_dir() and not child.name.startswith("."):
            entity_ids.append(child.name)
    return sorted(entity_ids)


def _iter_participants(rapids_dir: Path, participants: Optional[List[str]]) -> List[str]:
    """Compatibility alias for historical participant-oriented callers."""

    return _iter_entities(rapids_dir, participants)


def _resolve_feature_file(features_root: Path, entity_id: str, sensor: str, file_override: Optional[str]) -> Path:
    if file_override:
        override_path = Path(file_override)
        if override_path.is_absolute():
            return override_path
        return features_root / entity_id / file_override
    return features_root / entity_id / f"{sensor.lower()}.csv"


def _resolve_feature_column(columns: Iterable[str], sensor: str, provider: str, feature: str, column_override: Optional[str]) -> str:
    cols = list(columns)
    if column_override:
        if column_override in cols:
            return column_override
        raise KeyError(f"Column '{column_override}' not found in {cols}")

    base = f"{sensor.lower()}_{provider.lower()}_{feature}".lower()
    for col in cols:
        if col.lower() == base:
            return col

    feature_token = feature.lower().replace(".", "_")
    alt = f"{sensor.lower()}_{provider.lower()}_{feature_token}"
    for col in cols:
        if col.lower() == alt:
            return col

    # fallback: any column that ends with the feature token
    candidates = [col for col in cols if col.lower().endswith(feature_token)]
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        raise KeyError(f"Ambiguous feature column for {sensor}/{provider}/{feature}: {candidates}")

    raise KeyError(f"No feature column found for {sensor}/{provider}/{feature}")


def _slugify(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value.strip()).strip("_").lower()


def _merge_inputs(frames: List[pd.DataFrame], keys: List[str]) -> pd.DataFrame:
    merged = frames[0]
    for frame in frames[1:]:
        merged = merged.merge(frame, on=keys, how="outer")
    return merged


def _reduce_values(df: pd.DataFrame, value_cols: List[str], method: str, weights: Optional[List[float]]) -> pd.Series:
    subset = df[value_cols]
    if method == "mean":
        return subset.mean(axis=1, skipna=True)
    if method == "sum":
        return subset.sum(axis=1, skipna=True)
    if method == "min":
        return subset.min(axis=1, skipna=True)
    if method == "max":
        return subset.max(axis=1, skipna=True)
    if method == "first_non_null":
        return subset.bfill(axis=1).iloc[:, 0]
    if method == "coalesce":
        return subset.bfill(axis=1).iloc[:, 0]
    if method == "weighted_mean":
        if not weights:
            raise ValueError("weighted_mean requires weights")
        if len(weights) != len(value_cols):
            raise ValueError("weights length must match inputs")
        weighted = subset.mul(weights)
        denom = subset.notna().mul(weights).sum(axis=1)
        return weighted.sum(axis=1) / denom.replace({0: pd.NA})
    raise ValueError(f"Unknown reduce method: {method}")


def main() -> None:
    args = build_arg_parser().parse_args()

    spec = _load_yaml(args.spec)
    features_spec = list(spec.get("features", []))
    if not features_spec:
        raise ValueError("Spec must include features")

    entities = None
    selected_entities = args.entities or args.participants
    if selected_entities:
        entities = [entity.strip() for entity in selected_entities.split(",") if entity.strip()]

    rapids_dir = args.rapids_dir
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    features_root = rapids_dir / "data" / "processed" / "features"
    entities_list = _iter_entities(rapids_dir, entities)
    log.info("Reducing %d features for %d entities", len(features_spec), len(entities_list))

    for entity_id in entities_list:
        for feature_def in features_spec:
            feature_id = feature_def.get("id")
            if not feature_id:
                raise ValueError("Feature definition missing id")
            inputs = feature_def.get("inputs", [])
            if not inputs:
                raise ValueError(f"Feature {feature_id} missing inputs")
            reduce_method = feature_def.get("reduce", "mean")
            time_cols = list(feature_def.get("time_columns", DEFAULT_TIME_COLS))

            frames: List[pd.DataFrame] = []
            value_cols: List[str] = []
            weights: Optional[List[float]] = None

            if reduce_method == "weighted_mean":
                weights = [inp.get("weight", 1.0) for inp in inputs]

            for inp in inputs:
                sensor = inp.get("sensor")
                provider = inp.get("provider", "rapids")
                feature = inp.get("feature")
                if not sensor or not feature:
                    raise ValueError(f"Feature {feature_id} input missing sensor/feature")
                file_override = inp.get("file")
                column_override = inp.get("column")
                input_rapids_dir = Path(inp.get("rapids_dir", rapids_dir))
                input_features_root = input_rapids_dir / "data" / "processed" / "features"

                data_path = _resolve_feature_file(input_features_root, entity_id, sensor, file_override)
                if not data_path.exists():
                    log.warning("Missing feature file for %s %s: %s", entity_id, feature_id, data_path)
                    continue

                df = pd.read_csv(data_path)
                key_cols = [col for col in time_cols if col in df.columns]
                if not key_cols:
                    raise ValueError(f"No time columns found in {data_path} for {feature_id}")

                value_col = _resolve_feature_column(df.columns, sensor, provider, feature, column_override)
                df = df[key_cols + [value_col]].copy()
                base_name = f"{sensor.lower()}_{provider.lower()}_{feature}".lower()
                label = inp.get("label")
                if label:
                    base_name = f"{base_name}_{_slugify(str(label))}"
                target_name = base_name
                suffix = 1
                while target_name in value_cols:
                    suffix += 1
                    target_name = f"{base_name}_{suffix}"
                df.rename(columns={value_col: target_name}, inplace=True)
                frames.append(df)
                value_cols.append(target_name)

            if not frames:
                log.warning("No input frames for %s/%s", entity_id, feature_id)
                continue

            merged = _merge_inputs(frames, keys=[col for col in time_cols if col in frames[0].columns])
            reduced = _reduce_values(merged, value_cols, reduce_method, weights)
            output = merged[[col for col in time_cols if col in merged.columns]].copy()
            output[feature_id] = reduced

            output_pattern = feature_def.get("output_pattern") or spec.get("output_pattern")
            if output_pattern:
                rel = str(output_pattern).format(
                    entity_id=entity_id,
                    entity=entity_id,
                    participant_id=entity_id,
                    feature_id=feature_id,
                )
                target = output_dir / rel
                target.parent.mkdir(parents=True, exist_ok=True)
            else:
                target = output_dir / f"{entity_id}_{feature_id}.csv"
            output.to_csv(target, index=False)
            log.info("Wrote %s", target)


if __name__ == "__main__":
    main()
