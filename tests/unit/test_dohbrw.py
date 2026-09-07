from __future__ import annotations

from pathlib import Path

import pandas as pd

from training.dohbrw import MODEL_FEATURES, adapt_dohbrw, validate_source


def _source(path: Path, rows: int = 24) -> Path:
    frame = pd.DataFrame(
        {
            "FlowBytesSent": [100 + index for index in range(rows)],
            "FlowSentRate": [50 + index for index in range(rows)],
            "FlowBytesReceived": [40 + index for index in range(rows)],
            "FlowReceivedRate": [20 + index for index in range(rows)],
            "PacketLengthVariance": [4 + index / 10 for index in range(rows)],
            "PacketLengthMean": [70 + index / 10 for index in range(rows)],
            "Label": ["Benign" if index % 2 == 0 else "Malicious" for index in range(rows)],
        }
    )
    frame.to_csv(path, index=False)
    return path


def test_dohbrw_adapter_uses_only_shared_runtime_features(tmp_path: Path) -> None:
    source = _source(tmp_path / "BCCC-CIRA-CIC-DoHBrw-2020.csv")
    result = adapt_dohbrw(source, block_rows=2)

    assert set(result.table["label"]) == {
        "BENIGN_ENCRYPTED",
        "MALICIOUS_ENCRYPTED_SESSION",
    }
    assert set(f"feature__{name}" for name in MODEL_FEATURES).issubset(result.table)
    assert "feature__PacketTimeMean" not in result.table
    assert result.provenance["traffic_replayed"] is False
    assert result.provenance["payload_executed"] is False
    assert result.provenance["groups"] == 12


def test_dohbrw_source_rejects_binary_looking_csv(tmp_path: Path) -> None:
    source = tmp_path / "bad.csv"
    source.write_bytes(b"Label\x00FlowBytesSent")

    try:
        validate_source(source)
    except ValueError as exc:
        assert "binary-looking" in str(exc)
    else:
        raise AssertionError("binary-looking CSV should be rejected")
