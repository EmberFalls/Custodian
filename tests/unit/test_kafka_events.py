from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from custodian.config import KafkaSettings
from custodian.runtime.event_bus import (
    IdempotentEventHandler,
    KafkaEventBus,
    MetadataEvent,
    make_runtime_event,
)
from custodian.storage.postgres import PostgresRepository


def event(**updates):
    values = {
        "event_id": "e-1",
        "event_type": "runtime_event",
        "schema_version": "custodian.v1",
        "occurred_at": datetime.now(UTC),
        "run_id": "4",
        "capture_id": "cap-1",
        "correlation_id": "cap-1",
        "payload": {"application_event_id": "app-e-1", "name": "replay.started"},
    }
    return MetadataEvent(**(values | updates))


class FakeProducer:
    def __init__(self, fail=False):
        self.items = []
        self.fail = fail

    def produce(self, topic, **kwargs):
        if self.fail:
            raise RuntimeError("broker down")
        self.items.append((topic, kwargs))

    def flush(self, timeout):
        return 0

    def outq_len(self):
        return 0


def test_contract_and_publish_versioned_topic_with_identifiers():
    producer = FakeProducer()
    bus = KafkaEventBus(KafkaSettings(enabled=True), producer=producer)
    bus.publish(event())
    topic, message = producer.items[0]
    assert topic == "custodian.v1.runtime_event"
    decoded = MetadataEvent.model_validate_json(message["value"])
    assert (decoded.event_id, decoded.run_id, decoded.capture_id, decoded.correlation_id) == (
        "e-1",
        "4",
        "cap-1",
        "cap-1",
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"packet_payload": "secret packet bytes"},
        {"nested": {"jwt": "a.b.c"}},
        {"password": "nope"},
        {"note": "password=topsecret"},
        {"authorization": "Bearer abcdef0123456789"},
        {"metadata": b"raw"},
        {"model_binary": "AAAA"},
    ],
)
def test_contract_rejects_prohibited_payload_fields(payload):
    with pytest.raises(ValidationError):
        event(payload=payload)


@pytest.mark.parametrize(
    "kind,payload",
    [
        (
            "packet_observation",
            {
                "observation_id": "o1",
                "observed_at": datetime.now(UTC),
                "protocol": "tcp",
                "packet_length": 64,
                "raw_payload_text": "arbitrary packet",
            },
        ),
        (
            "flow_update",
            {
                "flow_id": "f1",
                "start_time": datetime.now(UTC),
                "last_seen": datetime.now(UTC),
                "protocol": "tcp",
                "source_ip": "1.1.1.1",
                "destination_ip": "2.2.2.2",
                "packets": 1,
                "bytes": 64,
                "payload_bytes": 4,
                "extra": "not in contract",
            },
        ),
    ],
)
def test_event_specific_contract_rejects_unknown_and_untrusted_fields(kind, payload):
    with pytest.raises(ValidationError):
        event(event_type=kind, payload=payload)


def test_event_contract_rejects_arbitrary_strings_even_with_safe_field_name():
    with pytest.raises(ValidationError):
        event(
            payload={
                "application_event_id": "app-1",
                "name": "replay.started",
                "description": "Bearer abcdef0123456789",
            }
        )


def feature_vector_event(values, *, family="behaviour", schema_version="behaviour.v1"):
    return event(
        event_type="feature_vector",
        payload={
            "vector_id": "window-1",
            "family": family,
            "schema_version": schema_version,
            "entity_id": "flow-1",
            "values": values,
            "availability": {name: value is not None for name, value in values.items()},
        },
    )


def test_feature_vector_accepts_complete_numeric_payload_byte_features():
    vector = feature_vector_event(
        {
            "payload_bytes_outbound": 12,
            "payload_bytes_inbound": 8,
            "payload_bytes_total": 20,
            "payload_packet_size_mean": 10.0,
            "payload_packet_size_variance": 0.0,
        }
    )
    assert vector.payload["values"] == {
        "payload_bytes_outbound": 12,
        "payload_bytes_inbound": 8,
        "payload_bytes_total": 20,
        "payload_packet_size_mean": 10.0,
        "payload_packet_size_variance": 0.0,
    }


