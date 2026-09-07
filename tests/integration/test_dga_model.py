"""Synthetic contract test for the real DGA train-export-load-infer path."""

from datetime import UTC, datetime

import pandas as pd

from custodian.core.schemas import CapabilityProfile
from custodian.features.dns import DNSFeatureExtractor, dns_lexical_values
from custodian.models.loader import load_model_package
from training.train_dga import train


def test_dga_package_trains_loads_and_accepts_runtime_dns_vectors(tmp_path, monkeypatch) -> None:
    rows = []
    for role_index, role in enumerate(("train", "validation", "calibration", "test")):
        for index in range(30):
            benign_domain = f"service-{role_index}-{index}.example.com"
            dga_domain = f"qx{role_index}{index:02d}z9k7m{index:02d}.invalid"
            for label, domain, family in (
                ("BENIGN", benign_domain, "benign"),
                ("DGA", dga_domain, f"heldout-family-{role}-{index}"),
            ):
                row = {
                    "label": label,
                    "dga_family": family,
                    "source_name": "SYNTHETIC_CONTRACT_TEST_ONLY",
                    "family": "dns",
                    "schema_version": "dns.v1",
                    "group_id": f"{label}:{role}:{index}",
                    "split": role,
                    "split_seed": 42,
                }
                row.update(
                    {
                        f"feature__{name}": value
                        for name, value in dns_lexical_values(domain).items()
                    }
                )
                rows.append(row)
    input_path = tmp_path / "synthetic-dga.parquet"
    pd.DataFrame(rows).to_parquet(input_path, index=False)
    monkeypatch.setenv("CUSTODIAN_ISOLATED_TRAINING", "YES")

    package_path = train(
        input_path,
        tmp_path / "dga-package",
        feature_set="lexical",
        isolation_acknowledged=True,
    )
    package = load_model_package(package_path)
    vector = DNSFeatureExtractor().extract_metadata(
        observed_at=datetime(2026, 1, 1, tzinfo=UTC),
        source_id="test-source",
        domain="qx999z9k7m99.invalid",
        query_type=None,
        recent_domains=(),
        window_seconds=60,
        capabilities=CapabilityProfile(has_dns_query_name=True),
        recent_history_available=False,
    )

    prediction = package.predict(vector)
    assert package.manifest["decision_policy"]["strategy"] == "positive_threshold"
    assert package.feature_schema["allow_runtime_feature_superset"] is True
    assert prediction[0] in {"BENIGN", "DGA"}
    assert set(prediction[3]) == {"BENIGN", "DGA"}
