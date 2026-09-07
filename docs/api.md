# Custodian API reference

## Overview

Custodian exposes a versioned, local API for passive analysis of authorized packet-capture files. It validates and reads capture files, reconstructs bounded flow state, extracts observable metadata, evaluates available trusted detectors, applies an Evidence Gate, and streams telemetry to the dashboard.

Custodian does not scan a network, inject or retransmit packets, block traffic, exploit hosts, or decrypt TLS/QUIC payloads. `PCAP replay` means local file processing, not transmission onto a network.

Current API version: `v1`  
Application/OpenAPI version: `0.3.0`

## Base URLs and interactive reference

Run the backend on its supported localhost binding:

```powershell
Set-Location 'C:\Users\Aaryan\Documents\ChatGPT\Custodian'
& 'E:\Python\python.exe' -m uvicorn custodian.api.app:app --app-dir src --host 127.0.0.1 --port 8000
```

| Resource | URL |
| --- | --- |
| API base | `http://127.0.0.1:8000/api/v1` |
| OpenAPI JSON | `http://127.0.0.1:8000/openapi.json` |
| Swagger UI | `http://127.0.0.1:8000/docs` |
| ReDoc | `http://127.0.0.1:8000/redoc` |

The frontend development server proxies `/api` and WebSocket requests to this backend. Direct examples below use port 8000 so they also work without the frontend.

## Authentication and exposure

Authentication is **not implemented** in the current prototype. Trusted-host filtering accepts `127.0.0.1`, `localhost`, and the test host, but that is not user authentication. Keep the backend and frontend bound to localhost. Authentication and protected API access are planned under their separate issue.

Do not expose this API to a LAN or the public internet without a separately reviewed authentication, authorization, TLS, origin, deployment, and rate-limit design.

## Request and response conventions

- JSON request bodies use `Content-Type: application/json`.
- Datetimes are timezone-aware ISO 8601 strings.
- Probabilities are numbers from `0.0` through `1.0`; the frontend converts them to percentages.
- Byte counts are integer bytes.
- Processing rates use Mbps, packets/second, and flows/second.
- Latencies are milliseconds.
- Bounded list routes return only retained runtime records, not unlimited history.

### Correlation ID

Every HTTP response contains `X-Correlation-ID`. A client can send its own value:

```powershell
curl.exe -i -H "X-Correlation-ID: demo-request-001" http://127.0.0.1:8000/api/v1/health
```

The same value is returned in the response header and included in stable error envelopes.

### HTTP error format

Handled HTTP errors use:

```json
{
  "detail": "alert not found or no longer retained",
  "error": {
    "code": "HTTP_404",
    "message": "alert not found or no longer retained",
    "correlation_id": "generated-or-client-supplied-id"
  }
}
```

Request-schema failures return HTTP 422:

```json
{
  "detail": "request validation failed",
  "error": {
    "code": "REQUEST_VALIDATION_FAILED",
    "message": "request validation failed",
    "correlation_id": "generated-or-client-supplied-id",
    "fields": []
  }
}
```

Common statuses:

| Status | Meaning |
| --- | --- |
| 200 | Request succeeded. |
| 400 | Invalid runtime state, path, capture, cursor, query bound, or requested action. |
| 404 | Requested retained/persisted alert does not exist. |
| 422 | JSON body or parameter does not match the declared schema. |
| 503 | Persistence-dependent operation requested while persistence is unavailable. |

## Health and readiness

### `GET /health`

Minimal unversioned process-health route.

```powershell
curl.exe http://127.0.0.1:8000/health
```

```json
{
  "status": "ok",
  "return_path": "NONE"
}
```

### `GET /api/v1/health`

Versioned alias with the same response.

```powershell
curl.exe http://127.0.0.1:8000/api/v1/health
```

### `GET /api/v1/readiness`

Reports operational components and safety properties.

```powershell
curl.exe http://127.0.0.1:8000/api/v1/readiness
```

Representative degraded response:

```json
{
  "status": "degraded",
  "passive_only": true,
  "outbound_traffic_path": false,
  "components": {
    "parser": {"status": "ready", "reason": null},
    "event_stream": {"status": "ready", "reason": null},
    "database": {"status": "ready", "reason": null},
    "models": {},
    "inputs": {}
  }
}
```

