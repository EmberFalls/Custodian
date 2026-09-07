"""Prepare DRIFT26DSN raw_including_TLD data for Custodian DNS training."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from custodian.core.enums import FeatureFamily
from custodian.features.schema import DNS_SCHEMA_VERSION, shannon_entropy, stable_bucket

REQUIRED_FILES = (
    "T17_benign.parquet",
    "T17_dga.parquet",
)

CLASS_MAPPING = {
    0: "BENIGN",
    1: "DGA",
}

CLASSES = ("BENIGN", "DGA")
SOURCE_NAME = "DRIFT26DSN / raw_including_TLD"

FEATURE_NAMES = (
    "domain_length",
    "subdomain_count",
    "mean_label_length",
    "character_entropy",
    "digit_ratio",
    "letter_ratio",
    "hyphen_ratio",
    "repeated_character_ratio",
    "query_type",
    "query_frequency",
    "unique_domain_ratio",
    "bigram_bucket_0",
    "bigram_bucket_1",
    "bigram_bucket_2",
    "bigram_bucket_3",
    "bigram_bucket_4",
    "bigram_bucket_5",
    "bigram_bucket_6",
    "bigram_bucket_7",
)

UNAVAILABLE_FEATURES = {
    "query_type",
    "query_frequency",
    "unique_domain_ratio",
}


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_sources(data_dir: str | Path) -> list[Path]:
    paths = [Path(data_dir) / name for name in REQUIRED_FILES]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("Required DRIFT26DSN files missing:\n" + "\n".join(missing))
    return paths


def normalize_domain(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("domain must be a string")
    domain = value.strip().lower().rstrip(".")
    if not domain:
        raise ValueError("domain must not be empty")
    return domain


def normalize_label(value: object) -> str:
    label = int(value)
    if label not in CLASS_MAPPING:
        raise ValueError(f"unsupported DRIFT label: {value!r}")
    return CLASS_MAPPING[label]


def _domain_features(domain: str) -> dict[str, int | float | None]:
    labels = domain.split(".")
    characters = domain.replace(".", "")

    length = len(domain)
    character_count = len(characters)

    counts: dict[str, int] = {}
    for character in characters:
        counts[character] = counts.get(character, 0) + 1

    bigrams = [domain[index : index + 2] for index in range(length - 1)]

    buckets = [0] * 8
    for bigram in bigrams:
        buckets[stable_bucket(bigram, 8)] += 1

    return {
        "domain_length": length,
        "subdomain_count": max(len(labels) - 2, 0),
        "mean_label_length": (
            sum(len(label) for label in labels) / len(labels) if labels else None
        ),
        "character_entropy": (shannon_entropy(list(characters)) if characters else None),
        "digit_ratio": (
            sum(character.isdigit() for character in characters) / character_count
            if character_count
            else None
        ),
        "letter_ratio": (
            sum(character.isalpha() for character in characters) / character_count
            if character_count
            else None
        ),
        "hyphen_ratio": (characters.count("-") / character_count if character_count else None),
        "repeated_character_ratio": (
            sum(count for count in counts.values() if count > 1) / character_count
            if character_count
            else None
        ),
        "query_type": None,
        "query_frequency": None,
        "unique_domain_ratio": None,
        **{f"bigram_bucket_{index}": count for index, count in enumerate(buckets)},
    }


def to_shared_features(frame: pd.DataFrame) -> pd.DataFrame:
    rows = [_domain_features(domain) for domain in frame["domain"]]

    features = pd.DataFrame.from_records(
        rows,
        index=frame.index,
    )

    for name in FEATURE_NAMES:
        column = f"feature__{name}"
        available_column = f"available__{name}"

        features[column] = features[name]
        features[available_column] = ~features[name].isna()

    for name in UNAVAILABLE_FEATURES:
        features[f"feature__{name}"] = np.nan
        features[f"available__{name}"] = False

    features = features.drop(columns=list(FEATURE_NAMES))

    table = pd.DataFrame(index=frame.index)

    table["label"] = frame["label"].to_numpy()
    table["group_id"] = [f"domain:{domain}" for domain in frame["domain"]]
    table["source_name"] = SOURCE_NAME
    table["family"] = FeatureFamily.DNS.value
    table["schema_version"] = DNS_SCHEMA_VERSION
    table["dga_family"] = frame["family"].to_numpy()

    for column in features.columns:
        table[column] = features[column].to_numpy()

    return table


def prepare_drift26dsn(
    data_dir: str | Path,
    *,
    max_rows_per_class: int | None = None,
    batch_size: int = 100_000,
):
    if max_rows_per_class is not None and max_rows_per_class < 1:
        raise ValueError("max_rows_per_class must be positive")

    if batch_size < 1:
        raise ValueError("batch_size must be positive")

    paths = validate_sources(data_dir)

    source_frames: list[pd.DataFrame] = []
    source_reports = []

    for path in paths:
        parquet = pq.ParquetFile(path)
        remaining = max_rows_per_class
        batches = []

        for record_batch in parquet.iter_batches(
            batch_size=batch_size,
            columns=["domain", "label", "family"],
        ):
            frame = record_batch.to_pandas()

            frame["domain"] = frame["domain"].map(normalize_domain)
            frame["label"] = frame["label"].map(normalize_label)

            if not frame["family"].map(lambda value: isinstance(value, str)).all():
                raise ValueError(f"{path} contains invalid family values")

            frame["family"] = frame["family"].str.strip()

            frame = frame.drop_duplicates(subset=["domain", "label", "family"])

            if remaining is not None:
                frame = frame.head(remaining)
                remaining -= len(frame)

            if not frame.empty:
                batches.append(frame)

            if remaining is not None and remaining <= 0:
                break

        if not batches:
            raise ValueError(f"{path} contains no usable rows")

        frame = pd.concat(batches, ignore_index=True)
        source_frames.append(frame)

        source_reports.append(
            {
                "filename": path.name,
                "path": str(path.resolve()),
                "sha256": file_sha256(path),
                "bytes": path.stat().st_size,
                "rows_retained": len(frame),
            }
        )

    source_frame = pd.concat(source_frames, ignore_index=True)

    if set(source_frame["label"].unique()) != set(CLASSES):
        raise ValueError(
            f"expected classes {CLASSES}, found {sorted(source_frame['label'].unique())}"
        )

    labels_per_domain = source_frame.groupby("domain")["label"].nunique()
    conflicting_domains = set(labels_per_domain[labels_per_domain > 1].index)

    conflicting_rows_removed = int(source_frame["domain"].isin(conflicting_domains).sum())

    if conflicting_domains:
        source_frame = source_frame[~source_frame["domain"].isin(conflicting_domains)].reset_index(
            drop=True
        )

    tables = []

    for start in range(0, len(source_frame), batch_size):
        batch = source_frame.iloc[start : start + batch_size]
        tables.append(to_shared_features(batch))

    table = pd.concat(tables, ignore_index=True)

    report = {
        "dataset": "DRIFT26DSN / raw_including_TLD",
        "sources": source_reports,
        "source_to_class": CLASS_MAPPING,
        "final_class_counts": table["label"].value_counts().to_dict(),
        "exact_conflicting_domains_removed": len(conflicting_domains),
        "exact_conflicting_rows_removed": conflicting_rows_removed,
        "dga_family_count": int(
            source_frame.loc[
                source_frame["label"] == "DGA",
                "dga_family",
            ].nunique()
        )
        if "dga_family" in source_frame.columns
        else int(
            source_frame.loc[
                source_frame["label"] == "DGA",
                "family",
            ].nunique()
        ),
        "schema_version": DNS_SCHEMA_VERSION,
        "feature_source": "Custodian DNSFeatureExtractor formulas",
        "training_target": "BENIGN vs DGA",
        "unavailable_features": sorted(UNAVAILABLE_FEATURES),
        "grouping": "normalized full domain",
    }

    return table, report
