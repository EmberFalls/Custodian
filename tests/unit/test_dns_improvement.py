import pandas as pd

from training.train_dns_candidates import (
    ROBUST_DNS_COLUMNS,
    _source_class_balanced_weights,
)


def test_robust_dns_columns_exclude_source_specific_metadata() -> None:
    assert ROBUST_DNS_COLUMNS
    assert all(column.startswith("feature__") for column in ROBUST_DNS_COLUMNS)
    assert not any("query_type" in column for column in ROBUST_DNS_COLUMNS)
    assert not any("query_frequency" in column for column in ROBUST_DNS_COLUMNS)
    assert not any("unique_domain_ratio" in column for column in ROBUST_DNS_COLUMNS)
    assert not any(column.startswith("available__") for column in ROBUST_DNS_COLUMNS)


def test_source_class_weighting_gives_each_stratum_equal_total_weight() -> None:
    frame = pd.DataFrame(
        {
            "source_name": [
                "train_combined_multiclass.csv.gz",
                "train_combined_multiclass.csv.gz",
                "train_combined_multiclass.csv.gz",
                "bccc.csv",
                "bccc.csv",
                "bccc.csv",
                "bccc.csv",
            ],
            "label": [
                "BENIGN_DNS",
                "BENIGN_DNS",
                "DNS_TUNNEL",
                "BENIGN_DNS",
                "DNS_TUNNEL",
                "DNS_TUNNEL",
                "DNS_TUNNEL",
            ],
        }
    )
    frame["weight"] = _source_class_balanced_weights(frame)
    frame["source_family"] = frame["source_name"].map(
        lambda name: "ctu" if name == "train_combined_multiclass.csv.gz" else "bccc"
    )

    totals = frame.groupby(["source_family", "label"])["weight"].sum()

    assert totals.max() == totals.min()
