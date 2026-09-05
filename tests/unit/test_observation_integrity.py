"""Capability routing tests do not invoke models or network interfaces."""

from custodian.core.enums import FeatureFamily, SourceType, TransportProtocol
from custodian.core.schemas import CapabilityProfile, FeatureVector, FlowRecord, NumericStats
from custodian.observation.integrity import CapabilityRouter, build_observation_frame


def flow(observed_at, client_endpoint, server_endpoint) -> FlowRecord:
    return FlowRecord(
        flow_id="flow-observation",
        start_time=observed_at,
        last_seen=observed_at,
        endpoint_a=client_endpoint,
        endpoint_b=server_endpoint,
        protocol=TransportProtocol.UDP,
        packets_a_to_b=1,
        packets_b_to_a=0,
        bytes_a_to_b=64,
        bytes_b_to_a=0,
        packet_size_stats=NumericStats(count=1, minimum=64, maximum=64, mean=64, variance=0),
        inter_arrival_stats=NumericStats(count=0),
    )


def vector() -> FeatureVector:
    return FeatureVector(
        family=FeatureFamily.DNS,
        schema_version="dns.v1",
        entity_id="dns:10.0.0.1",
        window_id="window-observation",
        values={"domain_length": None, "query_frequency": None},
        availability={"domain_length": False, "query_frequency": False},
    )


def test_dns_is_not_routed_without_visible_query_name(
    observed_at, client_endpoint, server_endpoint
) -> None:
    frame = build_observation_frame(
        flow(observed_at, client_endpoint, server_endpoint),
        vector(),
        CapabilityProfile(has_packet_timestamps=True),
        source_type=SourceType.PCAP_REPLAY,
    )

    result = CapabilityRouter().route(FeatureFamily.DNS, frame)

    assert result.allowed is False
    assert result.missing_capabilities == ("has_dns_query_name",)
    assert frame.capture_completeness is None
    assert "capture completeness" in frame.limitations[0]


def test_observation_id_and_score_are_deterministic(
    observed_at, client_endpoint, server_endpoint
) -> None:
    record = flow(observed_at, client_endpoint, server_endpoint)
    capabilities = CapabilityProfile(has_dns_query_name=True)
    first = build_observation_frame(record, vector(), capabilities)
    second = build_observation_frame(record, vector(), capabilities)

    assert first.observation_frame_id == second.observation_frame_id
    routed = CapabilityRouter().route(FeatureFamily.DNS, first)
    assert routed.allowed is True
    assert 0 <= routed.observation_confidence <= 1
