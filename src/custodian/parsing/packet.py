"""Ethernet/IP packet parsing into the stable PacketObservation contract."""

from __future__ import annotations

from datetime import UTC, datetime
from ipaddress import ip_address
from typing import Final

import dpkt

from custodian.core.enums import TransportProtocol
from custodian.core.schemas import PacketObservation
from custodian.parsing.dns import parse_dns_message
from custodian.parsing.tls_quic import parse_quic_metadata, parse_tls_metadata

_TCP_FLAGS: Final[tuple[tuple[int, str], ...]] = (
    (dpkt.tcp.TH_FIN, "FIN"),
    (dpkt.tcp.TH_SYN, "SYN"),
    (dpkt.tcp.TH_RST, "RST"),
    (dpkt.tcp.TH_PUSH, "PSH"),
    (dpkt.tcp.TH_ACK, "ACK"),
    (dpkt.tcp.TH_URG, "URG"),
    (dpkt.tcp.TH_ECE, "ECE"),
    (dpkt.tcp.TH_CWR, "CWR"),
)


class PacketParser:
    """Parse supported packets while skipping malformed/unsupported frames safely."""

    def parse(
        self,
        timestamp: float,
        frame: bytes,
        datalink: int = dpkt.pcap.DLT_EN10MB,
    ) -> PacketObservation | None:
        try:
            if datalink == dpkt.pcap.DLT_EN10MB:
                ethernet = dpkt.ethernet.Ethernet(frame)
                network = ethernet.data
                while isinstance(network, dpkt.ethernet.VLANtag8021Q):
                    network = network.data
            elif datalink == dpkt.pcap.DLT_LINUX_SLL:
                network = dpkt.sll.SLL(frame).data
            elif datalink == dpkt.pcap.DLT_RAW:
                version = frame[0] >> 4 if frame else 0
                network = dpkt.ip.IP(frame) if version == 4 else dpkt.ip6.IP6(frame)
            else:
                return None
            if not isinstance(network, (dpkt.ip.IP, dpkt.ip6.IP6)):
                return None
            # No fragment reassembly or truncated-payload guesses in this prototype.
            if isinstance(network, dpkt.ip.IP) and (
                network.mf or network.offset or network.len > len(network)
            ):
                return None
            if isinstance(network, dpkt.ip6.IP6) and (
                any(
                    isinstance(header, dpkt.ip6.IP6FragmentHeader)
                    for header in getattr(network, "all_extension_headers", [])
                )
                or network.plen > len(network) - 40
            ):
                return None
            src_ip = ip_address(network.src)
            dst_ip = ip_address(network.dst)
            transport = network.data
            observed_at = datetime.fromtimestamp(float(timestamp), tz=UTC)

            if isinstance(transport, dpkt.tcp.TCP):
                payload = bytes(transport.data)
                dns_metadata = None
                tls_metadata = None
                if 53 in {transport.sport, transport.dport}:
                    dns_payload = payload[2:] if len(payload) >= 2 else b""
                    dns_metadata = parse_dns_message(dns_payload)
                if 443 in {transport.sport, transport.dport} or 8443 in {
                    transport.sport,
                    transport.dport,
                }:
                    tls_metadata = parse_tls_metadata(payload)
                flags = frozenset(name for bit, name in _TCP_FLAGS if transport.flags & bit)
                return PacketObservation(
                    timestamp=observed_at,
                    src_ip=src_ip,
                    dst_ip=dst_ip,
                    src_port=int(transport.sport),
                    dst_port=int(transport.dport),
                    protocol=TransportProtocol.TCP,
                    packet_length=len(frame),
                    payload_length=len(payload),
                    tcp_flags=flags,
                    dns_metadata=dns_metadata,
                    tls_metadata=tls_metadata,
                )

            if isinstance(transport, dpkt.udp.UDP):
                payload = bytes(transport.data)
                dns_metadata = None
                quic_metadata = None
                if 53 in {transport.sport, transport.dport}:
                    dns_metadata = parse_dns_message(payload)
                if 443 in {transport.sport, transport.dport}:
                    quic_metadata = parse_quic_metadata(payload)
                return PacketObservation(
                    timestamp=observed_at,
                    src_ip=src_ip,
                    dst_ip=dst_ip,
                    src_port=int(transport.sport),
                    dst_port=int(transport.dport),
                    protocol=TransportProtocol.UDP,
                    packet_length=len(frame),
                    payload_length=len(payload),
                    dns_metadata=dns_metadata,
                    quic_metadata=quic_metadata,
                )

            if isinstance(transport, (dpkt.icmp.ICMP, dpkt.icmp6.ICMP6)):
                return PacketObservation(
                    timestamp=observed_at,
                    src_ip=src_ip,
                    dst_ip=dst_ip,
                    protocol=TransportProtocol.ICMP,
                    packet_length=len(frame),
                )
        except (dpkt.dpkt.NeedData, dpkt.dpkt.UnpackError, ValueError):
            return None
        return None

    def parse_with_status(
        self,
        timestamp: float,
        frame: bytes,
        datalink: int = dpkt.pcap.DLT_EN10MB,
    ) -> tuple[PacketObservation | None, str]:
        """Return a coarse accounting status without exposing packet payloads."""

        observation = self.parse(timestamp, frame, datalink)
        if observation is not None:
            return observation, "parsed"
        if not frame:
            return None, "truncated"
        if datalink not in {
            dpkt.pcap.DLT_EN10MB,
            dpkt.pcap.DLT_LINUX_SLL,
            dpkt.pcap.DLT_RAW,
        }:
            return None, "unsupported"
        try:
            if datalink == dpkt.pcap.DLT_EN10MB:
                network = dpkt.ethernet.Ethernet(frame).data
            elif datalink == dpkt.pcap.DLT_LINUX_SLL:
                network = dpkt.sll.SLL(frame).data
            else:
                version = frame[0] >> 4
                if version not in {4, 6}:
                    return None, "malformed"
                network = dpkt.ip.IP(frame) if version == 4 else dpkt.ip6.IP6(frame)
            if not isinstance(network, (dpkt.ip.IP, dpkt.ip6.IP6)):
                return None, "unsupported"
            if isinstance(network, dpkt.ip.IP) and (network.mf or network.offset):
                return None, "unsupported"
            if isinstance(network, dpkt.ip6.IP6) and any(
                isinstance(header, dpkt.ip6.IP6FragmentHeader)
                for header in getattr(network, "all_extension_headers", [])
            ):
                return None, "unsupported"
            if isinstance(network, dpkt.ip.IP) and network.len > len(network):
                return None, "truncated"
            if isinstance(network, dpkt.ip6.IP6) and network.plen > len(network) - 40:
                return None, "truncated"
            if isinstance(
                network.data, (dpkt.tcp.TCP, dpkt.udp.UDP, dpkt.icmp.ICMP, dpkt.icmp6.ICMP6)
            ):
                return None, "malformed"
            return None, "unsupported"
        except dpkt.dpkt.NeedData:
            return None, "truncated"
        except (dpkt.dpkt.UnpackError, ValueError):
            return None, "malformed"