`degraded` does not necessarily mean replay is broken. It commonly means parsing remains ready while one or more model artifacts are unavailable, untrusted, incomplete, or incompatible.

## Runtime and replay status

### `GET /api/v1/status`

Returns the current session state.

### `GET /api/v1/replay/status`

Alias of `/api/v1/status` for replay-focused clients.

```powershell
curl.exe http://127.0.0.1:8000/api/v1/replay/status
```

Representative idle response:

```json
{
  "passive_monitor": true,
  "return_path": "NONE",
  "replay_running": false,
  "replay_paused": false,
  "replay_state": "IDLE",
  "capture": null,
  "active_flows": 0,
  "source_type": "PCAP_REPLAY",
  "source_name": null,
  "mode": "paced",
  "speed_multiplier": 1.0,
  "progress": null,
  "rebuilding": false,
  "rebuild_progress": null,
  "progress_basis": "capture_file_bytes",
  "capture_size_bytes": 0,
  "processed_capture_bytes": 0,
  "checkpoint_origin_progress": null,
  "error": null,
  "run_id": 0,
  "telemetry_interval_ms": 250
}
```

Possible replay states include `IDLE`, `VALIDATING`, `READY`, `RUNNING`, `PAUSED`, `STOPPING`, `STOPPED`, `REBUILDING`, `COMPLETED`, `FAILED`, and `ERROR` according to the current action and failure path.

`progress` is a fraction of capture-file bytes processed. It is not threat-detection progress or percentage safe.

## Capture discovery and validation

Capture files must be located inside the configured capture root, currently `data/demo/`. Supported extensions are `.cap`, `.pcap`, and `.pcapng`, but extension alone is insufficient: the validator checks resolved path confinement, size, file magic/format, and supported link type.

### `GET /api/v1/captures`

Lists eligible files and their known validation state.

```powershell
curl.exe http://127.0.0.1:8000/api/v1/captures
```

```json
[
  {
    "display_name": "http.cap",
    "size_bytes": 25215,
    "capture_id": null,
    "status": "queued",
    "sha256": null
  }
]
```

Values depend on actual local files. Validation populates `capture_id`, `status`, and `sha256`.

### `POST /api/v1/captures/validate`

Request schema:

| Field | Type | Rules |
| --- | --- | --- |
| `capture` | string | Required; 1–255 characters; confined safe display name. |

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/captures/validate `
  -H "Content-Type: application/json" `
  -d '{"capture":"http.cap"}'
```

Success returns a `CaptureRecord` containing capture identity, source type, size, SHA-256, lifecycle status, packet accounting, parser warnings, and optional failure reason. Validation does not transmit packets.

Invalid paths, unsupported formats, unsupported datalinks, missing files, oversize files, and validation during an active replay return HTTP 400. Renaming an unrelated file to `.cap` does not make it a valid capture.

## Replay controls

### `POST /api/v1/replay/start`

Starts a fresh passive processing run and resets derived runtime state for that run.

| Field | Type | Rules |
| --- | --- | --- |
| `capture` | string | Required non-empty capture display name. |
| `mode` | string or null | `paced`, `fast`, or `benchmark`; default from configuration. |
| `speed_multiplier` | integer or null | `1`, `2`, `5`, or `10`; principally used by paced mode. |

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/replay/start `
  -H "Content-Type: application/json" `
  -d '{"capture":"http.cap","mode":"fast","speed_multiplier":1}'
```

```json
{
  "status": "started",
  "capture": "http.cap"
}
```

Starting while another replay is running returns HTTP 400. An invalid enum or multiplier returns HTTP 422.

Modes:

- `paced` follows capture timestamps at the selected multiplier;
- `fast` ignores captured inter-packet delays and processes locally as quickly as possible;
- `benchmark` reduces telemetry overhead for local pipeline measurement.

### `POST /api/v1/replay/pause`

Pauses an active controller.

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/replay/pause
```

```json
{"status":"paused"}
```

### `POST /api/v1/replay/resume`

Resumes a paused controller.

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/replay/resume
```

```json
{"status":"running"}
```

### `POST /api/v1/replay/stop`

