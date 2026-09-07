"""Static safety and reproducibility checks for the shared Colab notebook."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from training.colab import (
    HOSTED_COLAB_ACKNOWLEDGEMENT,
    require_hosted_colab,
    require_owned_workspace,
    validate_commit_sha,
)

ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = ROOT / "notebooks" / "custodian_training_colab.ipynb"
REQUIREMENTS = ROOT / "training" / "requirements-colab.txt"


def notebook() -> dict:
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))


def code_source(document: dict) -> str:
    return "\n".join(
        "".join(cell["source"])
        for cell in document["cells"]
        if cell["cell_type"] == "code"
    )


def test_notebook_is_clean_and_contains_reproducibility_gates() -> None:
    document = notebook()
    assert document["nbformat"] == 4
    for cell in document["cells"]:
        if cell["cell_type"] == "code":
            assert cell["execution_count"] is None
            assert cell["outputs"] == []
    source = code_source(document)
    for required in (
        "CUSTODIAN_COMMIT",
        "validate_commit_sha",
        "require_hosted_colab",
        '"git", "checkout", "--detach"',
        "requirements-colab.txt",
        "--no-deps",
        '"pip", "freeze"',
        "colab-environment-manifest.json",
        "require_owned_workspace",
    ):
        assert required in source


def test_common_notebook_does_not_train_mount_drive_or_accept_datasets() -> None:
    source = code_source(notebook())
    forbidden = (
        "files.upload",
        "drive.mount",
        "google.colab.drive",
        "training.train_behaviour",
        "training.train_dns",
        "training.train_tls_quic",
        "CUSTODIAN_ISOLATED_TRAINING",
        '"git", "clone", "--depth"',
        ".[dev]",
    )
    for value in forbidden:
        assert value not in source


def test_colab_requirements_are_exact_direct_pins() -> None:
    pins = [
        line.strip()
        for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert pins
    assert all(re.fullmatch(r"[A-Za-z0-9_.-]+==[^=\s]+", pin) for pin in pins)
    assert len(pins) == len({pin.casefold().split("==", 1)[0] for pin in pins})


def test_full_commit_validation() -> None:
    assert validate_commit_sha("A" * 40) == "a" * 40
    for invalid in ("main", "abc123", "g" * 40, "a" * 39, "a" * 41):
        with pytest.raises(ValueError, match="full 40-character"):
            validate_commit_sha(invalid)


def test_hosted_colab_guard_requires_ack_marker_and_content_root(tmp_path: Path) -> None:
    require_hosted_colab(
        HOSTED_COLAB_ACKNOWLEDGEMENT,
        environment={"COLAB_RELEASE_TAG": "release"},
        content_root=tmp_path,
    )
    with pytest.raises(RuntimeError, match="acknowledgement"):
        require_hosted_colab("yes", environment={"COLAB_RELEASE_TAG": "release"})
    with pytest.raises(RuntimeError, match="markers"):
        require_hosted_colab(
            HOSTED_COLAB_ACKNOWLEDGEMENT,
            environment={},
            content_root=tmp_path,
        )


def test_workspace_guard_accepts_only_dedicated_directory(tmp_path: Path) -> None:
    workspace = tmp_path / "custodian-workspace"
    assert require_owned_workspace(workspace, content_root=tmp_path) == workspace.resolve()
    with pytest.raises(ValueError, match="exactly"):
        require_owned_workspace(tmp_path / "other", content_root=tmp_path)
