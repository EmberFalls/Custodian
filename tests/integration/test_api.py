"""API integration tests that do not rely on a model mock or demo capture."""

from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from custodian.api.app import create_app
from custodian.config import load_config_bundle
from custodian.core.enums import TransportProtocol
from custodian.core.schemas import Endpoint, FlowRecord, NumericStats


def config_without_artifacts():
    root = Path(__file__).resolve().parents[2]
    config = load_config_bundle(root / "configs")
    for name, entry in config.models.models.items():
        variants = {
            variant_name: variant.model_copy(update={"artifact_path": None, "trusted": False})
            for variant_name, variant in entry.variants.items()
        }
        config.models.models[name] = entry.model_copy(
            update={"artifact_path": None, "trusted": False, "variants": variants}
        )
    return config


def test_health_and_detector_status_are_honest_about_missing_artifacts() -> None:
    app = create_app(config_without_artifacts())
    client = TestClient(app)

    assert client.get("/health").json() == {"status": "ok", "return_path": "NONE"}
    assert client.get("/api/v1/health").json() == {"status": "ok", "return_path": "NONE"}
    readiness = client.get("/api/v1/readiness").json()
    assert readiness["status"] == "degraded"
    assert readiness["passive_only"] is True
    assert readiness["outbound_traffic_path"] is False
    assert readiness["components"]["kafka"]["status"] == "disabled"
    assert client.get("/api/v1/diagnostics").json()["kafka"]["enabled"] is False
    status = client.get("/api/v1/status").json()
    assert status["source_type"] == "PCAP_REPLAY"
    assert status["mode"] == "paced"
    assert status["replay_paused"] is False
    detector_status = client.get("/api/v1/detectors").json()
    assert all(not detector["enabled"] for detector in detector_status)
    assert all(not detector["artifact_trusted"] for detector in detector_status)
    assert {detector["id"] for detector in detector_status} == {
        "behaviour",
        "dns",
        "dns_dga",
        "tls_quic",
    }
    assert client.get("/api/v1/models").json() == detector_status
    response = client.get("/api/v1/health")
    assert response.headers["X-Correlation-ID"]
    export = client.post("/api/v1/exports", json={"format": "json"})
    assert export.status_code == 200
    assert export.json()["directory"] == "runtime/reports"


def test_dashboard_alert_and_flow_lists_read_postgres_repository():
    app = create_app(config_without_artifacts())
    app.state.repository.alerts["persisted-alert"] = {
        "alert_id": "persisted-alert",
        "status": "open",
        "decision": "ACCEPT",
    }
    observed_at = datetime(2026, 9, 25, tzinfo=UTC)
    flow = FlowRecord(
        flow_id="persisted-flow",
        start_time=observed_at,
        last_seen=observed_at,
        endpoint_a=Endpoint(ip="192.0.2.10", port=50000),
        endpoint_b=Endpoint(ip="192.0.2.20", port=443),
        protocol=TransportProtocol.TCP,
        packets_a_to_b=1,
        packets_b_to_a=0,
        bytes_a_to_b=64,
        bytes_b_to_a=0,
        packet_size_stats=NumericStats(count=1, minimum=64, maximum=64, mean=64, variance=0),
        inter_arrival_stats=NumericStats(count=0),
    )
    app.state.repository.upsert_flow(flow)

    with TestClient(app) as client:
        alerts = client.get("/api/v1/alerts").json()
        flows = client.get("/api/v1/flows").json()

    assert [item["alert_id"] for item in alerts] == ["persisted-alert"]
    assert [item["flow_id"] for item in flows] == ["persisted-flow"]


def test_readiness_reports_postgres_disconnect_after_startup():
    app = create_app(config_without_artifacts())

    def disconnected():
        raise ConnectionError("test database stopped")

    app.state.repository.health_check = disconnected
    with TestClient(app) as client:
        readiness = client.get("/api/v1/readiness").json()
    assert readiness["status"] == "degraded"
    assert readiness["components"]["database"] == {
        "status": "unavailable",
        "reason": "PostgreSQL is unavailable",
    }


def test_replay_modes_progress_and_reset(tmp_path):
    import dpkt

    from custodian.ingest.pcap import CaptureReader

    config = config_without_artifacts()
    config = config.model_copy(
        update={"replay": config.replay.model_copy(update={"capture_root": tmp_path})}
    )
    path = tmp_path / "api-test.cap"
    with path.open("wb") as stream:
        writer = dpkt.pcap.Writer(stream)
        writer.writepkt(b"unsupported fixture frame", ts=1)
        writer.writepkt(b"unsupported fixture frame", ts=3601)
    app = create_app(config)
    with TestClient(app) as client:
        captures = client.get("/api/v1/captures").json()
        assert captures == [
            {
                "display_name": path.name,
                "size_bytes": path.stat().st_size,
                "capture_id": None,
                "status": "queued",
                "sha256": None,
            }
        ]
        validation = client.post("/api/v1/captures/validate", json={"capture": path.name})
        assert validation.status_code == 200
        assert validation.json()["status"] == "ready"
        listed = client.get("/api/v1/captures").json()[0]
        assert listed["status"] == "ready" and listed["capture_id"].startswith("capture-")
        events = client.get("/api/v1/events?after_sequence=0").json()
        assert events["events"][-1]["event_type"] == "capture.ready"
        assert events["latest_sequence"] >= 1
        for mode in ("fast", "benchmark"):
            response = client.post(
                "/api/v1/replay/start",
                json={"capture": path.name, "mode": mode, "speed_multiplier": 2},
            )
            assert response.status_code == 200
            app.state.session.thread.join(2)
            status = client.get("/api/v1/status").json()
            assert client.get("/api/v1/replay/status").json() == status
            assert status["mode"] == mode and status["replay_state"] == "COMPLETED"
            assert status["progress"] == 1
            assert status["processed_capture_bytes"] == CaptureReader(path).size_bytes
            metrics = client.get("/api/v1/telemetry").json()["metrics"]
            assert metrics["packets"] == 2 and metrics["flow_updates"] == 0
            seek = client.post("/api/v1/replay/seek", json={"target_progress": 0.5})
            assert seek.status_code == 200
            app.state.session.thread.join(2)
            assert client.get("/api/v1/replay/status").json()["replay_state"] == "COMPLETED"
            assert client.post("/api/v1/replay/reset").status_code == 200
            assert client.get("/api/v1/metrics").json()["packets"] == 0
        assert (
            client.post("/api/v1/replay/start", json={"capture": "../outside.cap"}).status_code
            == 400
        )
        invalid = client.post("/api/v1/replay/start", json={"capture": path.name, "mode": "bad"})
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "REQUEST_VALIDATION_FAILED"
        assert invalid.headers["X-Correlation-ID"]
        with client.websocket_connect("/api/v1/stream/telemetry") as ws:
            assert {"status", "metrics", "detectors"} == set(ws.receive_json())
