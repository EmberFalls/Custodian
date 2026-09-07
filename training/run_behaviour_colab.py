"""Hosted-Colab acquisition and candidate training for the Behaviour family."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from custodian.models.loader import load_model_package
from training.cicids2017 import CLASSES, REQUIRED_FILES, validate_sources
from training.colab import (
    HOSTED_COLAB_ACKNOWLEDGEMENT,
    require_hosted_colab,
    require_owned_workspace,
    sha256_file,
)
from training.train_behaviour import train

OFFICIAL_PAGE = "https://www.unb.ca/cic/datasets/ids-2017.html"
MIRROR_REPOSITORY = "San0160/CICIDS-2017"
MIRROR_PAGE = f"https://huggingface.co/datasets/{MIRROR_REPOSITORY}"
MAX_SOURCE_BYTES = 256 * 1024 * 1024
MINIMUM_INTERNAL_RECALL = 0.80


def _validate_csv(path: Path) -> dict[str, object]:
    if path.suffix.lower() != ".csv" or not path.is_file():
        raise ValueError(f"unexpected CICIDS2017 member: {path}")
    size = path.stat().st_size
    if size <= 0 or size > MAX_SOURCE_BYTES:
        raise ValueError(f"CICIDS2017 CSV has an unexpected size: {path.name} ({size} bytes)")
    with path.open("rb") as stream:
        if b"\x00" in stream.read(4096):
            raise ValueError(f"binary-looking CICIDS2017 CSV rejected: {path.name}")
    return {"name": path.name, "bytes": size, "sha256": sha256_file(path)}


def download_sources(workspace: Path) -> tuple[Path, Path]:
    """Download the exact reviewed CSV members and record the immutable mirror revision."""

    workspace = require_owned_workspace(workspace)
    from huggingface_hub import HfApi, hf_hub_download

    info = HfApi().dataset_info(MIRROR_REPOSITORY, revision="main")
    revision = str(info.sha)
    if len(revision) != 40:
        raise ValueError("dataset mirror did not expose an immutable 40-character revision")
    data_dir = workspace / "data" / "cicids2017"
    data_dir.mkdir(parents=True, exist_ok=True)
    downloads = []
    for filename in REQUIRED_FILES:
        downloaded = Path(
            hf_hub_download(
                repo_id=MIRROR_REPOSITORY,
                repo_type="dataset",
                filename=filename,
                revision=revision,
                local_dir=data_dir,
            )
        )
        if downloaded.name != filename or downloaded.parent.resolve() != data_dir.resolve():
            raise ValueError(f"download escaped the dedicated dataset directory: {downloaded}")
        downloads.append(_validate_csv(downloaded))
    validate_sources(data_dir)
    provenance = {
        "manifest_version": "custodian.behaviour_download.v1",
        "dataset": "CICIDS2017 MachineLearningCSV",
        "publisher": "Canadian Institute for Cybersecurity, University of New Brunswick",
        "official_page": OFFICIAL_PAGE,
        "mirror_page": MIRROR_PAGE,
        "mirror_repository": MIRROR_REPOSITORY,
        "mirror_revision": revision,
        "mirror_is_official": False,
        "files": downloads,
        "raw_pcap_downloaded": False,
        "source_content_executed": False,
        "network_interface_opened": False,
        "traffic_replayed": False,
        "google_drive_mounted": False,
    }
    provenance_path = workspace / "prepared" / "behaviour_download_provenance.json"
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8")
    return data_dir, provenance_path


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


def fit(
    workspace: Path,
    data_dir: Path,
    download_provenance: Path,
    output_dir: Path,
) -> Path:
    """Fit once, verify the package, and retain candidate-only review state."""

    workspace = require_owned_workspace(workspace)
    require_hosted_colab(HOSTED_COLAB_ACKNOWLEDGEMENT, environment=os.environ)
    os.environ["CUSTODIAN_HOSTED_COLAB_TRAINING"] = "YES"
    package = train(
        data_dir,
        output_dir,
        processed_path=workspace / "prepared" / "behaviour_cicids2017.parquet",
        isolation_acknowledged=True,
    )
    shutil.copy2(download_provenance, package / "download_provenance.json")
    metrics = json.loads((package / "metrics.json").read_text(encoding="utf-8"))
    report = metrics["final_test_calibrated"]["classification_report"]
    attack_recalls = {name: float(report[name]["recall"]) for name in CLASSES if name != "BENIGN"}
    internal_target_met = all(value >= MINIMUM_INTERNAL_RECALL for value in attack_recalls.values())
    review = {
        "status": (
            "CANDIDATE_INTERNAL_TARGET_MET_EXTERNAL_EVALUATION_REQUIRED"
            if internal_target_met
            else "CANDIDATE_FAILED_INTERNAL_RECALL_TARGET"
        ),
        "trusted": False,
        "must_not_enable_in_models_yaml": True,
        "minimum_internal_attack_recall": MINIMUM_INTERNAL_RECALL,
        "internal_attack_recalls": attack_recalls,
        "independent_external_evaluation_completed": False,
        "allowed_claim": "CICIDS2017 flow-classification candidate",
        "forbidden_claims": [
            "validated C2 detection",
            "validated exfiltration detection",
            "live-network accuracy",
        ],
    }
    (package / "review_status.json").write_text(
        json.dumps(review, indent=2, sort_keys=True), encoding="utf-8"
    )
    _hash_and_archive(package)
    loaded = load_model_package(package)
    if loaded.classes != tuple(CLASSES):
        raise ValueError(f"unexpected Behaviour classes: {loaded.classes}")
    return package
