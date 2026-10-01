"""Validated metadata event contracts and optional Kafka transport."""

from __future__ import annotations

import re
import time
from collections import deque
from datetime import UTC, datetime
from ipaddress import ip_address
from math import isfinite
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from custodian.config import KafkaSettings

EVENT_TYPES = (
    "packet_observation",
    "flow_update",
    "feature_vector",
    "detector_verdict",
    "alert",
    "runtime_event",
    "dead_letter",
)
SENSITIVE_KEYS = re.compile(
    r"(payload_bytes|raw_packet|packet_payload|raw_payload|password|passwd|secret|token|jwt|credential|model_binary|artifact_bytes|private_key)",
    re.IGNORECASE,
)
SENSITIVE_VALUE = re.compile(
    r"(?:\bBearer\s+[A-Za-z0-9._~+/-]+=*|\b(?:password|passwd|secret|api[_-]?key|token)\s*[:=]\s*\S+|-----BEGIN [A-Z ]*PRIVATE KEY-----|\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b)",
    re.IGNORECASE,
)

# These are the application-owned feature contracts for the currently supported
# family schema versions. A feature name is exempt from the generic sensitive-key
# heuristic only inside FeatureVectorPayload.values and only when it is in this
# allowlist. The event's Pydantic contract still validates the value type.
_BEHAVIOUR_FEATURE_NAMES = frozenset(
    {
        "flow_duration_seconds",
        "packets_outbound",
        "packets_inbound",
        "packet_count",
        "bytes_outbound",
        "bytes_inbound",
        "packet_size_mean",
        "packet_size_variance",
        "inter_arrival_mean",
        "inter_arrival_variance",
        "protocol_id",
        "tcp_syn_count",
        "directional_byte_ratio",
        "flows_per_second",
        "packets_per_second",
        "bytes_per_second",
        "unique_destinations",
        "unique_destination_ports",
        "unique_sources_for_destination",
        "destination_entropy",
        "source_entropy_for_destination",
        "target_concentration",
        "destination_recurrence",
        "connection_count",
        "mean_connection_interval",
        "connection_interval_cv",
        "periodicity_score",
        "ports_per_host",
        "outbound_volume_window",
        "outbound_inbound_ratio_window",
        "history_seconds",
        "history_complete",
        "short_flow_ratio",
        "udp_share",
        "burstiness",
        "target_packets_per_second",
        "source_window_packets",
        "source_window_flow_count",
        "target_window_packets",
        "flow_payload_bytes_per_second",
        "payload_bytes_outbound",
        "payload_bytes_inbound",
        "payload_bytes_total",
        "payload_packet_size_mean",
        "payload_packet_size_variance",
        "payload_directional_ratio",
        "flow_packets_per_second",
    }
)
_DNS_FEATURE_NAMES = frozenset(
    {
        "domain_length",
        "subdomain_count",
        "mean_label_length",
        "character_entropy",
        "digit_ratio",
        "letter_ratio",
        "hyphen_ratio",
        "repeated_character_ratio",
        "query_type",
        "query_frequency",
        "unique_domain_ratio",
        *(f"bigram_bucket_{index}" for index in range(8)),
    }
)
_TLS_QUIC_FEATURE_NAMES = frozenset(
    {
        "flow_duration_seconds",
        "packet_count",
        "total_bytes",
        "packet_size_mean",
        "packet_size_variance",
        "inter_arrival_mean",
        "inter_arrival_variance",
        "packets_a_to_b",
        "packets_b_to_a",
        "bytes_a_to_b",
        "bytes_b_to_a",
        "directional_byte_ratio",
        "byte_rate_a_to_b",
        "byte_rate_b_to_a",
        "tls_record_version",
        "tls_cipher_suite_count",
        "tls_extension_count",
        "tls_fingerprint_bucket",
        "quic_version",
        "quic_long_header",
        "destination_recurrence",
        "connection_frequency",
    }
)
_FEATURE_NAMES_BY_FAMILY = {
    "behaviour": _BEHAVIOUR_FEATURE_NAMES,
    "dns": _DNS_FEATURE_NAMES,
    "tls_quic": _TLS_QUIC_FEATURE_NAMES,
}


