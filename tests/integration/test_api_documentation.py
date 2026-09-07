"""Executable checks for the public examples and inventory in docs/api.md."""

from pathlib import Path

import dpkt
from fastapi.testclient import TestClient

from custodian.api.app import create_app
from custodian.config import load_config_bundle

ROOT = Path(__file__).resolve().parents[2]
API_DOC = ROOT / "docs" / "api.md"


def documented_app(tmp_path: Path, *, storage_enabled: bool = True):
    """Build an isolated API instance without loading unapproved model artifacts."""
    config = load_config_bundle(ROOT / "configs")
    model_entries = {
        family: entry.model_copy(update={"artifact_path": None})
        for family, entry in config.models.models.items()
    }
    capture_root = tmp_path / "captures"
    capture_root.mkdir()
    config = config.model_copy(
        update={
            "models": config.models.model_copy(update={"models": model_entries}),
            "replay": config.replay.model_copy(update={"capture_root": capture_root}),
            "storage": config.storage.model_copy(
                update={
                    "enabled": storage_enabled,
                    "database_path": tmp_path / "runtime" / "custodian.sqlite3",
                }
            ),
        }
    )
    return create_app(config), capture_root


def write_documented_capture(path: Path) -> None:
    """Write a harmless parser fixture; no packet is ever transmitted."""
    with path.open("wb") as stream:
        writer = dpkt.pcap.Writer(stream)
        writer.writepkt(b"unsupported documentation fixture", ts=1)
        writer.writepkt(b"unsupported documentation fixture", ts=2)


def test_openapi_inventory_has_human_readable_metadata(tmp_path: Path) -> None:
    app, _ = documented_app(tmp_path)
    expected_operations = {
        ("/api/v1/auth/login", "post"),
        ("/api/v1/auth/me", "get"),
        ("/api/v1/auth/logout", "post"),
        ("/api/v1/auth/demo-credentials", "get"),
        ("/health", "get"),
        ("/api/v1/health", "get"),
        ("/api/v1/readiness", "get"),
        ("/api/v1/status", "get"),
        ("/api/v1/replay/status", "get"),
        ("/api/v1/captures", "get"),
        ("/api/v1/captures/validate", "post"),
        ("/api/v1/alerts", "get"),
        ("/api/v1/alerts/{alert_id}", "get"),
        ("/api/v1/alerts/{alert_id}/acknowledge", "post"),
        ("/api/v1/alerts/{alert_id}/close", "post"),
        ("/api/v1/metrics", "get"),
        ("/api/v1/detectors", "get"),
        ("/api/v1/models", "get"),
        ("/api/v1/flows", "get"),
        ("/api/v1/timeline", "get"),
        ("/api/v1/diagnostics", "get"),
        ("/api/v1/events", "get"),
        ("/api/v1/exports", "post"),
        ("/api/v1/telemetry", "get"),
        ("/api/v1/replay/start", "post"),
        ("/api/v1/replay/pause", "post"),
        ("/api/v1/replay/resume", "post"),
        ("/api/v1/replay/stop", "post"),
        ("/api/v1/replay/seek", "post"),
        ("/api/v1/replay/reset", "post"),
    }

    with TestClient(app) as client:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()

    assert schema["info"]["title"] == "Custodian API"
    assert schema["info"]["version"] == "0.3.0"
    assert "passive-only" in schema["info"]["description"]
    actual_operations = {
        (path, method)
        for path, path_item in schema["paths"].items()
        for method in path_item
        if method in {"get", "post", "put", "patch", "delete"}
    }
    assert actual_operations == expected_operations
    for path, method in expected_operations:
        operation = schema["paths"][path][method]
        assert operation["summary"]
        assert operation["tags"]


def test_reference_mentions_every_http_and_websocket_route(tmp_path: Path) -> None:
    app, _ = documented_app(tmp_path)
    reference = API_DOC.read_text(encoding="utf-8")
    documented_paths = set(app.openapi()["paths"])
    documented_paths.update(
        {
            "/api/v1/stream/telemetry",
            "/api/v1/stream/alerts",
            "/api/v1/stream/metrics",
        }
    )

    for path in documented_paths:
        assert path in reference
    assert "Authentication is **not a production authorization boundary**" in reference
    assert "does not scan a network" in reference
    assert "Prototype versus planned API" in reference


