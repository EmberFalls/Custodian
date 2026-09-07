"""Local API for bounded passive replay, controls and aggregated telemetry."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from hashlib import sha256
from ipaddress import ip_address
from pathlib import Path
from threading import RLock, Thread
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse

from custodian.config import ConfigBundle, load_config_bundle
from custodian.core.enums import AlertStatus, CaptureStatus, ReplayMode
from custodian.core.schemas import AlertRecord, CapturePacketCounts, CaptureRecord
from custodian.exports import ExportService
from custodian.ingest.pcap import SUPPORTED_DATALINKS, CaptureReader
from custodian.ingest.replay import ReplayController
from custodian.ingestion import adapter_statuses
from custodian.ingestion.validation import CaptureValidator
from custodian.runtime.engine import CustodianEngine
from custodian.runtime.events import EventHub
from custodian.storage import SQLiteRepository

API_DESCRIPTION = """
Local, passive-only API for authorized capture-file analysis. Custodian reads packets from
approved files, produces bounded metadata and evidence-aware alerts, and exposes local telemetry.
It does not scan, inject, block, replay packets onto a network, or decrypt TLS/QUIC payloads.

Authentication is not implemented in this prototype. Keep the supported server binding on
`127.0.0.1`; trusted-host filtering is not a substitute for user authentication.
""".strip()

OPENAPI_TAGS = [
    {"name": "system", "description": "Health, readiness, and diagnostics."},
    {"name": "captures", "description": "Discover and validate confined capture files."},
    {"name": "replay", "description": "Control passive local capture-file processing."},
    {"name": "telemetry", "description": "Runtime counters, rates, resources, and status."},
    {"name": "alerts", "description": "Evidence-aware alerts and analyst lifecycle."},
    {"name": "detectors", "description": "Detector/model availability and trust state."},
    {"name": "traffic", "description": "Bounded flow summaries and host timelines."},
    {"name": "events", "description": "Cursor-aware bounded application events."},
    {"name": "exports", "description": "Local persisted-alert report generation."},
]


class ReplayStartRequest(BaseModel):
    capture: str = Field(min_length=1)
    mode: ReplayMode | None = None
    speed_multiplier: Literal[1, 2, 5, 10] | None = None


class CaptureValidateRequest(BaseModel):
    capture: str = Field(min_length=1, max_length=255)


class ReplaySeekRequest(BaseModel):
    target_progress: float = Field(ge=0, le=1)


class ExportRequest(BaseModel):
    format: Literal["json", "csv"]
    anonymize: bool = False


class ReplaySession:
    def __init__(
        self,
        engine: CustodianEngine,
        config: ConfigBundle,
        repository: SQLiteRepository | None = None,
        event_hub: EventHub | None = None,
    ) -> None:
        self.engine, self.config = engine, config
        self.repository = repository
        self.event_hub = event_hub or EventHub()
        self.capture_root = config.replay.capture_root.resolve()
        self.validator = CaptureValidator(
            self.capture_root, max_size_bytes=config.replay.max_capture_size_bytes
        )
        self.validated: dict[str, CaptureRecord] = {}
        self.thread: Thread | None = None
        self.controller: ReplayController | None = None
        self.running = False
        self.capture: str | None = None
        self.error: str | None = None
        self.state = "IDLE"
        self.run_id = 0
        self.capture_size_bytes = 0
        self._lock = RLock()

    def _publish(self, event_type: str, payload: dict) -> None:
        event = self.event_hub.publish(event_type, payload, run_id=self.run_id)
        if self.repository:
            self.repository.record_event(
                event.event_id, event.event_type, event.model_dump(mode="json")
            )

    def validate(self, capture: str):
        with self._lock:
            if self.running:
                raise RuntimeError("capture validation is unavailable while replay is running")
            self.state, self.error = "VALIDATING", None
        try:
            record = self.validator.validate(capture)
        except Exception as exc:
            with self._lock:
                self.state, self.error = "FAILED", str(exc)
            raise
        with self._lock:
            self.validated[capture] = record
            self.state = "READY"
        if self.repository:
            self.repository.upsert_capture(record)
            self.repository.save_checkpoint(
                f"{record.capture_id}:origin",
                record.capture_id,
                0.0,
                {
                    "strategy": "deterministic_rebuild_from_start",
                    "restorable": True,
                    "contains_raw_payload": False,
                },
            )
        self._publish(
            "capture.ready", {"capture_id": record.capture_id, "name": record.display_name}
        )
        return record

    def _set_capture_status(self, status: CaptureStatus, failure_reason: str | None = None) -> None:
        if not self.capture:
            return
        record = self.validated.get(self.capture)
        if record is None:
            return
        update: dict[str, object] = {
            "status": status,
            "failure_reason": failure_reason,
        }
        if status in {
            CaptureStatus.COMPLETED,
            CaptureStatus.STOPPED,
            CaptureStatus.FAILED,
        }:
            metrics = self.engine.metrics
            update["packet_counts"] = CapturePacketCounts(
                observed=metrics.packet_count,
                parsed=metrics.parsed_packets,
                malformed=metrics.malformed_frames,
                unsupported=metrics.unsupported_frames,
                truncated=metrics.truncated_frames,
                dropped=metrics.dropped_frames,
            )
        updated = record.model_copy(update=update)
        self.validated[self.capture] = updated
        if self.repository:
            self.repository.upsert_capture(updated)

    @property
    def telemetry_interval(self):
        benchmark = self.controller and self.controller.mode is ReplayMode.BENCHMARK
        return (
            self.config.replay.benchmark_telemetry_interval_ms
            if benchmark
            else self.config.replay.telemetry_interval_ms
        ) / 1000

    def start(
        self, capture: str, mode: ReplayMode | None = None, speed_multiplier: float | None = None
    ) -> None:
        with self._lock:
            if self.running:
                raise RuntimeError("a replay is already running")
            candidate = self.validator.resolve(capture)
            record = self.validated.get(capture)
            if record is None:
                record = self.validator.validate(capture)
                self.validated[capture] = record
            reader = CaptureReader(candidate)
            datalink = reader.datalink()
            if datalink not in SUPPORTED_DATALINKS:
                raise ValueError(
                    f"unsupported link-layer type {datalink}; choose an Ethernet, Linux cooked, or raw-IP capture"
                )
            self.controller = ReplayController(
                reader,
                mode=mode or self.config.replay.mode,
                speed_multiplier=speed_multiplier or self.config.replay.speed_multiplier,
            )
            self.engine.reset()
            self.engine.capture_id = record.capture_id
            self.capture, self.error = capture, None
            self.capture_size_bytes = reader.size_bytes
            self.state, self.running = "RUNNING", True
            self.run_id += 1
            controller = self.controller
            self._set_capture_status(CaptureStatus.RUNNING)
            self._publish("replay.started", {"capture": capture, "mode": controller.mode.value})
            self._launch(controller)

    def _launch(self, controller: ReplayController) -> None:
        def run():
            try:
                for alert in self.engine.run_controller(controller):
                    if self.repository:
                        record = self.validated.get(self.capture or "")
                        capture_id = getattr(record, "capture_id", None)
                        self.repository.upsert_alert(alert, capture_id=capture_id)
                    self._publish(
                        "alert.upserted",
                        {"alert_id": alert.alert_id, "decision": alert.decision.value},
                    )
                if self.repository:
                    record = self.validated.get(self.capture or "")
                    capture_id = record.capture_id if record else None
                    for flow in self.engine.recent_flows:
                        self.repository.upsert_flow(flow, capture_id=capture_id)
                with self._lock:
                    self.state = "COMPLETED" if controller.completed else "STOPPED"
                    self._set_capture_status(
                        CaptureStatus.COMPLETED if controller.completed else CaptureStatus.STOPPED
                    )
                    self._publish(
                        "replay.completed" if controller.completed else "replay.stopped",
                        {"capture": self.capture, "progress": controller.progress},
                    )
            except Exception as exc:
                with self._lock:
                    self.error = str(exc)
                    self.state = "ERROR"
                    self._set_capture_status(CaptureStatus.FAILED, str(exc))
                    self._publish("replay.failed", {"capture": self.capture, "reason": str(exc)})
            finally:
                with self._lock:
                    self.running = False

        self.thread = Thread(target=run, name="custodian-passive-replay", daemon=True)
        self.thread.start()

    def seek(self, target_progress: float):
        with self._lock:
            if self.capture is None or self.controller is None:
                raise RuntimeError("start or validate a replay before seeking")
            old_controller = self.controller
            old_thread = self.thread
            capture = self.capture
            mode = old_controller.mode
            speed = old_controller.speed_multiplier
            if self.running:
                old_controller.stop()
        if old_thread and old_thread.is_alive():
            old_thread.join(timeout=5)
            if old_thread.is_alive():
                raise RuntimeError("the current replay did not stop safely")
        candidate = self.validator.resolve(capture)

        def rebuild_complete() -> None:
            with self._lock:
                if self.running:
                    self.state = "RUNNING"

        with self._lock:
            self.engine.reset()
            record = self.validated.get(capture)
            self.engine.capture_id = record.capture_id if record else None
            self.error = None
            self.state = "REBUILDING" if target_progress > 0 else "RUNNING"
            self.running = True
            self.controller = ReplayController(
                CaptureReader(candidate),
                mode=mode,
                speed_multiplier=speed,
                rebuild_until_fraction=target_progress,
                on_rebuild_complete=rebuild_complete,
            )
            controller = self.controller
            record = self.validated.get(capture)
            if self.repository and record:
                checkpoint_id = f"{record.capture_id}:{target_progress:.6f}"
                self.repository.save_checkpoint(
                    checkpoint_id,
                    record.capture_id,
                    target_progress,
                    {
                        "strategy": "deterministic_rebuild_from_start",
                        "restorable": False,
                        "rebuild_origin_progress": 0.0,
                        "contains_raw_payload": False,
                    },
                )
            self._set_capture_status(CaptureStatus.RUNNING)
            self._publish("replay.seeked", {"target_progress": target_progress})
            self._launch(controller)

    def pause(self):
        with self._lock:
            if not self.running or self.controller is None:
                raise RuntimeError("no replay is running")
            self.controller.pause()
            self.engine.metrics.set_paused(True)
            self.state = "PAUSED"
            self._set_capture_status(CaptureStatus.PAUSED)
            self._publish("replay.paused", {"capture": self.capture})

    def resume(self):
        with self._lock:
            if not self.running or self.controller is None:
                raise RuntimeError("no replay is running")
            self.engine.metrics.set_paused(False)
            self.controller.resume()
            self.state = "RUNNING"
            self._set_capture_status(CaptureStatus.RUNNING)
            self._publish("replay.resumed", {"capture": self.capture})

    def stop(self):
        with self._lock:
            if not self.running or self.controller is None:
                raise RuntimeError("no replay is running")
            self.state = "STOPPING"
            self.controller.stop()
            self._publish("replay.stop_requested", {"capture": self.capture})

    def reset(self):
        with self._lock:
            if self.running:
                raise RuntimeError("stop replay before resetting runtime state")
            self.engine.reset()
            self.capture = self.controller = self.error = None
            self.state = "IDLE"
            self.run_id += 1
            self.capture_size_bytes = 0

    def status(self):
        controller = self.controller
        return {
            "passive_monitor": True,
            "return_path": "NONE",
            "replay_running": self.running,
            "replay_paused": bool(self.running and controller and controller.paused),
            "replay_state": self.state,
            "capture": self.capture,
            "active_flows": self.engine.flows.active_flow_count,
            "source_type": "PCAP_REPLAY",
            "source_name": self.capture,
            "mode": (controller.mode if controller else self.config.replay.mode).value,
            "speed_multiplier": controller.speed_multiplier
            if controller
            else self.config.replay.speed_multiplier,
            "progress": controller.progress if controller else None,
            "rebuilding": bool(controller and controller.rebuilding),
            "rebuild_progress": controller.rebuild_progress if controller else None,
            "progress_basis": "capture_file_bytes",
            "capture_size_bytes": self.capture_size_bytes,
            "processed_capture_bytes": controller.processed_bytes if controller else 0,
            "checkpoint_origin_progress": 0.0 if controller else None,
            "error": self.error,
            "run_id": self.run_id,
            "telemetry_interval_ms": round(self.telemetry_interval * 1000),
        }


def create_app(config: ConfigBundle) -> FastAPI:
    engine = CustodianEngine(config)
    repository = None
    storage_error = None
    recovery_warnings: list[str] = []
    if config.storage.enabled:
        try:
            repository = SQLiteRepository(config.storage.database_path)
            repository.initialize()
            repository.apply_retention(
                retention_days=config.storage.retention_days,
                max_database_bytes=config.storage.max_database_bytes,
            )
        except Exception as exc:
            storage_error = str(exc)
            repository = None
    event_hub = EventHub(max_events=min(config.defaults.max_temporal_events, 5000))
    session = ReplaySession(engine, config, repository, event_hub)
    if repository:
        for payload in reversed(repository.list_alerts(limit=min(config.defaults.max_alerts, 500))):
            try:
                engine.alerts.append(AlertRecord.model_validate(payload))
            except Exception as exc:
                recovery_warnings.append(f"Skipped incompatible persisted alert: {exc}")

    @asynccontextmanager
    async def lifespan(app):
        yield
        if session.running and session.controller:
            session.controller.stop()
        if session.thread:
            await asyncio.to_thread(session.thread.join, 2)

    app = FastAPI(
        title="Custodian API",
        description=API_DESCRIPTION,
        version="0.3.0",
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"]
    )
    app.state.engine, app.state.session = engine, session
    app.state.repository, app.state.event_hub = repository, event_hub

    @app.middleware("http")
    async def correlation_id(request: Request, call_next):
        request_id = request.headers.get("X-Correlation-ID") or str(uuid4())
        request.state.correlation_id = request_id
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = request_id
        return response

    @app.exception_handler(HTTPException)
    async def stable_http_error(request: Request, exc: HTTPException):
        request_id = getattr(request.state, "correlation_id", str(uuid4()))
        message = str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            headers={**(exc.headers or {}), "X-Correlation-ID": request_id},
            content={
                "detail": message,
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": message,
                    "correlation_id": request_id,
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def stable_validation_error(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "correlation_id", str(uuid4()))
        return JSONResponse(
            status_code=422,
            headers={"X-Correlation-ID": request_id},
            content={
                "detail": "request validation failed",
                "error": {
                    "code": "REQUEST_VALIDATION_FAILED",
                    "message": "request validation failed",
                    "correlation_id": request_id,
                    "fields": jsonable_encoder(exc.errors()),
                },
            },
        )

    @app.get("/health", tags=["system"], summary="Check basic process health")
    def health():
        return {"status": "ok", "return_path": "NONE"}

    @app.get("/api/v1/health", tags=["system"], summary="Check versioned API health")
    def health_v1():
        return health()

    @app.get(
        "/api/v1/readiness",
        tags=["system"],
        summary="Inspect component and passive-input readiness",
    )
    def readiness():
        model_status = detectors()
        model_components = {
            item["id"]: {
                "status": "ready" if item["enabled"] else "unavailable",
                "reason": item["reason"],
            }
            for item in model_status
        }
        database_ready = repository is not None and not recovery_warnings
        return {
            "status": "ready"
            if database_ready and all(item["enabled"] for item in model_status)
            else "degraded",
            "passive_only": True,
            "outbound_traffic_path": False,
            "components": {
                "parser": {"status": "ready", "reason": None},
                "event_stream": {"status": "ready", "reason": None},
                "database": {
                    "status": "degraded"
                    if recovery_warnings
                    else "ready"
                    if repository
                    else "unavailable",
                    "reason": "; ".join(recovery_warnings)
                    if recovery_warnings
                    else None
                    if repository
                    else storage_error or "Persistence is disabled",
                },
                "models": model_components,
                "inputs": {
                    item["source_type"]: {
                        "status": item["status"],
                        "reason": item["reason"],
                    }
                    for item in adapter_statuses()
                },
            },
        }

    @app.get("/api/v1/status", tags=["replay"], summary="Get current replay session status")
    def status():
        return session.status()

    @app.get(
        "/api/v1/replay/status",
        tags=["replay"],
        summary="Get current replay status through the replay namespace",
    )
    def replay_status():
        return status()

    @app.get("/api/v1/captures", tags=["captures"], summary="List confined capture candidates")
    def captures():
        records = []
        for candidate in session.validator.list_candidates():
            validated = session.validated.get(str(candidate["display_name"]))
            records.append(
                {
                    **candidate,
                    "capture_id": validated.capture_id if validated else None,
                    "status": validated.status.value if validated else "queued",
                    "sha256": validated.sha256 if validated else None,
                }
            )
        return records

    @app.post(
        "/api/v1/captures/validate",
        tags=["captures"],
        summary="Validate one capture before processing",
    )
    def validate_capture(request: CaptureValidateRequest):
        try:
            record = session.validate(request.capture)
        except (ValueError, FileNotFoundError, RuntimeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return record.model_dump(mode="json")

    @app.get("/api/v1/alerts", tags=["alerts"], summary="List retained alert records")
    def alerts(limit: int = 100, offset: int = 0):
        if not 1 <= limit <= 500 or offset < 0:
            raise HTTPException(status_code=400, detail="invalid alert pagination")
        records = list(engine.alerts)
        end = max(len(records) - offset, 0)
        start = max(end - limit, 0)
        return [alert.model_dump(mode="json") for alert in records[start:end]]

    @app.get("/api/v1/alerts/{alert_id}", tags=["alerts"], summary="Get one alert record")
    def alert_detail(alert_id: str):
        for alert in list(engine.alerts):
            if alert.alert_id == alert_id:
                return alert.model_dump(mode="json")
        if repository:
            persisted = repository.get_alert(alert_id)
            if persisted:
                return persisted
        raise HTTPException(status_code=404, detail="alert not found or no longer retained")

    def update_alert_status(alert_id: str, status: AlertStatus):
        if repository is None:
            raise HTTPException(status_code=503, detail="persistence is unavailable")
        if not repository.set_alert_status(alert_id, status.value):
            raise HTTPException(status_code=404, detail="alert not found")
        for index, alert in enumerate(engine.alerts):
            if alert.alert_id == alert_id:
                engine.alerts[index] = alert.model_copy(update={"status": status})
                engine.dedupe.set_status(alert_id, status)
                engine.alert_revision += 1
                break
        session._publish("alert.status_changed", {"alert_id": alert_id, "status": status.value})
        return {"status": status.value, "alert_id": alert_id}

    @app.post(
        "/api/v1/alerts/{alert_id}/acknowledge",
        tags=["alerts"],
        summary="Acknowledge a persisted alert",
    )
    def acknowledge_alert(alert_id: str):
        return update_alert_status(alert_id, AlertStatus.ACKNOWLEDGED)

    @app.post(
        "/api/v1/alerts/{alert_id}/close",
        tags=["alerts"],
        summary="Close a persisted alert",
    )
    def close_alert(alert_id: str):
        return update_alert_status(alert_id, AlertStatus.CLOSED)

    @app.get("/api/v1/metrics", tags=["telemetry"], summary="Get measured runtime metrics")
    def metrics():
        return engine.metrics.snapshot(interval_seconds=session.telemetry_interval)

    @app.get(
        "/api/v1/detectors",
        tags=["detectors"],
        summary="List detector readiness and artifact trust",
    )
    def detectors():
        return engine.detector_status()

    @app.get(
        "/api/v1/models",
        tags=["detectors"],
        summary="List model status through the compatibility alias",
    )
    def models():
        return detectors()

    @app.get("/api/v1/flows", tags=["traffic"], summary="List bounded flow summaries")
    def flows(limit: int = 100):
        if not 1 <= limit <= 500:
            raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
        active = list(engine.flows.snapshots(limit=limit))
        remaining = max(limit - len(active), 0)
        completed = list(engine.recent_flows)[-remaining:] if remaining else []
        return [flow.model_dump(mode="json") for flow in active + completed]

    @app.get(
        "/api/v1/timeline",
        tags=["traffic"],
        summary="List bounded host observations and alert markers",
    )
    def timeline(host: str | None = None, limit: int = 200):
        if not 1 <= limit <= 500:
            raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
        if host is not None:
            try:
                normalized_host = str(ip_address(host))
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="host must be an IP address") from exc
        else:
            normalized_host = None
        points = [
            point
            for point in engine.host_timeline
            if normalized_host is None or point["host"] == normalized_host
        ]
        return points[-limit:]

    @app.get(
        "/api/v1/diagnostics",
        tags=["system"],
        summary="Inspect routing, model-load, and input diagnostics",
    )
    def diagnostics():
        return {
            "routing": list(engine.routing_diagnostics),
            "model_load_errors": dict(engine._load_errors),
            "inputs": adapter_statuses(),
        }

    @app.get("/api/v1/events", tags=["events"], summary="Poll events after a sequence cursor")
    def events(after_sequence: int = 0, limit: int = 200):
        try:
            cursor_reset = event_hub.cursor_requires_resync(after_sequence)
            cursor = 0 if after_sequence > event_hub.latest_sequence else after_sequence
            records = event_hub.since(cursor, limit=limit)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "latest_sequence": event_hub.latest_sequence,
            "earliest_sequence": event_hub.earliest_sequence,
            "cursor_reset": cursor_reset,
            "events": [event.model_dump(mode="json") for event in records],
        }

    @app.post(
        "/api/v1/exports",
        tags=["exports"],
        summary="Create a local persisted-alert report",
    )
    def create_export(request: ExportRequest):
        if repository is None:
            raise HTTPException(status_code=503, detail="persistence is unavailable")
        try:
            record = session.validated.get(session.capture or "")
            model_metadata = [
                {
                    "family": item["id"],
                    "model_version": item["model_version"],
                    "feature_schema_version": item["schema_version"],
                    "status": item["status"],
                }
                for item in detectors()
            ]
            path = ExportService(
                repository, config.storage.database_path.parent / "reports"
            ).export_alerts(
                request.format,
                metadata={
                    "configuration_fingerprint": sha256(
                        config.model_dump_json().encode("utf-8")
                    ).hexdigest(),
                    "capture_id": record.capture_id if record else None,
                    "capture_sha256": record.sha256 if record else None,
                    "models": model_metadata,
                },
                anonymize=request.anonymize,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "status": "created",
            "format": request.format,
            "anonymized": request.anonymize,
            "filename": path.name,
            "directory": "runtime/reports",
        }

    @app.get(
        "/api/v1/telemetry",
        tags=["telemetry"],
        summary="Get combined status, metrics, and detector state",
    )
    def telemetry():
        return {"status": status(), "metrics": metrics(), "detectors": detectors()}

    @app.post("/api/v1/replay/start", tags=["replay"], summary="Start passive file replay")
    def start_replay(request: ReplayStartRequest):
        try:
            session.start(request.capture, request.mode, request.speed_multiplier)
        except (ValueError, FileNotFoundError, RuntimeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"status": "started", "capture": request.capture}

    def control(action, result):
        try:
            action()
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"status": result}

    @app.post("/api/v1/replay/pause", tags=["replay"], summary="Pause active file replay")
    def pause_replay():
        return control(session.pause, "paused")

    @app.post("/api/v1/replay/resume", tags=["replay"], summary="Resume paused file replay")
    def resume_replay():
        return control(session.resume, "running")

    @app.post("/api/v1/replay/stop", tags=["replay"], summary="Request a safe replay stop")
    def stop_replay():
        return control(session.stop, "stopping")

    @app.post(
        "/api/v1/replay/seek",
        tags=["replay"],
        summary="Rebuild state from capture origin to a target",
    )
    def seek_replay(request: ReplaySeekRequest):
        try:
            session.seek(request.target_progress)
        except (ValueError, FileNotFoundError, RuntimeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"status": "rebuilding", "target_progress": request.target_progress}

    @app.post("/api/v1/replay/reset", tags=["replay"], summary="Reset idle runtime state")
    def reset_replay():
        return control(session.reset, "reset")

    @app.websocket("/api/v1/stream/telemetry")
    async def stream_telemetry(websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                await websocket.send_json(telemetry())
                await asyncio.sleep(session.telemetry_interval)
        except (WebSocketDisconnect, RuntimeError):
            return

    @app.websocket("/api/v1/stream/alerts")
    async def stream_alerts(websocket: WebSocket):
        await websocket.accept()
        revision = -1
        try:
            while True:
                if engine.alert_revision != revision:
                    await websocket.send_json({"run_id": session.run_id, "alerts": alerts()})
                    revision = engine.alert_revision
                await asyncio.sleep(session.telemetry_interval)
        except (WebSocketDisconnect, RuntimeError):
            return

    @app.websocket("/api/v1/stream/metrics")
    async def stream_metrics(websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                await websocket.send_json(metrics())
                await asyncio.sleep(session.telemetry_interval)
        except (WebSocketDisconnect, RuntimeError):
            return

    @app.websocket("/api/v1/events")
    async def stream_events(websocket: WebSocket):
        await websocket.accept()
        try:
            sequence = max(int(websocket.query_params.get("after_sequence", "0")), 0)
            cursor_reset = event_hub.cursor_requires_resync(sequence)
            if sequence > event_hub.latest_sequence:
                sequence = 0
            while True:
                records = event_hub.since(sequence)
                if records or cursor_reset:
                    sequence = records[-1].sequence if records else event_hub.latest_sequence
                    await websocket.send_json(
                        {
                            "latest_sequence": sequence,
                            "earliest_sequence": event_hub.earliest_sequence,
                            "cursor_reset": cursor_reset,
                            "events": [event.model_dump(mode="json") for event in records],
                        }
                    )
                    cursor_reset = False
                await asyncio.sleep(session.telemetry_interval)
        except (WebSocketDisconnect, RuntimeError, ValueError):
            return

    return app


def create_default_app() -> FastAPI:
    config_dir = Path(__file__).resolve().parents[3] / "configs"
    return create_app(load_config_bundle(config_dir))


app = create_default_app()
