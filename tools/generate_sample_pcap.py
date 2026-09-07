"""Generate realistic sample PCAP captures for Custodian replay and validation."""

import socket
import time
from pathlib import Path
import dpkt


def create_sample_pcap(output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    base_time = time.time() - 120.0  # 2 minutes ago
    packets: list[tuple[float, bytes]] = []

    def eth_ip_tcp(
        src_ip: str,
        dst_ip: str,
        sport: int,
        dport: int,
        flags: int,
        seq: int = 1000,
        ack: int = 0,
        payload: bytes = b"",
        src_mac: bytes = b"\x00\x0c\x29\x4f\x8e\x35",
        dst_mac: bytes = b"\x00\x50\x56\xe8\x91\x2c",
    ) -> bytes:
        tcp = dpkt.tcp.TCP(
            sport=sport,
            dport=dport,
            flags=flags,
            seq=seq,
            ack=ack,
            data=payload,
        )
        tcp.off = 5
        ip = dpkt.ip.IP(
            src=socket.inet_aton(src_ip),
            dst=socket.inet_aton(dst_ip),
            p=dpkt.ip.IP_PROTO_TCP,
            ttl=64,
            data=tcp,
        )
        ip.len = len(ip)
        eth = dpkt.ethernet.Ethernet(
            src=src_mac,
            dst=dst_mac,
            type=dpkt.ethernet.ETH_TYPE_IP,
            data=ip,
        )
        return bytes(eth)

    def eth_ip_udp(
        src_ip: str,
        dst_ip: str,
        sport: int,
        dport: int,
        payload: bytes,
        src_mac: bytes = b"\x00\x0c\x29\x4f\x8e\x35",
        dst_mac: bytes = b"\x00\x50\x56\xe8\x91\x2c",
    ) -> bytes:
        udp = dpkt.udp.UDP(
            sport=sport,
            dport=dport,
            data=payload,
        )
        udp.ulen = len(udp)
        ip = dpkt.ip.IP(
            src=socket.inet_aton(src_ip),
            dst=socket.inet_aton(dst_ip),
            p=dpkt.ip.IP_PROTO_UDP,
            ttl=64,
            data=udp,
        )
        ip.len = len(ip)
        eth = dpkt.ethernet.Ethernet(
            src=src_mac,
            dst=dst_mac,
            type=dpkt.ethernet.ETH_TYPE_IP,
            data=ip,
        )
        return bytes(eth)

    def build_dns_query(qname: str, qid: int) -> bytes:
        dns = dpkt.dns.DNS(
            id=qid,
            qr=0,
            opcode=0,
            qd=[dpkt.dns.DNS.Q(name=qname, type=dpkt.dns.DNS_A)],
        )
        return bytes(dns)

    def build_dns_response(qname: str, qid: int, answer_ip: str) -> bytes:
        dns = dpkt.dns.DNS(
            id=qid,
            qr=1,
            ra=1,
            rcode=0,
            qd=[dpkt.dns.DNS.Q(name=qname, type=dpkt.dns.DNS_A)],
            an=[
                dpkt.dns.DNS.RR(
                    name=qname,
                    type=dpkt.dns.DNS_A,
                    ttl=300,
                    rdata=socket.inet_aton(answer_ip),
                )
            ],
        )
        return bytes(dns)

    def build_tls_client_hello(server_name: str) -> bytes:
        # TLS Record Header: ContentType=0x16 (Handshake), Version=0x0301 (TLS 1.0), length=...
        # Handshake: Type=0x01 (ClientHello), Length=...
        sni_bytes = server_name.encode("utf-8")
        sni_ext_data = (
            b"\x00"  # list length high
            + bytes([len(sni_bytes) + 3])
            + b"\x00"  # host_name type
            + b"\x00"  # name length high
            + bytes([len(sni_bytes)])
            + sni_bytes
        )
        ext_sni = b"\x00\x00" + bytes([0, len(sni_ext_data)]) + sni_ext_data

        client_hello_body = (
            b"\x03\x03"  # TLS 1.2
            + (b"\x11" * 32)  # Random
            + b"\x00"  # Session ID length = 0
            + b"\x00\x04\xc0\x2f\xc0\x30"  # Cipher suites length=4, 2 suites
            + b"\x01\x00"  # Compression methods length=1, null compression
            + bytes([0, len(ext_sni)])  # Extensions length
            + ext_sni
        )

        handshake_msg = (
            b"\x01"  # ClientHello
            + bytes([0, 0, len(client_hello_body)])
            + client_hello_body
        )

        record = (
            b"\x16"  # Handshake
            + b"\x03\x01"  # Version
            + bytes([0, len(handshake_msg)])
            + handshake_msg
        )
        return record

    cur_time = base_time

    # 1. Normal DNS resolution flow (Client 192.168.1.105 -> DNS Server 1.1.1.1)
    domains = [
        ("api.github.com", "140.82.121.6"),
        ("gateway.internal.lan", "192.168.1.1"),
        ("auth.service.io", "104.21.45.12"),
        ("cdn.static-assets.net", "151.101.65.140"),
    ]

    for i, (dom, ans_ip) in enumerate(domains):
        qid = 0x1A00 + i
        # Query
        packets.append((cur_time, eth_ip_udp("192.168.1.105", "1.1.1.1", 52100 + i, 53, build_dns_query(dom, qid))))
        cur_time += 0.02
        # Response
        packets.append((cur_time, eth_ip_udp("1.1.1.1", "192.168.1.105", 53, 52100 + i, build_dns_response(dom, qid, ans_ip))))
        cur_time += 0.05

    # 2. Web browsing session over HTTPS (TLS Handshake & Data)
    # Client 192.168.1.105 -> 140.82.121.6:443
    # SYN
    sport = 49200
    packets.append((cur_time, eth_ip_tcp("192.168.1.105", "140.82.121.6", sport, 443, dpkt.tcp.TH_SYN, seq=1000)))
    cur_time += 0.015
    # SYN-ACK
    packets.append((cur_time, eth_ip_tcp("140.82.121.6", "192.168.1.105", 443, sport, dpkt.tcp.TH_SYN | dpkt.tcp.TH_ACK, seq=5000, ack=1001)))
    cur_time += 0.012
    # ACK
    packets.append((cur_time, eth_ip_tcp("192.168.1.105", "140.82.121.6", sport, 443, dpkt.tcp.TH_ACK, seq=1001, ack=5001)))
    cur_time += 0.010
    # TLS Client Hello with SNI "api.github.com"
    tls_hello = build_tls_client_hello("api.github.com")
    packets.append((cur_time, eth_ip_tcp("192.168.1.105", "140.82.121.6", sport, 443, dpkt.tcp.TH_PUSH | dpkt.tcp.TH_ACK, seq=1001, ack=5001, payload=tls_hello)))
    cur_time += 0.025
    # Server ACK + Application Data
    packets.append((cur_time, eth_ip_tcp("140.82.121.6", "192.168.1.105", 443, sport, dpkt.tcp.TH_ACK, seq=5001, ack=1001 + len(tls_hello))))
    cur_time += 0.040
    # Server response data
    app_data = b"\x17\x03\x03\x00\x80" + (b"\xaa" * 128)
    packets.append((cur_time, eth_ip_tcp("140.82.121.6", "192.168.1.105", 443, sport, dpkt.tcp.TH_PUSH | dpkt.tcp.TH_ACK, seq=5001, ack=1001 + len(tls_hello), payload=app_data)))
    cur_time += 0.050
    # FIN / ACK
    packets.append((cur_time, eth_ip_tcp("192.168.1.105", "140.82.121.6", sport, 443, dpkt.tcp.TH_FIN | dpkt.tcp.TH_ACK, seq=1001 + len(tls_hello), ack=5001 + len(app_data))))
    cur_time += 0.020
    packets.append((cur_time, eth_ip_tcp("140.82.121.6", "192.168.1.105", 443, sport, dpkt.tcp.TH_ACK, seq=5001 + len(app_data), ack=1002 + len(tls_hello))))
    cur_time += 0.1

    # 3. HTTP Cleartext API traffic (Workstation 192.168.1.120 -> Internal Server 192.168.1.10:80)
    for req_idx in range(5):
        h_sport = 51000 + req_idx
        http_req = f"GET /api/v1/metrics?node={req_idx} HTTP/1.1\r\nHost: 192.168.1.10\r\nUser-Agent: Custodian-Agent/1.0\r\n\r\n".encode()
        http_res = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 32\r\n\r\n{\"status\":\"healthy\",\"load\":0.12}"
        
        # 3-way handshake
        packets.append((cur_time, eth_ip_tcp("192.168.1.120", "192.168.1.10", h_sport, 80, dpkt.tcp.TH_SYN, seq=2000)))
        cur_time += 0.01
        packets.append((cur_time, eth_ip_tcp("192.168.1.10", "192.168.1.120", 80, h_sport, dpkt.tcp.TH_SYN | dpkt.tcp.TH_ACK, seq=8000, ack=2001)))
        cur_time += 0.01
        packets.append((cur_time, eth_ip_tcp("192.168.1.120", "192.168.1.10", h_sport, 80, dpkt.tcp.TH_ACK, seq=2001, ack=8001)))
        cur_time += 0.01
        # Data
        packets.append((cur_time, eth_ip_tcp("192.168.1.120", "192.168.1.10", h_sport, 80, dpkt.tcp.TH_PUSH | dpkt.tcp.TH_ACK, seq=2001, ack=8001, payload=http_req)))
        cur_time += 0.02
        packets.append((cur_time, eth_ip_tcp("192.168.1.10", "192.168.1.120", 80, h_sport, dpkt.tcp.TH_PUSH | dpkt.tcp.TH_ACK, seq=8001, ack=2001 + len(http_req), payload=http_res)))
        cur_time += 0.01
        # Close
        packets.append((cur_time, eth_ip_tcp("192.168.1.120", "192.168.1.10", h_sport, 80, dpkt.tcp.TH_FIN | dpkt.tcp.TH_ACK, seq=2001 + len(http_req), ack=8001 + len(http_res))))
        cur_time += 0.01
        packets.append((cur_time, eth_ip_tcp("192.168.1.10", "192.168.1.120", 80, h_sport, dpkt.tcp.TH_ACK, seq=8001 + len(http_res), ack=2002 + len(http_req))))
        cur_time += 0.15

    # 4. Database query traffic (192.168.1.120 -> 192.168.1.10:5432 PostgreSQL)
    db_sport = 44120
    packets.append((cur_time, eth_ip_tcp("192.168.1.120", "192.168.1.10", db_sport, 5432, dpkt.tcp.TH_SYN, seq=10000)))
    cur_time += 0.01
    packets.append((cur_time, eth_ip_tcp("192.168.1.10", "192.168.1.120", 5432, db_sport, dpkt.tcp.TH_SYN | dpkt.tcp.TH_ACK, seq=20000, ack=10001)))
    cur_time += 0.01
    packets.append((cur_time, eth_ip_tcp("192.168.1.120", "192.168.1.10", db_sport, 5432, dpkt.tcp.TH_ACK, seq=10001, ack=20001)))
    cur_time += 0.02
    for q_i in range(8):
        query_payload = f"Q\x00\x00\x00\x20SELECT * FROM telemetry_events LIMIT {q_i * 10};\x00".encode()
        resp_payload = b"T\x00\x00\x00\x30\x00\x02id\x00\x00\x00\x17\x00\x04val\x00\x00\x00\x19\x00" + (b"\x00" * 40)
        packets.append((cur_time, eth_ip_tcp("192.168.1.120", "192.168.1.10", db_sport, 5432, dpkt.tcp.TH_PUSH | dpkt.tcp.TH_ACK, seq=10001 + q_i * 50, ack=20001 + q_i * 80, payload=query_payload)))
        cur_time += 0.015
        packets.append((cur_time, eth_ip_tcp("192.168.1.10", "192.168.1.120", 5432, db_sport, dpkt.tcp.TH_PUSH | dpkt.tcp.TH_ACK, seq=20001 + q_i * 80, ack=10001 + (q_i + 1) * 50, payload=resp_payload)))
        cur_time += 0.03

    # 5. Suspicious Activity: Rapid SYN Port Scan from 192.168.1.205 targeting 192.168.1.10 across 30 ports
    target_ports = [
        21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 993, 995, 1433,
        1521, 3306, 3389, 5432, 5900, 6379, 8000, 8080, 8443, 9000, 9200, 27017, 50000, 50001, 50002
    ]
    for p_idx, port in enumerate(target_ports):
        scan_sport = 60000 + p_idx
        # Outbound SYN probe
        packets.append((cur_time, eth_ip_tcp("192.168.1.205", "192.168.1.10", scan_sport, port, dpkt.tcp.TH_SYN, seq=30000 + p_idx)))
        cur_time += 0.01
        # If open port (80, 443, 5432), send SYN-ACK then immediate RST; otherwise RST-ACK (closed)
        if port in (80, 443, 5432):
            packets.append((cur_time, eth_ip_tcp("192.168.1.10", "192.168.1.205", port, scan_sport, dpkt.tcp.TH_SYN | dpkt.tcp.TH_ACK, seq=70000, ack=30001 + p_idx)))
            cur_time += 0.005
            packets.append((cur_time, eth_ip_tcp("192.168.1.205", "192.168.1.10", scan_sport, port, dpkt.tcp.TH_RST, seq=30001 + p_idx, ack=0)))
        else:
            packets.append((cur_time, eth_ip_tcp("192.168.1.10", "192.168.1.205", port, scan_sport, dpkt.tcp.TH_RST | dpkt.tcp.TH_ACK, seq=0, ack=30001 + p_idx)))
        cur_time += 0.015

    # 6. High-throughput bulk data transfer simulation (10.0.0.50 -> 10.0.0.100)
    bulk_sport = 48800
    packets.append((cur_time, eth_ip_tcp("10.0.0.50", "10.0.0.100", bulk_sport, 9000, dpkt.tcp.TH_SYN, seq=1000)))
    cur_time += 0.01
    packets.append((cur_time, eth_ip_tcp("10.0.0.100", "10.0.0.50", 9000, bulk_sport, dpkt.tcp.TH_SYN | dpkt.tcp.TH_ACK, seq=50000, ack=1001)))
    cur_time += 0.01
    packets.append((cur_time, eth_ip_tcp("10.0.0.50", "10.0.0.100", bulk_sport, 9000, dpkt.tcp.TH_ACK, seq=1001, ack=50001)))
    cur_time += 0.01

    payload_chunk = b"X" * 1400
    for chunk_i in range(40):
        packets.append((cur_time, eth_ip_tcp("10.0.0.50", "10.0.0.100", bulk_sport, 9000, dpkt.tcp.TH_PUSH | dpkt.tcp.TH_ACK, seq=1001 + chunk_i * 1400, ack=50001, payload=payload_chunk)))
        cur_time += 0.008
        if chunk_i % 4 == 0:
            packets.append((cur_time, eth_ip_tcp("10.0.0.100", "10.0.0.50", 9000, bulk_sport, dpkt.tcp.TH_ACK, seq=50001, ack=1001 + (chunk_i + 1) * 1400)))
            cur_time += 0.004

    # Close bulk transfer
    packets.append((cur_time, eth_ip_tcp("10.0.0.50", "10.0.0.100", bulk_sport, 9000, dpkt.tcp.TH_FIN | dpkt.tcp.TH_ACK, seq=1001 + 40 * 1400, ack=50001)))
    cur_time += 0.01
    packets.append((cur_time, eth_ip_tcp("10.0.0.100", "10.0.0.50", 9000, bulk_sport, dpkt.tcp.TH_ACK, seq=50001, ack=1002 + 40 * 1400)))

    # Write all packets into standard PCAP format
    with output_path.open("wb") as stream:
        writer = dpkt.pcap.Writer(stream)
        for ts, pkt_bytes in packets:
            writer.writepkt(pkt_bytes, ts=ts)
        writer.close()

    return len(packets)


if __name__ == "__main__":
    out = Path("data/demo/sample_network_traffic.pcap")
    count = create_sample_pcap(out)
    print(f"Generated {count} packets in {out} ({out.stat().st_size} bytes)")
