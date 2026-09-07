# Custodian API documentation issue: detailed authoring guide

## Goal of the issue

The API documentation issue should produce an accurate, testable reference for the current local API. It should help frontend contributors, testers, and future integrators understand what each route does without reading implementation internals.

The documentation must describe implemented behaviour only. Planned authentication, model training, optional passive live inputs, or future detector capabilities must be marked clearly as planned rather than documented as available.

## Recommended GitHub issue

### Title

```text
Document and verify the Custodian API
```

### Suggested labels

```text
api, documentation, testing
```

### Primary deliverables

- `docs/api.md` — human-readable API reference.
- Improved FastAPI route summaries, descriptions, tags, response models, and examples where appropriate.
- Tests that verify documented success and error examples.
- A route-inventory check preventing undocumented routes from silently appearing.
- Links from `README.md` and relevant frontend/contributor documentation.

## Source of truth

The contributor must inspect:

- `src/custodian/api/app.py` for routes and control semantics;
- `src/custodian/core/schemas.py` for stable Pydantic contracts;
- `frontend/src/types.ts` for current frontend expectations;
- `configs/*.yaml` for bounds and enabled features; and
- `tests/integration/test_api.py` for verified behaviour.

FastAPI's generated OpenAPI document at `/openapi.json` is a useful inventory, but it does not replace human documentation. If implementation and generated schema disagree, the implementation and tests must be corrected or the discrepancy documented before the issue closes.

## API-wide conventions to document

### Base URLs

```text
Frontend development proxy: http://127.0.0.1:5173/api/v1
Backend API directly:       http://127.0.0.1:8000/api/v1
```

Custodian currently binds to localhost for its supported demo workflow. The documentation must not provide public-interface binding instructions as the default.

### Content type

HTTP request and response examples use:

```http
Content-Type: application/json
```

### Correlation IDs

Every HTTP response contains `X-Correlation-ID`. A client may provide its own `X-Correlation-ID`; otherwise the API creates one. Error examples should include the correlation ID and explain that it is used to connect a client failure to runtime logs/events.

### Stable error envelope

Document the implemented HTTP-error shape:

```json
{
  "detail": "human-readable message",
  "error": {
    "code": "HTTP_400",
    "message": "human-readable message",
    "correlation_id": "uuid"
  }
}
```

Validation errors use HTTP 422 and include an `error.fields` array. Do not document every failure as HTTP 500.

### Authentication status

Authentication is currently not implemented. State this explicitly. The API is protected operationally by localhost binding and trusted-host filtering, but those controls are not user authentication. Link to the authentication issue as planned work without inventing bearer-token examples.

### Passive-only guarantee

State near the beginning of `docs/api.md`:

- replay reads a local capture file;
- no endpoint scans a network;
- no endpoint transmits captured packets;
- no endpoint mitigates or blocks traffic; and
- no endpoint decrypts TLS/QUIC payloads.

## Required endpoint inventory

The documentation must cover every current route below.

### Health and readiness

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Minimal unversioned health probe. |
| GET | `/api/v1/health` | Versioned health probe. |
| GET | `/api/v1/readiness` | Component readiness, passive-only state, outbound-path state, model status, database status, and input adapters. |

The readiness document must explain that `degraded` can mean replay/parsing is usable while one or more approved model artifacts are unavailable.

### Runtime status and telemetry

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/status` | Current replay session and progress. |
| GET | `/api/v1/replay/status` | Alias for current replay status. |
| GET | `/api/v1/metrics` | Counters, rates, resources, and latency percentiles. |
| GET | `/api/v1/telemetry` | Combined status, metrics, and detector state. |
| GET | `/api/v1/diagnostics` | Routing decisions, model-load errors, and input-adapter status. |

For metrics, define the units and distinguish:

- `packets` from `parsed_packets`;
- `flows` from `flow_updates`;
- `processing_rates` from `average_processing_rates`;
- replay-processing Mbps from original-capture Mbps;
- `feature_vectors` from `inference_vectors` and `inference_batches`;
- `evidence_decisions` from `alerts`; and
- p50 from p95 latency.

### Capture discovery and validation

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/captures` | List allowed capture candidates and validation state. |
| POST | `/api/v1/captures/validate` | Validate one filename inside the configured capture root. |

Request example:

```json
{
  "capture": "http.cap"
}
```

