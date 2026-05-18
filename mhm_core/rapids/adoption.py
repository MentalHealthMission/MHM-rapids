"""Neutral adoption contract for the first-party MHM RAPIDS module."""

from __future__ import annotations

from mhm_core.pipeline.adoption import PipelineModuleContract

RAPIDS_MODULE_ID = "mhm.rapids"


def rapids_module_contract() -> PipelineModuleContract:
    """Return the neutral reusable RAPIDS module contract."""

    return PipelineModuleContract(
        module_id=RAPIDS_MODULE_ID,
        display_name="MHM RAPIDS",
        capabilities=("passive_feature_extraction", "feature_reduction", "feature_combination"),
        required_inputs=("entity_metric_tree", "entity_group_map"),
        produced_outputs=("rapids_features", "rapids_manifest"),
        config_keys=("provider_map", "external_engine"),
        optional_dependencies=("rapids-engine", "snakemake", "docker"),
    )


__all__ = ["RAPIDS_MODULE_ID", "rapids_module_contract"]
