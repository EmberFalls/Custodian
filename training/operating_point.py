"""Validation-only DNS operating-point selection matching runtime decisions."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class OperatingPoint:
    threshold: float
    precision: float
    recall: float
    false_positive_rate: float
    false_negative_rate: float
    meets_constraints: bool


def _rates(labels: np.ndarray, predicted: np.ndarray, positive_class: str) -> tuple[float, ...]:
    positive = labels == positive_class
    predicted_positive = predicted == positive_class
    tp = int(np.sum(positive & predicted_positive))
    fp = int(np.sum(~positive & predicted_positive))
    fn = int(np.sum(positive & ~predicted_positive))
    tn = int(np.sum(~positive & ~predicted_positive))
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    false_positive_rate = fp / max(fp + tn, 1)
    false_negative_rate = fn / max(fn + tp, 1)
    return precision, recall, false_positive_rate, false_negative_rate


def select_dns_operating_point(
    labels,
    probabilities,
    classes,
    *,
    maximum_false_positive_rate: float = 0.01,
    minimum_precision: float = 0.90,
    minimum_recall: float = 0.80,
    negative_class_weight: float = 1.0,
) -> OperatingPoint:
    """Select using validation labels only and the exact runtime acceptance logic.

    Custodian first chooses the calibrated argmax class, then requires that a
    threat-class confidence meet its threshold. Candidate thresholds therefore
    never turn an argmax-benign observation into an alert.
    """

    return select_binary_operating_point(
        labels,
        probabilities,
        classes,
        positive_class="DNS_TUNNEL",
        expected_classes={"BENIGN_DNS", "DNS_TUNNEL"},
        maximum_false_positive_rate=maximum_false_positive_rate,
        minimum_precision=minimum_precision,
        minimum_recall=minimum_recall,
        negative_class_weight=negative_class_weight,
    )


def select_binary_operating_point(
    labels,
    probabilities,
    classes,
    *,
    positive_class: str,
    expected_classes: set[str] | frozenset[str] | None = None,
    maximum_false_positive_rate: float = 0.01,
    minimum_precision: float = 0.90,
    minimum_recall: float = 0.80,
    negative_class_weight: float = 1.0,
) -> OperatingPoint:
    """Select a threshold using the runtime's argmax-then-threshold policy."""

    labels_array = np.asarray(labels, dtype=str)
    probabilities_array = np.asarray(probabilities, dtype=float)
    class_names = tuple(map(str, classes))
    expected = set(expected_classes or class_names)
    if len(class_names) != 2 or set(class_names) != expected or positive_class not in expected:
        raise ValueError("binary operating-point classes do not match the declared contract")
    if probabilities_array.shape != (len(labels_array), 2):
        raise ValueError("probability matrix does not match labels and DNS classes")
    if not np.isfinite(probabilities_array).all():
        raise ValueError("probabilities must be finite")
    if set(labels_array) != set(class_names):
        raise ValueError("validation labels must contain both approved DNS classes")
    if not 0 <= maximum_false_positive_rate <= 1:
        raise ValueError("maximum_false_positive_rate must be between zero and one")
    if not 0 <= minimum_precision <= 1 or not 0 <= minimum_recall <= 1:
        raise ValueError("minimum precision and recall must be between zero and one")
    if not np.isfinite(negative_class_weight) or negative_class_weight <= 0:
        raise ValueError("negative_class_weight must be a positive finite value")

    positive_index = class_names.index(positive_class)
    positive_scores = probabilities_array[:, positive_index]
    argmax = np.asarray(class_names)[np.argmax(probabilities_array, axis=1)]
    eligible = argmax == positive_class
    eligible_scores = positive_scores[eligible]
    eligible_positive = labels_array[eligible] == positive_class
    total_positive = int(np.sum(labels_array == positive_class))
    total_negative = len(labels_array) - total_positive
    candidates: list[OperatingPoint] = []
    if not len(eligible_scores):
        return OperatingPoint(1.0, 0.0, 0.0, 0.0, 1.0, False)
    order = np.argsort(-eligible_scores, kind="stable")
    sorted_scores = eligible_scores[order]
    sorted_positive = eligible_positive[order]
    cumulative_true_positive = np.cumsum(sorted_positive)
    cumulative_false_positive = np.cumsum(~sorted_positive)
    boundaries = np.flatnonzero(
        np.r_[sorted_scores[:-1] != sorted_scores[1:], True]
    )
    for index in boundaries:
        tp = int(cumulative_true_positive[index])
        fp = int(cumulative_false_positive[index])
        fn = total_positive - tp
        weighted_fp = fp * negative_class_weight
        precision = tp / max(tp + weighted_fp, 1)
        recall = tp / max(total_positive, 1)
        fpr = weighted_fp / max(total_negative * negative_class_weight, 1)
        fnr = fn / max(total_positive, 1)
        candidates.append(
            OperatingPoint(
                threshold=float(sorted_scores[index]),
                precision=precision,
                recall=recall,
                false_positive_rate=fpr,
                false_negative_rate=fnr,
                meets_constraints=(
                    fpr <= maximum_false_positive_rate
                    and precision >= minimum_precision
                    and recall >= minimum_recall
                ),
            )
        )

    feasible = [
        point
        for point in candidates
        if point.false_positive_rate <= maximum_false_positive_rate
        and point.precision >= minimum_precision
    ]
    pool = feasible or [
        point
        for point in candidates
        if point.false_positive_rate <= maximum_false_positive_rate
    ]
    pool = pool or candidates
    return max(
        pool,
        key=lambda point: (
            point.recall,
            point.precision,
            -point.false_positive_rate,
            point.threshold,
        ),
    )
