"""Strict, versioned artifact loading and NumPy batch inference."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import joblib
import numpy as np

from custodian.core.enums import ThreatClass
from custodian.core.schemas import FeatureVector
from custodian.features.behaviour_flow import FLOW_DEFINITION_ID, FLOW_MODEL_FEATURES
from custodian.models.calibrator import MulticlassSigmoidCalibrator
from custodian.models.compatibility import validate_feature_compatibility


@dataclass(frozen=True, slots=True)
class LoadedModelPackage:
    directory: Path
    estimator: object
    calibrator: object
    feature_schema: dict
    classes: tuple[str, ...]
    thresholds: dict[str, float]
    manifest: dict

    @property
    def model_version(self) -> str:
        return str(self.manifest.get("model_version", self.directory.name))

    def _decision_index(self, probabilities: np.ndarray) -> int:
        """Apply the artifact's declared evaluation-time decision rule at runtime."""

        policy = self.manifest.get("decision_policy", {"strategy": "argmax"})
        strategy = policy.get("strategy", "argmax")
        argmax_index = int(np.argmax(probabilities))
        if strategy == "argmax":
            return argmax_index
        positive = str(policy["positive_class"])
        negative = str(policy["negative_class"])
        positive_index = self.classes.index(positive)
        negative_index = self.classes.index(negative)
        above_threshold = probabilities[positive_index] >= self.thresholds[positive]
        if strategy == "positive_threshold":
            return positive_index if above_threshold else negative_index
        if strategy == "argmax_and_threshold":
            return positive_index if argmax_index == positive_index and above_threshold else negative_index
        raise ValueError(f"unsupported model decision strategy: {strategy!r}")

    def predict_batch(self, vectors: list[FeatureVector]) -> list[tuple]:
        if not vectors:
            return []
        started = perf_counter()
        columns = self.feature_schema["columns"]
        rows = []
        for vector in vectors:
            validate_feature_compatibility(vector, self.feature_schema)
            rows.append(
                [
                    vector.values.get(column.removeprefix("feature__"))
                    if column.startswith("feature__")
                    else vector.availability[column.removeprefix("available__")]
                    for column in columns
                ]
            )
        matrix = np.asarray(rows, dtype=np.float32)
        if isinstance(self.calibrator, MulticlassSigmoidCalibrator):
            raw = self.estimator.predict_proba(matrix)
            calibrated = self.calibrator.transform(raw)
        else:
            import pandas as pd

            features = pd.DataFrame(matrix, columns=columns)
            raw = self.estimator.predict_proba(features)
            calibrated = self.calibrator.predict_proba(features)
        if raw.shape != calibrated.shape or raw.shape != (len(vectors), len(self.classes)):
            raise ValueError("model/calibrator returned incompatible probability shapes")
        if not np.isfinite(calibrated).all() or not np.isfinite(raw).all():
            raise ValueError("model returned nonfinite probabilities")
        elapsed_per_vector = (perf_counter() - started) * 1000 / len(vectors)
        results = []
        for raw_row, row in zip(raw, calibrated, strict=True):
            index = self._decision_index(row)
            results.append(
                (
                    self.classes[index],
                    float(raw_row[index]),
                    float(row[index]),
                    dict(zip(self.classes, map(float, row), strict=True)),
                    elapsed_per_vector,
                )
            )
        return results

    def predict(self, vector: FeatureVector) -> tuple:
        return self.predict_batch([vector])[0]


def _read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"required model artifact file is missing: {path}")
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError(f"artifact must be a JSON object: {path.name}")
    return result


def _verify_external_hash_manifest(directory: Path, required_files: set[str]) -> None:
    """Verify generic artifacts before any joblib deserialization occurs."""

    hashes = _read_json(directory / "artifact_sha256.json")
    if not required_files.issubset(hashes):
        missing = sorted(required_files - set(hashes))
        raise ValueError(f"artifact hash manifest is missing required files: {missing}")
    for name, expected in hashes.items():
        if Path(name).name != name or not isinstance(expected, str):
            raise ValueError("artifact hash manifest contains an invalid entry")
        path = directory / name
        if not path.is_file():
            raise FileNotFoundError(f"hashed artifact file is missing: {path}")
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected:
            raise ValueError(f"artifact integrity mismatch: {name}")