@pytest.mark.parametrize(
    "values",
    [
        {"payload_bytes_outbound": "raw packet content"},
        {"payload_bytes_outbound": float("nan")},
        {"payload_bytes_outbound": 12, "unexpected_numeric_feature": 1},
        {"password": 1},
    ],
)
def test_feature_vector_rejects_non_numeric_or_unapproved_fields(values):
    with pytest.raises(ValidationError):
        feature_vector_event(values)


def test_sensitive_field_name_stays_rejected_outside_feature_contract():
    with pytest.raises(ValidationError):
        event(
            event_type="runtime_event",
            payload={
                "application_event_id": "app-1",
                "name": "replay.started",
                "payload_bytes_outbound": 12,
            },
        )


def test_unknown_version_and_topic_event_are_rejected():
    with pytest.raises(ValidationError):
        event(schema_version="custodian.v2")
    with pytest.raises(ValidationError):
        event(event_type="unknown")


def test_event_size_is_checked_before_publish():
    producer = FakeProducer()
    bus = KafkaEventBus(KafkaSettings(enabled=True, max_event_bytes=80), producer=producer)
    with pytest.raises(ValueError, match="max_event_bytes"):
        bus.publish(event())
    assert not producer.items


def test_disabled_mode_does_not_require_broker():
    bus = KafkaEventBus(KafkaSettings())
    bus.publish(event())
    assert bus.readiness()["status"] == "disabled"


def test_publish_retries_are_bounded_and_health_degrades(monkeypatch):
    producer = FakeProducer(fail=True)
    bus = KafkaEventBus(
        KafkaSettings(enabled=True, retries=2, retry_backoff_seconds=0), producer=producer
    )
    monkeypatch.setattr("custodian.runtime.event_bus.time.sleep", lambda _: None)
    with pytest.raises(RuntimeError, match="bounded retries"):
        bus.publish(event())
    assert bus.readiness()["status"] == "degraded"


def test_idempotent_handler_skips_duplicate_event_ids():
    calls = []
    handler = IdempotentEventHandler(calls.append)
    handler(event())
    handler(event())
    assert len(calls) == 1


def test_postgres_event_id_claim_is_idempotent():
    class Cursor:
        def __init__(self, row):
            self.row = row

        def fetchone(self):
            return self.row

    class Connection:
        claimed = set()

        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, sql, parameters):
            event_id = parameters[0]
            if event_id in self.claimed:
                return Cursor(None)
            self.claimed.add(event_id)
            return Cursor((event_id,))

    repository = PostgresRepository("postgresql://test", connection_factory=Connection)
    writes = []
    assert repository.process_event_once("e-1", lambda connection: writes.append("write"))
    assert not repository.process_event_once("e-1", lambda connection: writes.append("duplicate"))
    assert writes == ["write"]


def test_runtime_event_rejects_prohibited_data_and_propagates_ids():
    runtime = make_runtime_event(
        event_type="runtime_event",
        payload={"name": "replay.started"},
        run_id=7,
        capture_id="cap-7",
        correlation_id="corr-7",
    )
    assert (runtime.run_id, runtime.capture_id, runtime.correlation_id) == ("7", "cap-7", "corr-7")
    with pytest.raises(ValidationError):
        make_runtime_event(
            event_type="runtime_event",
            payload={"raw_packet": "blocked"},
            run_id=7,
            capture_id="cap-7",
        )


def test_settings_reject_remote_broker():
    with pytest.raises(ValidationError, match="loopback"):
        KafkaSettings(enabled=True, bootstrap_servers=("broker.example:9092",))


class FakeMessage:
    def error(self):
        return None

    def value(self):
        return b'{"event_id":"broken"}'

    def topic(self):
        return "custodian.v1.runtime_event"


class FakeConsumer:
    def __init__(self, message=None):
        self.commits = 0
        self.message = message or FakeMessage()

    def poll(self, timeout):
        return self.message

    def commit(self, **kwargs):
        self.commits += 1


