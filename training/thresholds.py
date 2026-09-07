"""Validation-derived class thresholds."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import precision_recall_curve


def derive_class_thresholds(
    labels, probabilities, classes, minimum_precision: float = 0.80
) -> dict[str, float]:
    if not 0 < minimum_precision <= 1:
        raise ValueError("minimum_precision must be in (0, 1]")

    thresholds: dict[str, float] = {}

    for column, class_name in enumerate(classes):
        binary_labels = np.asarray(labels) == class_name

        if binary_labels.sum() == 0:
            raise ValueError(f"validation split contains no examples of class {class_name!r}")

        precision, recall, values = precision_recall_curve(
            binary_labels,
            probabilities[:, column],
        )

        f1 = 2 * precision[:-1] * recall[:-1] / np.maximum(precision[:-1] + recall[:-1], 1e-12)

        eligible = np.flatnonzero(precision[:-1] >= minimum_precision)

        if not len(eligible):
            raise ValueError(
                f"no validation threshold for {class_name!r} reaches precision {minimum_precision}"
            )

        best = eligible[np.argmax(f1[eligible])]
        thresholds[str(class_name)] = float(values[best])

    return thresholds
