from __future__ import annotations

import time
from pathlib import Path

import dpkt
from fastapi.testclient import TestClient

from custodian.api.app import create_app
from custodian.config import load_config_bundle
from custodian.ingestion.live_capture import CaptureInterface


class IdleHandle:
    def __init__(self, *, fail=False):
        self.filter = None
        self.closed = False
        self.fail = fail

    def datalink(self):
        return dpkt.pcap.DLT_EN10MB

    def setfilter(self, expression):
        self.filter = expression

    def next(self):
        if self.fail:
            raise OSError("capture backend stopped unexpectedly")
        time.sleep(0.005)
        return None, None

    def close(self):
        self.closed = True


class FakeBackend:
    def __init__(self, handle=None):
        self.handle = handle or IdleHandle()
        self.open_calls = []

    def list_interfaces(self):
        return [CaptureInterface("vm-lab-0", "VM Lab Adapter", "Isolated lab NIC")]

    def open_interface(self, interface_id, *, snaplen, timeout_ms):
        self.open_calls.append((interface_id, snaplen, timeout_ms))
        return self.handle


def _capture_config():
    root = Path(__file__).resolve().parents[2]
    bundle = load_config_bundle(root / "configs")
    models = {
        family: entry.model_copy(
            update={
                "artifact_path": None,
                "trusted": False,
                "variants": {
                    name: variant.model_copy(update={"artifact_path": None, "trusted": False})
                    for name, variant in entry.variants.items()
                },
            }
        )
        for family, entry in bundle.models.models.items()
    }
    return bundle.model_copy(
        update={
            "models": bundle.models.model_copy(update={"models": models}),
            "storage": bundle.storage.model_copy(update={"enabled": False}),
            "redis": bundle.redis.model_copy(update={"enabled": False}),
            "kafka": bundle.kafka.model_copy(update={"enabled": False}),
        }
    )


def test_live_capture_api_requires_selection_and_has_explicit_start_stop():
    backend = FakeBackend()
    app = create_app(_capture_config(), capture_backend=backend)
    with TestClient(app) as client:
        interfaces = client.get("/api/v1/live/interfaces").json()
        assert interfaces["status"] == "ready"
        assert interfaces["interfaces"][0]["interface_id"] == "vm-lab-0"
        assert backend.open_calls == []

        invalid = client.post("/api/v1/live/start", json={"interface_id": "missing"})
        assert invalid.status_code == 404
        assert backend.open_calls == []

        started = client.post(
            "/api/v1/live/start",
            json={"interface_id": "vm-lab-0", "capture_filter": "tcp"},
        )
        assert started.status_code == 200
        assert started.json()["source_type"] == "LIVE_PASSIVE"
        assert started.json()["selected_interface"] == "VM Lab Adapter"
        assert started.json()["capture_filter"] == "tcp"
        assert backend.handle.filter == "tcp"

        repeated_start = client.post("/api/v1/live/start", json={"interface_id": "vm-lab-0"})
        assert repeated_start.status_code == 400
        assert len(backend.open_calls) == 1

        stopping = client.post("/api/v1/live/stop")
        assert stopping.status_code == 200
        app.state.session.thread.join(2)
        assert client.get("/api/v1/live/status").json()["status"] == "STOPPED"
        assert backend.handle.closed
        assert client.post("/api/v1/live/stop").status_code == 400


def test_backend_failure_is_reported_and_handle_is_released():
    backend = FakeBackend(IdleHandle(fail=True))
    app = create_app(_capture_config(), capture_backend=backend)
    with TestClient(app) as client:
        response = client.post("/api/v1/live/start", json={"interface_id": "vm-lab-0"})
        assert response.status_code == 200
        app.state.session.thread.join(2)
        status = client.get("/api/v1/live/status").json()
        assert status["status"] == "ERROR"
        assert "stopped unexpectedly" in status["error"]
        assert backend.handle.closed
        readiness = client.get("/api/v1/readiness").json()
        diagnostics = client.get("/api/v1/diagnostics").json()
        assert readiness["components"]["live_capture"]["status"] == "degraded"
        assert "stopped unexpectedly" in readiness["components"]["live_capture"]["reason"]
        assert diagnostics["live_capture"]["state"] == "ERROR"
        assert diagnostics["live_capture"]["running"] is False


def test_missing_capture_backend_is_reported_without_starting_capture():
    from custodian.ingestion.live_capture import CaptureBackendUnavailable

    class MissingBackend:
        def list_interfaces(self):
            raise CaptureBackendUnavailable("pcapy-ng is not installed")

    app = create_app(_capture_config(), capture_backend=MissingBackend())
    with TestClient(app) as client:
        response = client.get("/api/v1/live/interfaces")
        assert response.json()["status"] == "unavailable"
        assert "not installed" in response.json()["reason"]
        assert client.get("/api/v1/status").json()["replay_running"] is False
