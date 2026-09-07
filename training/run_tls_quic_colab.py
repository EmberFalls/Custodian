"""Hosted-Colab preparation and fitting for the encrypted-session candidate."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from custodian.models.loader import load_model_package
from training.colab import (
    HOSTED_COLAB_ACKNOWLEDGEMENT,
    require_hosted_colab,
    require_owned_workspace,
    sha256_file,
)
from training.dohbrw import (
    BCCC_PAGE,
    DATASET_FILENAME,
    DATASET_HANDLE,
    KAGGLE_PAGE,
    OFFICIAL_PAGE,
    adapt_dohbrw,
    validate_source,
)
from training.prepare import write_feature_table
from training.train_tls_quic_candidates import BENIGN, MALICIOUS, train


def download_source(workspace: Path) -> tuple[Path, dict[str, object]]:
    """Download only the reviewed inert CSV into Colab-owned temporary storage."""

    workspace = require_owned_workspace(workspace)
    import kagglehub

    cache = workspace / "data" / "kaggle-cache"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ["KAGGLEHUB_CACHE"] = str(cache)
    source = Path(
        kagglehub.dataset_download(
            DATASET_HANDLE,
            path=DATASET_FILENAME,
            force_download=False,
        )
    )
    if source.name != DATASET_FILENAME:
        raise ValueError(f"unexpected Kaggle member: {source}")
    source = validate_source(source)
    return source, {
        "dataset_handle": DATASET_HANDLE,
        "dataset_member": DATASET_FILENAME,
        "source_bytes": source.stat().st_size,
        "source_sha256": sha256_file(source),
    }


def prepare(workspace: Path) -> tuple[Path, Path]:
    workspace = require_owned_workspace(workspace)
    source, download = download_source(workspace)
    result = adapt_dohbrw(source)
    prepared_dir = workspace / "prepared"
    prepared_path = write_feature_table(
        result.table,
        prepared_dir / "tls_quic_dohbrw.parquet",
    )
    provenance = {
        "manifest_version": "custodian.encrypted_training_data.v1",
        "dataset": "BCCC-CIRA-CIC-DoHBrw-2020",
        "publisher": "Behaviour-Centric Cybersecurity Center, York University",
        "official_original_page": OFFICIAL_PAGE,
        "bccc_page": BCCC_PAGE,
        "kaggle_page": KAGGLE_PAGE,
        "license_reported_by_kaggle": "MIT",
        "download": download,
        "adaptation": result.provenance,
        "prepared_rows": len(result.table),
        "feature_family": "tls_quic",
        "feature_schema_version": "tls_quic.v1",
        "source_content_executed": False,
        "network_interface_opened": False,
        "traffic_replayed": False,
        "google_drive_mounted": False,
    }
    provenance_path = prepared_dir / "tls_quic_dohbrw_provenance.json"
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8")
    return prepared_path, provenance_path


def _hash_and_archive(package_dir: Path) -> Path:
    hashes = {
        path.name: sha256_file(path)
        for path in sorted(package_dir.iterdir())
        if path.is_file() and path.name != "artifact_sha256.json"
    }
    (package_dir / "artifact_sha256.json").write_text(
        json.dumps(hashes, indent=2, sort_keys=True), encoding="utf-8"
    )
    return Path(shutil.make_archive(str(package_dir), "zip", root_dir=package_dir))


def fit(prepared_path: Path, provenance_path: Path, output_dir: Path) -> Path:
    require_hosted_colab(HOSTED_COLAB_ACKNOWLEDGEMENT, environment=os.environ)
    os.environ["CUSTODIAN_HOSTED_COLAB_TRAINING"] = "YES"
    package = train(prepared_path, output_dir, isolation_acknowledged=True)
    shutil.copy2(provenance_path, package / "dataset_provenance.json")
    review = {
        "status": "CANDIDATE_INTERNAL_EVALUATION_COMPLETE_EXTERNAL_EVALUATION_REQUIRED",
        "trusted": False,
        "must_not_enable_in_models_yaml": True,
        "allowed_claim": "experimental DoH-tunnel encrypted-session candidate",
        "forbidden_claim": "general malicious TLS or QUIC detection",
        "independent_external_evaluation_completed": False,
    }
    (package / "review_status.json").write_text(
        json.dumps(review, indent=2, sort_keys=True), encoding="utf-8"
    )
    _hash_and_archive(package)
    loaded = load_model_package(package)
    if loaded.classes != (BENIGN, MALICIOUS):
        raise ValueError(f"unexpected encrypted-session classes: {loaded.classes}")
    return package