def _metadata_only(
    value: Any, path: str = "payload", *, safe_numeric_keys: frozenset[str] = frozenset()
) -> None:
    if isinstance(value, (bytes, bytearray, memoryview)):
        raise ValueError(f"binary data is prohibited at {path}")
    if isinstance(value, dict):
        for key, child in value.items():
            if SENSITIVE_KEYS.search(str(key)) and not (
                path in {"payload.values", "payload.availability"}
                and str(key) in safe_numeric_keys
            ):
                raise ValueError(f"sensitive field is prohibited at {path}.{key}")
            if path == "payload.values" and str(key) in safe_numeric_keys:
                if child is not None and (
                    not isinstance(child, (bool, int, float))
                    or (not isinstance(child, bool) and not isfinite(child))
                ):
                    raise ValueError(f"feature value must be finite numeric metadata at {path}.{key}")
            else:
                _metadata_only(child, f"{path}.{key}", safe_numeric_keys=safe_numeric_keys)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _metadata_only(child, f"{path}[{index}]")
    elif isinstance(value, str) and SENSITIVE_VALUE.search(value):
        raise ValueError(f"credential-like value is prohibited at {path}")


class MetadataEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(min_length=1, max_length=128)
    event_type: str = Field(min_length=1)
    schema_version: str = Field(pattern=r"^custodian\.v1$")
    occurred_at: datetime
    run_id: str = Field(min_length=1, max_length=128)
    capture_id: str = Field(min_length=1, max_length=128)
    correlation_id: str = Field(min_length=1, max_length=128)
    payload: dict[str, Any]

    @field_validator("event_id", "run_id", "capture_id", "correlation_id")
    @classmethod
    def safe_identifier(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9:_-]+", value):
            raise ValueError("identifier contains unsupported characters")
        return value

    @field_validator("occurred_at")
    @classmethod
    def timestamp_must_include_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone")
        return value

    @field_validator("event_type")
    @classmethod
    def known_event_type(cls, value: str) -> str:
        if value not in EVENT_TYPES:
            raise ValueError("unsupported event_type")
        return value

    @model_validator(mode="after")
    def validate_typed_payload(self) -> MetadataEvent:
        """Reject arbitrary objects: each topic has a closed payload contract."""
        schemas = {
            "packet_observation": PacketObservationPayload,
            "flow_update": FlowUpdatePayload,
            "feature_vector": FeatureVectorPayload,
            "detector_verdict": DetectorVerdictPayload,
            "alert": AlertPayload,
            "runtime_event": RuntimeEventPayload,
            "dead_letter": DeadLetterPayload,
        }
        payload_type = schemas[self.event_type]
        validated_payload = payload_type.model_validate(self.payload)
        safe_numeric_keys = frozenset()
        if self.event_type == "feature_vector":
            safe_numeric_keys = _FEATURE_NAMES_BY_FAMILY[validated_payload.family]
            unknown_features = set(validated_payload.values) - safe_numeric_keys
            if unknown_features:
                raise ValueError(
                    f"unknown {validated_payload.schema_version} feature names: "
                    f"{', '.join(sorted(unknown_features))}"
                )
            for name, value in validated_payload.values.items():
                if value is not None and (
                    not isinstance(value, (bool, int, float))
                    or (not isinstance(value, bool) and not isfinite(value))
                ):
                    raise ValueError(f"feature {name!r} must be finite numeric metadata")
        object.__setattr__(self, "payload", validated_payload.model_dump(mode="json"))
        _metadata_only(self.payload, safe_numeric_keys=safe_numeric_keys)
        return self


class _Payload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PacketObservationPayload(_Payload):
    observation_id: str = Field(min_length=1, max_length=128)
    observed_at: datetime
    protocol: str = Field(pattern=r"^(tcp|udp|icmp|icmpv6|other)$")
    packet_length: int = Field(ge=0, le=65535)
    source_ip: str | None = None
    destination_ip: str | None = None
    source_port: int | None = Field(default=None, ge=0, le=65535)
    destination_port: int | None = Field(default=None, ge=0, le=65535)

    @field_validator("source_ip", "destination_ip")
    @classmethod
    def validate_ip(cls, value):
        return str(ip_address(value)) if value is not None else None