Requests safe termination. The immediate response means stop was requested; poll status or use events to observe `STOPPED`.

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/replay/stop
```

```json
{"status":"stopping"}
```

Pause, resume, and stop return HTTP 400 when no replay is active.

### `POST /api/v1/replay/seek`

Stops the current controller if necessary, clears derived state, and rebuilds deterministically from capture origin to a target fraction before continuing.

| Field | Type | Rules |
| --- | --- | --- |
| `target_progress` | number | Required; `0.0` through `1.0`. |

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/replay/seek `
  -H "Content-Type: application/json" `
  -d '{"target_progress":0.5}'
```

```json
{
  "status": "rebuilding",
  "target_progress": 0.5
}
```

Seek is deterministic replay from the start; it is not restoration of arbitrary serialized detector state. A request before a capture/controller exists returns HTTP 400. Out-of-range values return HTTP 422.

### `POST /api/v1/replay/reset`

Clears idle in-memory runtime state and increments the run boundary. It does not delete capture files.

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/replay/reset
```

```json
{"status":"reset"}
```

Reset during an active replay returns HTTP 400.

## Metrics and telemetry

### `GET /api/v1/metrics`

Returns current counters, rates, resource measurements, and stage latency.

```powershell
curl.exe http://127.0.0.1:8000/api/v1/metrics
```

Important fields:

| Field | Meaning |
| --- | --- |
| `packets` | Capture frames observed by the run. |
| `parsed_packets` | Frames successfully parsed into supported observations. |
| `flow_updates` | Times observations updated flow state; multiple updates can belong to one flow. |
| `flows` | Distinct reconstructed flows observed/finalized by telemetry. |
| `skipped_frames` | Frames not used by the analysis path. |
| `malformed_frames` | Structurally invalid frames. |
| `unsupported_frames` | Valid but unsupported encapsulation/protocol frames. |
| `truncated_frames` | Incomplete capture frames. |
| `dropped_frames` | Frames discarded because of runtime limits/policy. |
| `feature_vectors` | Shared feature snapshots produced. |
| `inference_vectors` | Feature vectors evaluated by models. |
| `inference_batches` | Model batch invocations. |
| `evidence_decisions` | Candidates evaluated by evidence policy. |
| `decisions` | Count by Evidence Gate decision. |
| `bytes` | Capture bytes/frames accounted for by processing metrics. |
| `alerts` | Standardized alert records emitted. |
| `cpu_percent` | Local process CPU measurement. |
| `memory_bytes` | Local process memory measurement. |
| `processing_rates` | Current interval Mbps, packets/s, and new flows/s. |
| `average_processing_rates` | Average rates for the run where available. |
| `observed_average_mbps` | Original capture-time average when derivable. |
| `latency_ms` | p50/p95 by pipeline stage. |
| `rate_samples` | Bounded backend-aggregated time series. |

Latency stages can include `parse`, `flow`, `state`, `features`, `inference`, `inference_batch`, `evidence`, `alert`, and `total_pipeline`. Missing measurements are `null`, not zero latency.

Processing Mbps measures how quickly this machine processes a file. It is not automatically the original network bandwidth.

### `GET /api/v1/telemetry`

Returns one synchronized envelope:

```json
{
  "status": {},
  "metrics": {},
  "detectors": []
}
```

The frontend uses this route for initial synchronization and a WebSocket for subsequent updates.

## Alerts

An alert is emitted only after a real detector candidate and Evidence Gate decision. Zero alerts does not prove the capture is safe, especially when a required detector is unavailable.

### `GET /api/v1/alerts`

Query parameters:

| Name | Default | Rules |
| --- | --- | --- |
| `limit` | 100 | Integer from 1 through 500. |
| `offset` | 0 | Non-negative integer offset from the newest retained end. |

```powershell
curl.exe "http://127.0.0.1:8000/api/v1/alerts?limit=100&offset=0"
```

Returns an array of `AlertRecord`. Invalid pagination returns HTTP 400.

### `GET /api/v1/alerts/{alert_id}`

Returns a retained in-memory alert or persisted record.

```powershell
curl.exe http://127.0.0.1:8000/api/v1/alerts/alert-id
```

Missing or expired IDs return HTTP 404.

### `POST /api/v1/alerts/{alert_id}/acknowledge`

Changes a persisted alert lifecycle to `acknowledged`.

```json
{"status":"acknowledged","alert_id":"alert-id"}
```

### `POST /api/v1/alerts/{alert_id}/close`

Changes a persisted alert lifecycle to `closed`.

```json
{"status":"closed","alert_id":"alert-id"}
```

Lifecycle changes require persistence. They return HTTP 503 if persistence is unavailable and HTTP 404 if the ID does not exist.

### AlertRecord schema

| Field group | Fields |
| --- | --- |
| Identity | `alert_id`, `capture_id`, `source_type`, `flow_id`, `window_id`, `observation_frame_id` |
| Time/lifecycle | `timestamp`, `first_seen`, `last_seen`, `emitted_at`, `status`, `occurrence_count` |
| Classification | `threat_class`, `severity`, `decision`, `detector_id` |
| Confidence | `raw_score`, `calibrated_confidence`, `threat_confidence`, `observation_confidence`, `observation_robustness`, `class_threshold` |
| Evidence | `evidence_quality`, `evidence`, `available_evidence`, `missing_evidence`, `limitations`, `capabilities` |
| Provenance | `model_version`, `feature_schema_version`, `policy_versions` |
| Timing | `inference_latency_ms`, `total_pipeline_latency_ms`, `stage_timings_ms` |
| Network context | `source`, `destination` with IP and optional port |

Decisions:

- `ACCEPT`: configured confidence and evidence policy accepted the candidate;
- `UNKNOWN_SUSPICIOUS`: suspicious behaviour without justified narrow classification;
- `INSUFFICIENT_EVIDENCE`: required observation evidence is absent or inadequate.

Decision is not synonymous with severity. Confidence is not a mathematical guarantee that an event is malicious.

## Detectors and models

### `GET /api/v1/detectors`

Returns Behaviour, DNS, and TLS/QUIC detector states.

### `GET /api/v1/models`

Current compatibility alias returning the same payload.

```powershell
curl.exe http://127.0.0.1:8000/api/v1/detectors
```

Each record contains:

- `id`;
- `enabled`;
- `status` (`READY`, `DEGRADED`, or `UNAVAILABLE`);
- `reason`;
- `model_version`;
- `schema_version`;
- `classes`;
- `artifact_trusted`;
- `required_evidence`;
- `available_evidence`; and
- `distribution_support`.

An unavailable detector is an expected safe condition when no approved compatible artifact exists. Do not set artifact trust merely to make alerts appear.

## Traffic summaries

### `GET /api/v1/flows`

Returns bounded active and recent completed `FlowRecord` summaries.

| Parameter | Default | Rules |
| --- | --- | --- |
| `limit` | 100 | Integer from 1 through 500. |

```powershell
curl.exe "http://127.0.0.1:8000/api/v1/flows?limit=100"
```

A flow includes canonical endpoints, IP version, protocol, initiator direction, close reason, directional packet/byte totals, and compact statistics. The route does not return reconstructed payloads.

### `GET /api/v1/timeline`

Returns bounded host-window measurements and alert markers.

| Parameter | Default | Rules |
| --- | --- | --- |
| `host` | omitted | Valid IPv4 or IPv6 address when supplied. |
| `limit` | 200 | Integer from 1 through 500. |

```powershell
curl.exe "http://127.0.0.1:8000/api/v1/timeline?host=10.0.0.15&limit=100"
```

Points can include packet/byte/flow counts, destination and port diversity, inbound/outbound bytes, rolling-window size, and associated alert identity/class. Invalid hosts or bounds return HTTP 400.

## Diagnostics

### `GET /api/v1/diagnostics`

```powershell
curl.exe http://127.0.0.1:8000/api/v1/diagnostics
```

Returns:

```json
{
  "routing": [],
  "model_load_errors": {},
  "inputs": []
}
```

Routing entries explain detector routing and missing evidence. Model-load errors expose safe diagnostic reasons. Input entries identify adapter status and whether an adapter is passive or opens a network interface.

## Events

### `GET /api/v1/events`

Polls bounded events after a cursor.

| Parameter | Default | Rules |
| --- | --- | --- |
| `after_sequence` | 0 | Non-negative sequence cursor. |
| `limit` | 200 | Enforced by the bounded event hub. |

```powershell
curl.exe "http://127.0.0.1:8000/api/v1/events?after_sequence=0&limit=200"
```

```json
{
  "latest_sequence": 0,
  "earliest_sequence": 1,
  "cursor_reset": false,
  "events": []
}
```

An event contains `event_id`, monotonically increasing `sequence`, `event_type`, `created_at`, `run_id`, and bounded JSON `payload`.

If the requested cursor is older than retained history, `cursor_reset` tells the client to resynchronize. If it is beyond the latest known sequence, the server resets its working cursor rather than waiting forever on an impossible position.

## Exports

### `POST /api/v1/exports`

Creates a report on the backend's local filesystem. It does not upload the report.

| Field | Type | Rules |
| --- | --- | --- |
| `format` | string | Required: `json` or `csv`. |
| `anonymize` | boolean | Optional; default `false`. |

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/exports `
  -H "Content-Type: application/json" `
  -d '{"format":"json","anonymize":true}'
```

