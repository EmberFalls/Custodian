import pandas as pd

from training.splits import complete_class_grouped_splits


def test_complete_group_split_balances_labels_without_group_overlap() -> None:
    rows = []
    for group in range(50):
        label = "DNS_TUNNEL" if group % 2 else "BENIGN_DNS"
        size = 5 + (group % 7) * 3
        rows.extend(
            {"group_id": f"group-{group}", "label": label, "feature__x": group} for _ in range(size)
        )
    frame = pd.DataFrame(rows)

    splits, selected_seed = complete_class_grouped_splits(frame, seed=42, search_attempts=200)

    parts = [splits.train, splits.validation, splits.calibration, splits.test]
    assert selected_seed >= 42
    assert all(set(part["label"]) == {"BENIGN_DNS", "DNS_TUNNEL"} for part in parts)
    group_sets = [set(part["group_id"]) for part in parts]
    assert all(
        not group_sets[left] & group_sets[right]
        for left in range(4)
        for right in range(left + 1, 4)
    )
    assert sum(len(part) for part in parts) == len(frame)


def test_small_dataset_assigns_two_groups_to_each_held_out_role() -> None:
    rows = []
    for group in range(15):
        label = "BENIGN_DNS" if group < 5 else "DNS_TUNNEL"
        rows.extend({"group_id": f"source-{group}", "label": label} for _ in range(10 + group))
    frame = pd.DataFrame(rows)

    splits, _ = complete_class_grouped_splits(frame, search_attempts=500)

    assert splits.train["group_id"].nunique() == 9
    assert splits.validation["group_id"].nunique() == 2
    assert splits.calibration["group_id"].nunique() == 2
    assert splits.test["group_id"].nunique() == 2
    assert all(
        set(part["label"]) == {"BENIGN_DNS", "DNS_TUNNEL"}
        for part in (splits.train, splits.validation, splits.calibration, splits.test)
    )