Document path confinement, supported extensions, magic validation, maximum size, supported datalink types, SHA-256 identity, and the rule that renaming a file does not convert its format.

### Replay controls

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/replay/start` | Start a new passive file-processing run. |
| POST | `/api/v1/replay/pause` | Pause the active run. |
| POST | `/api/v1/replay/resume` | Resume a paused run. |
| POST | `/api/v1/replay/stop` | Request a safe stop. |
| POST | `/api/v1/replay/seek` | Deterministically rebuild from capture start to a target file-progress fraction. |
| POST | `/api/v1/replay/reset` | Reset runtime telemetry/state when no replay is active. |

Start request:

```json
{
  "capture": "http.cap",
  "mode": "fast",
  "speed_multiplier": 1
}
```

Document valid modes from the enum and explain that speed multiplier is meaningful for paced replay. Current accepted multiplier values are `1`, `2`, `5`, and `10`.

Seek request:

```json
{
  "target_progress": 0.5
}
```

Explain that `target_progress` is between `0.0` and `1.0` and is based on capture-file bytes. Seek stops any current controller, clears derived state, rebuilds deterministically from the capture origin, and then continues. It must not be described as restoring an arbitrary serialized detector snapshot.

For every control endpoint, document invalid-state failures, such as pausing with no active replay or resetting while a replay is running.

### Alerts and lifecycle

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/alerts` | Paginated retained in-memory alert list. |
| GET | `/api/v1/alerts/{alert_id}` | One current or persisted alert. |
| POST | `/api/v1/alerts/{alert_id}/acknowledge` | Mark a persisted alert acknowledged. |
| POST | `/api/v1/alerts/{alert_id}/close` | Mark a persisted alert closed. |

List query constraints:

- `limit`: 1 through 500, default 100;
- `offset`: zero or greater, default 0.

The `AlertRecord` field reference must cover:

- stable IDs and capture/source context;
- timestamps and occurrence count;
- flow/window context;
- threat class and severity;
- `ACCEPT`, `UNKNOWN_SUSPICIOUS`, and `INSUFFICIENT_EVIDENCE` decisions;
- calibrated, threat, and observation confidence;
- raw score and class threshold;
- evidence quality;
- available and missing evidence;
- limitations and capabilities;
- detector/model/schema versions; and
- inference, pipeline, and stage timings.

Explain that acknowledge/close require persistence. If persistence is unavailable, the API returns HTTP 503.

### Detectors and models

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/detectors` | Detector-family readiness and artifact compatibility. |
| GET | `/api/v1/models` | Current alias for detector status. |

Document `enabled`, `status`, `reason`, `artifact_trusted`, model/schema version, classes, required/available evidence, and distribution-support state. An unavailable detector is an expected safe result, not necessarily a server failure.

### Flows and host timeline

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/flows` | Recent active and completed flow summaries. |
| GET | `/api/v1/timeline` | Bounded host-window measurements and alert markers. |

Flow `limit` is 1 through 500. Timeline `limit` is 1 through 500 and optional `host` must be a valid IPv4 or IPv6 address. Document canonical endpoint direction and clarify that no payload is returned.

### Events

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/events` | Poll bounded application events after a sequence cursor. |
| WebSocket | `/api/v1/events` | Stream application events with cursor resynchronization. |

Document:

- `after_sequence` semantics;
- `latest_sequence` and `earliest_sequence`;
- `cursor_reset` when a client cursor fell outside retained history;
- bounded retention; and
- reconnect/resynchronization behaviour.

Avoid ambiguity in `docs/api.md` by labelling one as HTTP GET and the other as WebSocket despite sharing the same path.

### Exports

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/exports` | Export persisted alert data to a local report file. |

Request example:

```json
{
  "format": "json",
  "anonymize": true
}
```

Valid formats are `json` and `csv`. Explain the returned filename/directory, anonymization flag, capture/model metadata, and the HTTP 503 response when persistence is unavailable. This endpoint creates a local file; it does not upload data.

### WebSocket streams

| Path | Payload |
| --- | --- |
| `/api/v1/stream/telemetry` | Combined status, metrics, and detector envelope. |
| `/api/v1/stream/alerts` | `{run_id, alerts}` when alert revision changes. |
| `/api/v1/stream/metrics` | Metrics snapshot at the telemetry interval. |
| `/api/v1/events` | Cursor-aware event batches. |

For each stream, document:

