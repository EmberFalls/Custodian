"""ObservationFrame creation and capability-aware pre-inference routing."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from custodian.core.enums import EvidenceAvailability, FeatureFamily, SourceType
from custodian.core.schemas import (
    CapabilityProfile,
    FeatureVector,
    FlowRecord,
    ObservationFrame,
)


def build_observation_frame(
    flow: FlowRecord,
    vector: FeatureVector,
    capabilities: CapabilityProfile,
    *,
    source_type: SourceType = SourceType.PCAP_REPLAY,
) -> ObservationFrame:
    """Describe evidence that is actually present without assuming capture completeness."""

    identity = "|".join(
        (source_type.value, vector.family.value, vector.entity_id, vector.window_id, flow.flow_id)
    )
    frame_id = "observation-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
    mask = {
        name: EvidenceAvailability.AVAILABLE if available else EvidenceAvailability.UNAVAILABLE
        for name, available in vector.availability.items()
    }
    return ObservationFrame(
        observation_frame_id=frame_id,
        source_type=source_type,
        entity_type="flow" if vector.entity_id == flow.flow_id else "host_window",
        entity_id=vector.entity_id,
        window_start=flow.start_time,
        window_end=flow.last_seen,
        capabilities=capabilities,
        sampling_known=False,
        sampling_rate=None,
        timestamp_resolution_ns=None,
        capture_completeness=None,
        packet_loss_indicated=None,
        usable_sample_count=flow.packets_a_to_b + flow.packets_b_to_a,
        parse_error_rate=0.0,
        evidence_mask=mask,
        limitations=("capture completeness and packet loss are unknown",),
    )


@dataclass(frozen=True, slots=True)
class RoutingResult:
    allowed: bool
    observation_confidence: float
    missing_capabilities: tuple[str, ...]
    reason: str | None


class CapabilityRouter:
    """Prevent a model from running when the input cannot support its family."""

    REQUIRED = {
        FeatureFamily.BEHAVIOUR: (
            "has_packet_timestamps",
            "has_packet_sizes",
            "has_directionality",
        ),
        FeatureFamily.DNS: ("has_dns_query_name",),
        FeatureFamily.TLS_QUIC: (),
    }
    ANY = {FeatureFamily.TLS_QUIC: ("has_tls_metadata", "has_quic_metadata")}

    def route(self, family: FeatureFamily, frame: ObservationFrame) -> RoutingResult:
        required = self.REQUIRED[family]
        missing = tuple(name for name in required if not getattr(frame.capabilities, name, False))
        any_capabilities = self.ANY.get(family, ())
        if any_capabilities and not any(
            getattr(frame.capabilities, name, False) for name in any_capabilities
        ):
            missing += ("one_of:" + ",".join(any_capabilities),)
        capability_coverage = (
            (len(required) - len([name for name in missing if not name.startswith("one_of:")]))
            / len(required)
            if required
            else (0.0 if missing else 1.0)
        )
        available_features = sum(
            state is EvidenceAvailability.AVAILABLE for state in frame.evidence_mask.values()
        )
        feature_coverage = available_features / max(len(frame.evidence_mask), 1)
        sample_quality = min(frame.usable_sample_count / 10, 1.0)
        confidence = round(
            max(
                0.0,
                min(1.0, 0.5 * capability_coverage + 0.3 * feature_coverage + 0.2 * sample_quality),
            ),
            6,
        )
        if missing:
            return RoutingResult(
                False,
                confidence,
                missing,
                "required passive evidence is unavailable",
            )
        return RoutingResult(True, confidence, (), None)