class FlowUpdatePayload(_Payload):
    flow_id: str = Field(min_length=1, max_length=128)
    start_time: datetime
    last_seen: datetime
    protocol: str = Field(pattern=r"^(tcp|udp|icmp|icmpv6|other)$")
    source_ip: str
    destination_ip: str
    packets: int = Field(ge=0)
    bytes: int = Field(ge=0)
    observed_payload_length: int = Field(ge=0)

    @field_validator("source_ip", "destination_ip")
    @classmethod
    def validate_ip(cls, value):
        return str(ip_address(value))


class FeatureVectorPayload(_Payload):
    vector_id: str = Field(min_length=1, max_length=128)
    family: str = Field(pattern=r"^(behaviour|dns|tls_quic)$")
    schema_version: str = Field(pattern=r"^(behaviour|dns|tls_quic)\.v1$")
    entity_id: str = Field(min_length=1, max_length=128)
    values: dict[str, float | int | bool | None]
    availability: dict[str, bool]

    @model_validator(mode="after")
    def values_match_availability(self):
        if set(self.values) != set(self.availability):
            raise ValueError("feature values and availability must have matching keys")
        if not re.fullmatch(rf"{self.family}\.v1", self.schema_version):
            raise ValueError("feature family and schema_version do not match")
        return self


class DetectorVerdictPayload(_Payload):
    result_id: str = Field(min_length=1, max_length=128)
    detector_id: str = Field(min_length=1, max_length=128)
    threat_class: str = Field(min_length=1, max_length=64)
    raw_score: float = Field(ge=0, le=1)
    calibrated_confidence: float = Field(ge=0, le=1)
    model_version: str = Field(min_length=1, max_length=128)
    feature_schema_version: str = Field(min_length=1, max_length=128)
    distribution_support: str = Field(
        pattern=r"^(supported|outside_evaluated_support|not_evaluated)$"
    )
    out_of_range_feature_count: int = Field(ge=0)


class AlertPayload(_Payload):
    alert_id: str = Field(min_length=1, max_length=128)
    capture_id: str = Field(min_length=1, max_length=128)
    timestamp: datetime
    threat_class: str = Field(min_length=1, max_length=64)
    severity: str = Field(min_length=1, max_length=32)
    decision: str = Field(min_length=1, max_length=64)
    detector_id: str = Field(min_length=1, max_length=128)
    model_version: str = Field(min_length=1, max_length=128)
    calibrated_confidence: float = Field(ge=0, le=1)
    status: str = Field(pattern=r"^(open|acknowledged|closed)$")
    occurrence_count: int = Field(ge=1)
    flow_id: str | None = Field(default=None, max_length=128)
    window_id: str | None = Field(default=None, max_length=128)
    source_ip: str | None = None
    destination_ip: str | None = None

    @field_validator("source_ip", "destination_ip")
    @classmethod
    def validate_ip(cls, value):
        return str(ip_address(value)) if value is not None else None


class RuntimeEventPayload(_Payload):
    application_event_id: str = Field(min_length=1, max_length=128)
    name: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,127}$")


class DeadLetterPayload(_Payload):
    source_topic: str = Field(min_length=1, max_length=249)
    original_event_id: str | None = Field(default=None, max_length=128)
    error_code: str = Field(
        pattern=r"^(invalid_event|handler_failed|oversize|broker_message_error)$"
    )


class EventPublisher(Protocol):
    def publish(self, event: MetadataEvent) -> None: ...

    def readiness(self) -> dict[str, Any]: ...

    def close(self) -> None: ...


class EventConsumer(Protocol):
    def consume_once(self, handler) -> bool: ...


class InProcessEventBus:
    """Bounded local publisher used when Kafka is disabled."""

    def __init__(self, max_events: int = 2000) -> None:
        self._events = deque(maxlen=max_events)

    def publish(self, event: MetadataEvent) -> None:
        self._events.append(event)

    def readiness(self) -> dict[str, Any]:
        return {
            "status": "disabled",
            "enabled": False,
            "producer": "in_process",
            "consumer": "in_process",
            "queue_backlog": len(self._events),
            "dead_letter_count": 0,
            "error": None,
        }

    def close(self) -> None:
        return None