```json
{
  "status": "created",
  "format": "json",
  "anonymized": true,
  "filename": "generated-report-name.json",
  "directory": "runtime/reports"
}
```

Exports include configuration, capture identity/checksum where available, and model-version/schema metadata. Persistence must be available; unsupported formats return HTTP 422.

## WebSocket streams

WebSockets are local streams and are not listed as ordinary HTTP operations in OpenAPI.

| URL | Initial/update behaviour | Payload |
| --- | --- | --- |
| `ws://127.0.0.1:8000/api/v1/stream/telemetry` | Sends at the configured telemetry interval. | `{status, metrics, detectors}` |
| `ws://127.0.0.1:8000/api/v1/stream/alerts` | Sends initially and when alert revision changes. | `{run_id, alerts}` |
| `ws://127.0.0.1:8000/api/v1/stream/metrics` | Sends at the configured telemetry interval. | Metrics object |
| `ws://127.0.0.1:8000/api/v1/events?after_sequence=0` | Sends when events exist or cursor resync is required. | Event-page object |

Clients should reconnect with bounded backoff. On a new `run_id`, clients must not mix prior run-specific alerts or telemetry into the active display. Event clients should preserve their last processed sequence and honor `cursor_reset`.

Browser example:

```javascript
const socket = new WebSocket("ws://127.0.0.1:8000/api/v1/stream/telemetry");
socket.onmessage = (event) => {
  const telemetry = JSON.parse(event.data);
  console.log(telemetry.status.replay_state);
};
```

