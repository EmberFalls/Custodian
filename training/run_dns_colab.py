"""Hosted-Colab preparation and explicit-fit entry point for DNS tunnelling."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)

from custodian.models.loader import load_model_package
from training.bccc_dns import (
    BCCC_DATASET_HANDLE,
    BCCC_EXF_PREFIX,
    adapt_bccc_dns_sources,
)
from training.colab import (
    HOSTED_COLAB_ACKNOWLEDGEMENT,
    require_hosted_colab,
    require_owned_workspace,
    sha256_file,
)
from training.ctu_dns import prepare_ctu_final_evaluation
from training.evaluate import classification_metrics
from training.prepare import write_feature_table
from training.train_common import _matrix
from training.train_dns_candidates import (
    TARGET_MAXIMUM_FALSE_POSITIVE_RATE,
    TARGET_MINIMUM_PRECISION,
    TARGET_MINIMUM_RECALL,
    train,
)

OFFICIAL_DATASET_PAGE = (
    "https://www.yorku.ca/research/bccc/ucs-technical/cybersecurity-datasets-cds/"
    "malicious-dns-and-attacks-bccc-cic-bell-dns-2024/"
)
KAGGLE_DATASET_PAGE = (
    "https://www.kaggle.com/datasets/bcccdatasets/malicious-dns-and-attacks-bccc-cic-bell-dns-2024"
)
SELECTED_FILES = (
    "benign.csv",
    "benign_1.csv",
    "benign_2.csv",
    "benign_heavy_1.csv",
    "benign_heavy_2.csv",
    "heavy_compressed.csv",
    "heavy_exe.csv",
    "heavy_image.csv",
    "heavy_video.csv",
    "light_audio.csv",
    "light_compressed.csv",
    "light_exe.csv",
    "light_image.csv",
    "light_text.csv",
    "light_video.csv",
)
EXTERNAL_HOLDOUT_FILES = (
    "benign_heavy_3.csv",
    "heavy_audio.csv",
    "heavy_text.csv",
)
MAX_SOURCE_BYTES = 300 * 1024 * 1024


def _validate_csv(path: Path) -> dict[str, object]:
    resolved = path.resolve()
    if resolved.suffix.lower() != ".csv" or not resolved.is_file():
        raise ValueError(f"dataset download did not produce an expected CSV: {resolved}")
    size = resolved.stat().st_size
    if size <= 0 or size > MAX_SOURCE_BYTES:
        raise ValueError(f"dataset CSV has an unexpected size: {resolved.name} ({size} bytes)")
    with resolved.open("rb") as stream:
        if b"\x00" in stream.read(4096):
            raise ValueError(f"binary-looking dataset file rejected: {resolved.name}")
    return {"name": resolved.name, "size_bytes": size, "sha256": sha256_file(resolved)}


def download_selected_sources(
    workspace: Path,
    *,
    filenames: tuple[str, ...] = SELECTED_FILES,
) -> tuple[list[Path], list[dict[str, object]]]:
    """Download only reviewed CSV members into Colab-managed temporary storage."""

    import kagglehub

    cache = workspace / "data" / "kaggle-cache"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ["KAGGLEHUB_CACHE"] = str(cache)
    paths: list[Path] = []
    downloads: list[dict[str, object]] = []
    for filename in filenames:
        member = f"{BCCC_EXF_PREFIX}/{filename}"
        path = Path(
            kagglehub.dataset_download(
                BCCC_DATASET_HANDLE,
                path=member,
                force_download=False,
            )
        )
        if path.name != filename:
            raise ValueError(f"unexpected Kaggle member for {filename}: {path.name}")
        validation = _validate_csv(path)
        validation["dataset_member"] = member
        paths.append(path)
        downloads.append(validation)
    return paths, downloads


def prepare(workspace: Path) -> tuple[Path, Path]:
    """Download, validate, adapt, and persist shared dns.v1 feature rows."""

    workspace = require_owned_workspace(workspace)
    paths, downloads = download_selected_sources(workspace)
    result = adapt_bccc_dns_sources(paths)
    prepared_dir = workspace / "prepared"
    prepared_path = write_feature_table(result.table, prepared_dir / "dns_bccc.parquet")
    provenance = {
        "manifest_version": "custodian.dns_training_data.v1",
        "dataset": "BCCC-CIC-Bell-DNS-2024 / BCCC-CIC-Bell-DNS-EXF",
        "publisher": "Behaviour-Centric Cybersecurity Center (BCCC), York University",
        "official_page": OFFICIAL_DATASET_PAGE,
        "kaggle_page": KAGGLE_DATASET_PAGE,
        "kaggle_handle": BCCC_DATASET_HANDLE,
        "license_reported_by_kaggle": "MIT",
        "selected_files": list(SELECTED_FILES),
        "downloads": downloads,
        "adaptation": list(result.sources),
        "prepared_rows": len(result.table),
        "class_counts": {
            str(label): int(count)
            for label, count in result.table["label"].value_counts().sort_index().items()
        },
        "group_count": int(result.table["group_id"].nunique()),
        "feature_family": "dns",
        "feature_schema_version": "dns.v1",
        "shared_extractor": "custodian.features.dns.DNSFeatureExtractor",
        "third_party_engineered_columns_used": False,
        "dns_resolution_performed": False,
        "payload_execution_performed": False,
        "traffic_replay_performed": False,
    }
    provenance_path = prepared_dir / "dns_bccc_provenance.json"
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8")
    return prepared_path, provenance_path


def prepare_external_holdout(workspace: Path) -> tuple[Path, Path]:
    """Lock whole-file heavy scenarios before fitting and keep them separate."""

    workspace = require_owned_workspace(workspace)
    if set(SELECTED_FILES) & set(EXTERNAL_HOLDOUT_FILES):
        raise RuntimeError("development and external holdout files overlap")
    paths, downloads = download_selected_sources(
        workspace,
        filenames=EXTERNAL_HOLDOUT_FILES,
    )
    result = adapt_bccc_dns_sources(paths)
    if set(result.table["label"]) != {"BENIGN_DNS", "DNS_TUNNEL"}:
        raise ValueError("external holdout must contain both approved DNS classes")
    prepared_dir = workspace / "prepared"
    prepared_path = write_feature_table(
        result.table,
        prepared_dir / "dns_bccc_external_holdout.parquet",
    )
    provenance = {
        "manifest_version": "custodian.dns_external_holdout.v1",
        "selection_locked_before_model_fit": True,
        "dataset": "BCCC-CIC-Bell-DNS-2024 / BCCC-CIC-Bell-DNS-EXF",
        "publisher": "Behaviour-Centric Cybersecurity Center (BCCC), York University",
        "official_page": OFFICIAL_DATASET_PAGE,
        "kaggle_page": KAGGLE_DATASET_PAGE,
        "selected_files": list(EXTERNAL_HOLDOUT_FILES),
        "downloads": downloads,
        "adaptation": list(result.sources),
        "prepared_rows": len(result.table),
        "class_counts": {
            str(label): int(count)
            for label, count in result.table["label"].value_counts().sort_index().items()
        },
        "group_count": int(result.table["group_id"].nunique()),
        "shared_extractor": "custodian.features.dns.DNSFeatureExtractor",
        "third_party_engineered_columns_used": False,
        "dns_resolution_performed": False,
        "payload_execution_performed": False,
        "traffic_replay_performed": False,
    }
    provenance_path = prepared_dir / "dns_bccc_external_holdout_provenance.json"
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
    """Open the hosted-training gate, fit, verify, and package real artifacts."""

    require_hosted_colab(
        HOSTED_COLAB_ACKNOWLEDGEMENT,
        environment=os.environ,
    )
    os.environ["CUSTODIAN_HOSTED_COLAB_TRAINING"] = "YES"
    package_dir = train(
        prepared_path,
        output_dir,
        isolation_acknowledged=True,
    )
    shutil.copy2(provenance_path, package_dir / "dataset_provenance.json")
    _hash_and_archive(package_dir)
    loaded = load_model_package(package_dir)
    if loaded.classes != ("BENIGN_DNS", "DNS_TUNNEL"):
        raise ValueError(f"unexpected DNS model classes: {loaded.classes}")
    return package_dir


def evaluate_external_holdout(
    package_dir: Path,
    holdout_path: Path,
    holdout_provenance_path: Path,
) -> dict[str, object]:
    """Evaluate once without fitting, calibrating, or changing thresholds."""

    package = load_model_package(package_dir)
    table = pd.read_parquet(holdout_path)
    columns = package.feature_schema["columns"]
    features = _matrix(table, columns)
    probabilities = package.calibrator.predict_proba(features)
    classes = list(package.classes)
    positive_index = classes.index("DNS_TUNNEL")
    labels = table["label"].to_numpy()
    positives = (labels == "DNS_TUNNEL").astype(int)
    tunnel_scores = probabilities[:, positive_index]
    argmax_predictions = np.asarray(classes)[np.argmax(probabilities, axis=1)]
    threshold = package.thresholds["DNS_TUNNEL"]
    runtime_predictions = np.where(
        (argmax_predictions == "DNS_TUNNEL") & (tunnel_scores >= threshold),
        "DNS_TUNNEL",
        "BENIGN_DNS",
    )
    score_only_predictions = np.where(
        tunnel_scores >= threshold,
        "DNS_TUNNEL",
        "BENIGN_DNS",
    )
    runtime_metrics = classification_metrics(labels, runtime_predictions, classes)
    runtime_matrix = np.asarray(runtime_metrics["confusion_matrix"])
    tn, fp, fn, tp = runtime_matrix.ravel()
    metrics: dict[str, object] = {
        "evaluation_version": "custodian.dns_external_evaluation.v1",
        "evaluated_at_utc": datetime.now(UTC).isoformat(),
        "selection_locked_before_model_fit": True,
        "thresholds_tuned_on_external_holdout": False,
        "external_files": list(EXTERNAL_HOLDOUT_FILES),
        "rows": len(table),
        "groups": int(table["group_id"].nunique()),
        "class_counts": {
            str(label): int(count)
            for label, count in table["label"].value_counts().sort_index().items()
        },
        "dns_tunnel_threshold_from_internal_validation": float(threshold),
        "argmax": classification_metrics(labels, argmax_predictions, classes),
        "runtime_acceptance": runtime_metrics,
        "score_only_threshold_diagnostic": classification_metrics(
            labels, score_only_predictions, classes
        ),
        "runtime_logic": ("argmax DNS_TUNNEL and calibrated confidence meets validation threshold"),
        "dns_tunnel_average_precision": float(average_precision_score(positives, tunnel_scores)),
        "dns_tunnel_roc_auc": float(roc_auc_score(positives, tunnel_scores)),
        "dns_tunnel_brier_score": float(brier_score_loss(positives, tunnel_scores)),
        "multiclass_log_loss": float(log_loss(labels, probabilities, labels=classes)),
        "runtime_false_positive_rate": float(fp / max(fp + tn, 1)),
        "runtime_false_negative_rate": float(fn / max(fn + tp, 1)),
        "dns_resolution_performed": False,
        "payload_execution_performed": False,
        "traffic_replay_performed": False,
    }
    (package_dir / "external_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8"
    )
    shutil.copy2(
        holdout_provenance_path,
        package_dir / "external_holdout_provenance.json",
    )
    review_status = {
        "status": "CANDIDATE_AWAITING_FRESH_EXTERNAL_EVALUATION",
        "trusted": False,
        "diagnostic_holdout_used_for_retuning": False,
        "must_not_enable_in_models_yaml": True,
        "allowed_use": "offline review and continued model development only",
        "diagnostic_runtime_false_positive_rate": metrics["runtime_false_positive_rate"],
        "diagnostic_runtime_false_negative_rate": metrics["runtime_false_negative_rate"],
    }
    (package_dir / "review_status.json").write_text(
        json.dumps(review_status, indent=2, sort_keys=True), encoding="utf-8"
    )
    _hash_and_archive(package_dir)
    return metrics


def evaluate_fresh_external_once(
    package_dir: Path,
    final_path: Path,
    final_provenance_path: Path,
) -> dict[str, object]:
    """Evaluate the locked CTU split once, without any model or threshold changes."""

    metrics_path = package_dir / "fresh_external_metrics.json"
    if metrics_path.exists():
        raise RuntimeError("fresh external evaluation has already run for this candidate package")
    package = load_model_package(package_dir)
    table = pd.read_parquet(final_path)
    columns = package.feature_schema["columns"]
    features = _matrix(table, columns)
    probabilities = package.calibrator.predict_proba(features)
    classes = list(package.classes)
    positive_index = classes.index("DNS_TUNNEL")
    labels = table["label"].to_numpy()
    positives = (labels == "DNS_TUNNEL").astype(int)
    tunnel_scores = probabilities[:, positive_index]
    argmax_predictions = np.asarray(classes)[np.argmax(probabilities, axis=1)]
    threshold = package.thresholds["DNS_TUNNEL"]
    runtime_predictions = np.where(
        (argmax_predictions == "DNS_TUNNEL") & (tunnel_scores >= threshold),
        "DNS_TUNNEL",
        "BENIGN_DNS",
    )
    runtime_metrics = classification_metrics(labels, runtime_predictions, classes)
    runtime_matrix = np.asarray(runtime_metrics["confusion_matrix"])
    tn, fp, fn, tp = runtime_matrix.ravel()
    false_positive_rate = float(fp / max(fp + tn, 1))
    false_negative_rate = float(fn / max(fn + tp, 1))
    tunnel_report = runtime_metrics["classification_report"]["DNS_TUNNEL"]
    external_targets_met = bool(
        false_positive_rate <= TARGET_MAXIMUM_FALSE_POSITIVE_RATE
        and float(tunnel_report["precision"]) >= TARGET_MINIMUM_PRECISION
        and float(tunnel_report["recall"]) >= TARGET_MINIMUM_RECALL
    )
    metrics: dict[str, object] = {
        "evaluation_version": "custodian.dns_fresh_external_evaluation.v1",
        "evaluated_at_utc": datetime.now(UTC).isoformat(),
        "evaluation_run_count_for_candidate": 1,
        "selection_locked_before_model_fit": True,
        "candidate_or_threshold_changed_after_source_lock": False,
        "thresholds_tuned_on_fresh_external_data": False,
        "dataset": "DNS Threats Dataset, Version 1 — fixed test split",
        "dataset_doi": "10.5281/zenodo.6508640",
        "rows": len(table),
        "groups": int(table["group_id"].nunique()),
        "class_counts": {
            str(label): int(count)
            for label, count in table["label"].value_counts().sort_index().items()
        },
        "dns_tunnel_threshold_from_internal_validation": float(threshold),
        "runtime_acceptance": runtime_metrics,
        "runtime_logic": ("argmax DNS_TUNNEL and calibrated confidence meets validation threshold"),
        "dns_tunnel_average_precision": float(average_precision_score(positives, tunnel_scores)),
        "dns_tunnel_roc_auc": float(roc_auc_score(positives, tunnel_scores)),
        "dns_tunnel_brier_score": float(brier_score_loss(positives, tunnel_scores)),
        "multiclass_log_loss": float(log_loss(labels, probabilities, labels=classes)),
        "runtime_false_positive_rate": false_positive_rate,
        "runtime_false_negative_rate": false_negative_rate,
        "predeclared_acceptance_targets": {
            "maximum_false_positive_rate": TARGET_MAXIMUM_FALSE_POSITIVE_RATE,
            "minimum_dns_tunnel_precision": TARGET_MINIMUM_PRECISION,
            "minimum_dns_tunnel_recall": TARGET_MINIMUM_RECALL,
        },
        "predeclared_external_targets_met": external_targets_met,
        "source_limitations": [
            "no client or timestamp fields",
            "no DNS query-type field",
            "no temporal history",
            "laboratory-generated tunnelling domains",
        ],
        "dns_resolution_performed": False,
        "payload_execution_performed": False,
        "traffic_replay_performed": False,
    }
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    shutil.copy2(
        final_provenance_path,
        package_dir / "fresh_external_provenance.json",
    )
    review_status = {
        "status": (
            "CANDIDATE_MEETS_EXTERNAL_TARGETS_AWAITING_HUMAN_APPROVAL"
            if external_targets_met
            else "CANDIDATE_FAILED_PREDECLARED_EXTERNAL_TARGETS"
        ),
        "trusted": False,
        "must_not_enable_in_models_yaml": True,
        "fresh_external_evaluation_completed": True,
        "fresh_external_data_used_for_retuning": False,
        "requires_explicit_human_review": True,
        "live_network_validation_completed": False,
        "allowed_use": "offline review only",
    }
    (package_dir / "review_status.json").write_text(
        json.dumps(review_status, indent=2, sort_keys=True), encoding="utf-8"
    )
    _hash_and_archive(package_dir)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path("/content/custodian-workspace"))
    parser.add_argument("--fit", action="store_true")
    parser.add_argument("--evaluate-fresh-external", action="store_true")
    parser.add_argument("--acknowledgement", default="")
    args = parser.parse_args()
    require_hosted_colab(args.acknowledgement, environment=os.environ)
    prepared_path, provenance_path = prepare(args.workspace)
    print(f"Prepared shared DNS features: {prepared_path}")
    print(f"Recorded dataset provenance: {provenance_path}")
    if not args.fit:
        print("Preparation complete. Model fitting was not requested and did not run.")
        return
    holdout_path, holdout_provenance_path = prepare_external_holdout(args.workspace)
    package = fit(prepared_path, provenance_path, args.workspace / "output" / "dns")
    external_metrics = evaluate_external_holdout(
        package,
        holdout_path,
        holdout_provenance_path,
    )
    print(f"Verified DNS model package: {package}")
    print(f"Downloadable artifact archive: {package}.zip")
    print(
        "External runtime false-positive/false-negative rates:",
        external_metrics["runtime_false_positive_rate"],
        external_metrics["runtime_false_negative_rate"],
    )
    if args.evaluate_fresh_external:
        final_path, final_provenance = prepare_ctu_final_evaluation(args.workspace)
        final_metrics = evaluate_fresh_external_once(
            package,
            final_path,
            final_provenance,
        )
        print(
            "Fresh external targets met:",
            final_metrics["predeclared_external_targets_met"],
        )


if __name__ == "__main__":
    main()
