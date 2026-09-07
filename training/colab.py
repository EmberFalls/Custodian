"""Small, testable safety and provenance helpers for hosted Colab setup."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from pathlib import Path

FULL_GIT_SHA = re.compile(r"[0-9a-f]{40}")
HOSTED_COLAB_ACKNOWLEDGEMENT = "I AM USING A HOSTED GOOGLE COLAB RUNTIME"
HOSTED_COLAB_MARKERS = ("COLAB_RELEASE_TAG", "COLAB_BACKEND_VERSION")


def validate_commit_sha(value: str) -> str:
    """Accept only an immutable, full lowercase Git commit identifier."""

    candidate = value.strip().lower()
    if FULL_GIT_SHA.fullmatch(candidate) is None:
        raise ValueError("CUSTODIAN_COMMIT must be a full 40-character Git commit SHA")
    return candidate


def require_hosted_colab(
    acknowledgement: str,
    *,
    environment: Mapping[str, str],
    content_root: Path = Path("/content"),
) -> None:
    """Reject obvious local-runtime use; marker checks are a guard, not proof of isolation."""

    if acknowledgement != HOSTED_COLAB_ACKNOWLEDGEMENT:
        raise RuntimeError("hosted Colab acknowledgement is missing or incorrect")
    if not any(environment.get(marker) for marker in HOSTED_COLAB_MARKERS):
        raise RuntimeError("hosted Colab markers are absent; do not use a local runtime")
    if environment.get("CUSTODIAN_ALLOW_LOCAL_RUNTIME"):
        raise RuntimeError("local-runtime override variables are not supported")
    if not content_root.is_dir():
        raise RuntimeError("expected hosted Colab content root is unavailable")


def require_owned_workspace(path: Path, *, content_root: Path = Path("/content")) -> Path:
    """Confine setup and cleanup to Custodian's dedicated child of the Colab root."""

    resolved_root = content_root.resolve()
    resolved = path.resolve()
    expected = resolved_root / "custodian-workspace"
    if resolved != expected:
        raise ValueError(f"workspace must be exactly {expected}")
    return resolved


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Hash a file without loading the whole dataset or artifact into memory."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()