def test_malformed_consumed_message_is_dead_lettered_and_committed_once():
    producer, consumer = FakeProducer(), FakeConsumer()
    bus = KafkaEventBus(KafkaSettings(enabled=True), producer=producer, consumer=consumer)
    bus.consume_once(lambda _: pytest.fail("malformed event reached handler"))
    assert producer.items[0][0] == "custodian.v1.dead_letter"
    assert consumer.commits == 1
    assert bus.readiness()["dead_letter_count"] == 1


def test_valid_consumed_message_reaches_handler_and_commits():
    class ValidMessage(FakeMessage):
        def value(self):
            return event().model_dump_json().encode()

    consumer = FakeConsumer(ValidMessage())
    bus = KafkaEventBus(KafkaSettings(enabled=True), producer=FakeProducer(), consumer=consumer)
    received = []
    assert bus.consume_once(received.append)
    assert received[0].event_id == "e-1"
    assert consumer.commits == 1


def test_consumer_creates_all_versioned_topics_before_subscribing(monkeypatch):
    import sys
    from types import ModuleType

    actions = []

    class Topic:
        def __init__(self, name, **kwargs):
            self.name = name

    class Future:
        def result(self, timeout):
            assert timeout == 10

    class Admin:
        def __init__(self, config):
            assert config["bootstrap.servers"] == "127.0.0.1:9092"

        def create_topics(self, topics):
            actions.append(("create", [topic.name for topic in topics]))
            return {topic.name: Future() for topic in topics}

    class Consumer:
        def __init__(self, _config):
            pass

        def subscribe(self, topics):
            actions.append(("subscribe", topics))

    kafka = ModuleType("confluent_kafka")
    kafka.Consumer = Consumer
    kafka.KafkaError = type("KafkaError", (), {"TOPIC_ALREADY_EXISTS": 1})
    admin_module = ModuleType("confluent_kafka.admin")
    admin_module.AdminClient = Admin
    admin_module.NewTopic = Topic
    monkeypatch.setitem(sys.modules, "confluent_kafka", kafka)
    monkeypatch.setitem(sys.modules, "confluent_kafka.admin", admin_module)

    bus = KafkaEventBus(KafkaSettings(enabled=True), producer=FakeProducer())
    bus.start_consumer()
    expected = [
        f"custodian.v1.{kind}"
        for kind in (
            "packet_observation",
            "flow_update",
            "feature_vector",
            "detector_verdict",
            "alert",
            "runtime_event",
            "dead_letter",
        )
    ]
    assert actions == [("create", expected), ("subscribe", expected)]


def test_consumer_rejects_event_topic_mismatch():
    class WrongTopic(FakeMessage):
        def value(self):
            return event().model_dump_json().encode()

        def topic(self):
            return "custodian.v1.alert"

    producer, consumer = FakeProducer(), FakeConsumer(WrongTopic())
    bus = KafkaEventBus(KafkaSettings(enabled=True), producer=producer, consumer=consumer)
    bus.consume_once(lambda _: pytest.fail("topic mismatch reached handler"))
    dead = MetadataEvent.model_validate_json(producer.items[0][1]["value"])
    assert dead.event_type == "dead_letter"
    assert dead.payload["error_code"] == "invalid_event"
    assert consumer.commits == 1


def test_consumer_handler_retries_are_bounded_before_dead_letter(monkeypatch):
    class ValidMessage(FakeMessage):
        def value(self):
            return event().model_dump_json().encode()

    producer, consumer = FakeProducer(), FakeConsumer(ValidMessage())
    bus = KafkaEventBus(
        KafkaSettings(enabled=True, retries=2, retry_backoff_seconds=0),
        producer=producer,
        consumer=consumer,
    )
    monkeypatch.setattr("custodian.runtime.event_bus.time.sleep", lambda _: None)
    attempts = []

    def fail(_event):
        attempts.append(1)
        raise ConnectionError("database unavailable")

    bus.consume_once(fail)
    dead = MetadataEvent.model_validate_json(producer.items[0][1]["value"])
    assert len(attempts) == 3
    assert dead.payload["error_code"] == "handler_failed"
    assert "database unavailable" not in dead.model_dump_json()
    assert consumer.commits == 1


