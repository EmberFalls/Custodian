"""Hosted-Colab-only orchestration for the DRIFT26DSN DGA candidate."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from custodian.models.loader import load_model_package
from training.colab import (
    HOSTED_COLAB_ACKNOWLEDGEMENT,
    require_hosted_colab,
    require_owned_workspace,
)
from training.commands import prepare_dga
from training.train_dga import _write_hash_manifest, train


def run(workspace: Path, source_dir: Path) -> Path:
    """Prepare, fit and verify DGA artifacts without contacting observed domains.

    Dataset acquisition is deliberately separate. ``source_dir`` must contain only
    the reviewed ``T17_benign.parquet`` and ``T17_dga.parquet`` members inside the
    disposable Colab workspace.
    """

    require_hosted_colab(HOSTED_COLAB_ACKNOWLEDGEMENT, environment=os.environ)
    workspace = require_owned_workspace(workspace)
    source_dir = source_dir.resolve()
    if workspace not in source_dir.parents:
        raise ValueError("DGA source directory must be inside the owned Colab workspace")
    os.environ["CUSTODIAN_HOSTED_COLAB_TRAINING"] = "YES"
    prepared = workspace / "prepared" / "dns_dga_drift26dsn.parquet"
    provenance = workspace / "prepared" / "dns_dga_drift26dsn.json"
    prepare_dga(
        source_dir,
        prepared,
        manifest_path=provenance,
        isolation_acknowledged=True,
    )
    package = train(
        prepared,
        workspace / "output" / "dns-dga-drift26dsn-hgb-v1",
        feature_set="lexical",
        isolation_acknowledged=True,
    )
    shutil.copy2(provenance, package / "dataset_provenance.json")
    review = {
        "status": "CANDIDATE_INTERNAL_EVALUATION_COMPLETE_EXTERNAL_EVALUATION_REQUIRED",
        "trusted": False,
        "must_not_enable_in_models_yaml": True,
        "allowed_claim": "DRIFT26DSN binary lexical DGA candidate",
        "forbidden_claims": [
            "DGA family attribution",
            "production DGA detection",
            "live-network accuracy",
        ],
        "independent_external_evaluation_completed": False,
    }
    (package / "review_status.json").write_text(
        json.dumps(review, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_hash_manifest(package)
    loaded = load_model_package(package)
    if loaded.classes != ("BENIGN", "DGA"):
        raise ValueError(f"unexpected DGA classes: {loaded.classes}")
    return package
