"""Capture validation tests use inert synthetic container fixtures only."""

from pathlib import Path

import dpkt
import pytest

from custodian.core.enums import CaptureStatus, SourceType
from custodian.ingestion.validation import CaptureValidator


def write_capture(path: Path) -> None:
    with path.open("wb") as stream:
        writer = dpkt.pcap.Writer(stream)
        writer.writepkt(b"metadata-only-test-frame", ts=1)


def test_validator_hashes_and_identifies_allow_listed_capture(tmp_path: Path) -> None:
    path = tmp_path / "approved.cap"
    write_capture(path)
    validator = CaptureValidator(tmp_path, max_size_bytes=1024)

    record = validator.validate(path.name)

    assert record.status is CaptureStatus.READY
    assert record.source_type is SourceType.PCAP_REPLAY
    assert record.packet_counts.observed == 1
    assert record.sha256 and len(record.sha256) == 64
    assert validator.list_candidates() == [
        {"display_name": "approved.cap", "size_bytes": path.stat().st_size}
    ]


@pytest.mark.parametrize("name", ["../outside.cap", "folder/file.cap", "dataset.csv"])
def test_validator_rejects_paths_and_non_capture_inputs(tmp_path: Path, name: str) -> None:
    validator = CaptureValidator(tmp_path, max_size_bytes=1024)

    with pytest.raises((ValueError, FileNotFoundError)):
        validator.resolve(name)


def test_validator_enforces_size_before_parsing(tmp_path: Path) -> None:
    path = tmp_path / "large.cap"
    write_capture(path)

    with pytest.raises(ValueError, match="size limit"):
        CaptureValidator(tmp_path, max_size_bytes=4).validate(path.name)
