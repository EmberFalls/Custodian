"""Tests for shared temporal, Behaviour, DNS, and TLS/QUIC feature extraction."""

from datetime import timedelta

from custodian.core.enums import TransportProtocol
from custodian.core.schemas import CapabilityProfile, PacketObservation
from custodian.features.behaviour import BehaviourFeatureExtractor, periodicity_score
from custodian.features.dns import DNSFeatureExtractor, dns_lexical_values
from custodian.features.tls_quic import TLSQUICFeatureExtractor
from custodian.flow.manager import FlowManager
from custodian.observation.capabilities import build_capability_profile
from custodian.state.manager import TemporalStateManager


def _packet(observed_at, *, dns_metadata=None, tls_metadata=None) -> PacketObservation:
    return PacketObservation(
        timestamp=observed_at,
        src_ip="10.0.0.15",
        dst_ip="10.0.0.20",
        src_port=50000,
        dst_port=443,
        protocol=TransportProtocol.TCP,
        packet_length=100,
        tcp_flags=frozenset({"ACK"}),
        dns_metadata=dns_metadata,
        tls_metadata=tls_metadata,
    )


def test_periodicity_is_unavailable_with_too_few_observations(observed_at) -> None:
    assert periodicity_score((observed_at, observed_at + timedelta(seconds=10))) == (
        None,
        None,
        None,
    )


def test_behaviour_features_use_bounded_temporal_state(observed_at) -> None:
    manager = FlowManager()
    state = TemporalStateManager()
    for offset in (0, 10, 20):
        packet = _packet(observed_at + timedelta(seconds=offset))
        update = manager.process(packet)
        state.observe(packet, update)
    snapshot = state.snapshot("10.0.0.15", "10.0.0.20", observed_at + timedelta(seconds=20), 60)
    capabilities = build_capability_profile(packet, update.snapshot)

    vector = BehaviourFeatureExtractor().extract(update.snapshot, snapshot, capabilities)

    assert vector.values["connection_count"] == 1
    assert vector.values["packets_per_second"] == 3 / 60
    assert vector.values["tcp_syn_count"] == 0


def test_dns_features_keep_hidden_query_text_unavailable(observed_at) -> None:
    manager = FlowManager()
    state = TemporalStateManager()
    packet = _packet(
        observed_at,
        dns_metadata={"queries": [{"name": "abc-123.example", "type": 1}]},
    )
    update = manager.process(packet)
    state.observe(packet, update)
    snapshot = state.snapshot("10.0.0.15", "10.0.0.20", observed_at, 10)
    visible = CapabilityProfile(has_dns_query_name=True, has_dns_query_type=True)

    vector = DNSFeatureExtractor().extract(packet, snapshot, visible)
    assert vector.values["domain_length"] == 15
    assert vector.values["digit_ratio"] > 0

    hidden = DNSFeatureExtractor().extract(packet, snapshot, CapabilityProfile())
    assert hidden.values["domain_length"] is None
    assert not hidden.availability["domain_length"]


def test_dns_metadata_boundary_matches_runtime_packet_path(observed_at) -> None:
    manager = FlowManager()
    state = TemporalStateManager()
    packet = _packet(
        observed_at,
        dns_metadata={"queries": [{"name": "abc-123.example", "type": 1}]},
    )
    update = manager.process(packet)
    state.observe(packet, update)
    snapshot = state.snapshot("10.0.0.15", "10.0.0.20", observed_at, 10)
    capabilities = CapabilityProfile(has_dns_query_name=True, has_dns_query_type=True)

    runtime_vector = DNSFeatureExtractor().extract(packet, snapshot, capabilities)
    training_vector = DNSFeatureExtractor().extract_metadata(
        observed_at=observed_at,
        source_id="10.0.0.15",
        domain="abc-123.example",
        query_type=1,
        recent_domains=("abc-123.example",),
        window_seconds=10,
        capabilities=capabilities,
    )

    assert training_vector == runtime_vector


def test_dns_metadata_boundary_can_mark_temporal_history_unavailable(observed_at) -> None:
    capabilities = CapabilityProfile(has_dns_query_name=True)
    vector = DNSFeatureExtractor().extract_metadata(
        observed_at=observed_at,
        source_id="source",
        domain="encoded.example",
        query_type=None,
        recent_domains=(),
        window_seconds=60,
        capabilities=capabilities,
        recent_history_available=False,
    )

    assert vector.availability["domain_length"] is True
    assert vector.availability["query_frequency"] is False
    assert vector.availability["unique_domain_ratio"] is False
    assert vector.values["query_frequency"] is None


def test_dns_training_and_runtime_share_normalization_and_lexical_values(observed_at) -> None:
    capabilities = CapabilityProfile(has_dns_query_name=True)
    vector = DNSFeatureExtractor().extract_metadata(
        observed_at=observed_at,
        source_id="source",
        domain="  Qx7K9.Example.COM. ",
        query_type=None,
        recent_domains=(),
        window_seconds=60,
        capabilities=capabilities,
        recent_history_available=False,
    )

    expected = dns_lexical_values("qx7k9.example.com")
    assert all(vector.values[name] == value for name, value in expected.items())


def test_tls_features_do_not_require_decrypted_payload(observed_at) -> None:
    manager = FlowManager()
    packet = _packet(observed_at, tls_metadata={"record_version": 771, "ja3": "abc"})
    update = manager.process(packet)
    state = TemporalStateManager()
    state.observe(packet, update)
    snapshot = state.snapshot("10.0.0.15", "10.0.0.20", observed_at, 10)

    vector = TLSQUICFeatureExtractor().extract(
        update.snapshot,
        snapshot,
        CapabilityProfile(has_tls_metadata=True, has_tls_fingerprint=True),
    )
    assert vector.values["tls_record_version"] == 771
    assert vector.values["tls_fingerprint_bucket"] is not None
    assert vector.values["byte_rate_a_to_b"] is None


def test_tls_metadata_boundary_matches_runtime_formulas(observed_at) -> None:
    manager = FlowManager()
    first = _packet(observed_at, tls_metadata={"record_version": 771, "ja3": "abc"})
    second = _packet(
        observed_at + timedelta(seconds=2),
        tls_metadata={"record_version": 771, "ja3": "abc"},
    )
    first_update = manager.process(first)
    update = manager.process(second)
    state = TemporalStateManager()
    state.observe(first, first_update)
    state.observe(second, update)
    snapshot = state.snapshot("10.0.0.15", "10.0.0.20", second.timestamp, 10)
    extractor = TLSQUICFeatureExtractor()
    vector = extractor.extract(
        update.snapshot,
        snapshot,
        CapabilityProfile(has_tls_metadata=True, has_tls_fingerprint=True),
    )
    expected = extractor.metadata_values(
        duration_seconds=2.0,
        packet_count=2,
        total_bytes=200,
        packet_size_mean=100.0,
        packet_size_variance=0.0,
        inter_arrival_mean=2.0,
        inter_arrival_variance=0.0,
        packets_a_to_b=2,
        packets_b_to_a=0,
        bytes_a_to_b=200,
        bytes_b_to_a=0,
        tls_metadata={"record_version": 771, "ja3": "abc"},
        destination_recurrence=snapshot.destination_counts.get(snapshot.destination_ip, 0)
        / max(snapshot.packet_count, 1),
        connection_frequency=snapshot.flow_count / snapshot.window_seconds,
    )

    assert vector.values == expected
    assert vector.values["byte_rate_a_to_b"] == 100.0
