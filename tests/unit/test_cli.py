"""CLI safety gates are testable without starting servers or touching datasets."""

import pytest

from custodian.cli import main


def test_safety_status_is_local_and_gated(capsys) -> None:
    assert main(["safety-status"]) == 0
    output = capsys.readouterr().out
    assert '"api_bind": "127.0.0.1"' in output
    assert '"outbound_traffic_path": false' in output
    assert "prepare_train_entrypoint" in output


def test_training_command_is_gated_without_acknowledgement(capsys) -> None:
    assert main(["train", "dns", "--input-path", "missing.parquet"]) == 2
    assert "VM safety checklist" in capsys.readouterr().out


def test_prepare_data_command_is_gated_without_acknowledgement(capsys) -> None:
    assert (
        main(
            [
                "prepare-data",
                "--family",
                "dns",
                "--data-dir",
                "data/raw/drift26dsn",
                "--output",
                "data/processed/out.parquet",
            ]
        )
        == 2
    )
    assert "VM safety checklist" in capsys.readouterr().out


def test_live_command_remains_gated(capsys) -> None:
    assert main(["live"]) == 2
    assert "Passive live capture is not enabled" in capsys.readouterr().out


def test_train_requires_family() -> None:
    with pytest.raises(SystemExit):
        main(["train"])
