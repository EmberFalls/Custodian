"""CLI safety gates are testable without starting servers or touching datasets."""

from pathlib import Path

import pytest

from custodian.cli import _demo_constraints, main


def test_safety_status_is_local_and_gated(capsys) -> None:
    assert main(["safety-status"]) == 0
    output = capsys.readouterr().out
    assert '"api_bind": "127.0.0.1"' in output
    assert '"outbound_traffic_path": false' in output


def test_training_command_is_gated(capsys) -> None:
    assert (
        main(
            [
                "train",
                "dga",
                "--input-path",
                "missing.parquet",
                "--output-dir",
                "model_artifacts/test-dga",
            ]
        )
        == 2
    )
    assert "checklist" in capsys.readouterr().out


def test_training_command_requires_family() -> None:
    with pytest.raises(SystemExit):
        main(["train"])


def test_dga_preparation_is_gated_before_source_access(capsys) -> None:
    assert (
        main(
            [
                "prepare-data",
                "--family",
                "dga",
                "--data-dir",
                "missing",
                "--output",
                "missing.parquet",
            ]
        )
        == 2
    )
    assert "checklist" in capsys.readouterr().out


def test_demo_constraints_reads_exact_pins(tmp_path: Path) -> None:
    constraints = tmp_path / "constraints.txt"
    constraints.write_text(
        "# verified runtime\nscikit-learn==1.7.2\n\njoblib==1.5.2\n",
        encoding="utf-8",
    )

    assert _demo_constraints(constraints) == {
        "scikit-learn": "1.7.2",
        "joblib": "1.5.2",
    }
