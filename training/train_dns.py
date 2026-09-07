"""Train the DNS DGA family from a prepared engineered-feature Parquet table.

Invoked by `custodian train dns` via training.commands; not a standalone entrypoint.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from training.train_common import train_family

INPUT_PATH = Path("data/processed/dns_dga_t17_1m_engineered.parquet")
DEFAULT_OUTPUT_DIR = Path("model_artifacts/dns-dga-t17-1m-hgb")

ORIGINAL_FEATURES = [
    "feature__domain_length",
    "feature__subdomain_count",
    "feature__mean_label_length",
    "feature__character_entropy",
    "feature__digit_ratio",
    "feature__letter_ratio",
    "feature__hyphen_ratio",
    "feature__repeated_character_ratio",
    "feature__query_type",
    "feature__query_frequency",
    "feature__unique_domain_ratio",
    "feature__bigram_bucket_0",
    "feature__bigram_bucket_1",
    "feature__bigram_bucket_2",
    "feature__bigram_bucket_3",
    "feature__bigram_bucket_4",
    "feature__bigram_bucket_5",
    "feature__bigram_bucket_6",
    "feature__bigram_bucket_7",
]

TOP12_FEATURES = [
    "feature__consonant_to_vowel_transitions",
    "feature__longest_label_length",
    "feature__vowel_to_consonant_transitions",
    "feature__letter_ratio",
    "feature__mean_label_length",
    "feature__vowel_ratio",
    "feature__hyphen_ratio",
    "feature__max_letter_run",
    "feature__digit_to_letter_transitions",
    "feature__character_entropy",
    "feature__hex_character_ratio",
    "feature__domain_length",
]


def select_columns(table: pd.DataFrame, feature_set: str) -> list[str]:
    if feature_set == "original":
        columns = ORIGINAL_FEATURES
    elif feature_set == "top12":
        columns = TOP12_FEATURES
    else:
        columns = [
            column
            for column in table.columns
            if column.startswith("feature__") or column.startswith("available__")
        ]
    missing = [column for column in columns if column not in table.columns]
    if missing:
        raise ValueError(f"requested feature set is missing columns: {missing}")
    return columns


def _build_estimator() -> Pipeline:
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            (
                "classifier",
                HistGradientBoostingClassifier(
                    max_iter=300,
                    learning_rate=0.05,
                    max_leaf_nodes=31,
                    random_state=42,
                ),
            ),
        ]
    )


def train(
    input_path: str | Path = INPUT_PATH,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    *,
    feature_set: str = "full",
    isolation_acknowledged: bool = False,
) -> Path:
    return train_family(
        input_path,
        output_dir,
        family="dns",
        schema_version="dns.v1",
        isolation_acknowledged=isolation_acknowledged,
        estimator_factory=_build_estimator,
        feature_columns=lambda table: select_columns(table, feature_set),
        split_strategy="column",
        validate_family_schema=False,
        prediction_strategy="threshold",
        positive_class="DGA",
        negative_class="BENIGN",
        training_data_sources=["DRIFT26DSN"],
    )
