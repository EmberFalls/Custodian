from pathlib import Path

import pandas as pd
import pytest

from training.bccc_dns import adapt_bccc_dns_sources


def _write_source(path: Path) -> None:
    pd.DataFrame(
        [
            {
                "flow_id": "flow-1",
                "timestamp": "2024-01-01T00:00:00Z",
                "src_ip": "192.0.2.10",
                "dst_ip": "192.0.2.53",
                "src_port": 53000,
                "dst_port": 53,
                "dns_domain_name": "ordinary.example",
                "query_resource_record_type": "[]",
                "label": "Benign",
            },
            {
                "flow_id": "flow-2",
                "timestamp": "2024-01-01T00:00:01Z",
                "src_ip": "192.0.2.10",
                "dst_ip": "192.0.2.53",
                "src_port": 53001,
                "dst_port": 53,
                "dns_domain_name": "encoded-subdomain.example",
                "query_resource_record_type": "[1]",
                "label": "Light-Audio",
            },
        ]
    ).to_csv(path, index=False)


def test_bccc_adapter_uses_shared_dns_schema_and_pseudonyms(tmp_path: Path) -> None:
    source = tmp_path / "dns.csv"
    _write_source(source)

    result = adapt_bccc_dns_sources([source])

    assert result.table["label"].tolist() == ["BENIGN_DNS", "DNS_TUNNEL"]
    assert set(result.table["schema_version"]) == {"dns.v1"}
    assert result.table["entity_id"].str.startswith("dns:").all()
    assert not result.table["entity_id"].str.contains("192.0.2.10", regex=False).any()
    assert result.table["feature__query_frequency"].tolist() == [1, 1]
    assert result.table["available__query_type"].tolist() == [False, True]
    assert result.sources[0]["third_party_engineered_columns_used"] is False
    assert result.sources[0]["domain_resolution_performed"] is False


def test_bccc_adapter_rejects_unknown_labels(tmp_path: Path) -> None:
    source = tmp_path / "dns.csv"
    _write_source(source)
    frame = pd.read_csv(source)
    frame.loc[0, "label"] = "UNREVIEWED"
    frame.to_csv(source, index=False)

    with pytest.raises(ValueError, match="unsupported BCCC"):
        adapt_bccc_dns_sources([source])


@pytest.mark.parametrize("sentinel", ["malformed-packet", "not a dns flow"])
def test_bccc_adapter_rejects_invalid_domain_sentinel(tmp_path: Path, sentinel: str) -> None:
    source = tmp_path / "dns.csv"
    _write_source(source)
    frame = pd.read_csv(source)
    frame.loc[0, "dns_domain_name"] = sentinel
    frame.to_csv(source, index=False)

    result = adapt_bccc_dns_sources([source])

    assert result.table["label"].tolist() == ["DNS_TUNNEL"]
    assert result.sources[0]["rejected_rows"] == 1
