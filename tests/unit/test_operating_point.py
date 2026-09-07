import numpy as np
import pytest

from training.operating_point import select_binary_operating_point, select_dns_operating_point


def test_operating_point_matches_argmax_then_threshold_runtime_logic() -> None:
    labels = np.array(["BENIGN_DNS"] * 4 + ["DNS_TUNNEL"] * 4)
    probabilities = np.array(
        [
            [0.95, 0.05],
            [0.90, 0.10],
            [0.80, 0.20],
            [0.49, 0.51],
            [0.40, 0.60],
            [0.30, 0.70],
            [0.20, 0.80],
            [0.10, 0.90],
        ]
    )

    point = select_dns_operating_point(
        labels,
        probabilities,
        ["BENIGN_DNS", "DNS_TUNNEL"],
        maximum_false_positive_rate=0.0,
        minimum_precision=1.0,
        minimum_recall=0.75,
    )

    assert point.threshold == pytest.approx(0.60)
    assert point.precision == 1.0
    assert point.recall == 1.0
    assert point.false_positive_rate == 0.0
    assert point.meets_constraints


def test_operating_point_rejects_nonfinite_probabilities() -> None:
    with pytest.raises(ValueError, match="finite"):
        select_dns_operating_point(
            ["BENIGN_DNS", "DNS_TUNNEL"],
            [[1.0, 0.0], [np.nan, np.nan]],
            ["BENIGN_DNS", "DNS_TUNNEL"],
        )


def test_binary_operating_point_supports_encrypted_session_contract() -> None:
    labels = np.array(
        ["BENIGN_ENCRYPTED", "BENIGN_ENCRYPTED", "MALICIOUS_ENCRYPTED_SESSION"]
    )
    probabilities = np.array([[0.9, 0.1], [0.8, 0.2], [0.1, 0.9]])
    point = select_binary_operating_point(
        labels,
        probabilities,
        ["BENIGN_ENCRYPTED", "MALICIOUS_ENCRYPTED_SESSION"],
        positive_class="MALICIOUS_ENCRYPTED_SESSION",
        expected_classes={"BENIGN_ENCRYPTED", "MALICIOUS_ENCRYPTED_SESSION"},
    )

    assert point.meets_constraints
    assert point.recall == 1.0


def test_negative_sampling_weight_changes_reported_precision_not_fpr() -> None:
    labels = np.array(["BENIGN_DNS", "BENIGN_DNS", "DNS_TUNNEL", "DNS_TUNNEL"])
    probabilities = np.array([[0.1, 0.9], [0.9, 0.1], [0.1, 0.9], [0.2, 0.8]])
    classes = ["BENIGN_DNS", "DNS_TUNNEL"]

    unweighted = select_dns_operating_point(
        labels,
        probabilities,
        classes,
        maximum_false_positive_rate=1.0,
        minimum_precision=0.0,
        minimum_recall=1.0,
    )
    weighted = select_dns_operating_point(
        labels,
        probabilities,
        classes,
        maximum_false_positive_rate=1.0,
        minimum_precision=0.0,
        minimum_recall=1.0,
        negative_class_weight=8.0,
    )

    assert weighted.recall == unweighted.recall == 1.0
    assert weighted.false_positive_rate == unweighted.false_positive_rate
    assert weighted.precision < unweighted.precision
