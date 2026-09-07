"""Safe adapters for the official DNS Threats Dataset v1 CSV splits."""

from __future__ import annotations

import gzip
import hashlib
import os
import urllib.request
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from custodian.core.enums import ThreatClass
from custodian.core.schemas import CapabilityProfile
from custodian.features.dns import DNSFeatureExtractor
from training.colab import (
    HOSTED_COLAB_ACKNOWLEDGEMENT,
    require_hosted_colab,
    require_owned_workspace,
    sha256_file,
)
from training.prepare import feature_rows, write_feature_table

CTU_RECORD_ID = "6508640"
CTU_DOI = "10.5281/zenodo.6508640"
CTU_FINAL_URL = (
    "https://zenodo.org/records/6508640/files/test_combined_multiclass.csv.gz?download=1"
)
CTU_TRAIN_URL = (
    "https://zenodo.org/records/6508640/files/train_combined_multiclass.csv.gz?download=1"
)
CTU_TRAIN_ARCHIVE_NAME = "train_combined_multiclass.csv.gz"
CTU_TRAIN_PUBLISHED_MD5 = "c30a49c6f362e0c2dffe3881504a6825"
CTU_FINAL_ARCHIVE_NAME = "test_combined_multiclass.csv.gz"
CTU_FINAL_PUBLISHED_MD5 = "ce52df239c4245ffaa15c642b8b0b625"
CTU_FINAL_SHA256 = "028fd97a4c498e8b6f22b93c2f804e4e0f3afe0c15ff5b3e71f9a12d0ddd4783"
CTU_REQUIRED_COLUMNS = ("domain", "class")
CTU_MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024
CTU_MAX_DOMAIN_LENGTH = 253
CTU_DEVELOPMENT_BENIGN_SAMPLE_MODULUS = 8


@dataclass(frozen=True, slots=True)
class CTUAdaptationResult:
    """Shared-feature rows and an audit report for the immutable test split."""

    table: pd.DataFrame
    report: dict[str, Any]


def _md5_file(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def download_ctu_final_source(workspace: Path) -> tuple[Path, dict[str, Any]]:
    """Download the fixed Zenodo test split only inside a hosted Colab runtime."""

    require_hosted_colab(HOSTED_COLAB_ACKNOWLEDGEMENT, environment=os.environ)
    workspace = require_owned_workspace(workspace)
    destination = workspace / "data" / "independent" / CTU_FINAL_ARCHIVE_NAME
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        request = urllib.request.Request(
            CTU_FINAL_URL,
            headers={"User-Agent": "Custodian-Final-Evaluation/1.0"},
        )
        with (
            urllib.request.urlopen(request, timeout=60) as response,
            destination.open("xb") as output,
        ):
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > CTU_MAX_DOWNLOAD_BYTES:
                raise ValueError("CTU test split exceeds the download-size limit")
            copied = 0
            while chunk := response.read(1024 * 1024):
                copied += len(chunk)
                if copied > CTU_MAX_DOWNLOAD_BYTES:
                    raise ValueError("CTU test split exceeded the download-size limit")
                output.write(chunk)
    if not destination.is_file() or not 0 < destination.stat().st_size <= CTU_MAX_DOWNLOAD_BYTES:
        raise ValueError("CTU test split has an invalid size")
    verified_md5 = _md5_file(destination)
    verified_sha256 = sha256_file(destination)
    if verified_md5 != CTU_FINAL_PUBLISHED_MD5:
        raise ValueError("CTU test split failed the published Zenodo MD5")
    if verified_sha256 != CTU_FINAL_SHA256:
        raise ValueError("CTU test split failed Custodian's locked SHA-256")
    with gzip.open(destination, "rt", encoding="utf-8-sig", newline="") as stream:
        header = tuple(pd.read_csv(stream, nrows=0).columns)
    if header != CTU_REQUIRED_COLUMNS:
        raise ValueError(f"unexpected CTU test schema: {header!r}")
    return destination, {
        "record_id": CTU_RECORD_ID,
        "doi": CTU_DOI,
        "download_url": CTU_FINAL_URL,
        "archive_name": CTU_FINAL_ARCHIVE_NAME,
        "size_bytes": destination.stat().st_size,
        "published_md5": CTU_FINAL_PUBLISHED_MD5,
        "verified_md5": verified_md5,
        "sha256": verified_sha256,
        "header": list(header),
        "selection_locked_before_model_fit": True,
        "dataset_member_executed": False,
    }


def download_ctu_development_source(workspace: Path) -> tuple[Path, dict[str, Any]]:
    """Download and verify the published training split in hosted Colab only."""

    require_hosted_colab(HOSTED_COLAB_ACKNOWLEDGEMENT, environment=os.environ)
    workspace = require_owned_workspace(workspace)
    destination = workspace / "data" / "development" / CTU_TRAIN_ARCHIVE_NAME
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        request = urllib.request.Request(
            CTU_TRAIN_URL,
            headers={"User-Agent": "Custodian-DNS-Development/2.0"},
        )
        with (
            urllib.request.urlopen(request, timeout=60) as response,
            destination.open("xb") as output,
        ):
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > CTU_MAX_DOWNLOAD_BYTES:
                raise ValueError("CTU training split exceeds the download-size limit")
            copied = 0
            while chunk := response.read(1024 * 1024):
                copied += len(chunk)
                if copied > CTU_MAX_DOWNLOAD_BYTES:
                    raise ValueError("CTU training split exceeded the download-size limit")
                output.write(chunk)
    if not destination.is_file() or not 0 < destination.stat().st_size <= CTU_MAX_DOWNLOAD_BYTES:
        raise ValueError("CTU training split has an invalid size")
    verified_md5 = _md5_file(destination)
    if verified_md5 != CTU_TRAIN_PUBLISHED_MD5:
        raise ValueError("CTU training split failed the published Zenodo MD5")
    with gzip.open(destination, "rt", encoding="utf-8-sig", newline="") as stream:
        header = tuple(pd.read_csv(stream, nrows=0).columns)
    if header != CTU_REQUIRED_COLUMNS:
        raise ValueError(f"unexpected CTU training schema: {header!r}")
    return destination, {
        "record_id": CTU_RECORD_ID,
        "doi": CTU_DOI,
        "download_url": CTU_TRAIN_URL,
        "archive_name": CTU_TRAIN_ARCHIVE_NAME,
        "size_bytes": destination.stat().st_size,
        "published_md5": CTU_TRAIN_PUBLISHED_MD5,
        "verified_md5": verified_md5,
        "sha256": sha256_file(destination),
        "header": list(header),
        "official_publisher_split_role": "train",
        "dataset_member_executed": False,
    }


def _target_label(value: object) -> str | None:
    try:
        label = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"invalid CTU class label: {value!r}") from error
    if label == 0:
        return ThreatClass.BENIGN_DNS.value
    if label == 2:
        return ThreatClass.DNS_TUNNEL.value
    if label == 1:
        return None  # DGA is a distinct threat family and outside this binary model.
    raise ValueError(f"unsupported CTU class label: {label!r}")