def test_api_enabled_kafka_failure_is_visible_in_readiness_and_diagnostics(monkeypatch):
    from fastapi.testclient import TestClient

    from custodian.api.app import create_app
    from custodian.config import load_config_bundle
    from custodian.runtime.event_bus import KafkaEventBus

    class FailedProducer(FakeProducer):
        def __init__(self):
            super().__init__(fail=True)

    monkeypatch.setattr(KafkaEventBus, "start_consumer", lambda self: None)
    monkeypatch.setattr(KafkaEventBus, "consume_once", lambda self, handler: False)
    config = load_config_bundle("configs")
    for family, entry in config.models.models.items():
        config.models.models[family] = entry.model_copy(update={"artifact_path": None})
    config = config.model_copy(
        update={
            "storage": config.storage.model_copy(update={"enabled": False}),
            "kafka": config.kafka.model_copy(update={"enabled": True}),
        }
    )
    app = create_app(config)
    app.state.session.event_bus._producer = FailedProducer()
    event_bus = app.state.session.event_bus
    with TestClient(app) as client:
        try:
            event_bus.publish(event())
        except RuntimeError:
            pass
        assert client.get("/api/v1/readiness").json()["components"]["kafka"]["status"] == "degraded"
        assert client.get("/api/v1/diagnostics").json()["kafka"]["status"] == "degraded"


def test_pipeline_durable_handler_claims_event_once_and_updates_alert_once():
    class Cursor:
        def __init__(self, row):
            self.row = row

        def fetchone(self):
            return self.row

    class Connection:
        claimed = set()
        stored = {}

        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, sql, parameters):
            if "INSERT INTO processed_event_ids" in sql:
                event_id = parameters[0]
                if event_id in self.claimed:
                    return Cursor(None)
                self.claimed.add(event_id)
                return Cursor((event_id,))
            if "INSERT INTO alerts" in sql:
                self.stored[parameters[0]] = parameters[-1]
            return Cursor(None)

    repository = PostgresRepository("postgresql://test", connection_factory=Connection)
    alert_payload = {
        "alert_id": "alert-1",
        "capture_id": "cap-1",
        "timestamp": datetime.now(UTC),
        "threat_class": "scan",
        "severity": "high",
        "decision": "accept",
        "detector_id": "dns",
        "model_version": "1",
        "calibrated_confidence": 0.9,
        "status": "open",
        "occurrence_count": 1,
    }
    alert_event = event(event_id="alert-event-1", event_type="alert", payload=alert_payload)
    writes = []

    def process(ev):
        repository.process_event_once(
            ev.event_id,
            lambda conn: (
                PostgresRepository.apply_pipeline_event(conn, ev),
                writes.append(ev.event_id),
            ),
        )

    process(alert_event)
    process(alert_event)
    assert writes == ["alert-event-1"]
    assert list(Connection.stored) == ["alert-1"]


def test_replay_session_flushes_non_alert_stage_events():
    from custodian.api.app import ReplaySession
    from custodian.config import load_config_bundle
    from custodian.runtime.events import EventHub

    class Engine:
        capture_id = "cap-1"
        pipeline_events = [
            {
                "event_type": "flow_update",
                "payload": {
                    "flow_id": "flow-1",
                    "start_time": datetime.now(UTC).isoformat(),
                    "last_seen": datetime.now(UTC).isoformat(),
                    "protocol": "tcp",
                    "source_ip": "10.0.0.1",
                    "destination_ip": "10.0.0.2",
                    "packets": 1,
                    "bytes": 60,
                    "observed_payload_length": 20,
                },
            }
        ]

    class Bus:
        def __init__(self):
            self.published = []

        def publish(self, item):
            self.published.append(item)

    config = load_config_bundle("configs")
    config = config.model_copy(update={"kafka": config.kafka.model_copy(update={"enabled": True})})
    bus = Bus()
    session = ReplaySession(Engine(), config, event_hub=EventHub(), event_bus=bus)
    session.publish_pipeline_events()
    assert not session.engine.pipeline_events
    assert [item.event_type for item in bus.published] == ["flow_update"]
