"""Optional localhost Redpanda integration, opt in with CUSTODIAN_TEST_KAFKA=1."""

import os
import shutil
import socket
import subprocess
import time
from datetime import UTC, datetime
from uuid import uuid4

import psycopg
import pytest

from custodian.config import KafkaSettings
from custodian.runtime.event_bus import KafkaEventBus, make_runtime_event
from custodian.storage.postgres import PostgresRepository

ENABLED = os.getenv("CUSTODIAN_TEST_KAFKA") == "1"
pytestmark = pytest.mark.skipif(
    not ENABLED, reason="set CUSTODIAN_TEST_KAFKA=1 to run local Redpanda integration"
)


def _wait_for_port(host: str, port: int, timeout: float = 90) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return
        except OSError:
            time.sleep(1)
    raise TimeoutError("local Redpanda did not become ready on 127.0.0.1:9092")


def _start_kafka(compose: list[str]) -> None:
    subprocess.run(compose + ["up", "-d", "kafka"], check=True, timeout=180)
    try:
        deadline = time.monotonic() + 120
        last_output = ""
        while time.monotonic() < deadline:
            health = subprocess.run(
                compose
                + [
                    "exec",
                    "-T",
                    "kafka",
                    "rpk",
                    "cluster",
                    "health",
                    "--api-urls",
                    "127.0.0.1:9644",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
            last_output = health.stdout + health.stderr
            if health.returncode == 0:
                _wait_for_port("127.0.0.1", 9092)
                return
            time.sleep(2)
        logs = subprocess.run(
            compose + ["logs", "--tail", "100", "kafka"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        raise RuntimeError(
            "Local Kafka service did not become healthy. Last health check:\n"
            f"{last_output}\nKafka logs:\n{logs.stdout}\n{logs.stderr}"
        )
    except Exception:
        subprocess.run(compose + ["stop", "kafka"], check=False, timeout=60)
        raise


def _test_settings() -> KafkaSettings:
    """Give each integration run fresh topics so retained broker history is irrelevant."""
    run_id = uuid4().hex
    return KafkaSettings(
        enabled=True,
        consumer_group=f"test-{run_id}",
        topic_prefix=f"custodian.test-{run_id}.v1",
    )


def test_local_redpanda_publish_and_consume():
    docker = shutil.which("docker")
    if not docker:
        pytest.skip("Docker executable is unavailable")
    compose = [docker, "compose", "-f", "docker-compose.pilot.yml"]
    _start_kafka(compose)
    bus = None
    try:
        settings = _test_settings()
        bus = KafkaEventBus(settings)
        bus.start_consumer()
        event = make_runtime_event(
            event_type="runtime_event",
            payload={"application_event_id": f"app-{uuid4().hex}", "name": "test.kafka"},
            run_id=1,
            capture_id=f"capture-{uuid4().hex}",
        )
        bus.publish(event)
        received = []
        deadline = time.monotonic() + 30
        while not received and time.monotonic() < deadline:
            bus.consume_once(received.append)
        assert [item.event_id for item in received] == [event.event_id]
    finally:
        if bus is not None:
            bus.close()
        subprocess.run(compose + ["stop", "kafka"], check=False, timeout=60)


def test_local_redpanda_to_postgres_is_idempotent():
    """Exercise the Kafka consumer and PostgreSQL transaction as one path."""
    database_url = os.getenv("CUSTODIAN_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("set CUSTODIAN_TEST_DATABASE_URL to a dedicated local test database")
    docker = shutil.which("docker")
    if not docker:
        pytest.skip("Docker executable is unavailable")
    repository = PostgresRepository(database_url)
    repository.initialize()
    compose = [docker, "compose", "-f", "docker-compose.pilot.yml"]
    _start_kafka(compose)
    bus = None
    alert_id = f"it-alert-{uuid4().hex}"
    event_id = f"it-event-{uuid4().hex}"
    try:
        settings = _test_settings()
        bus = KafkaEventBus(settings)
        bus.start_consumer()
        event = make_runtime_event(
            event_type="alert",
            payload={
                "alert_id": alert_id,
                "capture_id": f"capture-{uuid4().hex}",
                "timestamp": datetime.now(UTC).isoformat(),
                "threat_class": "scan",
                "severity": "high",
                "decision": "accept",
                "detector_id": "integration-test",
                "model_version": "test-v1",
                "calibrated_confidence": 0.9,
                "status": "open",
                "occurrence_count": 1,
            },
            run_id=1,
            capture_id=f"capture-{uuid4().hex}",
        ).model_copy(update={"event_id": event_id})

        def handle(received):
            repository.process_event_once(
                received.event_id,
                lambda connection: repository.apply_pipeline_event(connection, received),
            )

        bus.publish(event)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            bus.consume_once(handle)
            with psycopg.connect(database_url) as connection:
                count = connection.execute(
                    "SELECT COUNT(*) FROM alerts WHERE alert_id=%s", (alert_id,)
                ).fetchone()[0]
            if count == 1:
                break
        assert count == 1

        # Republish the same ID and verify PostgreSQL's transaction claim suppresses it.
        bus.publish(event)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            bus.consume_once(handle)
            with psycopg.connect(database_url) as connection:
                alert_count = connection.execute(
                    "SELECT COUNT(*) FROM alerts WHERE alert_id=%s", (alert_id,)
                ).fetchone()[0]
                event_count = connection.execute(
                    "SELECT COUNT(*) FROM processed_event_ids WHERE event_id=%s", (event_id,)
                ).fetchone()[0]
            if alert_count == event_count == 1:
                break
        assert (alert_count, event_count) == (1, 1)
    finally:
        if bus is not None:
            bus.close()
        with psycopg.connect(database_url) as connection:
            connection.execute("DELETE FROM alerts WHERE alert_id=%s", (alert_id,))
            connection.execute("DELETE FROM processed_event_ids WHERE event_id=%s", (event_id,))
        subprocess.run(compose + ["stop", "kafka"], check=False, timeout=60)