def adapt_ctu_source(
    path: str | Path,
    *,
    group_prefix: str,
    benign_sample_modulus: int = 1,
) -> CTUAdaptationResult:
    """Read domain strings passively and use the shared runtime DNS extractor.

    The benchmark has no timestamp, client, query type, or temporal sequence. Those
    features remain unavailable instead of being invented. DGA rows are excluded
    because this package evaluates only BENIGN_DNS versus DNS_TUNNEL.
    """

    if not group_prefix or benign_sample_modulus <= 0:
        raise ValueError("a group prefix and positive benign sample modulus are required")
    archive = Path(path)
    if archive.suffix.lower() != ".gz" or not archive.is_file():
        raise ValueError(f"CTU source must be an existing .gz file: {archive}")
    extractor = DNSFeatureExtractor()
    items = []
    counts: Counter[str] = Counter()
    rejected_rows = 0
    excluded_dga_rows = 0
    sampled_out_benign_rows = 0
    observed_at = datetime(1970, 1, 1, tzinfo=UTC)
    for chunk in pd.read_csv(
        archive,
        compression="gzip",
        usecols=list(CTU_REQUIRED_COLUMNS),
        chunksize=100_000,
        low_memory=False,
    ):
        if tuple(chunk.columns) != CTU_REQUIRED_COLUMNS:
            raise ValueError(f"unexpected CTU test schema: {tuple(chunk.columns)!r}")
        for row in chunk.itertuples(index=False):
            target = _target_label(row[1])
            if target is None:
                excluded_dga_rows += 1
                continue
            domain = str(row[0]).strip().lower().rstrip(".")
            if not domain or len(domain) > CTU_MAX_DOMAIN_LENGTH or "\x00" in domain:
                rejected_rows += 1
                continue
            full_digest = hashlib.sha256(domain.encode("utf-8")).hexdigest()
            stable_id = full_digest[:20]
            if (
                target == ThreatClass.BENIGN_DNS.value
                and benign_sample_modulus > 1
                and int(full_digest[:8], 16) % benign_sample_modulus != 0
            ):
                sampled_out_benign_rows += 1
                continue
            vector = extractor.extract_metadata(
                observed_at=observed_at,
                source_id=f"{group_prefix}-{stable_id}",
                domain=domain,
                query_type=None,
                recent_domains=(),
                window_seconds=60,
                capabilities=CapabilityProfile(
                    has_packet_timestamps=False,
                    has_dns_query_name=True,
                    has_dns_query_type=False,
                ),
                recent_history_available=False,
            )
            counts[target] += 1
            items.append((vector, target, f"{group_prefix}:{stable_id}", archive.name))
    table = feature_rows(items)
    report = {
        "source_name": archive.name,
        "sha256": sha256_file(archive),
        "prepared_rows": len(table),
        "rejected_rows": rejected_rows,
        "excluded_dga_rows": excluded_dga_rows,
        "sampled_out_benign_rows": sampled_out_benign_rows,
        "benign_sample_modulus": benign_sample_modulus,
        "labels": dict(sorted(counts.items())),
        "raw_domain_column_used": True,
        "third_party_engineered_columns_used": False,
        "timestamps_available": False,
        "query_types_available": False,
        "temporal_history_available": False,
        "placeholder_timestamp_used_only_for_non_feature_ids": True,
        "dns_resolution_performed": False,
        "payload_execution_performed": False,
        "traffic_replay_performed": False,
    }
    return CTUAdaptationResult(table=table, report=report)


