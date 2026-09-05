"""Explicit phase gate for dataset processing and model training."""

from __future__ import annotations

import os


def require_isolated_training_approval(*, acknowledged: bool = False) -> None:
    """Require two deliberate signals; this does not attempt to prove VM isolation."""

    if not acknowledged or os.environ.get("CUSTODIAN_ISOLATED_TRAINING") != "YES":
        raise RuntimeError(
            "training is blocked: first complete the VM safety checklist, then pass the "
            "explicit acknowledgement and set CUSTODIAN_ISOLATED_TRAINING=YES inside that VM"
        )
