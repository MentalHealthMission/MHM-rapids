"""Reusable MHM RAPIDS module surfaces."""

from .adoption import RAPIDS_MODULE_ID, rapids_module_contract
from .features import RAPIDS_FEATURE_ID_PREFIX, RapidsFeatureKey, canonical_rapids_feature_id
from .fixtures import NeutralRapidsStageResult, stage_entity_metric_tree_for_rapids
from .staging import (
    RapidsMetricStageResult,
    concat_gzip_csv,
    find_entity_metric_file,
    gather_entity_metric_files,
    normalize_os_key,
    normalize_platform_key,
    normalize_sensor_key,
    stage_rapids_metric_inputs,
)

__all__ = [
    "NeutralRapidsStageResult",
    "RAPIDS_MODULE_ID",
    "RAPIDS_FEATURE_ID_PREFIX",
    "RapidsMetricStageResult",
    "RapidsFeatureKey",
    "canonical_rapids_feature_id",
    "concat_gzip_csv",
    "find_entity_metric_file",
    "gather_entity_metric_files",
    "normalize_os_key",
    "normalize_platform_key",
    "normalize_sensor_key",
    "rapids_module_contract",
    "stage_entity_metric_tree_for_rapids",
    "stage_rapids_metric_inputs",
]
