"""Train and export the calibrated DRIFT26DSN HGB DGA candidate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.utils.class_weight import compute_sample_weight

from training.calibrate import fit_sigmoid_calibrator
from training.drift26dsn import LEXICAL_FEATURES
from training.evaluate import classification_metrics
from training.export import export_model_package
from training.safety import require_isolated_training_approval
from training.splits import column_splits, complete_class_grouped_splits
from training.thresholds import derive_class_thresholds
from training.train_common import _matrix

BENIGN = "BENIGN"
DGA = "DGA"
CLASSES = (BENIGN, DGA)
DEFAULT_OUTPUT_DIR = Path("model_artifacts/dns-dga-drift26dsn-hgb-v1")
PARAMETERS = {
    "learning_rate": 0.05,
    "max_iter": 300,
    "max_leaf_nodes": 31,
    "l2_regularization": 1.0,
    "random_state": 42,
}


def _columns(table: pd.DataFrame, feature_set: str) -> list[str]:
    if feature_set == "full":
        columns = sorted(
            column
            for column in table.columns
            if column.startswith("feature__") or column.startswith("available__")
        )
    elif feature_set in {"lexical", "original"}:
        columns = [f"feature__{name}" for name in LEXICAL_FEATURES]
    else:
        raise ValueError("DGA feature_set must be 'full', 'lexical', or 'original'")
    missing = sorted(set(columns) - set(table.columns))
    if missing:
        raise ValueError(f"prepared DGA table is missing model features: {missing}")
    return columns


def _predictions(probabilities, classes: list[str], threshold: float) -> np.ndarray:
    positive_index = classes.index(DGA)
    return np.where(probabilities[:, positive_index] >= threshold, DGA, BENIGN)


def _metrics(labels, probabilities, classes: list[str], threshold: float) -> dict:
    labels_array = np.asarray(labels, dtype=str)
    predictions = _predictions(probabilities, classes, threshold)
    report = classification_metrics(labels_array, predictions, classes)
    matrix = np.asarray(report["confusion_matrix"])
    tn, fp, fn, tp = matrix.ravel()
    positive_index = classes.index(DGA)
    binary = (labels_array == DGA).astype(int)
    return {
        "runtime_acceptance": report,
        "accuracy": float(accuracy_score(labels_array, predictions)),
        "false_positive_rate": float(fp / max(fp + tn, 1)),
        "false_negative_rate": float(fn / max(fn + tp, 1)),
        "average_precision": float(
            average_precision_score(binary, probabilities[:, positive_index])
        ),
        "roc_auc": float(roc_auc_score(binary, probabilities[:, positive_index])),
    }


def _write_hash_manifest(package: Path) -> None:
    hashes = {}
    for path in sorted(package.iterdir()):
        if path.is_file() and path.name != "artifact_sha256.json":
            with path.open("rb") as stream:
                hashes[path.name] = hashlib.file_digest(stream, "sha256").hexdigest()
    (package / "artifact_sha256.json").write_text(
        json.dumps(hashes, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def train(
    input_path: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    *,
    feature_set: str = "lexical",
    isolation_acknowledged: bool = False,
) -> Path:
    """Fit, calibrate, evaluate and export without reading test labels early."""

    require_isolated_training_approval(acknowledged=isolation_acknowledged)
    destination = Path(output_dir)
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"refusing to overwrite existing artifacts: {destination}")
    table = pd.read_parquet(input_path)
    if table.empty:
        raise ValueError("cannot train on an empty prepared DGA table")
    if set(table["family"]) != {"dns"} or set(table["schema_version"]) != {"dns.v1"}:
        raise ValueError("DGA input must contain shared dns.v1 feature rows")
    if set(table["label"]) != set(CLASSES):
        raise ValueError(f"DGA input classes must be exactly {CLASSES}")
    if "split" in table.columns:
        splits = column_splits(table)
        split_seed_values = table.get("split_seed")
        split_seed = (
            int(split_seed_values.iloc[0])
            if split_seed_values is not None and split_seed_values.nunique() == 1
            else None
        )
    else:
        splits, split_seed = complete_class_grouped_splits(table)
    columns = _columns(table, feature_set)
    matrices = {
        role: _matrix(getattr(splits, role), columns)
        for role in ("train", "validation", "calibration", "test")
    }
    estimator = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("classifier", HistGradientBoostingClassifier(**PARAMETERS)),
        ]
    )
    weights = compute_sample_weight("balanced", splits.train["label"])
    estimator.fit(matrices["train"], splits.train["label"], classifier__sample_weight=weights)
    calibrator = fit_sigmoid_calibrator(
        estimator,
        matrices["calibration"],
        splits.calibration["label"],
    )
    classes = [str(label) for label in calibrator.classes_]
    if set(classes) != set(CLASSES):
        raise ValueError(f"calibrator returned unexpected DGA classes: {classes}")
    validation_probabilities = calibrator.predict_proba(matrices["validation"])
    thresholds = derive_class_thresholds(
        splits.validation["label"],
        validation_probabilities,
        classes,
        minimum_precision=0.80,
    )
    dga_threshold = thresholds[DGA]
    validation_metrics = _metrics(
        splits.validation["label"], validation_probabilities, classes, dga_threshold
    )
    test_probabilities = calibrator.predict_proba(matrices["test"])
    test_metrics = _metrics(splits.test["label"], test_probabilities, classes, dga_threshold)
    metrics = {
        "decision_policy": "DGA when calibrated DGA probability reaches the validation-derived threshold; BENIGN otherwise",
        "validation": validation_metrics,
        "internal_test": test_metrics,
        "family_holdout": "DGA family groups are disjoint across all split roles",
        "external_evaluation_performed": False,
    }
    feature_schema = {
        "family": "dns",
        "schema_version": "dns.v1",
        "columns": columns,
        "allow_runtime_feature_superset": True,
        "preprocessing": "shared DNS lexical definitions followed by median imputation",
    }
    roles = ("train", "validation", "calibration", "test")
    manifest = {
        "model_version": destination.name,
        "family": "dns",
        "detector_variant": "dga",
        "schema_version": "dns.v1",
        "model_type": "HistGradientBoostingClassifier",
        "parameters": PARAMETERS,
        "feature_set": feature_set,
        "decision_policy": {
            "strategy": "positive_threshold",
            "positive_class": DGA,
            "negative_class": BENIGN,
        },
        "split_seed": split_seed,
        "split_roles": {
            role: {
                "rows": len(getattr(splits, role)),
                "groups": int(getattr(splits, role)["group_id"].nunique()),
                "classes": {
                    str(label): int(count)
                    for label, count in getattr(splits, role)["label"].value_counts().items()
                },
                "dga_families": int(
                    getattr(splits, role)
                    .loc[getattr(splits, role)["label"] == DGA, "dga_family"]
                    .nunique()
                ),
            }
            for role in roles
        },
        "training_data_sources": sorted(str(name) for name in table["source_name"].unique()),
        "balance_policy": "inverse class-frequency sample weights on training rows",
        "trusted": False,
        "independent_external_evaluation_completed": False,
    }
    package = export_model_package(
        destination,
        estimator=estimator,
        calibrator=calibrator,
        feature_schema=feature_schema,
        classes=classes,
        thresholds=thresholds,
        metrics=metrics,
        manifest=manifest,
    )
    _write_hash_manifest(package)
    return package
