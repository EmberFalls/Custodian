"""The live adapter's metadata uses the same downstream engine as PCAP replay."""

from pathlib import Path

import dpkt

from custodian.config import load_config_bundle
from custodian.ingestion.live_capture import CaptureInterface, LiveCaptureSource
from custodian.runtime.engine import CustodianEngine


class Header:
    def getts(self):
        return 1_800_000_000, 250_000

    def getlen(self):
        return 54


class Handle:
    def __init__(self, frame):
        self.frame = frame

    def datalink(self):
        return dpkt.pcap.DLT_EN10MB

    def setfilter(self, expression):
        raise AssertionError("test opens capture without a filter")

    def next(self):
        frame, self.frame = self.frame, None
        return (Header(), frame) if frame else (None, None)

    def close(self):
        pass


class Backend:
    def __init__(self, handle):
        self.handle = handle

    def list_interfaces(self):
        return [CaptureInterface("lab0", "Lab interface", "isolated test interface")]

    def open_interface(self, interface_id, *, snaplen, timeout_ms):
        assert interface_id == "lab0"
        return self.handle


def _tcp_frame():
    tcp = dpkt.tcp.TCP(sport=50_000, dport=443, flags=dpkt.tcp.TH_SYN, seq=1)
    tcp.off = 5
    ip = dpkt.ip.IP(
        src=bytes((192, 0, 2, 10)),
        dst=bytes((198, 51, 100, 20)),
        p=dpkt.ip.IP_PROTO_TCP,
        ttl=64,
        data=tcp,
    )
    ip.len = len(ip)
    return bytes(dpkt.ethernet.Ethernet(src=b"123456", dst=b"abcdef", type=0x0800, data=ip))


def test_live_observation_enters_shared_flow_and_feature_pipeline():
    root = Path(__file__).resolve().parents[2]
    bundle = load_config_bundle(root / "configs")
    engine = CustodianEngine(bundle)
    engine.mode = bundle.replay.mode
    source = LiveCaptureSource.open(Backend(Handle(_tcp_frame())), "lab0")
    packet = source.next_observation()
    source.close()

    assert packet is not None
    engine.process_observation(packet, wire_length=54)
    engine.finish()

    assert engine.metrics.parsed_packets == 1
    assert engine.flows.active_flow_count == 0
    assert len(engine.recent_flows) == 1
    assert engine.recent_flows[0].packets_a_to_b + engine.recent_flows[0].packets_b_to_a == 1
    assert any(event["event_type"] == "flow_update" for event in engine.pipeline_events)
    assert any(event["event_type"] == "feature_vector" for event in engine.pipeline_events)
