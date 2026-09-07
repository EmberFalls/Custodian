"""Feature-schema compatibility checks for runtime inference."""

from __future__ import annotations

from custodian.core.schemas import FeatureVector
from custodian.features.behaviour_flow import FLOW_DEFINITION_ID, FLOW_MODEL_FEATURES


def validate_feature_compatibility(vector: FeatureVector, schema: dict) -> None:
    """Reject vectors that differ from the exact exported schema."""

    if vector.family.value != schema.get("family"):
        raise ValueError("feature family does not match model artifact")
    if vector.schema_version != schema.get("schema_version"):
        raise ValueError("feature schema version does not match model artifact")
    expected = set(schema.get("columns", []))
    actual = {
        *(f"feature__{name}" for name in vector.values),
        *(f"available__{name}" for name in vector.availability),
    }
    if schema.get("definition_id") == FLOW_DEFINITION_ID:
        if expected != {f"feature__{name}" for name in FLOW_MODEL_FEATURES}:
            raise ValueError(
                "behaviour artifact does not use the supported shared feature definitions"
            )
        if not expected.issubset(actual):
            raise ValueError("runtime vector is missing required behaviour model inputs")
        return
    if schema.get("allow_runtime_feature_superset") is True:
        if not expected.issubset(actual):
            missing = sorted(expected - actual)
            raise ValueError(f"runtime vector is missing required model inputs: {missing}")
        return
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(f"feature columns differ from artifact; missing={missing}, extra={extra}")
