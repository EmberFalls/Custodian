"""Prepare inert DRIFT26DSN domain tables for the Custodian DGA detector."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from custodian.core.enums import FeatureFamily
from custodian.features.dns import dns_lexical_values, normalize_dns_name
from custodian.features.schema import DNS_SCHEMA_VERSION, stable_bucket

REQUIRED_FILES = ("T17_benign.parquet", "T17_dga.parquet")
CLASS_MAPPING = {0: "BENIGN", 1: "DGA"}
CLASSES = ("BENIGN", "DGA")
SOURCE_NAME = "DRIFT26DSN / raw_including_TLD"
LEXICAL_FEATURES = (
    "domain_length",
    "subdomain_count",
    "mean_label_length",
    "character_entropy",
    "digit_ratio",
    "letter_ratio",
    "hyphen_ratio",
    "repeated_character_ratio",
    *(f"bigram_bucket_{index}" for index in range(8)),
)


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_sources(data_dir: str | Path) -> list[Path]:
    directory = Path(data_dir)
    paths = [directory / name for name in REQUIRED_FILES]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("Required DRIFT26DSN files missing:\n" + "\n".join(missing))
    return paths


def normalize_label(value: object) -> str:
    try:
        label = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid DRIFT label: {value!r}") from exc
    if label not in CLASS_MAPPING:
        raise ValueError(f"unsupported DRIFT label: {value!r}")
    return CLASS_MAPPING[label]


def _feature_table(frame: pd.DataFrame) -> pd.DataFrame:
    records = [dns_lexical_values(domain) for domain in frame["domain"]]
    lexical = pd.DataFrame.from_records(records, index=frame.index)
    table = pd.DataFrame(index=frame.index)
    table["label"] = frame["label"].to_numpy()
    table["dga_family"] = frame["dga_family"].to_numpy()
    table["source_name"] = SOURCE_NAME
    table["family"] = FeatureFamily.DNS.value
    table["schema_version"] = DNS_SCHEMA_VERSION
    table["group_id"] = [
        f"dga-family:{family}"
        if label == "DGA"
        else f"benign-bucket:{stable_bucket(domain, 4096)}"
        for domain, label, family in zip(
            frame["domain"], frame["label"], frame["dga_family"], strict=True
        )
    ]
    for name in LEXICAL_FEATURES:
        table[f"feature__{name}"] = lexical[name].to_numpy()
        table[f"available__{name}"] = True
    for name in ("query_type", "query_frequency", "unique_domain_ratio"):
        table[f"feature__{name}"] = float("nan")
        table[f"available__{name}"] = False
    return table


def prepare_drift26dsn(
    data_dir: str | Path,
    *,
    max_rows_per_class: int | None = None,
    batch_size: int = 100_000,
) -> tuple[pd.DataFrame, dict]:
    """Validate, normalize, deduplicate and feature-engineer DRIFT26DSN rows.

    DGA families are kept wholly inside one split group. Benign domains receive
    per-domain groups, so benign support can exist in every role without leaking an
    identical normalized domain across roles.
    """

    if max_rows_per_class is not None and max_rows_per_class < 1:
        raise ValueError("max_rows_per_class must be positive")
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    paths = validate_sources(data_dir)
    source_frames: list[pd.DataFrame] = []
    source_reports: list[dict] = []
    for path in paths:
        parquet = pq.ParquetFile(path)
        required_columns = {"domain", "label", "family"}
        if not required_columns.issubset(parquet.schema.names):
            missing = sorted(required_columns - set(parquet.schema.names))
            raise ValueError(f"{path.name} is missing required columns: {missing}")
        remaining = max_rows_per_class
        batches: list[pd.DataFrame] = []
        input_rows = 0
        invalid_rows = 0
        for record_batch in parquet.iter_batches(
            batch_size=batch_size,
            columns=["domain", "label", "family"],
        ):
            batch = record_batch.to_pandas()
            input_rows += len(batch)
            normalized_rows = []
            for row in batch.itertuples(index=False):
                try:
                    domain = normalize_dns_name(row.domain)
                    label = normalize_label(row.label)
                    if not isinstance(row.family, str):
                        raise ValueError("invalid family")
                    dga_family = row.family.strip()
                    if not dga_family:
                        raise ValueError("empty family")
                except (TypeError, ValueError):
                    invalid_rows += 1
                    continue
                normalized_rows.append((domain, label, dga_family))
            clean = pd.DataFrame(
                normalized_rows,
                columns=["domain", "label", "dga_family"],
            ).drop_duplicates()
            if remaining is not None:
                clean = clean.head(remaining)
                remaining -= len(clean)
            if not clean.empty:
                batches.append(clean)
            if remaining is not None and remaining <= 0:
                break
        if not batches:
            raise ValueError(f"{path.name} contains no usable rows")
        retained = pd.concat(batches, ignore_index=True).drop_duplicates()
        source_frames.append(retained)
        source_reports.append(
            {
                "filename": path.name,
                "bytes": path.stat().st_size,
                "sha256": file_sha256(path),
                "input_rows_read": input_rows,
                "invalid_rows_removed": invalid_rows,
                "rows_retained_before_cross_file_cleaning": len(retained),
            }
        )
    source = pd.concat(source_frames, ignore_index=True).drop_duplicates()
    if set(source["label"]) != set(CLASSES):
        raise ValueError(f"expected classes {CLASSES}, found {sorted(source['label'].unique())}")
    labels_per_domain = source.groupby("domain")["label"].nunique()
    conflicting_domains = set(labels_per_domain[labels_per_domain > 1].index)
    conflicting_rows_removed = int(source["domain"].isin(conflicting_domains).sum())
    if conflicting_domains:
        source = source.loc[~source["domain"].isin(conflicting_domains)].reset_index(drop=True)
    duplicate_domains = int(source.duplicated(subset=["domain", "label"]).sum())
    source = source.drop_duplicates(subset=["domain", "label"], keep="first").reset_index(drop=True)
    table = _feature_table(source)
    dga_family_count = int(source.loc[source["label"] == "DGA", "dga_family"].nunique())
    if dga_family_count < 4:
        raise ValueError("DGA preparation requires at least four families for held-out roles")
    report = {
        "manifest_version": "custodian.dga_training_data.v1",
        "dataset": SOURCE_NAME,
        "sources": source_reports,
        "source_to_class": CLASS_MAPPING,
        "final_class_counts": {
            str(label): int(count) for label, count in table["label"].value_counts().items()
        },
        "duplicate_domains_removed": duplicate_domains,
        "conflicting_domains_removed": len(conflicting_domains),
        "conflicting_rows_removed": conflicting_rows_removed,
        "dga_family_count": dga_family_count,
        "schema_version": DNS_SCHEMA_VERSION,
        "shared_feature_code": "custodian.features.dns.dns_lexical_values",
        "split_grouping": (
            "whole DGA family; deterministic normalized-domain hash buckets for benign rows"
        ),
        "training_target": "BENIGN versus DGA",
        "domain_resolution_performed": False,
        "payload_execution_performed": False,
        "traffic_replay_performed": False,
    }
    return table, report
