"""API integration tests that do not rely on a model mock or demo capture."""

from pathlib import Path

from fastapi.testclient import TestClient

from custodian.api.app import create_app
from custodian.config import load_config_bundle


def config_without_artifacts():
    root = Path(__file__).resolve().parents[2]
    config = load_config_bundle(root / "configs")
    for name, entry in config.models.models.items():
        config.models.models[name] = entry.model_copy(update={"artifact_path": None})
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