class KafkaEventBus:
    """Synchronous bounded Kafka publisher; consumer lifecycle is explicitly driven."""

    def __init__(self, settings: KafkaSettings, *, producer=None, consumer=None) -> None:
        self.settings = settings
        self._producer = producer
        self._consumer = consumer
        self._error: str | None = None
        self._paused = False
        self._published = 0
        self._dead_letters = 0
        if settings.enabled and self._producer is None:
            try:
                from confluent_kafka import Producer
            except ImportError:
                self._error = "Kafka enabled but optional confluent-kafka package is missing"
            else:
                try:
                    self._producer = Producer(
                        {"bootstrap.servers": ",".join(settings.bootstrap_servers)}
                    )
                except Exception as exc:
                    self._error = str(exc)

    def _encode(self, event: MetadataEvent) -> bytes:
        encoded = event.model_dump_json().encode("utf-8")
        if len(encoded) > self.settings.max_event_bytes:
            raise ValueError("event exceeds configured max_event_bytes")
        return encoded

    def publish(self, event: MetadataEvent) -> None:
        value = self._encode(event)
        if self._producer is None:
            if self.settings.enabled:
                raise RuntimeError(self._error or "Kafka producer unavailable")
            return
        topic = f"{self.settings.topic_prefix}.{event.event_type}"
        if event.event_type == "dead_letter":
            self._publish_dead_letter(topic, value)
            return
        last_error = None
        for attempt in range(self.settings.retries + 1):
            try:
                self._producer.produce(
                    topic,
                    key=event.capture_id.encode(),
                    value=value,
                    on_delivery=self._delivery,
                )
                remaining = self._producer.flush(5)
                if remaining:
                    raise RuntimeError(f"producer flush left {remaining} messages queued")
                if self._error:
                    raise RuntimeError(self._error)
                self._published += 1
                self._error = None
                return
            except Exception as exc:
                last_error = exc
                self._error = f"publish failed ({type(exc).__name__})"
                if attempt < self.settings.retries:
                    time.sleep(min(self.settings.retry_backoff_seconds * (2**attempt), 5))
        raise RuntimeError(f"Kafka publish failed after bounded retries: {last_error}")

    def _publish_dead_letter(self, topic: str, value: bytes) -> None:
        """DLQ writes are single-attempt to avoid self-retry loops."""
        self._producer.produce(topic, value=value)
        remaining = self._producer.flush(5)
        if remaining:
            raise RuntimeError("dead-letter publish did not drain")

    def start_consumer(self) -> None:
        """Subscribe this process to the versioned contract topics."""
        if self._consumer is not None:
            return
        try:
            from confluent_kafka import Consumer, KafkaError
            from confluent_kafka.admin import AdminClient, NewTopic

            client_config = {"bootstrap.servers": ",".join(self.settings.bootstrap_servers)}
            admin = AdminClient(client_config)
            topic_names = [f"{self.settings.topic_prefix}.{kind}" for kind in EVENT_TYPES]
            topic_futures = admin.create_topics(
                [NewTopic(name, num_partitions=1, replication_factor=1) for name in topic_names]
            )
            for future in topic_futures.values():
                try:
                    future.result(timeout=10)
                except Exception as exc:
                    error = exc.args[0] if exc.args else None
                    if getattr(error, "code", lambda: None)() != KafkaError.TOPIC_ALREADY_EXISTS:
                        raise

            consumer = Consumer(
                {
                    **client_config,
                    "group.id": self.settings.consumer_group,
                    "enable.auto.commit": False,
                    "auto.offset.reset": "earliest",
                }
            )
            consumer.subscribe(topic_names)
            self._consumer = consumer
            self._error = None
        except Exception as exc:
            self._error = str(exc)
            raise RuntimeError(f"Kafka consumer unavailable: {exc}") from exc

    def _delivery(self, error, message) -> None:
        if error:
            self._error = str(error)

    def consume_once(self, handler) -> bool:
        if self._paused:
            return False
        if self._consumer is None:
            raise RuntimeError("Kafka consumer is not configured")
        message = self._consumer.poll(0.2)
        if message is None:
            return False
        error_code = "handler_failed"
        original_event_id = None
        try:
            if message.error():
                error_code = "broker_message_error"
                raise ValueError(str(message.error()))
            raw = message.value()
            if len(raw) > self.settings.max_event_bytes:
                error_code = "oversize"
                raise ValueError("event exceeds configured max_event_bytes")
            event = MetadataEvent.model_validate_json(raw)
            if message.topic() != f"{self.settings.topic_prefix}.{event.event_type}":
                error_code = "invalid_event"
                raise ValueError("event type does not match subscribed topic")
            original_event_id = event.event_id
            error_code = "handler_failed"
            last_handler_error = None
            for attempt in range(self.settings.retries + 1):
                try:
                    handler(event)
                    last_handler_error = None
                    break
                except Exception as handler_error:
                    last_handler_error = handler_error
                    if attempt < self.settings.retries:
                        time.sleep(min(self.settings.retry_backoff_seconds * (2**attempt), 5))
            if last_handler_error is not None:
                raise RuntimeError("consumer handler retries exhausted") from last_handler_error
            self._consumer.commit(message=message, asynchronous=False)
        except Exception as exc:
            self._dead_letters += 1
            self._error = f"consumer failed ({type(exc).__name__})"
            try:
                dead_id = f"dlq-{uuid4().hex}"
                dead = MetadataEvent(
                    event_id=dead_id,
                    event_type="dead_letter",
                    schema_version="custodian.v1",
                    occurred_at=datetime.now(UTC),
                    run_id="0",
                    capture_id="unknown",
                    correlation_id=original_event_id or dead_id,
                    payload={
                        "error_code": error_code,
                        "source_topic": message.topic(),
                        "original_event_id": original_event_id,
                    },
                )
                self._publish_dead_letter(
                    f"{self.settings.topic_prefix}.dead_letter", self._encode(dead)
                )
                self._consumer.commit(message=message, asynchronous=False)
            except Exception as dlq_error:
                self._error = f"dead-letter publish failed ({type(dlq_error).__name__})"
                self._paused = True
                try:
                    self._consumer.pause(self._consumer.assignment())
                except Exception:
                    pass
            return True
        return True

    def readiness(self) -> dict[str, Any]:
        status = (
            "disabled"
            if not self.settings.enabled
            else (
                "degraded"
                if self._error or self._consumer is None or self._producer is None
                else "ready"
            )
        )
        return {
            "status": status,
            "enabled": self.settings.enabled,
            "producer": "unavailable" if self._error else "ready" if self._producer else "disabled",
            "consumer": "ready" if self._consumer else "not_started",
            "queue_backlog": getattr(self._producer, "outq_len", lambda: 0)()
            if self._producer
            else 0,
            "dead_letter_count": self._dead_letters,
            "error": self._error,
        }

    def close(self) -> None:
        if self._producer:
            self._producer.flush(5)
        if self._consumer:
            self._consumer.close()


