"""Shared training path used by all model families (dns, tls_quic, and others).

This module intentionally supports two axes of variation between families
without special-casing any one family by name:

  * split strategy   -- "grouped"  derives train/validation/calibration/test
                         via GroupShuffleSplit on a `group_id` column.
                       -- "column"  reuses a precomputed `split` column already
                         present in the prepared table (e.g. dns).

  * prediction strategy -- "argmax"    uses the calibrator's own decision rule
                            (calibrator.predict()).
                          -- "threshold" applies a derived per-class threshold
                            to the positive class's calibrated probability,
                            falling back to the negative class otherwise
                            (used by dns, where recall/precision are tuned
                            explicitly rather than left to the classifier).

Family/schema validation and the `training_data_sources` manifest field are
both optional, since not every prepared table carries `family`,
`schema_version`, or `source_name` columns.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from training.calibrate import fit_sigmoid_calibrator
from training.evaluate import classification_metrics
from training.export import export_model_package
from training.splits import DatasetSplits, column_splits, grouped_splits
from training.thresholds import derive_class_thresholds

FeatureColumnsFn = Callable[[pd.DataFrame], list[str]]
EstimatorFactory = Callable[[], Any]


def _default_estimator() -> Pipeline:
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=300,
                    class_weight="balanced",
                    n_jobs=-1,
                    random_state=42,
                ),
            ),
        ]
    )


def _default_feature_columns(frame: pd.DataFrame) -> list[str]:
    columns = sorted(
        column
        for column in frame.columns
        if column.startswith("feature__") or column.startswith("available__")
    )
    if not columns:
        raise ValueError("prepared table contains no shared feature columns")
    return columns


def _matrix(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    matrix = frame.loc[:, columns].copy()
    for column in matrix:
        if column.startswith("available__"):
            matrix[column] = matrix[column].astype(float)
        else:
            matrix[column] = pd.to_numeric(matrix[column], errors="coerce")
    return matrix


def _resolve_splits(table: pd.DataFrame, split_strategy: str) -> DatasetSplits:
    if split_strategy == "grouped":
        return grouped_splits(table)
    if split_strategy == "column":
        return column_splits(table)
    raise ValueError(f"unknown split_strategy: {split_strategy!r} (expected 'grouped' or 'column')")


def _resolve_training_data_sources(
    table: pd.DataFrame, training_data_sources: list[str] | None
) -> list[str]:
    if training_data_sources is not None:
        return sorted(training_data_sources)
    if "source_name" in table.columns:
        return sorted(str(name) for name in table["source_name"].unique())
    return []


def _validate_family_schema(table: pd.DataFrame, family: str, schema_version: str) -> None:
    if "family" not in table.columns or "schema_version" not in table.columns:
        raise ValueError(
            "validate_family_schema=True requires 'family' and 'schema_version' columns "
            "in the prepared table; pass validate_family_schema=False for tables that "
            "don't carry these columns"
        )
    if set(table["family"]) != {family} or set(table["schema_version"]) != {schema_version}:
        raise ValueError("input table family/schema does not match requested model family")


def _predict(
    *,
    calibrator: Any,
    test_features: pd.DataFrame,
    classes: list[str],
    thresholds: dict[str, float],
    prediction_strategy: str,
    positive_class: str | None,
    negative_class: str | None,
) -> np.ndarray:
    if prediction_strategy == "argmax":
        return calibrator.predict(test_features)

    if prediction_strategy == "threshold":
        if positive_class is None:
            raise ValueError("prediction_strategy='threshold' requires positive_class")
        if positive_class not in classes:
            raise ValueError(f"positive_class {positive_class!r} not among classes: {classes}")
        resolved_negative = negative_class
        if resolved_negative is None:
            others = [label for label in classes if label != positive_class]
            if len(others) != 1:
                raise ValueError(
                    "prediction_strategy='threshold' requires binary classification "
                    "unless negative_class is given explicitly"
                )
            resolved_negative = others[0]
        class_index = classes.index(positive_class)
        threshold = thresholds[positive_class]
        test_probabilities = calibrator.predict_proba(test_features)
        return np.where(
            test_probabilities[:, class_index] >= threshold,
            positive_class,
            resolved_negative,
        )

    raise ValueError(
        f"unknown prediction_strategy: {prediction_strategy!r} (expected 'argmax' or 'threshold')"
    )


def train_family(
    input_path,
    output_dir,
    *,
    family: str,
    schema_version: str,
    isolation_acknowledged: bool = False,
    estimator_factory: EstimatorFactory = _default_estimator,
    feature_columns: FeatureColumnsFn | None = None,
    split_strategy: str = "grouped",
    validate_family_schema: bool = True,
    prediction_strategy: str = "argmax",
    positive_class: str | None = None,
    negative_class: str | None = None,
    training_data_sources: list[str] | None = None,
    verbose: bool = True,
):
    """Fit, calibrate, evaluate, and export a model family through one shared path.

    Defaults reproduce the original tls_quic behavior exactly: grouped splits,
    a balanced RandomForest, full feature-column autodetection, mandatory
    family/schema validation, argmax prediction, and source_name-derived
    manifest provenance. Families that differ from that shape (e.g. dns, with
    a precomputed split column, a custom estimator, a fixed feature set, and
    threshold-based prediction) opt in via the keyword arguments above rather
    than by branching inside this function.
    """
    from training.safety import require_isolated_training_approval

    require_isolated_training_approval(acknowledged=isolation_acknowledged)

    table = pd.read_parquet(input_path)
    if table.empty:
        raise ValueError("cannot train on an empty prepared table")

    if validate_family_schema:
        _validate_family_schema(table, family, schema_version)

    splits = _resolve_splits(table, split_strategy)

    columns_fn = feature_columns or _default_feature_columns
    columns = columns_fn(table)

    training_features = _matrix(splits.train, columns)
    validation_features = _matrix(splits.validation, columns)
    calibration_features = _matrix(splits.calibration, columns)
    test_features = _matrix(splits.test, columns)

    if verbose:
        print(f"Family: {family}")
        print(f"Features: {len(columns)}")
        print(f"Train: {len(training_features)}")
        print(f"Validation: {len(validation_features)}")
        print(f"Calibration: {len(calibration_features)}")
        print(f"Test: {len(test_features)}")

    estimator = estimator_factory()
    estimator.fit(training_features, splits.train["label"])

    calibrator = fit_sigmoid_calibrator(
        estimator, calibration_features, splits.calibration["label"]
    )
    classes = [str(label) for label in calibrator.classes_]

    validation_probabilities = calibrator.predict_proba(validation_features)
    thresholds = derive_class_thresholds(
        splits.validation["label"], validation_probabilities, classes
    )

    predictions = _predict(
        calibrator=calibrator,
        test_features=test_features,
        classes=classes,
        thresholds=thresholds,
        prediction_strategy=prediction_strategy,
        positive_class=positive_class,
        negative_class=negative_class,
    )
    metrics = classification_metrics(splits.test["label"], predictions, classes)

    feature_schema = {
        "family": family,
        "schema_version": schema_version,
        "columns": columns,
        "preprocessing": "median-imputation plus explicit availability indicators",
    }
    manifest = {
        "family": family,
        "schema_version": schema_version,
        "model_type": type(estimator.named_steps["classifier"]).__name__,
        "split_roles": {
            "train_rows": len(splits.train),
            "validation_rows": len(splits.validation),
            "calibration_rows": len(splits.calibration),
            "test_rows": len(splits.test),
        },
        "training_data_sources": _resolve_training_data_sources(table, training_data_sources),
    }

    output_path = export_model_package(
        output_dir,
        estimator=estimator,
        calibrator=calibrator,
        feature_schema=feature_schema,
        classes=classes,
        thresholds=thresholds,
        metrics=metrics,
        manifest=manifest,
    )

    if verbose:
        print()
        print(json.dumps(metrics, indent=2))

    return output_path
