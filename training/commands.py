"""Safety-gated CLI orchestration for DGA preparation and training."""

from __future__ import annotations

import json
from pathlib import Path

from training.drift26dsn import prepare_drift26dsn
from training.prepare import write_feature_table
from training.safety import require_isolated_training_approval
from training.splits import complete_class_grouped_splits
from training.train_dga import DEFAULT_OUTPUT_DIR, train


def prepare_dga(
    data_dir: str | Path,
    output_path: str | Path,
    *,
    manifest_path: str | Path | None = None,
    max_rows_per_class: int | None = None,
    isolation_acknowledged: bool = False,
) -> Path:
    require_isolated_training_approval(acknowledged=isolation_acknowledged)
    output = Path(output_path)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite prepared data: {output}")
    table, provenance = prepare_drift26dsn(
        data_dir,
        max_rows_per_class=max_rows_per_class,
    )
    splits, split_seed = complete_class_grouped_splits(table)
    roles = ("train", "validation", "calibration", "test")
    role_by_group = {
        group_id: role
        for role in roles
        for group_id in getattr(splits, role)["group_id"].unique()
    }
    table["split"] = table["group_id"].map(role_by_group)
    table["split_seed"] = split_seed
    written = write_feature_table(table, output)
    split_report = {
        role: {
            "rows": len(getattr(splits, role)),
            "groups": int(getattr(splits, role)["group_id"].nunique()),
            "classes": {
                str(label): int(count)
                for label, count in getattr(splits, role)["label"].value_counts().items()
            },
            "dga_families": int(
                getattr(splits, role)
                .loc[getattr(splits, role)["label"] == "DGA", "dga_family"]
                .nunique()
            ),
        }
        for role in roles
    }
    report = {
        **provenance,
        "split_seed": split_seed,
        "splits": split_report,
        "processed_table": str(written.resolve()),
    }
    report_path = (
        Path(manifest_path)
        if manifest_path is not None
        else Path("data/manifests") / f"{written.stem}.json"
    )
    if report_path.exists():
        raise FileExistsError(f"refusing to overwrite preparation manifest: {report_path}")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    return written


def train_dga(
    input_path: str | Path,
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    feature_set: str = "lexical",
    isolation_acknowledged: bool = False,
) -> Path:
    return train(
        input_path,
        output_dir,
        feature_set=feature_set,
        isolation_acknowledged=isolation_acknowledged,
    )