def test_documented_http_examples_work_locally(tmp_path: Path) -> None:
    app, capture_root = documented_app(tmp_path)
    capture_path = capture_root / "http.cap"
    write_documented_capture(capture_path)

    with TestClient(app) as client:
        health = client.get(
            "/api/v1/health", headers={"X-Correlation-ID": "docs-example-001"}
        )
        assert health.status_code == 200
        assert health.json() == {"status": "ok", "return_path": "NONE"}
        assert health.headers["X-Correlation-ID"] == "docs-example-001"

        readiness = client.get("/api/v1/readiness").json()
        assert readiness["passive_only"] is True
        assert readiness["outbound_traffic_path"] is False
        assert set(readiness["components"]) == {
            "parser",
            "event_stream",
            "database",
            "models",
            "inputs",
        }

        status = client.get("/api/v1/status").json()
        assert client.get("/api/v1/replay/status").json() == status
        assert status["replay_state"] == "IDLE"
        assert status["return_path"] == "NONE"

        captures = client.get("/api/v1/captures").json()
        assert [item["display_name"] for item in captures] == ["http.cap"]
        validated = client.post(
            "/api/v1/captures/validate", json={"capture": "http.cap"}
        )
        assert validated.status_code == 200
        assert validated.json()["status"] == "ready"
        assert validated.json()["sha256"]

        started = client.post(
            "/api/v1/replay/start",
            json={"capture": "http.cap", "mode": "fast", "speed_multiplier": 1},
        )
        assert started.status_code == 200
        assert started.json() == {"status": "started", "capture": "http.cap"}
        app.state.session.thread.join(2)
        completed = client.get("/api/v1/replay/status").json()
        assert completed["replay_state"] == "COMPLETED"
        assert completed["progress"] == 1

        metrics = client.get("/api/v1/metrics").json()
        assert metrics["packets"] == 2
        assert metrics["unsupported_frames"] == 2
        telemetry = client.get("/api/v1/telemetry").json()
        assert set(telemetry) == {"status", "metrics", "detectors"}
        assert client.get("/api/v1/alerts?limit=100&offset=0").json() == []
        assert client.get("/api/v1/models").json() == client.get(
            "/api/v1/detectors"
        ).json()
        assert client.get("/api/v1/flows?limit=100").json() == []
        assert client.get("/api/v1/timeline?limit=100").json() == []
        assert set(client.get("/api/v1/diagnostics").json()) == {
            "routing",
            "model_load_errors",
            "inputs",
        }

        events = client.get("/api/v1/events?after_sequence=0&limit=200").json()
        assert events["events"]
        assert events["latest_sequence"] >= events["events"][-1]["sequence"]

        exported = client.post(
            "/api/v1/exports", json={"format": "json", "anonymize": True}
        )
        assert exported.status_code == 200
        assert exported.json()["status"] == "created"
        assert exported.json()["anonymized"] is True
        assert exported.json()["filename"].endswith(".json")

        reset = client.post("/api/v1/replay/reset")
        assert reset.status_code == 200
        assert reset.json() == {"status": "reset"}


def test_documented_error_envelopes_are_stable(tmp_path: Path) -> None:
    app, _ = documented_app(tmp_path)
    with TestClient(app) as client:
        missing = client.get(
            "/api/v1/alerts/not-present",
            headers={"X-Correlation-ID": "docs-error-404"},
        )
        assert missing.status_code == 404
        assert missing.json()["error"] == {
            "code": "HTTP_404",
            "message": "alert not found or no longer retained",
            "correlation_id": "docs-error-404",
        }

        invalid = client.post(
            "/api/v1/replay/start",
            headers={"X-Correlation-ID": "docs-error-422"},
            json={"capture": "http.cap", "mode": "not-a-mode"},
        )
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "REQUEST_VALIDATION_FAILED"
        assert invalid.json()["error"]["correlation_id"] == "docs-error-422"
        assert invalid.json()["error"]["fields"]

        invalid_bounds = client.get("/api/v1/flows?limit=501")
        assert invalid_bounds.status_code == 400
        assert invalid_bounds.json()["error"]["code"] == "HTTP_400"
        invalid_host = client.get("/api/v1/timeline?host=not-an-ip")
        assert invalid_host.status_code == 400
        invalid_pagination = client.get("/api/v1/alerts?limit=0")
        assert invalid_pagination.status_code == 400
        invalid_event_limit = client.get("/api/v1/events?limit=501")
        assert invalid_event_limit.status_code == 400
        invalid_export = client.post("/api/v1/exports", json={"format": "xml"})
        assert invalid_export.status_code == 422
        no_active_replay = client.post("/api/v1/replay/pause")
        assert no_active_replay.status_code == 400