- `ws://127.0.0.1:8000/...` local example;
- initial message behaviour;
- update cadence;
- payload schema;
- disconnect handling;
- reconnect expectations;
- run-ID boundaries; and
- event cursor behaviour where applicable.

## Required structure for `docs/api.md`

Use this order:

1. Purpose and passive-only boundary.
2. Quick start and base URLs.
3. Versioning and compatibility policy.
4. Authentication status.
5. Headers and correlation IDs.
6. Stable error format.
7. Health/readiness.
8. Captures and validation.
9. Replay state machine and controls.
10. Telemetry and metric definitions.
11. Alerts and evidence semantics.
12. Flows and timelines.
13. Detectors/models.
14. Events and WebSockets.
15. Local exports.
16. Complete schema reference.
17. Troubleshooting examples.
18. Limitations and planned features.

## Example quality requirements

Every endpoint entry should contain:

- method and path;
- one-sentence purpose;
- state/preconditions;
- path/query/header/body parameters;
- request example, when applicable;
- success status and response example;
- documented error statuses;
- side effects;
- security/privacy notes; and
- source test proving the example.

Do not hand-invent response fields. Generate or capture examples from tests running against the actual app, then remove machine-specific paths and nondeterministic IDs only when clearly marked.

## Testing requirements

Add or extend integration tests to verify at least:

- both health paths;
- readiness in degraded and ready configurations where fixtures permit;
- capture list and validation success/failure;
- replay start and invalid duplicate start;
- pause, resume, stop, seek, and reset state validation;
- alert list pagination bounds;
- alert lookup 404;
- acknowledge/close with and without persistence;
- metric field presence and units/types;
- detector status;
- flow/timeline bounds and invalid host handling;
- event cursor resynchronization;
- export format validation and persistence failure;
- HTTP correlation-ID propagation;
- stable HTTP 400/404/503 envelopes;
- 422 validation envelope; and
- WebSocket payload compatibility.

Where examples include timestamps, UUIDs, counters, performance values, or hashes, tests should verify type/range/shape rather than a fabricated fixed value.

## OpenAPI improvements

The contributor should review the generated FastAPI schema for:

- meaningful operation summaries;
- route tags;
- request and response models instead of anonymous dictionaries where practical;
- response descriptions;
- error models;
- enum descriptions;
- representative examples; and
- accidental exposure of internal-only fields.

Any schema refactor must preserve frontend compatibility or update `frontend/src/types.ts` and tests in the same PR.

## Suggested contributor workflow

1. Assign and comment on the issue.
2. Create a branch such as `docs/api-reference`.
3. Capture the route inventory from `/openapi.json`.
4. Map each route to implementation and tests.
5. Write `docs/api.md` in the required structure.
6. Add missing FastAPI metadata and typed response models where safely scoped.
7. Add integration tests for every documented example and failure shape.
8. Run backend tests and lint.
9. Review all examples for fabricated results, private paths, and security overclaims.
10. Open a PR linked to the issue and request API plus frontend review.

## Pull-request evidence

The PR should include:

- route inventory before/after;
- link to rendered `docs/api.md`;
- test output;
- lint output;
- sample `/openapi.json` validation or schema diff;
- confirmation that no endpoint capability was invented;
- confirmation that authentication is marked unimplemented if still absent; and
- confirmation that localhost/passive-only boundaries are documented.

## Acceptance criteria

- [ ] Every HTTP and WebSocket route in `src/custodian/api/app.py` is documented.
- [ ] All parameters, bounds, enums, units, and state preconditions are accurate.
- [ ] Alert confidence and Evidence Gate semantics are explained.
- [ ] Replay is accurately described as passive local file processing.
- [ ] Readiness degradation and unavailable models are explained.
- [ ] Authentication status is truthful.
- [ ] Correlation ID and error envelopes are documented.
- [ ] Examples are generated from or verified by tests.
- [ ] OpenAPI and human documentation do not materially disagree.
- [ ] No private paths, secrets, dataset rows, or fabricated metrics appear.
- [ ] README links to the completed API reference.
- [ ] Backend tests and lint pass.

## Out of scope

- Adding public internet deployment instructions.
- Adding active scanning or traffic-control endpoints.
- Implementing authentication as part of a documentation-only PR unless separately approved.
- Documenting planned model families as currently available.
- Publishing raw captures, datasets, database contents, or model artifacts.
- Treating generated Swagger UI as the entire documentation deliverable.