## Prototype versus planned API

Implemented now:

- localhost health/readiness;
- capture discovery and validation;
- passive PCAP/CAP/PCAPNG file processing;
- replay start, pause, resume, stop, deterministic seek, and reset;
- telemetry, metrics, flows, host timeline, detector state, alerts, events, exports, and WebSockets;
- evidence-aware alert records; and
- persistence-dependent alert lifecycle.

Planned or separately scoped:

- user authentication and authorization;
- production TLS/public deployment;
- live passive network-interface capture;
- remote sensors;
- DNS and TLS/QUIC detection until approved artifacts exist; and
- any additional model-management administration.

There are no active scanning, mitigation, traffic-injection, payload-replay, or TLS/QUIC decryption endpoints planned under the current safety contract.

## Troubleshooting

### Connection refused

Confirm the backend is running on `127.0.0.1:8000`. Starting only the frontend is insufficient.

### Address already in use

Port 8000 already has a listener. Stop only the server process you own or select a different coordinated API/proxy port. Do not terminate unrelated applications.

### Capture missing from `/captures`

Confirm it is located directly in the configured capture root and uses a supported extension. Then validate it; extension renaming does not convert format.

### Replay works but alerts remain empty

Check `/api/v1/detectors`, `/api/v1/readiness`, and `/api/v1/diagnostics`. Traffic measurement can work while models are unavailable. Zero alerts does not prove benign traffic.

### Alert acknowledge/close/export returns 503

The configured SQLite repository failed or persistence is disabled. Replay and in-memory telemetry can still be usable.

## Compatibility policy

Clients should target `/api/v1`. Additive fields may appear within v1; clients should ignore fields they do not need. Renaming/removing fields, changing meanings/units, or changing enum values requires explicit compatibility review and synchronized backend, frontend, tests, and documentation.

The Pydantic contracts in `src/custodian/core/schemas.py`, API implementation in `src/custodian/api/app.py`, frontend types in `frontend/src/types.ts`, generated `/openapi.json`, integration tests, and this document must remain consistent.