def test_documented_replay_control_state_transitions(tmp_path: Path) -> None:
    app, capture_root = documented_app(tmp_path)
    capture_path = capture_root / "paced.cap"
    with capture_path.open("wb") as stream:
        writer = dpkt.pcap.Writer(stream)
        writer.writepkt(b"first passive fixture frame", ts=1)
        writer.writepkt(b"second passive fixture frame", ts=3601)

    with TestClient(app) as client:
        started = client.post(
            "/api/v1/replay/start",
            json={"capture": "paced.cap", "mode": "paced", "speed_multiplier": 1},
        )
        assert started.status_code == 200
        paused = client.post("/api/v1/replay/pause")
        assert paused.json() == {"status": "paused"}
        assert client.get("/api/v1/replay/status").json()["replay_paused"] is True

        duplicate = client.post(
            "/api/v1/replay/start", json={"capture": "paced.cap", "mode": "fast"}
        )
        assert duplicate.status_code == 400
        assert client.post("/api/v1/replay/reset").status_code == 400

        resumed = client.post("/api/v1/replay/resume")
        assert resumed.json() == {"status": "running"}
        stopped = client.post("/api/v1/replay/stop")
        assert stopped.json() == {"status": "stopping"}
        app.state.session.thread.join(2)
        assert client.get("/api/v1/replay/status").json()["replay_state"] == "STOPPED"
        assert client.post("/api/v1/replay/reset").json() == {"status": "reset"}


def test_documented_persistence_failures_and_event_cursor(tmp_path: Path) -> None:
    app, _ = documented_app(tmp_path, storage_enabled=False)
    with TestClient(app) as client:
        readiness = client.get("/api/v1/readiness").json()
        assert readiness["components"]["database"]["status"] == "unavailable"
        export = client.post("/api/v1/exports", json={"format": "json"})
        assert export.status_code == 503
        assert export.json()["error"]["code"] == "HTTP_503"
        acknowledge = client.post("/api/v1/alerts/not-present/acknowledge")
        assert acknowledge.status_code == 503
        close = client.post("/api/v1/alerts/not-present/close")
        assert close.status_code == 503

        future_cursor = client.get("/api/v1/events?after_sequence=999").json()
        assert future_cursor["cursor_reset"] is True
        assert future_cursor["latest_sequence"] == 0
        assert future_cursor["earliest_sequence"] == 1


def test_documented_websocket_payloads_work_locally(tmp_path: Path) -> None:
    app, capture_root = documented_app(tmp_path)
    capture_path = capture_root / "events.cap"
    write_documented_capture(capture_path)

    with TestClient(app) as client:
        client.post("/api/v1/captures/validate", json={"capture": "events.cap"})

        with client.websocket_connect("/api/v1/stream/telemetry") as socket:
            assert set(socket.receive_json()) == {"status", "metrics", "detectors"}
        with client.websocket_connect("/api/v1/stream/alerts") as socket:
            assert set(socket.receive_json()) == {"run_id", "alerts"}
        with client.websocket_connect("/api/v1/stream/metrics") as socket:
            assert "packets" in socket.receive_json()
        with client.websocket_connect("/api/v1/events?after_sequence=0") as socket:
            event_page = socket.receive_json()
            assert event_page["events"]
            assert event_page["events"][-1]["event_type"] == "capture.ready"
