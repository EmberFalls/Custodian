from __future__ import annotations

import time
from dataclasses import dataclass

import dpkt
import pytest

from custodian.ingestion.live_capture import (
    LIVE_CAPTURE_SNAPLEN,
    LIVE_CAPTURE_TIMEOUT_MS,
    CaptureBackendError,
    CaptureBackendUnavailable,
    CaptureInterface,
    CapturePermissionError,
    InterfaceUnavailable,
    LiveCaptureSource,
    UnsupportedLinkType,
    capture_backend_status,
)
from custodian.parsing.packet import PacketParser


@dataclass
class FakeHeader:
    wire_length: int

    def getts(self):
        return (1_800_000_000, 250_000)

    def getlen(self):
        return self.wire_length


def tcp_frame(payload=b"GET /private-message HTTP/1.1\r\n\r\n"):
    tcp = bytearray(20)
    tcp[0:4] = (50000).to_bytes(2, "big") + (80).to_bytes(2, "big")
    tcp[12] = 0x50
    tcp[13] = 0x18
    ip = bytearray(20)
    ip[0] = 0x45
    ip[2:4] = (20 + 20 + len(payload)).to_bytes(2, "big")
    ip[8] = 64
    ip[9] = 6
    ip[12:16] = bytes((192, 0, 2, 10))
    ip[16:20] = bytes((192, 0, 2, 20))
    ethernet = bytes.fromhex("00112233445566778899aabb0800")
    return ethernet + bytes(ip) + bytes(tcp) + payload


class FakeHandle:
    def __init__(self, link_type=dpkt.pcap.DLT_EN10MB, *, packet=None, fail=None):
        self.link_type = link_type
        self.packet = packet
        self.fail = fail
        self.filter = None
        self.closed = False

    def datalink(self):
        return self.link_type

    def setfilter(self, expression):
        if expression == "bad filter":
            raise ValueError("invalid BPF expression")
        self.filter = expression

    def next(self):
        if self.fail:
            raise self.fail
        if self.packet is not None:
            packet, self.packet = self.packet, None
            return FakeHeader(len(packet) + 12), packet
        time.sleep(0.005)
        return None, None

    def close(self):
        self.closed = True


class FakeBackend:
    def __init__(self, interfaces=None, handle=None, error=None):
        self.interfaces = (
            [CaptureInterface("if-1", "lab0", "Lab NIC")]
            if interfaces is None
            else interfaces
        )
        self.handle = handle or FakeHandle()
        self.error = error
        self.opened = []

    def list_interfaces(self):
        if self.error:
            raise self.error
        return self.interfaces

    def open_interface(self, interface_id, *, snaplen, timeout_ms):
        self.opened.append((interface_id, snaplen, timeout_ms))
        if self.error:
            raise self.error
        return self.handle


def test_live_source_lists_interfaces_without_opening_any_device():
    backend = FakeBackend()
    result = capture_backend_status(backend)
    assert result["status"] == "ready"
    assert result["interfaces"][0]["interface_id"] == "if-1"
    assert backend.opened == []


def test_live_source_requires_explicit_existing_interface():
    backend = FakeBackend()
    with pytest.raises(InterfaceUnavailable, match="select one explicitly"):
        LiveCaptureSource.open(backend, "")
    with pytest.raises(InterfaceUnavailable):
        LiveCaptureSource.open(backend, "missing")
    assert backend.opened == []


def test_live_source_uses_non_promiscuous_bounded_capture_and_visible_filter():
    handle = FakeHandle()
    backend = FakeBackend(handle=handle)
    source = LiveCaptureSource.open(backend, "if-1", "tcp")
    assert backend.opened == [("if-1", LIVE_CAPTURE_SNAPLEN, LIVE_CAPTURE_TIMEOUT_MS)]
    assert source.capture_filter == "tcp"
    assert handle.filter == "tcp"
    assert source.interface.link_type == dpkt.pcap.DLT_EN10MB
    source.close()
    source.close()
    assert handle.closed


