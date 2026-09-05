"""Passive adapter implementations and explicitly disabled future sources."""

from __future__ import annotations

from collections.abc import Iterator

from custodian.core.enums import SourceType
from custodian.core.schemas import CapabilityProfile, PacketObservation
from custodian.ingest.pcap import CaptureReader
from custodian.parsing.packet import PacketParser


class PCAPObservationAdapter:
    """Convert local capture frames into canonical metadata observations."""

    source_type = SourceType.PCAP_REPLAY
    capabilities = CapabilityProfile(
        has_packet_timestamps=True,
        has_packet_sizes=True,
        has_directionality=True,
    )

    def __init__(self, reader: CaptureReader) -> None:
        self.reader = reader
        self.parser = PacketParser()

    def observations(self) -> Iterator[PacketObservation]:
        for frame in self.reader.frames():
            observation = self.parser.parse(frame.timestamp, frame.data, frame.datalink)
            if observation is not None:
                yield observation


class DisabledPassiveAdapter:
    """Declare a future passive source without touching an interface or socket."""

    capabilities = CapabilityProfile()

    def __init__(self, source_type: SourceType, reason: str) -> None:
        if source_type is SourceType.PCAP_REPLAY:
            raise ValueError("use PCAPObservationAdapter for capture replay")
        self.source_type = source_type
        self.reason = reason

    def observations(self) -> Iterator[PacketObservation]:
        raise RuntimeError(self.reason)
        yield  # pragma: no cover


def disabled_live_adapter() -> DisabledPassiveAdapter:
    return DisabledPassiveAdapter(
        SourceType.LIVE_PASSIVE,
        "passive live capture is disabled pending explicit user approval and interface review",
    )


def adapter_statuses() -> list[dict[str, object]]:
    """Describe input support without opening a file, socket, or interface."""

    disabled = {
        SourceType.ZEEK_METADATA: "derived-metadata adapter is not implemented",
        SourceType.LIVE_PASSIVE: (
            "disabled pending explicit user approval and passive-interface review"
        ),
        SourceType.NETFLOW: "NetFlow adapter is not implemented",
        SourceType.IPFIX: "IPFIX adapter is not implemented",
        SourceType.SFLOW: "sFlow adapter is not implemented",
    }
    records: list[dict[str, object]] = [
        {
            "source_type": SourceType.PCAP_REPLAY.value,
            "status": "ready",
            "passive": True,
            "opens_network_interface": False,
            "reason": None,
        }
    ]
    records.extend(
        {
            "source_type": source_type.value,
            "status": "unavailable",
            "passive": True,
            "opens_network_interface": False,
            "reason": reason,
        }
        for source_type, reason in disabled.items()
    )
    return records
