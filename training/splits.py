"""Group-aware TRAIN/VALIDATION/CALIBRATION/TEST splitting."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit


@dataclass(frozen=True, slots=True)
class DatasetSplits:
    train: pd.DataFrame
    validation: pd.DataFrame
    calibration: pd.DataFrame
    test: pd.DataFrame


def _split(
    frame: pd.DataFrame, test_size: float, random_state: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    groups = frame["group_id"]
    if groups.nunique() < 2:
        raise ValueError("group-aware splitting requires at least two unique groups")
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    left_index, right_index = next(splitter.split(frame, groups=groups))
    return frame.iloc[left_index].copy(), frame.iloc[right_index].copy()


def grouped_splits(frame: pd.DataFrame, random_state: int = 42) -> DatasetSplits:
    """Create non-overlapping group splits with explicit evaluation roles."""

    if "group_id" not in frame or "label" not in frame:
        raise ValueError("prepared data requires group_id and label columns")
    train, held_out = _split(frame, test_size=0.30, random_state=random_state)
    validation, remaining = _split(held_out, test_size=2 / 3, random_state=random_state + 1)
    calibration, test = _split(remaining, test_size=0.50, random_state=random_state + 2)
    sets = (train, validation, calibration, test)
    group_sets = [set(part["group_id"]) for part in sets]
    if any(
        group_sets[left] & group_sets[right] for left in range(4) for right in range(left + 1, 4)
    ):
        raise RuntimeError("group leakage detected while splitting")
    return DatasetSplits(train=train, validation=validation, calibration=calibration, test=test)


def complete_class_grouped_splits(
    frame: pd.DataFrame,
    seed: int = 42,
    *,
    search_attempts: int = 10_000,
):
    """Choose a deterministic, class-balanced partition of whole groups.

    Candidate partitions are scored from group sizes and labels only. Features and
    model outputs are never read, and every group remains wholly within one role.
    This avoids accepting the first technically complete split when one calibration
    class is represented by only a handful of rows.
    """

    if "group_id" not in frame or "label" not in frame:
        raise ValueError("prepared data requires group_id and label columns")
    if search_attempts <= 0:
        raise ValueError("search_attempts must be positive")
    labels = sorted(map(str, frame["label"].unique()))
    if len(labels) < 2:
        raise ValueError("group-aware splitting requires at least two classes")
    group_counts = (
        frame.groupby(["group_id", "label"], sort=True)
        .size()
        .unstack(fill_value=0)
        .reindex(columns=labels, fill_value=0)
    )
    group_ids = group_counts.index.to_numpy()
    counts = group_counts.to_numpy(dtype=np.int64)
    if len(group_ids) < 10:
        raise ValueError("balanced four-role splitting requires at least ten groups")
    held_out_group_count = max(len(labels), round(len(group_ids) * 0.10))
    train_group_count = len(group_ids) - 3 * held_out_group_count
    if train_group_count < len(labels):
        raise ValueError("not enough groups to give every split role support for every class")
    group_role_counts = np.asarray(
        [
            train_group_count,
            held_out_group_count,
            held_out_group_count,
            held_out_group_count,
        ],
        dtype=int,
    )
    role_fractions = group_role_counts / len(group_ids)
    target_class_counts = role_fractions[:, None] * counts.sum(axis=0)
    best: tuple[float, int, list[np.ndarray]] | None = None
    for candidate_seed in range(seed, seed + search_attempts):
        order = np.random.default_rng(candidate_seed).permutation(len(group_ids))
        assignments = list(np.split(order, np.cumsum(group_role_counts)[:-1]))
        class_counts = np.stack([counts[indices].sum(axis=0) for indices in assignments])
        if np.any(class_counts == 0):
            continue
        relative_error = (class_counts - target_class_counts) / np.maximum(target_class_counts, 1)
        score = float(np.square(relative_error).sum())
        if best is None or score < best[0]:
            best = (score, candidate_seed, assignments)
    if best is None:
        raise ValueError(
            "No four-role grouped split contains every class; use richer provenance, "
            "not row-random splitting."
        )
    _, selected_seed, assignments = best
    parts = [
        frame.loc[frame["group_id"].isin(set(group_ids[indices]))].copy() for indices in assignments
    ]
    group_sets = [set(part["group_id"]) for part in parts]
    if any(
        group_sets[left] & group_sets[right] for left in range(4) for right in range(left + 1, 4)
    ):
        raise RuntimeError("group leakage detected while splitting")
    return DatasetSplits(*parts), selected_seed
