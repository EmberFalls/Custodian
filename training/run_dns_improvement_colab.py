"""Round-two hosted DNS-tunnelling training with cross-source development data."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

from custodian.models.loader import load_model_package
from training.colab import (
    HOSTED_COLAB_ACKNOWLEDGEMENT,
    require_hosted_colab,
    require_owned_workspace,
)
from training.ctu_dns import prepare_ctu_development, prepare_ctu_final_evaluation
from training.evaluate import classification_metrics
from training.prepare import write_feature_table
from training.run_dns_colab import _hash_and_archive, fit
from training.run_dns_colab import prepare as prepare_bccc
from training.train_common import _matrix
from training.train_dns_candidates import (
    TARGET_MAXIMUM_FALSE_POSITIVE_RATE,
    TARGET_MINIMUM_PRECISION,
    TARGET_MINIMUM_RECALL,
)


def prepare(workspace: Path) -> tuple[Path, Path]:
    """Combine BCCC development rows with the official CTU training split."""

    workspace = require_owned_workspace(workspace)
    bccc_path, bccc_provenance_path = prepare_bccc(workspace)
    ctu_path, ctu_provenance_path = prepare_ctu_development(workspace)
    bccc = pd.read_parquet(bccc_path)
    ctu = pd.read_parquet(ctu_path)
    table = pd.concat([bccc, ctu], ignore_index=True, sort=False)
    if set(table["label"]) != {"BENIGN_DNS", "DNS_TUNNEL"}:
        raise ValueError("improved DNS development data requires both approved classes")
    prepared_path = write_feature_table(
        table,
        workspace / "prepared" / "dns_round2_development.parquet",
    )
    provenance = {
        "manifest_version": "custodian.dns_round2_development.v1",
        "development_sources": [
            json.loads(bccc_provenance_path.read_text(encoding="utf-8")),
            json.loads(ctu_provenance_path.read_text(encoding="utf-8")),
        ],
        "prepared_rows": len(table),
        "class_counts": {
            str(label): int(count)
            for label, count in table["label"].value_counts().sort_index().items()
        },
        "source_counts": {
            str(name): int(count)
            for name, count in table["source_name"].value_counts().sort_index().items()
        },
        "group_count": int(table["group_id"].nunique()),
        "feature_schema_version": "dns.v1",
        "shared_extractor": "custodian.features.dns.DNSFeatureExtractor",
        "model_input_policy": "universally observable lexical feature subset only",
        "ctu_test_split_used_for_fit_calibration_or_selection": False,
        "google_drive_mounted": False,
        "dns_resolution_performed": False,
        "payload_execution_performed": False,
        "traffic_replay_performed": False,
    }
    provenance_path = workspace / "prepared" / "dns_round2_development_provenance.json"
    provenance_path.write_text(
        json.dumps(provenance, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return prepared_path, provenance_path


def evaluate_reused_ctu_benchmark(
    package_dir: Path,
    benchmark_path: Path,
    benchmark_provenance_path: Path,
) -> dict[str, object]:
    """Measure regression on the already-exposed CTU test split without retuning."""

    metrics_path = package_dir / "ctu_reused_benchmark_metrics.json"
    if metrics_path.exists():
        raise RuntimeError("the reused CTU benchmark has already run for this package")
    package = load_model_package(package_dir)
    table = pd.read_parquet(benchmark_path)
    classes = list(package.classes)
    features = _matrix(table, package.feature_schema["columns"])
    probabilities = package.calibrator.predict_proba(features)
    positive_index = classes.index("DNS_TUNNEL")
    scores = probabilities[:, positive_index]
    argmax = np.asarray(classes)[np.argmax(probabilities, axis=1)]
    threshold = package.thresholds["DNS_TUNNEL"]
    predictions = np.where(
        (argmax == "DNS_TUNNEL") & (scores >= threshold),
        "DNS_TUNNEL",
        "BENIGN_DNS",
    )
    report = classification_metrics(table["label"], predictions, classes)
    tn, fp, fn, tp = np.asarray(report["confusion_matrix"]).ravel()
    tunnel = report["classification_report"]["DNS_TUNNEL"]
    positives = (table["label"].to_numpy() == "DNS_TUNNEL").astype(int)
    targets_met = bool(
        fp / max(fp + tn, 1) <= TARGET_MAXIMUM_FALSE_POSITIVE_RATE
        and float(tunnel["precision"]) >= TARGET_MINIMUM_PRECISION
        and float(tunnel["recall"]) >= TARGET_MINIMUM_RECALL
    )
    metrics: dict[str, object] = {
        "evaluation_version": "custodian.dns_reused_regression_benchmark.v1",
        "benchmark_was_exposed_in_previous_development_round": True,
        "benchmark_used_for_round2_fit_calibration_selection_or_thresholding": False,
        "eligible_as_fresh_final_evaluation": False,
        "rows": len(table),
        "class_counts": {
            str(label): int(count)
            for label, count in table["label"].value_counts().sort_index().items()
        },
        "dns_tunnel_threshold": float(threshold),
        "runtime_acceptance": report,
        "dns_tunnel_average_precision": float(average_precision_score(positives, scores)),
        "dns_tunnel_roc_auc": float(roc_auc_score(positives, scores)),
        "dns_tunnel_brier_score": float(brier_score_loss(positives, scores)),
        "multiclass_log_loss": float(log_loss(table["label"], probabilities, labels=classes)),
        "runtime_false_positive_rate": float(fp / max(fp + tn, 1)),
        "runtime_false_negative_rate": float(fn / max(fn + tp, 1)),
        "round2_numerical_targets_met_on_reused_benchmark": targets_met,
    }
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    shutil.copy2(benchmark_provenance_path, package_dir / "ctu_reused_benchmark_provenance.json")
    review = {
        "status": "CANDIDATE_ROUND2_AWAITING_NEW_INDEPENDENT_EVALUATION",
        "trusted": False,
        "must_not_enable_in_models_yaml": True,
        "ctu_reused_benchmark_completed": True,
        "ctu_reused_benchmark_targets_met": targets_met,
        "fresh_independent_evaluation_completed": False,
        "allowed_use": "offline review and continued development only",
    }
    (package_dir / "review_status.json").write_text(
        json.dumps(review, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _hash_and_archive(package_dir)
    return metrics


def run(workspace: Path) -> tuple[Path, dict[str, object]]:
    """Prepare, train and run the non-fresh CTU regression benchmark."""

    require_hosted_colab(HOSTED_COLAB_ACKNOWLEDGEMENT, environment=os.environ)
    workspace = require_owned_workspace(workspace)
    prepared, provenance = prepare(workspace)
    package = fit(prepared, provenance, workspace / "output" / "dns_round2_candidate")
    benchmark, benchmark_provenance = prepare_ctu_final_evaluation(workspace)
    metrics = evaluate_reused_ctu_benchmark(package, benchmark, benchmark_provenance)
    return package, metrics
