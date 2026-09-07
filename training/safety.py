"""Explicit phase gate for dataset processing and model training."""

from __future__ import annotations

import os
from pathlib import Path


def require_isolated_training_approval(*, acknowledged: bool = False) -> None:
    """Require two deliberate signals; this does not attempt to prove VM isolation."""

    if not acknowledged:
        raise RuntimeError(
            "training is blocked: complete the VM safety checklist or hosted Colab "
            "checklist and provide the explicit isolation acknowledgement"
        )
    if os.environ.get("CUSTODIAN_ISOLATED_TRAINING") == "YES":
        return
    hosted_requested = os.environ.get("CUSTODIAN_HOSTED_COLAB_TRAINING") == "YES"
    hosted_marker = any(
        os.environ.get(name) for name in ("COLAB_RELEASE_TAG", "COLAB_BACKEND_VERSION")
    )
    hosted_root = Path("/content").is_dir()
    local_override = bool(os.environ.get("CUSTODIAN_ALLOW_LOCAL_RUNTIME"))
    if hosted_requested and hosted_marker and hosted_root and not local_override:
        return
    raise RuntimeError(
        "training is blocked: complete the VM safety checklist or use an approved "
        "hosted Colab runtime; local runtimes are not supported"
    )
