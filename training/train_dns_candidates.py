"""Compare calibrated DNS classifiers without touching either external holdout."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline

from training.calibrate import fit_sigmoid_calibrator
from training.evaluate import classification_metrics
from training.export import export_model_package
from training.operating_point import OperatingPoint, select_dns_operating_point
from training.safety import require_isolated_training_approval
from training.splits import complete_class_grouped_splits
from training.train_common import _matrix

TARGET_MAXIMUM_FALSE_POSITIVE_RATE = 0.0005
TARGET_MINIMUM_PRECISION = 0.90
TARGET_MINIMUM_RECALL = 0.80
CTU_DEVELOPMENT_SOURCE = "train_combined_multiclass.csv.gz"
CTU_BENIGN_SAMPLE_WEIGHT = 8.0
ROBUST_DNS_FEATURES = (
    "character_entropy",
    "digit_ratio",
    "domain_length",
    "hyphen_ratio",
    "letter_ratio",
    "mean_label_length",
    "repeated_character_ratio",
    "subdomain_count",
    *(f"bigram_bucket_{bucket}" for bucket in range(8)),
)
ROBUST_DNS_COLUMNS = tuple(f"feature__{name}" for name in ROBUST_DNS_FEATURES)


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
                n_estimators=300,
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
        "random_forest": _pipeline(
            RandomForestClassifier(
                n_estimators=300,
                min_samples_leaf=2,
                n_jobs=-1,
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


def _source_family(frame: pd.DataFrame) -> pd.Series:
    return frame["source_name"].map(
        lambda name: "ctu_dns_threats_train"
        if str(name) == CTU_DEVELOPMENT_SOURCE
        else "bccc_dns_exf"
    )


def _runtime_predictions(probabilities, classes, threshold: float) -> np.ndarray:
    positive_index = classes.index("DNS_TUNNEL")
    argmax = np.asarray(classes)[np.argmax(probabilities, axis=1)]
    return np.where(
        (argmax == "DNS_TUNNEL") & (probabilities[:, positive_index] >= threshold),
        "DNS_TUNNEL",
        "BENIGN_DNS",
    )


def _source_reports(frame, probabilities, classes, threshold: float) -> dict[str, dict]:
    reports = {}
    families = _source_family(frame)
    for family in sorted(families.unique()):
        selected = families == family
        reports[str(family)] = classification_metrics(
            frame.loc[selected, "label"],
            _runtime_predictions(probabilities[selected], classes, threshold),
            classes,
        )
    return reports


def _source_class_balanced_weights(frame: pd.DataFrame) -> np.ndarray:
    strata = _source_family(frame).astype(str) + "\0" + frame["label"].astype(str)
    counts = strata.value_counts()
    return strata.map(lambda value: len(strata) / (len(counts) * counts[value])).to_numpy()


def train(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    isolation_acknowledged: bool = False,
) -> Path:
    """Select on validation data, evaluate the winner once on internal test data."""

    require_isolated_training_approval(acknowledged=isolation_acknowledged)
    table = pd.read_parquet(input_path)
    if table.empty:
        raise ValueError("cannot train on an empty prepared table")
    if set(table["family"]) != {"dns"} or set(table["schema_version"]) != {"dns.v1"}:
        raise ValueError("candidate input must contain shared dns.v1 features only")
    splits, split_seed = complete_class_grouped_splits(table)
    columns = list(ROBUST_DNS_COLUMNS)
    missing = sorted(set(columns) - set(table.columns))
    if missing:
        raise ValueError(f"prepared DNS table is missing robust lexical features: {missing}")
    matrices = {
        "train": _matrix(splits.train, columns),
        "validation": _matrix(splits.validation, columns),
        "calibration": _matrix(splits.calibration, columns),
        "test": _matrix(splits.test, columns),
    }
    reports = {}
    fitted = {}
    if CTU_DEVELOPMENT_SOURCE not in set(table["source_name"]):
        raise ValueError("improved DNS training requires the official CTU development split")
    training_weights = _source_class_balanced_weights(splits.train)
    calibration_is_ctu = _source_family(splits.calibration) == "ctu_dns_threats_train"
    validation_is_ctu = _source_family(splits.validation) == "ctu_dns_threats_train"
    calibration_frame = splits.calibration.loc[calibration_is_ctu]
    validation_frame = splits.validation.loc[validation_is_ctu]
    if set(calibration_frame["label"]) != {"BENIGN_DNS", "DNS_TUNNEL"}:
        raise ValueError("CTU calibration partition does not contain both DNS classes")
    if set(validation_frame["label"]) != {"BENIGN_DNS", "DNS_TUNNEL"}:
        raise ValueError("CTU validation partition does not contain both DNS classes")
    for name, estimator in _candidates().items():
        estimator.fit(
            matrices["train"],
            splits.train["label"],
            classifier__sample_weight=training_weights,
        )
        calibrator = fit_sigmoid_calibrator(
            estimator,
            _matrix(calibration_frame, columns),
            calibration_frame["label"],
        )
        classes = [str(label) for label in calibrator.classes_]
        probabilities = calibrator.predict_proba(_matrix(validation_frame, columns))
        positive_index = classes.index("DNS_TUNNEL")
        positives = (validation_frame["label"].to_numpy() == "DNS_TUNNEL").astype(int)
        point = select_dns_operating_point(
            validation_frame["label"],
            probabilities,
            classes,
            maximum_false_positive_rate=TARGET_MAXIMUM_FALSE_POSITIVE_RATE,
            minimum_precision=TARGET_MINIMUM_PRECISION,
            minimum_recall=TARGET_MINIMUM_RECALL,
            negative_class_weight=CTU_BENIGN_SAMPLE_WEIGHT,
        )
        all_validation_probabilities = calibrator.predict_proba(matrices["validation"])
        reports[name] = {
            "operating_point": _point_dict(point),
            "operating_point_source": "official CTU training split validation partition",
            "negative_prevalence_correction": CTU_BENIGN_SAMPLE_WEIGHT,
            "average_precision": float(
                average_precision_score(positives, probabilities[:, positive_index])
            ),
            "roc_auc": float(roc_auc_score(positives, probabilities[:, positive_index])),
            "validation_by_source_family": _source_reports(
                splits.validation,
                all_validation_probabilities,
                classes,
                point.threshold,
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
    runtime_predictions = _runtime_predictions(test_probabilities, classes, point.threshold)
    metrics = {
        "selected_candidate": selected_name,
        "selection_basis": "validation-only runtime operating point",
        "candidate_validation_reports": reports,
        "internal_test": classification_metrics(
            splits.test["label"], runtime_predictions, classes
        ),
        "internal_test_by_source_family": _source_reports(
            splits.test,
            test_probabilities,
            classes,
            point.threshold,
        ),
        "external_evaluation_performed": False,
    }
    thresholds = {
        # The Evidence Gate returns before thresholding benign classes. Keep the
        # package mapping complete without inventing a benign acceptance metric.
        "BENIGN_DNS": 0.0,
        "DNS_TUNNEL": point.threshold,
    }
    feature_schema = {
        "family": "dns",
        "schema_version": "dns.v1",
        "columns": columns,
        "allow_runtime_feature_superset": True,
        "preprocessing": (
            "median-imputation over universally observable lexical dns.v1 features; "
            "source availability, query type, and temporal history are excluded"
        ),
    }
    manifest = {
        "family": "dns",
        "schema_version": "dns.v1",
        "model_type": type(estimator.named_steps["classifier"]).__name__,
        "candidate_selection": selected_name,
        "split_seed": split_seed,
        "acceptance_targets": {
            "maximum_false_positive_rate": TARGET_MAXIMUM_FALSE_POSITIVE_RATE,
            "minimum_precision": TARGET_MINIMUM_PRECISION,
            "minimum_recall": TARGET_MINIMUM_RECALL,
        },
        "validation_target_met": point.meets_constraints,
        "selection_domain": "CTU official training split only; test split excluded",
        "source_class_weighting": "equal total fit weight per source-family and class stratum",
        "non_alert_threshold_policy": {
            "BENIGN_DNS": "0.0 sentinel; benign verdicts never generate alerts"
        },
        "split_roles": {
            "train_rows": len(splits.train),
            "validation_rows": len(splits.validation),
            "calibration_rows": len(splits.calibration),
            "test_rows": len(splits.test),
        },
        "split_group_counts": {
            "train": int(splits.train["group_id"].nunique()),
            "validation": int(splits.validation["group_id"].nunique()),
            "calibration": int(splits.calibration["group_id"].nunique()),
            "test": int(splits.test["group_id"].nunique()),
        },
        "training_data_sources": sorted(str(name) for name in table["source_name"].unique()),
    }
    return export_model_package(
        output_dir,
        estimator=estimator,
        calibrator=calibrator,
        feature_schema=feature_schema,
        classes=classes,
        thresholds=thresholds,
        metrics=metrics,
        manifest=manifest,
    )
