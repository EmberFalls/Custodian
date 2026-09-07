"""CLI-facing prepare/train orchestration shared by the Custodian entrypoint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from training.prepare import write_feature_table
from training.safety import require_isolated_training_approval
from training.splits import complete_class_grouped_splits

FAMILY_ALIASES = {
    "behaviour": "behaviour",
    "behavior": "behaviour",
    "dns": "dns",
    "tls_quic": "tls_quic",
    "encrypted-session": "tls_quic",
    "encrypted_session": "tls_quic",
}


def normalize_family(family: str) -> str:
    key = family.strip().lower().replace(" ", "-")
    if key not in FAMILY_ALIASES:
        raise ValueError(
            f"unknown family {family!r}; expected one of: "
            "behaviour|behavior, dns, tls_quic|encrypted-session"
        )
    return FAMILY_ALIASES[key]


def _write_json(path: Path, content: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(content, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )


def _attach_splits(table):
    splits, split_seed = complete_class_grouped_splits(table)
    roles = {
        role: getattr(splits, role) for role in ("train", "validation", "calibration", "test")
    }
    role_map = {
        group: role for role, part in roles.items() for group in part["group_id"].unique()
    }
    table = table.copy()
    table["split"] = table["group_id"].map(role_map)
    split_counts = {
        role: {
            "rows": len(part),
            "groups": int(part["group_id"].nunique()),
            "classes": part["label"].value_counts().to_dict(),
        }
        for role, part in roles.items()
    }
    return table, split_seed, split_counts


def prepare_data(
    *,
    family: str,
    data_dir: str | Path,
    output_path: str | Path,
    isolation_acknowledged: bool = False,
    max_rows_per_class: int | None = None,
    manifest_path: str | Path | None = None,
) -> Path:
    """Prepare a versioned feature table for one model family."""

    require_isolated_training_approval(acknowledged=isolation_acknowledged)
    resolved = normalize_family(family)
    data_dir = Path(data_dir)
    output = Path(output_path)

    if resolved == "dns":
        from training.drift26dsn import prepare_drift26dsn

        table, provenance = prepare_drift26dsn(
            data_dir,
            max_rows_per_class=max_rows_per_class,
        )
    elif resolved == "behaviour":
        from training.cicids2017 import prepare_cicids2017

        table, provenance = prepare_cicids2017(data_dir)
    else:
        raise ValueError(
            "tls_quic/encrypted-session preparation is not implemented yet; "
            "provide a prepared Parquet table and use `custodian train tls_quic`"
        )

    table, split_seed, split_counts = _attach_splits(table)
    written = write_feature_table(table, output)
    report = {
        **provenance,
        "family": resolved,
        "splits": split_counts,
        "split_seed": split_seed,
        "processed_table": str(written.resolve()),
    }
    report_path = (
        Path(manifest_path)
        if manifest_path is not None
        else Path("data/manifests") / f"{written.stem}.json"
    )
    _write_json(report_path, report)
    print(json.dumps({"prepared_table": str(written), "manifest": str(report_path)}, indent=2))
    return written


def train_model(
    *,
    family: str,
    isolation_acknowledged: bool = False,
    data_dir: str | Path | None = None,
    input_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    feature_set: str = "full",
    n_jobs: int | None = None,
    prepare_only: bool = False,
) -> Path:
    """Train one model family through the shared training modules."""

    require_isolated_training_approval(acknowledged=isolation_acknowledged)
    resolved = normalize_family(family)

    if resolved == "dns":
        from training import train_dns

        if input_path is None:
            raise ValueError("dns training requires --input-path to a prepared Parquet table")
        return train_dns.train(
            input_path=input_path,
            output_dir=output_dir or train_dns.DEFAULT_OUTPUT_DIR,
            feature_set=feature_set,
            isolation_acknowledged=True,
        )

    if resolved == "behaviour":
        from training import train_behaviour

        if data_dir is None:
            raise ValueError("behaviour training requires --data-dir with CICIDS2017 CSVs")
        return train_behaviour.train(
            data_dir,
            output_dir or Path("model_artifacts/behaviour-xgb-v1"),
            n_jobs=n_jobs,
            processed_path=input_path,
            prepare_only=prepare_only,
            isolation_acknowledged=True,
        )

    from training import train_tls_quic

    if input_path is None:
        raise ValueError("tls_quic training requires --input-path to a prepared Parquet table")
    return train_tls_quic.train(
        input_path,
        output_dir or Path("model_artifacts/tls-quic-v1"),
        isolation_acknowledged=True,
    )