def load_model_package(path: str | Path) -> LoadedModelPackage:
    directory = Path(path)
    if not directory.is_dir():
        raise FileNotFoundError(f"model artifact directory does not exist: {directory}")
    feature_schema = _read_json(directory / "feature_schema.json")
    thresholds = _read_json(directory / "thresholds.json")
    manifest = _read_json(directory / "manifest.json")
    _read_json(directory / "metrics.json")
    is_xgb = manifest.get("artifact_format") == "custodian.xgboost_package.v1"
    if is_xgb:
        expected_files = {
            "model.json",
            "calibrator.joblib",
            "feature_schema.json",
            "class_mapping.json",
            "thresholds.json",
            "metrics.json",
        }
        hashes = manifest.get("artifact_sha256", {})
        if set(hashes) != expected_files:
            raise ValueError("manifest is missing the complete artifact hash set")
        for name, expected in hashes.items():
            with (directory / name).open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                    raise ValueError(f"artifact integrity mismatch: {name}")
        classes = tuple(_read_json(directory / "class_mapping.json").get("classes", []))
        if classes != ("BENIGN", "DDOS", "RECON", "BOT_OR_C2_LIKE"):
            raise ValueError("Behaviour class mapping must match the approved four-class prototype")
        if (
            feature_schema.get("definition_id") != FLOW_DEFINITION_ID
            or feature_schema.get("family") != "behaviour"
            or feature_schema.get("schema_version") != "behaviour.v1"
            or feature_schema.get("columns") != [f"feature__{name}" for name in FLOW_MODEL_FEATURES]
        ):
            raise ValueError("incompatible shared behaviour feature definitions")
        from xgboost import XGBClassifier

        estimator = XGBClassifier()
        estimator.load_model(directory / "model.json")
        # Small runtime batches should not start a full laptop-sized thread pool.
        estimator.set_params(n_jobs=1)
        calibrator = joblib.load(directory / "calibrator.joblib")
        if not isinstance(calibrator, MulticlassSigmoidCalibrator) or len(calibrator.models) != len(
            classes
        ):
            raise ValueError("unsupported or incomplete Behaviour calibrator")
        if estimator.n_features_in_ != len(feature_schema["columns"]):
            raise ValueError("model feature count disagrees with schema")
    else:
        _verify_external_hash_manifest(
            directory,
            {
                "model.joblib",
                "calibrator.joblib",
                "feature_schema.json",
                "classes.json",
                "thresholds.json",
                "metrics.json",
                "manifest.json",
            },
        )
        classes = tuple(_read_json(directory / "classes.json").get("classes", []))
        estimator = joblib.load(directory / "model.joblib")
        calibrator = joblib.load(directory / "calibrator.joblib")
        if (
            tuple(map(str, estimator.classes_)) != classes
            or tuple(map(str, calibrator.classes_)) != classes
        ):
            raise ValueError("model and calibrator class ordering differs from metadata")
    if not classes or len(set(classes)) != len(classes) or set(thresholds) != set(classes):
        raise ValueError("class mapping and thresholds must be complete and consistent")
    for name in classes:
        ThreatClass(name)
        value = float(thresholds[name])
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"invalid class threshold for {name}")
    decision_policy = manifest.get("decision_policy", {"strategy": "argmax"})
    if not isinstance(decision_policy, dict):
        raise ValueError("model decision_policy must be an object")
    strategy = decision_policy.get("strategy", "argmax")
    if strategy not in {"argmax", "positive_threshold", "argmax_and_threshold"}:
        raise ValueError(f"unsupported model decision strategy: {strategy!r}")
    if strategy != "argmax":
        positive = decision_policy.get("positive_class")
        negative = decision_policy.get("negative_class")
        if len(classes) != 2 or positive not in classes or negative not in classes:
            raise ValueError(
                "threshold decision policies require two distinct artifact classes"
            )
        if positive == negative:
            raise ValueError("positive and negative decision classes must differ")
    return LoadedModelPackage(
        directory,
        estimator,
        calibrator,
        feature_schema,
        classes,
        {name: float(value) for name, value in thresholds.items()},
        manifest,
    )
