import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from sklearn.impute import SimpleImputer

from custodian.core.enums import FeatureFamily
from custodian.core.schemas import FeatureVector
from custodian.models.compatibility import validate_feature_compatibility
from custodian.models.loader import (
    _legacy_loss_module_alias,
    _restore_legacy_sklearn_state,
    load_model_package,
)


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def test_generic_integrity_is_checked_before_joblib_load(tmp_path: Path, monkeypatch) -> None:
    package = tmp_path / "dns"
    package.mkdir()
    (package / "model.joblib").write_bytes(b"not-a-model")
    (package / "calibrator.joblib").write_bytes(b"not-a-calibrator")
    _write_json(
        package / "feature_schema.json",
        {"family": "dns", "schema_version": "dns.v1", "columns": []},
    )
    _write_json(package / "classes.json", {"classes": ["BENIGN_DNS", "DNS_TUNNEL"]})
    _write_json(package / "thresholds.json", {"BENIGN_DNS": 0.5, "DNS_TUNNEL": 0.5})
    _write_json(package / "metrics.json", {})
    _write_json(package / "manifest.json", {"artifact_format": "custodian.model_package.v1"})
    required = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in package.iterdir()
        if path.is_file()
    }
    required["model.joblib"] = "0" * 64
    _write_json(package / "artifact_sha256.json", required)

    def fail_if_loaded(*_args, **_kwargs):
        raise AssertionError("joblib.load ran before integrity verification")

    monkeypatch.setattr("custodian.models.loader.joblib.load", fail_if_loaded)
    with pytest.raises(ValueError, match="integrity mismatch: model.joblib"):
        load_model_package(package)


def test_generic_schema_can_declare_runtime_feature_superset() -> None:
    vector = FeatureVector(
        family=FeatureFamily.TLS_QUIC,
        schema_version="tls_quic.v1",
        entity_id="flow",
        window_id="window",
        values={"total_bytes": 10, "packet_count": 1},
        availability={"total_bytes": True, "packet_count": True},
    )
    validate_feature_compatibility(
        vector,
        {
            "family": "tls_quic",
            "schema_version": "tls_quic.v1",
            "columns": ["feature__total_bytes", "available__total_bytes"],
            "allow_runtime_feature_superset": True,
        },
    )

    with pytest.raises(ValueError, match="missing required model inputs"):
        validate_feature_compatibility(
            vector,
            {
                "family": "tls_quic",
                "schema_version": "tls_quic.v1",
                "columns": ["feature__unknown"],
                "allow_runtime_feature_superset": True,
            },
        )


def test_legacy_loss_module_alias_is_scoped() -> None:
    import sys

    original = sys.modules.get("_loss")
    with _legacy_loss_module_alias():
        assert sys.modules["_loss"].__name__ == "sklearn._loss._loss"
    assert sys.modules.get("_loss") is original


def test_legacy_simple_imputer_state_can_run_on_sklearn_19() -> None:
    imputer = SimpleImputer(strategy="median", keep_empty_features=True).fit(
        np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    )
    del imputer._fill_dtype

    _restore_legacy_sklearn_state(imputer)

    assert imputer._fill_dtype == imputer.statistics_.dtype
    assert imputer.transform(np.array([[np.nan, 5.0]], dtype=np.float32)).tolist() == [
        [2.0, 5.0]
    ]
