"""TLS/QUIC metadata features that never rely on decrypted payloads."""

from __future__ import annotations

from custodian.core.enums import FeatureFamily
from custodian.core.ids import make_window_id
from custodian.core.schemas import CapabilityProfile, FeatureVector, FlowRecord
from custodian.features.schema import TLS_QUIC_SCHEMA_VERSION, stable_bucket
from custodian.state.windows import TemporalSnapshot


class TLSQUICFeatureExtractor:
    """Create numeric encrypted-session metadata features from observed headers."""

    @staticmethod
    def metadata_values(
        *,
        duration_seconds: float | None,
        packet_count: int | None,
        total_bytes: int | float | None,
        packet_size_mean: float | None,
        packet_size_variance: float | None,
        inter_arrival_mean: float | None,
        inter_arrival_variance: float | None,
        packets_a_to_b: int | None,
        packets_b_to_a: int | None,
        bytes_a_to_b: int | float | None,
        bytes_b_to_a: int | float | None,
        tls_metadata: dict | None = None,
        quic_metadata: dict | None = None,
        destination_recurrence: float | None = None,
        connection_frequency: float | None = None,
    ) -> dict[str, int | float | None]:
        """Return the shared ``tls_quic.v1`` values from observable metadata.

        Dataset adapters call this boundary rather than reimplementing production
        formulas. Missing source fields stay ``None``; they are never replaced by
        invented packet counts, handshakes, timestamps, or identifiers.
        """

        metadata = tls_metadata or quic_metadata or {}
        fingerprint = metadata.get("ja3") if tls_metadata else None
        directional_ratio = (
            float(bytes_a_to_b) / (float(bytes_b_to_a) + 1.0)
            if bytes_a_to_b is not None and bytes_b_to_a is not None
            else None
        )
        byte_rate_a_to_b = (
            float(bytes_a_to_b) / duration_seconds
            if bytes_a_to_b is not None and duration_seconds is not None and duration_seconds > 0
            else None
        )
        byte_rate_b_to_a = (
            float(bytes_b_to_a) / duration_seconds
            if bytes_b_to_a is not None and duration_seconds is not None and duration_seconds > 0
            else None
        )
        return {
            "flow_duration_seconds": duration_seconds,
            "packet_count": packet_count,
            "total_bytes": total_bytes,
            "packet_size_mean": packet_size_mean,
            "packet_size_variance": packet_size_variance,
            "inter_arrival_mean": inter_arrival_mean,
            "inter_arrival_variance": inter_arrival_variance,
            "packets_a_to_b": packets_a_to_b,
            "packets_b_to_a": packets_b_to_a,
            "bytes_a_to_b": bytes_a_to_b,
            "bytes_b_to_a": bytes_b_to_a,
            "directional_byte_ratio": directional_ratio,
            "byte_rate_a_to_b": byte_rate_a_to_b,
            "byte_rate_b_to_a": byte_rate_b_to_a,
            "tls_record_version": metadata.get("record_version") if tls_metadata else None,
            "tls_cipher_suite_count": (
                metadata.get("cipher_suite_count") if tls_metadata else None
            ),
            "tls_extension_count": metadata.get("extension_count") if tls_metadata else None,
            "tls_fingerprint_bucket": stable_bucket(fingerprint) if fingerprint else None,
            "quic_version": metadata.get("version") if quic_metadata else None,
            "quic_long_header": (
                int(bool(metadata.get("long_header"))) if quic_metadata else None
            ),
            "destination_recurrence": destination_recurrence,
            "connection_frequency": connection_frequency,
        }

    def extract(
        self,
        flow: FlowRecord,
        state: TemporalSnapshot,
        capabilities: CapabilityProfile,
    ) -> FeatureVector:
        duration = max((flow.last_seen - flow.start_time).total_seconds(), 0.0)
        total_packets = flow.packets_a_to_b + flow.packets_b_to_a
        total_bytes = flow.bytes_a_to_b + flow.bytes_b_to_a
        values = self.metadata_values(
            duration_seconds=duration,
            packet_count=total_packets,
            total_bytes=total_bytes,
            packet_size_mean=flow.packet_size_stats.mean,
            packet_size_variance=flow.packet_size_stats.variance,
            inter_arrival_mean=flow.inter_arrival_stats.mean,
            inter_arrival_variance=flow.inter_arrival_stats.variance,
            packets_a_to_b=flow.packets_a_to_b,
            packets_b_to_a=flow.packets_b_to_a,
            bytes_a_to_b=flow.bytes_a_to_b,
            bytes_b_to_a=flow.bytes_b_to_a,
            tls_metadata=flow.tls_metadata,
            quic_metadata=flow.quic_metadata,
            destination_recurrence=(
                state.destination_counts.get(state.destination_ip, 0)
                / max(state.packet_count, 1)
            ),
            connection_frequency=state.flow_count / state.window_seconds,
        )
        availability = {key: value is not None for key, value in values.items()}
        return FeatureVector(
            family=FeatureFamily.TLS_QUIC,
            schema_version=TLS_QUIC_SCHEMA_VERSION,
            entity_id=flow.flow_id,
            window_id=make_window_id(state.source_ip, state.observed_at, state.window_seconds),
            values=values,
            availability=availability,
        )
