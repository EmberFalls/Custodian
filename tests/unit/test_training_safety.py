"""Training requires deliberate VM approval signals."""

import pytest

from training.safety import require_isolated_training_approval


def test_training_is_blocked_without_both_approval_signals(monkeypatch) -> None:
    monkeypatch.delenv("CUSTODIAN_ISOLATED_TRAINING", raising=False)
    with pytest.raises(RuntimeError, match="VM safety checklist"):
        require_isolated_training_approval(acknowledged=True)
    monkeypatch.setenv("CUSTODIAN_ISOLATED_TRAINING", "YES")
    with pytest.raises(RuntimeError, match="VM safety checklist"):
        require_isolated_training_approval(acknowledged=False)


def test_training_gate_opens_only_after_explicit_vm_acknowledgement(monkeypatch) -> None:
    monkeypatch.setenv("CUSTODIAN_ISOLATED_TRAINING", "YES")
    require_isolated_training_approval(acknowledged=True)