def test_no_capture_filter_is_kept_unfiltered():
    handle = FakeHandle()
    source = LiveCaptureSource.open(FakeBackend(handle=handle), "if-1")
    assert source.capture_filter is None
    assert handle.filter is None
    source.close()


def test_unavailable_backend_and_insufficient_permissions_fail_closed():
    unavailable = FakeBackend(error=CaptureBackendUnavailable("pcap missing"))
    assert capture_backend_status(unavailable)["status"] == "unavailable"
    with pytest.raises(CaptureBackendUnavailable):
        LiveCaptureSource.open(unavailable, "if-1")

    denied = FakeBackend(error=CapturePermissionError("permission denied"))
    with pytest.raises(CapturePermissionError):
        LiveCaptureSource.open(denied, "if-1")


def test_unsupported_link_type_closes_handle_without_fallback():
    handle = FakeHandle(link_type=999)
    backend = FakeBackend(handle=handle)
    with pytest.raises(UnsupportedLinkType):
        LiveCaptureSource.open(backend, "if-1")
    assert handle.closed
    assert len(backend.opened) == 1


def test_invalid_or_overlong_filter_is_not_silently_changed():
    handle = FakeHandle()
    with pytest.raises(ValueError, match="invalid BPF"):
        LiveCaptureSource.open(FakeBackend(handle=handle), "if-1", "bad filter")
    assert handle.closed
    with pytest.raises(ValueError, match="cannot exceed"):
        LiveCaptureSource.open(FakeBackend(), "if-1", "x" * 513)


def test_capture_returns_observation_not_raw_frame_or_payload():
    frame = tcp_frame()
    handle = FakeHandle(packet=frame)
    source = LiveCaptureSource.open(FakeBackend(handle=handle), "if-1")
    observation = source.next_observation()
    assert observation is not None
    assert str(observation.src_ip) == "192.0.2.10"
    assert observation.payload_length == len(b"GET /private-message HTTP/1.1\r\n\r\n")
    serialized = observation.model_dump_json()
    assert "private-message" not in serialized
    assert '"raw_payload"' not in serialized
    source.close()


def test_existing_pcap_parser_can_extract_approved_protocol_metadata_only():
    # The replay parser can derive a DNS name for lexical features; the resulting
    # observation contains structured DNS metadata, never the raw DNS wire bytes.
    query = dpkt.dns.DNS(
        id=7,
        qd=[dpkt.dns.DNS.Q(name="tunnel.example", type=dpkt.dns.DNS_A)],
    )
    udp = bytearray(8)
    udp[0:4] = (50000).to_bytes(2, "big") + (53).to_bytes(2, "big")
    udp[4:6] = (8 + len(query)).to_bytes(2, "big")
    ip = bytearray(20)
    ip[0] = 0x45
    ip[2:4] = (20 + 8 + len(query)).to_bytes(2, "big")
    ip[8] = 64
    ip[9] = 17
    ip[12:16] = bytes((192, 0, 2, 10))
    ip[16:20] = bytes((192, 0, 2, 53))
    frame = bytes.fromhex("00112233445566778899aabb0800") + bytes(ip) + bytes(udp) + bytes(query)
    observation = PacketParser().parse(1_800_000_000.25, frame)
    assert observation is not None
    assert observation.dns_metadata["queries"][0]["name"] == "tunnel.example"
    assert observation.dns_metadata["queries"][0]["type"] == 1
    assert bytes(query).hex() not in observation.model_dump_json()


def test_source_surfaces_unexpected_capture_failure():
    source = LiveCaptureSource.open(
        FakeBackend(handle=FakeHandle(fail=OSError("capture device stopped"))),
        "if-1",
    )
    with pytest.raises(CaptureBackendError, match="stopped unexpectedly"):
        source.next_observation()
    source.close()
