"""Frozen Pydantic contracts shared by ingest, training, runtime, and API layers."""

from __future__ import annotations

from datetime import datetime
from ipaddress import ip_address
from typing import Annotated, Literal, TypeAlias

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    IPvAnyAddress,
    JsonValue,
    model_validator,
)

from custodian.core.enums import (
    AlertDecision,
    AlertStatus,
    CaptureStatus,
    EvidenceAvailability,
    EvidenceQuality,
    FeatureFamily,
    FlowCloseReason,
    Severity,
    SourceType,
    ThreatClass,
    TransportProtocol,
)

NonNegativeInt: TypeAlias = Annotated[int, Field(ge=0)]
NonNegativeFloat: TypeAlias = Annotated[float, Field(ge=0)]
Probability: TypeAlias = Annotated[float, Field(ge=0, le=1)]
Port: TypeAlias = Annotated[int, Field(ge=0, le=65535)]
FeatureValue: TypeAlias = int | float | str | bool | None


class ContractModel(BaseModel):
    """Base configuration for stable cross-module data contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)


class Endpoint(ContractModel):
    """An observed network endpoint; ports are absent for non-port protocols."""

    ip: IPvAnyAddress
    port: Port | None = None


class NumericStats(ContractModel):
    """Compact descriptive statistics without retaining the underlying samples."""

    count: NonNegativeInt
    minimum: float | None = None
    maximum: float | None = None
    mean: float | None = None
    variance: NonNegativeFloat | None = None

    @model_validator(mode="after")
    def validate_population(self) -> NumericStats:
        values = (self.minimum, self.maximum, self.mean, self.variance)
        if self.count == 0 and any(value is not None for value in values):
            raise ValueError("empty statistics must not contain numeric values")
        if self.count > 0 and any(value is None for value in values):
            raise ValueError("non-empty statistics require minimum, maximum, mean, and variance")
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("minimum must not exceed maximum")
        return self


class PacketObservation(ContractModel):
    """Metadata for one packet passively observed from a replay capture."""

    timestamp: AwareDatetime
    src_ip: IPvAnyAddress
    dst_ip: IPvAnyAddress
    src_port: Port | None = None
    dst_port: Port | None = None
    protocol: TransportProtocol
    packet_length: NonNegativeInt
    payload_length: NonNegativeInt | None = None
    tcp_flags: frozenset[str] | None = None
    dns_metadata: dict[str, JsonValue] | None = None
    tls_metadata: dict[str, JsonValue] | None = None
    quic_metadata: dict[str, JsonValue] | None = None

    @model_validator(mode="after")
    def validate_protocol_fields(self) -> PacketObservation:
        if self.protocol in {TransportProtocol.TCP, TransportProtocol.UDP}:
            if self.src_port is None or self.dst_port is None:
                raise ValueError("TCP and UDP observations require source and destination ports")
        if self.protocol is not TransportProtocol.TCP and self.tcp_flags is not None:
            raise ValueError("TCP flags are only valid for TCP observations")
        return self


class CapturePacketCounts(ContractModel):
    """Validation and parser accounting attached to a capture."""

    observed: NonNegativeInt = 0
    parsed: NonNegativeInt = 0
    malformed: NonNegativeInt = 0
    unsupported: NonNegativeInt = 0
    truncated: NonNegativeInt = 0
    dropped: NonNegativeInt = 0


class CaptureRecord(ContractModel):
    """Identity and validation state for one allow-listed passive input."""

    capture_id: Annotated[str, Field(min_length=1)]
    source_type: SourceType
    display_name: Annotated[str, Field(min_length=1)]
    sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None = None
    size_bytes: NonNegativeInt
    created_at: AwareDatetime
    first_packet_at: AwareDatetime | None = None
    last_packet_at: AwareDatetime | None = None
    status: CaptureStatus
    packet_counts: CapturePacketCounts = Field(default_factory=CapturePacketCounts)
    parser_warnings: tuple[str, ...] = ()
    failure_reason: str | None = None

    @model_validator(mode="after")
    def validate_capture_state(self) -> CaptureRecord:
        if (
            self.last_packet_at
            and self.first_packet_at
            and self.last_packet_at < self.first_packet_at
        ):
            raise ValueError("last_packet_at must not precede first_packet_at")
        if self.status is CaptureStatus.FAILED and not self.failure_reason:
            raise ValueError("failed captures require a failure reason")
        if self.status is not CaptureStatus.FAILED and self.failure_reason:
            raise ValueError("failure_reason is only valid for failed captures")
        return self


class FlowRecord(ContractModel):
    """A bidirectional flow snapshot with canonical endpoints and preserved direction."""

    flow_id: Annotated[str, Field(min_length=1)]
    start_time: AwareDatetime
    last_seen: AwareDatetime
    endpoint_a: Endpoint
    endpoint_b: Endpoint
    protocol: TransportProtocol
    ip_version: Literal[4, 6]
    initiator_direction: Literal["a", "b", "unknown"] = "unknown"
    close_reason: FlowCloseReason | None = None
    packets_a_to_b: NonNegativeInt
    packets_b_to_a: NonNegativeInt
    bytes_a_to_b: NonNegativeInt
    bytes_b_to_a: NonNegativeInt
    packet_size_stats: NumericStats
    inter_arrival_stats: NumericStats
    tcp_flag_counts: dict[str, NonNegativeInt] = Field(default_factory=dict)
    initiator: Endpoint | None = None
    payload_bytes_a_to_b: NonNegativeInt = 0
    payload_bytes_b_to_a: NonNegativeInt = 0
    payload_size_stats: NumericStats | None = None
    dns_metadata: dict[str, JsonValue] | None = None
    tls_metadata: dict[str, JsonValue] | None = None
    quic_metadata: dict[str, JsonValue] | None = None

    @model_validator(mode="before")
    @classmethod
    def populate_ip_version(cls, values):
        if isinstance(values, dict) and values.get("ip_version") is None:
            endpoint = values.get("endpoint_a")
            if isinstance(endpoint, Endpoint):
                version = endpoint.ip.version
            elif isinstance(endpoint, dict) and endpoint.get("ip") is not None:
                version = ip_address(str(endpoint["ip"])).version
            else:
                return values
            values = dict(values)
            values["ip_version"] = version
        return values

    @model_validator(mode="after")
    def validate_flow(self) -> FlowRecord:
        if self.endpoint_a.ip.version != self.endpoint_b.ip.version:
            raise ValueError("flow endpoints must use the same IP version")
        if self.ip_version != self.endpoint_a.ip.version:
            raise ValueError("ip_version must match the canonical endpoints")
        if self.last_seen < self.start_time:
            raise ValueError("last_seen must not precede start_time")
        packet_count = self.packets_a_to_b + self.packets_b_to_a
        if self.packet_size_stats.count != packet_count:
            raise ValueError("packet_size_stats.count must match directional packet counts")
        expected_iat_count = max(packet_count - 1, 0)
        if self.inter_arrival_stats.count != expected_iat_count:
            raise ValueError("inter_arrival_stats.count must equal max(packet_count - 1, 0)")
        return self


class CapabilityProfile(ContractModel):
    """Evidence capabilities actually exposed by the passive observation path."""

    has_packet_timestamps: bool = False
    has_packet_sizes: bool = False
    has_directionality: bool = False
    has_tcp_flags: bool = False
    has_dns_query_name: bool = False
    has_dns_query_type: bool = False
    has_tls_metadata: bool = False
    has_tls_fingerprint: bool = False
    has_quic_metadata: bool = False
    has_bidirectional_stats: bool = False


class ObservationFrame(ContractModel):
    """Capabilities and quality actually visible for one passive observation."""

    observation_frame_id: Annotated[str, Field(min_length=1)]
    source_type: SourceType
    entity_type: Annotated[str, Field(min_length=1)]
    entity_id: Annotated[str, Field(min_length=1)]
    window_start: AwareDatetime
    window_end: AwareDatetime
    capabilities: CapabilityProfile
    sampling_known: bool = False
    sampling_rate: Probability | None = None
    timestamp_resolution_ns: NonNegativeInt | None = None
    capture_completeness: Probability | None = None
    packet_loss_indicated: bool | None = None
    usable_sample_count: NonNegativeInt = 0
    parse_error_rate: Probability = 0.0
    evidence_mask: dict[str, EvidenceAvailability] = Field(default_factory=dict)
    limitations: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_observation_quality(self) -> ObservationFrame:
        if self.window_end < self.window_start:
            raise ValueError("window_end must not precede window_start")
        if self.sampling_known != (self.sampling_rate is not None):
            raise ValueError("sampling_rate must be present exactly when sampling is known")
        return self


class ApplicationEvent(ContractModel):
    """Bounded event-stream record suitable for reconnect/resynchronization."""

    event_id: Annotated[str, Field(min_length=1)]
    sequence: Annotated[int, Field(ge=1)]
    event_type: Annotated[str, Field(min_length=1)]
    created_at: AwareDatetime
    run_id: NonNegativeInt
    payload: dict[str, JsonValue] = Field(default_factory=dict)


class FeatureVector(ContractModel):
    """Versioned features plus explicit per-feature availability."""

    family: FeatureFamily
    schema_version: Annotated[str, Field(min_length=1)]
    entity_id: Annotated[str, Field(min_length=1)]
    window_id: Annotated[str, Field(min_length=1)]
    values: dict[str, FeatureValue]
    availability: dict[str, bool]

    @model_validator(mode="after")
    def validate_schema_and_availability(self) -> FeatureVector:
        expected_schema = {
            FeatureFamily.BEHAVIOUR: "behaviour.v1",
            FeatureFamily.DNS: "dns.v1",
            FeatureFamily.TLS_QUIC: "tls_quic.v1",
        }[self.family]
        if self.schema_version != expected_schema:
            raise ValueError(f"{self.family.value} features require schema {expected_schema}")
        if set(self.values) != set(self.availability):
            raise ValueError("values and availability must contain identical feature names")
        for name, is_available in self.availability.items():
            value = self.values[name]
            if is_available and value is None:
                raise ValueError(f"available feature {name!r} must contain a value")
            if not is_available and value is not None:
                raise ValueError(f"unavailable feature {name!r} must be null")
        return self


class DetectorVerdict(ContractModel):
    """Common output returned by each calibrated detector family."""

    detector_id: Annotated[str, Field(min_length=1)]
    threat_class: ThreatClass
    raw_score: Probability
    calibrated_confidence: Probability
    threat_confidence: Probability | None = None
    observation_confidence: Probability | None = None
    observation_frame_id: str | None = None
    available_evidence: tuple[str, ...] = ()
    evidence: dict[str, JsonValue] = Field(default_factory=dict)
    required_evidence: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    model_version: Annotated[str, Field(min_length=1)]
    feature_schema_version: Annotated[str, Field(min_length=1)]
    inference_latency_ms: NonNegativeFloat
    scores: dict[str, Probability] = Field(default_factory=dict)
    limitations: tuple[str, ...] = ()
    stage_timings_ms: dict[str, NonNegativeFloat] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def populate_threat_confidence(cls, values):
        if isinstance(values, dict) and values.get("threat_confidence") is None:
            values = dict(values)
            values["threat_confidence"] = values.get("calibrated_confidence")
        return values

    @model_validator(mode="after")
    def validate_evidence_sets(self) -> DetectorVerdict:
        if not set(self.missing_evidence).issubset(self.required_evidence):
            raise ValueError("missing_evidence must be a subset of required_evidence")
        if set(self.available_evidence) & set(self.missing_evidence):
            raise ValueError("evidence cannot be both available and missing")
        return self


class AlertRecord(ContractModel):
    """Standard evidence-backed alert emitted after policy and evidence validation."""

    alert_id: Annotated[str, Field(min_length=1)]
    capture_id: str | None = None
    source_type: SourceType = SourceType.PCAP_REPLAY
    timestamp: AwareDatetime
    first_seen: AwareDatetime | None = None
    last_seen: AwareDatetime | None = None
    status: AlertStatus = AlertStatus.OPEN
    occurrence_count: Annotated[int, Field(ge=1)] = 1
    flow_id: str | None = None
    window_id: str | None = None
    threat_class: ThreatClass
    severity: Severity
    decision: AlertDecision
    calibrated_confidence: Probability
    threat_confidence: Probability | None = None
    observation_confidence: Probability | None = None
    observation_robustness: Probability | None = None
    observation_frame_id: str | None = None
    raw_score: Probability | None = None
    class_threshold: Probability | None = None
    emitted_at: AwareDatetime | None = None
    evidence_quality: EvidenceQuality
    source: Endpoint | None = None
    destination: Endpoint | None = None
    evidence: dict[str, JsonValue] = Field(default_factory=dict)
    missing_evidence: tuple[str, ...] = ()
    available_evidence: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    capabilities: CapabilityProfile | None = None
    detector_id: Annotated[str, Field(min_length=1)]
    model_version: Annotated[str, Field(min_length=1)]
    feature_schema_version: Annotated[str, Field(min_length=1)]
    inference_latency_ms: NonNegativeFloat
    total_pipeline_latency_ms: NonNegativeFloat
    stage_timings_ms: dict[str, NonNegativeFloat] = Field(default_factory=dict)
    policy_versions: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def populate_alert_threat_confidence(cls, values):
        if isinstance(values, dict) and values.get("threat_confidence") is None:
            values = dict(values)
            values["threat_confidence"] = values.get("calibrated_confidence")
        return values

    @model_validator(mode="after")
    def validate_context_and_evidence(self) -> AlertRecord:
        if not self.flow_id and not self.window_id:
            raise ValueError("an alert requires at least one of flow_id or window_id")
        if self.decision is AlertDecision.INSUFFICIENT_EVIDENCE and not self.missing_evidence:
            raise ValueError("INSUFFICIENT_EVIDENCE alerts must list missing evidence")
        if self.evidence_quality is EvidenceQuality.INSUFFICIENT and not self.missing_evidence:
            raise ValueError("INSUFFICIENT evidence quality must list missing evidence")
        return self


# The full-build name for the single structured alert contract. AlertRecord remains
# as a source-compatible alias while callers migrate.
ProofStreamAlert = AlertRecord


Timestamp = datetime
