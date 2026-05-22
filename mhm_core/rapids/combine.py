#!/usr/bin/env python3
"""Combine RAPIDS reduced outputs with derived features into a single table per entity."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd


DEFAULT_TIME_COLS = [
    "local_segment",
    "local_segment_label",
    "local_segment_start_datetime",
    "local_segment_end_datetime",
]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Combine RAPIDS reduced outputs with derived features.")
    parser.add_argument("--rapids-dir", required=True, type=Path, help="RAPIDS reduced output directory")
    parser.add_argument("--derived-dir", required=True, type=Path, help="Derived features output directory")
    parser.add_argument("--output-dir", required=True, type=Path, help="Output directory")
    parser.add_argument("--entities", type=str, help="Comma-separated entity IDs")
    parser.add_argument("--participants", type=str, help="Compatibility alias for --entities")
    parser.add_argument("--rapids-glob", default="rapids_*.csv", help="Glob for RAPIDS files under participant dir")
    parser.add_argument("--derived-glob", default="*.csv", help="Glob for derived feature files under participant dir")
    return parser


def _iter_entities(rapids_dir: Path, entities: Optional[List[str]]) -> List[str]:
    if entities:
        return entities
    return sorted([p.name for p in rapids_dir.iterdir() if p.is_dir()])


def _iter_participants(rapids_dir: Path, participants: Optional[List[str]]) -> List[str]:
    """Compatibility alias for participant-oriented callers."""

    return _iter_entities(rapids_dir, participants)


def _merge_frames(frames: List[pd.DataFrame], keys: List[str]) -> pd.DataFrame:
    merged = frames[0]
    for frame in frames[1:]:
        merged = merged.merge(frame, on=keys, how="outer")
    return merged


def _load_rapids_wide(participant_dir: Path, glob_pattern: str) -> pd.DataFrame:
    files = sorted(participant_dir.glob(glob_pattern))
    if not files:
        return pd.DataFrame()
    frames: List[pd.DataFrame] = []
    time_cols: List[str] = []
    for path in files:
        df = pd.read_csv(path)
        if df.empty:
            continue
        if not time_cols:
            time_cols = [col for col in DEFAULT_TIME_COLS if col in df.columns]
        if not time_cols:
            continue
        value_cols = [col for col in df.columns if col not in time_cols]
        if not value_cols:
            continue
        df = df[time_cols + value_cols]
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return _merge_frames(frames, keys=time_cols)


def _load_derived_wide(participant_dir: Path, glob_pattern: str, date_column: str = "segment_date") -> pd.DataFrame:
    files = sorted(participant_dir.glob(glob_pattern))
    if not files:
        return pd.DataFrame()
    frames: List[pd.DataFrame] = []
    for path in files:
        df = pd.read_csv(path)
        if df.empty:
            continue
        if date_column not in df.columns:
            continue
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return _merge_frames(frames, keys=[date_column])


def _add_segment_date(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if "segment_date" in df.columns:
        return df
    if "local_segment_start_datetime" in df.columns:
        df = df.copy()
        df["segment_date"] = pd.to_datetime(df["local_segment_start_datetime"], errors="coerce").dt.date.astype(str)
    return df


def combine_for_participant(
    participant_id: str,
    rapids_root: Path,
    derived_root: Path,
    output_dir: Path,
    rapids_glob: str,
    derived_glob: str,
) -> Optional[Path]:
    rapids_dir = rapids_root / participant_id
    derived_dir = derived_root / participant_id

    rapids_wide = _load_rapids_wide(rapids_dir, rapids_glob)
    derived_wide = _load_derived_wide(derived_dir, derived_glob)

    if rapids_wide.empty and derived_wide.empty:
        return None

    rapids_wide = _add_segment_date(rapids_wide)
    if rapids_wide.empty:
        combined = derived_wide
    elif derived_wide.empty:
        combined = rapids_wide
    else:
        combined = rapids_wide.merge(derived_wide, on="segment_date", how="outer")

    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{participant_id}.csv"
    combined.to_csv(target, index=False)
    return target


def combine_for_entity(
    entity_id: str,
    rapids_root: Path,
    derived_root: Path,
    output_dir: Path,
    rapids_glob: str,
    derived_glob: str,
) -> Optional[Path]:
    return combine_for_participant(entity_id, rapids_root, derived_root, output_dir, rapids_glob, derived_glob)


def main() -> None:
    args = build_arg_parser().parse_args()
    entities = None
    selected_entities = args.entities or args.participants
    if selected_entities:
        entities = [entity.strip() for entity in selected_entities.split(",") if entity.strip()]

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    entities_list = _iter_entities(args.rapids_dir, entities)

    for entity_id in entities_list:
        combine_for_entity(
            entity_id,
            args.rapids_dir,
            args.derived_dir,
            output_dir,
            args.rapids_glob,
            args.derived_glob,
        )


if __name__ == "__main__":
    main()
