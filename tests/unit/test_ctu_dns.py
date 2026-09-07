import gzip
from pathlib import Path

import pandas as pd
import pytest

from training.ctu_dns import adapt_ctu_development_source, adapt_ctu_final_source


def _write_source(path: Path, rows: list[dict[str, object]]) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as stream:
        pd.DataFrame(rows).to_csv(stream, index=False)


def test_ctu_adapter_excludes_dga_and_preserves_unavailable_metadata(
    tmp_path: Path,
) -> None:
    source = tmp_path / "test.csv.gz"
    _write_source(
        source,
        [
            {"domain": "ordinary.example", "class": 0},
            {"domain": "dga-example.test", "class": 1},
            {"domain": "encoded.payload.tunnel.example", "class": 2},
        ],
    )

    result = adapt_ctu_final_source(source)

    assert result.table["label"].tolist() == ["BENIGN_DNS", "DNS_TUNNEL"]
    assert set(result.table["schema_version"]) == {"dns.v1"}
    assert result.table["available__query_type"].eq(False).all()
    assert result.table["available__query_frequency"].eq(False).all()
    assert result.table["available__unique_domain_ratio"].eq(False).all()
    assert result.report["excluded_dga_rows"] == 1
    assert result.report["third_party_engineered_columns_used"] is False
    assert result.report["dns_resolution_performed"] is False


def test_ctu_adapter_rejects_unknown_class(tmp_path: Path) -> None:
    source = tmp_path / "test.csv.gz"
    _write_source(source, [{"domain": "example.test", "class": 9}])

    with pytest.raises(ValueError, match="unsupported CTU"):
        adapt_ctu_final_source(source)


def test_ctu_development_adapter_keeps_tunnels_and_hash_samples_benign(
    tmp_path: Path,
) -> None:
    source = tmp_path / "train.csv.gz"
    rows = [{"domain": f"normal-{index}.example", "class": 0} for index in range(100)]
    rows.extend(
        [
            {"domain": "encoded-one.tunnel.example", "class": 2},
            {"domain": "encoded-two.tunnel.example", "class": 2},
        ]
    )
    _write_source(source, rows)

    first = adapt_ctu_development_source(source)
    second = adapt_ctu_development_source(source)

    assert first.table.equals(second.table)
    assert int((first.table["label"] == "DNS_TUNNEL").sum()) == 2
    assert 0 < int((first.table["label"] == "BENIGN_DNS").sum()) < 100
    assert first.report["sampled_out_benign_rows"] > 0
    assert first.report["benign_sample_modulus"] == 8