def adapt_ctu_final_source(path: str | Path) -> CTUAdaptationResult:
    """Adapt every benign/tunnel row from the previously locked test split."""

    return adapt_ctu_source(path, group_prefix="ctu-final")


def adapt_ctu_development_source(path: str | Path) -> CTUAdaptationResult:
    """Adapt all tunnels plus a deterministic benign sample from the train split."""

    return adapt_ctu_source(
        path,
        group_prefix="ctu-development",
        benign_sample_modulus=CTU_DEVELOPMENT_BENIGN_SAMPLE_MODULUS,
    )


def prepare_ctu_development(workspace: Path) -> tuple[Path, Path]:
    """Prepare the official training split as a second development source."""

    workspace = require_owned_workspace(workspace)
    source, download = download_ctu_development_source(workspace)
    result = adapt_ctu_development_source(source)
    if set(result.table["label"]) != {"BENIGN_DNS", "DNS_TUNNEL"}:
        raise ValueError("CTU development data requires both approved DNS classes")
    prepared_dir = workspace / "prepared"
    prepared_path = write_feature_table(
        result.table,
        prepared_dir / "dns_ctu_development.parquet",
    )
    provenance = {
        "manifest_version": "custodian.dns_development_source.v2",
        "dataset": "DNS Threats Dataset, Version 1 — official training split",
        "publisher": "Palau et al.; Zenodo",
        "doi": CTU_DOI,
        "download": download,
        "adaptation": result.report,
        "prepared_rows": len(result.table),
        "class_counts": {
            str(label): int(count)
            for label, count in result.table["label"].value_counts().sort_index().items()
        },
        "group_count": int(result.table["group_id"].nunique()),
        "shared_extractor": "custodian.features.dns.DNSFeatureExtractor",
        "feature_schema_version": "dns.v1",
        "raw_domain_column_used": True,
        "third_party_engineered_columns_used": False,
        "previously_published_test_split_used_for_fit": False,
    }
    provenance_path = prepared_dir / "dns_ctu_development_provenance.json"
    provenance_path.write_text(
        __import__("json").dumps(provenance, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return prepared_path, provenance_path


def prepare_ctu_final_evaluation(workspace: Path) -> tuple[Path, Path]:
    """Prepare the immutable final split without fitting or loading a model."""

    workspace = require_owned_workspace(workspace)
    source, download = download_ctu_final_source(workspace)
    result = adapt_ctu_final_source(source)
    if set(result.table["label"]) != {"BENIGN_DNS", "DNS_TUNNEL"}:
        raise ValueError("CTU final evaluation requires both approved DNS classes")
    prepared_dir = workspace / "prepared"
    prepared_path = write_feature_table(
        result.table,
        prepared_dir / "dns_ctu_final_evaluation.parquet",
    )
    provenance = {
        "manifest_version": "custodian.dns_fresh_external_holdout.v1",
        "selection_locked_before_model_fit": True,
        "dataset": "DNS Threats Dataset, Version 1 — fixed test split",
        "publisher": "Palau et al.; Zenodo",
        "doi": CTU_DOI,
        "download": download,
        "adaptation": result.report,
        "prepared_rows": len(result.table),
        "class_counts": {
            str(label): int(count)
            for label, count in result.table["label"].value_counts().sort_index().items()
        },
        "group_count": int(result.table["group_id"].nunique()),
        "shared_extractor": "custodian.features.dns.DNSFeatureExtractor",
        "feature_schema_version": "dns.v1",
        "candidate_selection_accessed_rows": False,
    }
    provenance_path = prepared_dir / "dns_ctu_final_evaluation_provenance.json"
    provenance_path.write_text(
        __import__("json").dumps(provenance, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return prepared_path, provenance_path
