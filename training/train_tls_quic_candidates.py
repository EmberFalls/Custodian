"""Select and evaluate encrypted-session candidates without external-data tuning."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.utils.class_weight import compute_sample_weight

from training.calibrate import fit_sigmoid_calibrator
from training.evaluate import classification_metrics
from training.export import export_model_package
from training.operating_point import OperatingPoint, select_binary_operating_point
from training.safety import require_isolated_training_approval
from training.splits import complete_class_grouped_splits
from training.train_common import _feature_columns, _matrix

BENIGN = "BENIGN_ENCRYPTED"
MALICIOUS = "MALICIOUS_ENCRYPTED_SESSION"
TARGET_MAXIMUM_FALSE_POSITIVE_RATE = 0.05
TARGET_MINIMUM_PRECISION = 0.80
TARGET_MINIMUM_RECALL = 0.80


def _pipeline(classifier) -> Pipeline:
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("classifier", classifier),
        ]
    )


def _candidates() -> dict[str, Pipeline]:
    return {
        "extra_trees": _pipeline(
            ExtraTreesClassifier(
                n_estimators=250,
                min_samples_leaf=2,
                n_jobs=-1,
                random_state=42,
            )
        ),
        "hist_gradient_boosting": _pipeline(
            HistGradientBoostingClassifier(
                learning_rate=0.08,
                max_iter=300,
                max_leaf_nodes=31,
                l2_regularization=1.0,
                random_state=42,
            )
        ),
    }


def _point_dict(point: OperatingPoint) -> dict[str, float | bool]:
    return {
        "threshold": point.threshold,
        "precision": point.precision,
        "recall": point.recall,
        "false_positive_rate": point.false_positive_rate,
        "false_negative_rate": point.false_negative_rate,
        "meets_constraints": point.meets_constraints,
    }


def _runtime_predictions(probabilities, classes, threshold: float) -> np.ndarray:
    class_names = np.asarray(classes)
    positive_index = list(classes).index(MALICIOUS)
    argmax = class_names[np.argmax(probabilities, axis=1)]
    return np.where(
        (argmax == MALICIOUS) & (probabilities[:, positive_index] >= threshold),
        MALICIOUS,
        BENIGN,
    )


def _probability_metrics(labels, probabilities, classes, threshold: float) -> dict:
    labels_array = np.asarray(labels, dtype=str)
    positive_index = list(classes).index(MALICIOUS)
    scores = probabilities[:, positive_index]
    positives = (labels_array == MALICIOUS).astype(int)
    predictions = _runtime_predictions(probabilities, classes, threshold)
    report = classification_metrics(labels_array, predictions, classes)
    matrix = np.asarray(report["confusion_matrix"])
    tn, fp, fn, tp = matrix.ravel()
    return {
        "runtime_acceptance": report,
        "false_positive_rate": float(fp / max(fp + tn, 1)),
        "false_negative_rate": float(fn / max(fn + tp, 1)),
        "average_precision": float(average_precision_score(positives, scores)),
        "roc_auc": float(roc_auc_score(positives, scores)),
        "brier_score": float(brier_score_loss(positives, scores)),
        "log_loss": float(log_loss(labels_array, probabilities, labels=list(classes))),
    }


def train(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    isolation_acknowledged: bool = False,
) -> Path:
    """Select on validation data and evaluate once on a locked internal test split."""

    require_isolated_training_approval(acknowledged=isolation_acknowledged)
    destination = Path(output_dir)
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"refusing to overwrite existing artifacts: {destination}")
    table = pd.read_parquet(input_path)
    if table.empty:
        raise ValueError("cannot train on an empty prepared table")
    if set(table["family"]) != {"tls_quic"} or set(table["schema_version"]) != {
        "tls_quic.v1"
    }:
        raise ValueError("candidate input must contain shared tls_quic.v1 features only")
    if set(table["label"]) != {BENIGN, MALICIOUS}:
        raise ValueError("encrypted-session training requires the approved binary classes")

    splits, split_seed = complete_class_grouped_splits(table)
    columns = _feature_columns(table)
    matrices = {
        role: _matrix(getattr(splits, role), columns)
        for role in ("train", "validation", "calibration", "test")
    }
    reports: dict[str, dict] = {}
    fitted: dict[str, tuple] = {}
    weights = compute_sample_weight("balanced", splits.train["label"])
    for name, estimator in _candidates().items():
        estimator.fit(matrices["train"], splits.train["label"], classifier__sample_weight=weights)
        calibrator = fit_sigmoid_calibrator(
            estimator,
            matrices["calibration"],
            splits.calibration["label"],
        )
        classes = [str(value) for value in calibrator.classes_]
        probabilities = calibrator.predict_proba(matrices["validation"])
        point = select_binary_operating_point(
            splits.validation["label"],
            probabilities,
            classes,
            positive_class=MALICIOUS,
            expected_classes={BENIGN, MALICIOUS},
            maximum_false_positive_rate=TARGET_MAXIMUM_FALSE_POSITIVE_RATE,
            minimum_precision=TARGET_MINIMUM_PRECISION,
            minimum_recall=TARGET_MINIMUM_RECALL,
        )
        reports[name] = {
            "operating_point": _point_dict(point),
            **_probability_metrics(
                splits.validation["label"], probabilities, classes, point.threshold
            ),
        }
        fitted[name] = (estimator, calibrator, classes, point)

    selected_name = max(
        reports,
        key=lambda name: (
            bool(reports[name]["operating_point"]["meets_constraints"]),
            float(reports[name]["operating_point"]["recall"]),
            float(reports[name]["average_precision"]),
            -float(reports[name]["operating_point"]["false_positive_rate"]),
        ),
    )
    estimator, calibrator, classes, point = fitted[selected_name]
    test_probabilities = calibrator.predict_proba(matrices["test"])
    metrics = {
        "selected_candidate": selected_name,
        "selection_basis": "validation-only calibrated operating point",
        "candidate_validation_reports": reports,
        "internal_test": _probability_metrics(
            splits.test["label"], test_probabilities, classes, point.threshold
        ),
        "external_evaluation_performed": False,
        "claim_scope": "BCCC-CIRA-CIC-DoHBrw-2020 DoH tunnelling only",
    }
    feature_schema = {
        "family": "tls_quic",
        "schema_version": "tls_quic.v1",
        "columns": columns,
        "allow_runtime_feature_superset": True,
        "preprocessing": "median imputation; only shared runtime-reproducible flow metadata",
    }
    manifest = {
        "family": "tls_quic",
        "schema_version": "tls_quic.v1",
        "model_type": type(estimator.named_steps["classifier"]).__name__,
        "candidate_selection": selected_name,
        "split_seed": split_seed,
        "acceptance_targets": {
            "maximum_false_positive_rate": TARGET_MAXIMUM_FALSE_POSITIVE_RATE,
            "minimum_precision": TARGET_MINIMUM_PRECISION,
            "minimum_recall": TARGET_MINIMUM_RECALL,
        },
        "validation_target_met": point.meets_constraints,
        "split_roles": {
            role: {
                "rows": len(getattr(splits, role)),
                "groups": int(getattr(splits, role)["group_id"].nunique()),
            }
            for role in ("train", "validation", "calibration", "test")
        },
        "training_data_sources": sorted(map(str, table["source_name"].unique())),
        "trusted": False,
        "independent_external_evaluation_completed": False,
    }
    return export_model_package(
        destination,
        estimator=estimator,
        calibrator=calibrator,
        feature_schema=feature_schema,
        classes=classes,
        thresholds={BENIGN: 0.0, MALICIOUS: point.threshold},
        metrics=metrics,
        manifest=manifest,
    )
