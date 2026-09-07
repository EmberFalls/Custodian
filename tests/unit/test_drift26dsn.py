"""DRIFT26DSN preparation uses shared DNS features and family-aware groups."""

from pathlib import Path

import pandas as pd

from custodian.features.dns import dns_lexical_values
from custodian.features.schema import stable_bucket
from training.drift26dsn import prepare_drift26dsn


def test_drift_adapter_preserves_dga_families_and_shared_features(tmp_path: Path) -> None:
    benign = pd.DataFrame(
        {
            "domain": ["Example.COM.", "openai.com", "python.org", "ietf.org"],
            "label": [0, 0, 0, 0],
            "family": ["benign"] * 4,
        }
    )
    dga = pd.DataFrame(
        {
            "domain": ["qx7k9.example", "ab12cd.test", "zz991.invalid", "p9q8r7.example"],
            "label": [1, 1, 1, 1],
            "family": ["family-a", "family-b", "family-c", "family-d"],
        }
    )
    benign.to_parquet(tmp_path / "T17_benign.parquet", index=False)
    dga.to_parquet(tmp_path / "T17_dga.parquet", index=False)

    table, report = prepare_drift26dsn(tmp_path, batch_size=2)

    assert set(table["label"]) == {"BENIGN", "DGA"}
    assert report["dga_family_count"] == 4
    assert set(table.loc[table["label"] == "DGA", "group_id"]) == {
        "dga-family:family-a",
        "dga-family:family-b",
        "dga-family:family-c",
        "dga-family:family-d",
    }
    example = table.loc[
        table["group_id"] == f"benign-bucket:{stable_bucket('example.com', 4096)}"
    ].iloc[0]
    expected = dns_lexical_values("example.com")
    assert example["feature__domain_length"] == expected["domain_length"]
    assert example["feature__character_entropy"] == expected["character_entropy"]