def make_runtime_event(
    *,
    event_type: str,
    payload: dict,
    run_id: int,
    capture_id: str | None,
    correlation_id: str | None = None,
) -> MetadataEvent:
    if event_type == "runtime_event" and "application_event_id" not in payload:
        payload = {**payload, "application_event_id": f"app-{uuid4().hex}"}
    return MetadataEvent(
        event_id=f"evt-{uuid4().hex}",
        event_type=event_type if event_type in EVENT_TYPES else "runtime_event",
        schema_version="custodian.v1",
        occurred_at=datetime.now(UTC),
        run_id=str(run_id),
        capture_id=capture_id or "none",
        correlation_id=correlation_id or (capture_id or f"run-{run_id}"),
        payload=payload,
    )


class IdempotentEventHandler:
    """Process event IDs once in-process; durable handlers should persist the ID."""

    def __init__(self, handler, max_seen: int = 100_000, claim_event=None) -> None:
        self.handler = handler
        self.max_seen = max_seen
        self.claim_event = claim_event
        self.seen: set[str] = set()

    def __call__(self, event: MetadataEvent) -> None:
        if event.event_id in self.seen:
            return
        if self.claim_event is not None and not self.claim_event(event.event_id):
            self.seen.add(event.event_id)
            return
        if len(self.seen) >= self.max_seen:
            raise RuntimeError(
                "in-process idempotency capacity exhausted; durable claim store required"
            )
        self.handler(event)
        self.seen.add(event.event_id)
