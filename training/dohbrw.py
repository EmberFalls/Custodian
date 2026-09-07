"""BCCC-CIRA-CIC-DoHBrw adapter for shared encrypted-session features.

The source contains inert flow-level CSV measurements.  This adapter never opens a
network interface, replays traffic, resolves indicators, or executes dataset content.
Only measurements reproducible by ``TLSQUICFeatureExtractor`` are selected.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from custodian.core.enums import ThreatClass
from custodian.features.tls_quic import TLSQUICFeatureExtractor
from training.colab import sha256_file

DATASET_HANDLE = "bcccdatasets/bccc-cira-cic-dohbrw-2020"
DATASET_FILENAME = "BCCC-CIRA-CIC-DoHBrw-2020.csv"
OFFICIAL_PAGE = "https://www.unb.ca/cic/datasets/dohbrw-2020.html"
BCCC_PAGE = (
    "https://www.yorku.ca/research/bccc/ucs-technical/cybersecurity-datasets-cds/"
    "dns-over-https-bccc-cira-cic-dohbrw-2020/"
)
KAGGLE_PAGE = "https://www.kaggle.com/datasets/bcccdatasets/bccc-cira-cic-dohbrw-2020"

REQUIRED_COLUMNS = (
    "FlowBytesSent",
    "FlowSentRate",
    "FlowBytesReceived",
    "FlowReceivedRate",
    "PacketLengthVariance",
    "PacketLengthMean",
    "Label",
)
MODEL_FEATURES = (
    "flow_duration_seconds",
    "total_bytes",
    "packet_size_mean",
    "packet_size_variance",
    "bytes_a_to_b",
    "bytes_b_to_a",
    "directional_byte_ratio",
    "byte_rate_a_to_b",
    "byte_rate_b_to_a",
)
MAX_SOURCE_BYTES = 512 * 1024 * 1024
LABEL_MAPPING = {
    "benign": ThreatClass.BENIGN_ENCRYPTED.value,
    "malicious": ThreatClass.MALICIOUS_ENCRYPTED_SESSION.value,
}


@dataclass(frozen=True, slots=True)
class DoHBrwAdaptationResult:
    table: pd.DataFrame
    provenance: dict[str, Any]


def validate_source(path: str | Path) -> Path:
    source = Path(path)
    if source.suffix.lower() != ".csv" or not source.is_file():
        raise ValueError(f"DoHBrw source must be an existing CSV: {source}")
    size = source.stat().st_size
    if size <= 0 or size > MAX_SOURCE_BYTES:
        raise ValueError(f"DoHBrw CSV has an unexpected size: {size} bytes")
    with source.open("rb") as stream:
        if b"\x00" in stream.read(4096):
            raise ValueError("binary-looking DoHBrw input rejected")
    columns = pd.read_csv(source, nrows=0).columns
    missing = sorted(set(REQUIRED_COLUMNS) - set(columns))
    if missing:
        raise ValueError(f"DoHBrw CSV is missing required columns: {missing}")
    return source


def _duration_seconds(frame: pd.DataFrame) -> pd.Series:
    """Derive source flow duration only from its documented byte/rate pairs."""

    candidates = pd.DataFrame(index=frame.index)
    for direction, bytes_name, rate_name in (
        ("sent", "FlowBytesSent", "FlowSentRate"),
        ("received", "FlowBytesReceived", "FlowReceivedRate"),
    ):
        rate = frame[rate_name].where(frame[rate_name] > 0)
        candidates[direction] = frame[bytes_name] / rate
    return candidates.median(axis=1, skipna=True).where(lambda values: values > 0)


def adapt_dohbrw(path: str | Path, *, block_rows: int = 512) -> DoHBrwAdaptationResult:
    """Convert the reviewed CSV into a deduplicated shared ``tls_quic.v1`` table."""

    source = validate_source(path)
    if block_rows < 2:
        raise ValueError("provenance blocks must contain at least two rows")
    frame = pd.read_csv(source, usecols=list(REQUIRED_COLUMNS), low_memory=False)
    input_rows = len(frame)
    labels = frame.pop("Label").astype(str).str.strip().str.casefold().map(LABEL_MAPPING)
    numeric = frame.apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    invalid_numeric = numeric.lt(0).any(axis=1) | numeric.isna().any(axis=1)
    unsupported_label = labels.isna()
    usable = ~(invalid_numeric | unsupported_label)
    numeric = numeric.loc[usable].copy()
    labels = labels.loc[usable].copy()
    durations = _duration_seconds(numeric)

    rows: list[dict[str, object]] = []
    extractor = TLSQUICFeatureExtractor()
    for original_index, values in numeric.iterrows():
        duration = durations.loc[original_index]
        shared = extractor.metadata_values(
            duration_seconds=float(duration) if pd.notna(duration) else None,
            packet_count=None,
            total_bytes=float(values["FlowBytesSent"] + values["FlowBytesReceived"]),
            packet_size_mean=float(values["PacketLengthMean"]),
            packet_size_variance=float(values["PacketLengthVariance"]),
            inter_arrival_mean=None,
            inter_arrival_variance=None,
            packets_a_to_b=None,
            packets_b_to_a=None,
            bytes_a_to_b=float(values["FlowBytesSent"]),
            bytes_b_to_a=float(values["FlowBytesReceived"]),
        )
        row: dict[str, object] = {
            "label": labels.loc[original_index],
            "group_id": f"{source.name}:row-block:{original_index // block_rows}",
            "source_name": source.name,
            "family": "tls_quic",
            "schema_version": "tls_quic.v1",
            "entity_id": f"{source.name}:row:{original_index + 2}",
            "window_id": f"{source.name}:row:{original_index + 2}",
        }
        for name in MODEL_FEATURES:
            value = shared[name]
            row[f"feature__{name}"] = value
            row[f"available__{name}"] = value is not None
        rows.append(row)

    table = pd.DataFrame(rows)
    feature_columns = [f"feature__{name}" for name in MODEL_FEATURES]
    fingerprints = pd.util.hash_pandas_object(table[feature_columns], index=False)
    labels_per_vector = table["label"].groupby(fingerprints).transform("nunique")
    conflicting = labels_per_vector > 1
    table = table.loc[~conflicting].copy()
    duplicates = table.duplicated(feature_columns)
    table = table.loc[~duplicates].reset_index(drop=True)
    if set(table["label"]) != set(LABEL_MAPPING.values()):
        raise ValueError("clean DoHBrw table does not contain both encrypted-session classes")

    provenance = {
        "dataset": "BCCC-CIRA-CIC-DoHBrw-2020",
        "source_filename": source.name,
        "source_bytes": source.stat().st_size,
        "source_sha256": sha256_file(source),
        "input_rows": input_rows,
        "unsupported_label_rows": int(unsupported_label.sum()),
        "invalid_numeric_rows": int(invalid_numeric.sum()),
        "conflicting_feature_rows_removed": int(conflicting.sum()),
        "duplicate_feature_rows_removed": int(duplicates.sum()),
        "prepared_rows": len(table),
        "class_counts": {
            str(label): int(count)
            for label, count in table["label"].value_counts().sort_index().items()
        },
        "groups": int(table["group_id"].nunique()),
        "shared_extractor": "custodian.features.tls_quic.TLSQUICFeatureExtractor.metadata_values",
        "selected_features": list(MODEL_FEATURES),
        "excluded_source_features": [
            "packet-time statistics whose definition does not match runtime inter-arrival statistics",
            "response-time statistics not reproduced by the runtime",
            "all source-only labels and identifiers",
        ],
        "limitations": [
            "The source is balanced with SMOTE and is not an independent natural-traffic distribution.",
            "Malicious means DoH tunnelling in this dataset, not every malicious TLS/QUIC session.",
            "The source has no packet counts, TLS ClientHello fields, QUIC fields, host identity, or timestamps.",
            "Contiguous row blocks are provenance proxies, not verified host/session groups.",
            "A separate independent dataset is required before broad encrypted-session claims.",
        ],
        "network_interface_opened": False,
        "traffic_replayed": False,
        "payload_executed": False,
    }
    return DoHBrwAdaptationResult(table=table, provenance=provenance)
