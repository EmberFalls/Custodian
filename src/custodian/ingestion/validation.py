"""Bounded validation for allow-listed local capture files."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from custodian.core.enums import CaptureStatus, SourceType
from custodian.core.schemas import CapturePacketCounts, CaptureRecord
from custodian.ingest.pcap import SUPPORTED_DATALINKS, CaptureReader

CAPTURE_EXTENSIONS = frozenset({".cap", ".pcap", ".pcapng"})


class CaptureValidator:
    """Resolve and inspect a capture without executing or transmitting its contents."""

    def __init__(self, capture_root: str | Path, *, max_size_bytes: int) -> None:
        self.capture_root = Path(capture_root).resolve()
        self.max_size_bytes = max_size_bytes

    def resolve(self, display_name: str) -> Path:
        if not display_name or Path(display_name).name != display_name:
            raise ValueError("capture must be a filename inside the approved capture directory")
        if Path(display_name).suffix.lower() not in CAPTURE_EXTENSIONS:
            raise ValueError("capture must use a .cap, .pcap, or .pcapng extension")
        candidate = self.capture_root / display_name
        if candidate.is_symlink():
            raise ValueError("symbolic-link captures are not allowed")
        resolved = candidate.resolve()
        try:
            resolved.relative_to(self.capture_root)
        except ValueError as exc:
            raise ValueError("capture resolves outside the approved capture directory") from exc
        if not resolved.is_file():
            raise FileNotFoundError("selected capture does not exist")
        size = resolved.stat().st_size
        if size <= 0:
            raise ValueError("capture is empty")
        if size > self.max_size_bytes:
            raise ValueError(
                f"capture exceeds the configured {self.max_size_bytes}-byte size limit"
            )
        return resolved

    def list_candidates(self) -> list[dict[str, int | str]]:
        if not self.capture_root.is_dir():
            return []
        results: list[dict[str, int | str]] = []
        for candidate in sorted(self.capture_root.iterdir(), key=lambda path: path.name.lower()):
            if (
                candidate.is_file()
                and not candidate.is_symlink()
                and candidate.suffix.lower() in CAPTURE_EXTENSIONS
            ):
                results.append(
                    {"display_name": candidate.name, "size_bytes": candidate.stat().st_size}
                )
        return results

    def validate(self, display_name: str) -> CaptureRecord:
        path = self.resolve(display_name)
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        reader = CaptureReader(path)
        datalink = reader.datalink()
        if datalink not in SUPPORTED_DATALINKS:
            raise ValueError(
                f"unsupported link-layer type {datalink}; Ethernet, Linux cooked, or raw IP is required"
            )
        first: float | None = None
        last: float | None = None
        count = 0
        for frame in reader.frames():
            first = frame.timestamp if first is None else first
            last = frame.timestamp
            count += 1
        if count == 0:
            raise ValueError("capture contains no packet records")
        sha256 = digest.hexdigest()
        return CaptureRecord(
            capture_id=f"capture-{sha256[:24]}",
            source_type=SourceType.PCAP_REPLAY,
            display_name=display_name,
            sha256=sha256,
            size_bytes=path.stat().st_size,
            created_at=datetime.now(UTC),
            first_packet_at=datetime.fromtimestamp(first, UTC) if first is not None else None,
            last_packet_at=datetime.fromtimestamp(last, UTC) if last is not None else None,
            status=CaptureStatus.READY,
            packet_counts=CapturePacketCounts(observed=count),
            parser_warnings=(),
        )
