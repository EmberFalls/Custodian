"""Tests for strict loading of the Phase 0 configuration bundle."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from custodian.config import DefaultSettings, load_config_bundle
from custodian.core.enums import FeatureFamily, ReplayMode


def test_repository_config_bundle_loads() -> None:
    config_dir = Path(__file__).resolve().parents[2] / "configs"

    bundle = load_config_bundle(config_dir)

    assert bundle.defaults.temporal_windows_seconds == (10, 60, 300)
    assert bundle.replay.mode is ReplayMode.PACED
    assert set(bundle.models.models) == set(FeatureFamily)
    assert bundle.models.models[FeatureFamily.BEHAVIOUR].artifact_path.name == "behaviour-xgb-v1"
    assert not bundle.models.models[FeatureFamily.BEHAVIOUR].trusted
    assert not bundle.models.models[FeatureFamily.DNS].enabled
    assert "dga" in bundle.models.models[FeatureFamily.DNS].variants
    assert not bundle.models.models[FeatureFamily.DNS].variants["dga"].enabled
    assert not bundle.models.models[FeatureFamily.TLS_QUIC].enabled
    assert bundle.storage.enabled
    assert bundle.storage.database_path.name == "custodian.sqlite3"


def test_local_models_config_can_be_selected_explicitly(tmp_path, monkeypatch) -> None:
    config_dir = Path(__file__).resolve().parents[2] / "configs"
    override = tmp_path / "models.local.yaml"
    override.write_text((config_dir / "models.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setenv("CUSTODIAN_MODELS_CONFIG", str(override))

    bundle = load_config_bundle(config_dir)

    assert bundle.models.models[FeatureFamily.BEHAVIOUR].artifact_path.name == "behaviour-xgb-v1"


def test_temporal_windows_must_be_sorted_and_unique() -> None:
    with pytest.raises(ValidationError, match="unique and sorted"):
        DefaultSettings(
            project_name="Custodian",
            environment="test",
            log_level="INFO",
            flow_idle_timeout_seconds=60,
            temporal_windows_seconds=(60, 10, 60),
        )
