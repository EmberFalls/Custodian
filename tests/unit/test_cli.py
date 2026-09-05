"""CLI safety gates are testable without starting servers or touching datasets."""

from custodian.cli import main


def test_safety_status_is_local_and_gated(capsys) -> None:
    assert main(["safety-status"]) == 0
    output = capsys.readouterr().out
    assert '"api_bind": "127.0.0.1"' in output
    assert '"outbound_traffic_path": false' in output


def test_training_command_is_gated(capsys) -> None:
    assert main(["train"]) == 2
    assert "isolated VM" in capsys.readouterr().out
