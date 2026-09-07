import zipfile
from pathlib import Path

import pytest

from training.zenodo_dns import inspect_zip


def test_zip_inspection_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("../escape.csv", "label\n0\n")

    with pytest.raises(ValueError, match="unsafe archive member"):
        inspect_zip(archive)


def test_zip_inspection_reports_members_without_extracting(tmp_path: Path) -> None:
    archive = tmp_path / "safe.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("dataset/test.csv", "label\n0\n")

    records = inspect_zip(archive)

    assert records == [
        {
            "name": "dataset/test.csv",
            "size_bytes": 8,
            "compressed_bytes": 8,
            "is_directory": False,
        }
    ]
    assert not (tmp_path / "dataset").exists()
