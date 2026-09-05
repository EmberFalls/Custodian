# Custodian — Full Implementation Blueprint

**Status:** implementation-ready specification  
**Product:** Custodian  
**Target:** a local-first, passive network-analysis system that can run reliably on one laptop  
**Important:** this document defines the full build. It does not claim that any capability, model, result, or benchmark already exists.

## 0. Authority and non-negotiable rules

This is the governing implementation contract. If an older blueprint, prototype note, presentation, mock, comment, or existing behavior conflicts with this file, this file wins unless the product owner explicitly approves a revision.

1. Custodian is passive and read-only. It may read captures and observe interfaces; it must never scan, probe, inject, replay onto a network, exploit, block, or modify traffic.
2. TLS and QUIC analysis uses observable metadata only. Payload decryption is out of scope.
3. Training, evaluation, PCAP replay, and live inference must use the same versioned feature-extraction package.
4. Never fabricate datasets, labels, model artifacts, metrics, benchmarks, or trained results.
5. A model loads only when its manifest, checksums, feature version/order, label map, and runtime compatibility pass validation.
6. Weak, unsupported, incomplete, or out-of-distribution evidence must produce an honest abstention rather than a forced threat label.
7. Mocks are permitted only for isolated UI/integration development, must be visibly marked `MOCK`, and must not be presented as detection evidence.
8. Raw datasets, captures, local databases, model binaries, reports, caches, secrets, environment files, and build output are not committed by default.
9. Every alert must be traceable to its capture/session, entity, observation window, detector, model, feature version, and evidence.
10. Keep the system bounded and simple enough for a dependable one-laptop demonstration.

## 1. Product definition

Custodian ingests packet-capture files or optional passive live observations, reconstructs bidirectional flows, extracts non-decrypting features, runs specialized detector families, fuses their findings, and presents evidence-backed alerts in a local browser dashboard.

It answers:

- What traffic was observed?
- Which behavior appears suspicious, and how strongly?
- What evidence produced that assessment?
- Where in the timeline did the behavior build and the alert fire?

It is not an intrusion-prevention system, vulnerability scanner, attack generator, packet editor, traffic injector, or autonomous mitigation platform.

## 2. Scope and exact semantics

### 2.1 Inputs

- Offline `.pcap`, `.pcapng`, and compatible libpcap `.cap` files.
- Optional, explicitly enabled passive capture from a selected local interface.
- Replay of derived metadata, including Zeek logs, when an adapter can declare its available evidence accurately.
- Passive flow-export adapters for NetFlow, IPFIX, and sFlow after the core replay pipeline is complete.
- Dataset CSV files only in training/evaluation tooling, never in the replay control.

Extensions are hints. Validate capture magic and parser compatibility; renaming a file does not convert its format.

### 2.3 Meaning of unidirectional monitoring

Unidirectional describes Custodian's monitoring path, not necessarily the packet directions visible in a capture. A TAP, mirror, or data-diode arrangement can provide copies of both sides of a conversation while preventing Custodian from transmitting into the protected network. Custodian may therefore calculate bidirectional statistics when both directions are observed, but it must never inject packets, initiate connections, complete handshakes, issue mitigation commands through ingest, or decrypt protected application payloads.

### 2.2 Detector families and outcomes

The full build has three detector families and seven explicit malicious outcomes:

| Family | Supported outcomes |
|---|---|
| Behavior | `DDOS`, `C2`, `RECON`, `EXFILTRATION` |
| DNS | `DGA`, `DNS_TUNNEL` |
| Encrypted session | `MALICIOUS_ENCRYPTED_SESSION` |

`BENIGN` is non-malicious. `UNKNOWN_SUSPICIOUS` and `INSUFFICIENT_EVIDENCE` are decision states, not trained threat classes. A legacy broad label such as `BOT_OR_C2_LIKE` must not be silently converted into validated `C2`, counted in final acceptance, or shown as proof of C2 detection.

The source blueprint refers in places to “six” threat families, but its own enumerated requirements contain the seven malicious outcomes listed above. Custodian treats the explicit outcome list as authoritative.

Decision meanings:

- `ALERT`: sufficient calibrated evidence for one supported malicious outcome.
- `BENIGN`: supported evidence is sufficient and below alert thresholds.
- `UNKNOWN_SUSPICIOUS`: meaningful anomaly or detector conflict without adequate support for a validated class.
- `INSUFFICIENT_EVIDENCE`: incomplete, unsupported, too-short, corrupted, or low-quality observation.
- `ERROR`: processing failed; it is never a security verdict.

## 3. Architecture

```text
Offline capture ---------+          +--------- Passive interface
                         v          v
                    Input validation
                           |
                    Metadata parsing
                           |
              Canonical bidirectional flows
                           |
              Shared versioned feature package
                    /      |       \
              Behavior    DNS    TLS/QUIC
                    \      |       /
              Calibration and abstention
                           |
                  Fusion and evidence
                           |
             SQLite, local API, event stream
                           |
                  Custodian dashboard
```

Interfaces depend on application services, services depend on domain contracts, and adapters implement domain ports. Feature extraction has no API or UI dependency. All queues, caches, flow tables, and histories are bounded and observable.

## 4. Target repository structure

```text
Custodian/
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── pyproject.toml
├── package.json
├── docs/
│   ├── CUSTODIAN_FULL_IMPLEMENTATION_BLUEPRINT.md
│   ├── architecture.md
│   ├── data-governance.md
│   ├── threat-model.md
│   └── demo-runbook.md
├── config/{default,development,demo}.yaml
├── src/custodian/
│   ├── cli.py
│   ├── core/{enums,ids,clocks,schemas,exceptions}.py
│   ├── contracts/
│   ├── ingestion/
│   ├── parsing/
│   ├── flows/
│   ├── state/
│   ├── features/
│   ├── observation/
│   ├── detectors/{behavior,dns,encrypted_session}/
│   ├── model_runtime/
│   ├── calibration/
│   ├── fusion/
│   ├── evidence/
│   ├── alerts/
│   ├── storage/
│   ├── telemetry/
│   ├── runtime/
│   └── api/
├── training/{manifests,prepare,train,evaluate,export}/
├── evaluation/{classification,calibration,degradation,throughput,reporting}/
├── frontend/{src,public,tests}/
├── tests/{unit,contract,integration,fixtures,e2e}/
├── scripts/
├── data/{raw,interim,processed,manifests}/
├── models/manifests/
├── reports/{metrics,figures,benchmarks}/
├── runtime/{captures,reports}/
└── docker/
```

The internal migration to `src/custodian` is a deliberate phase. Product strings, imports, entry points, environment prefixes, artifact metadata, tests, and docs change together. A compatibility shim may last one release only, must warn, and must not preserve old branding in user-facing output.

## 5. Canonical data contracts

Use typed schemas. External timestamps are UTC ISO 8601; internal timing uses integer nanoseconds when available and monotonic clocks for durations. Enumerations and required fields are strict; optional extensions must be documented.

### 5.1 Capture

Required fields: `capture_id`, `source_type`, `display_name`, `sha256` (null for live), `size_bytes`, `created_at`, `first_packet_at`, `last_packet_at`, `status`, `packet_counts`, `parser_warnings`, and `failure_reason`.

Capture status is `queued | validating | ready | running | paused | completed | stopped | failed`.

### 5.2 Flow

A flow is bidirectional with canonical endpoint ordering independent of packet direction. Required fields: `flow_id`, `capture_id`, IP version, protocol, endpoint A/B IP and port, initiator (`a | b | unknown`), first/last seen, directional packet/byte counters, TCP flag counters, and close reason (`fin | rst | idle_timeout | capture_end | evicted`).

### 5.3 Feature vector

Required fields: `feature_schema`, semantic `feature_version`, `family`, `entity_type`, `entity_id`, window start/end, ordered values, explicit missing fields, and quality metadata. Feature order comes from the schema/model manifest, never map iteration. A major version is incompatible; a minor addition requires documented defaults and compatibility tests.

### 5.4 Detector result

Required fields: `result_id`, capture/entity IDs, family, model ID/version, feature version, per-label scores, top label, calibrated confidence, decision, reason codes, evidence, limitations, and timestamp.

### 5.5 Alert

Required fields: `alert_id`, capture/entity IDs, threat outcome, severity (`INFO | LOW | MEDIUM | HIGH | CRITICAL`), calibrated confidence, first/last seen, status (`open | acknowledged | closed`), contributing results, evidence, timeline, limitations, and policy version.

Contracts live in one package and are used by runtime, API, storage, events, UI-generated types, and tests.

## 6. Passive replay and ingestion

Offline replay reads local files and never transmits packets:

```text
IDLE -> VALIDATING -> READY -> RUNNING <-> PAUSED -> COMPLETED
                                  |          |
                                  +-> STOPPED+
Any state may transition to FAILED with a recorded reason.
```

Controls: start, pause, resume, stop, seek backward, seek forward, and speed. Seeking resets volatile flow/detector state and deterministically rebuilds from the nearest safe checkpoint. Show rebuilding status. Stable IDs and upserts prevent duplicate persisted alerts after seeking.

Validation enforces configurable size limits, verifies magic, prevents traversal/symlink escapes, never executes content, and returns actionable errors. Count and safely skip malformed packets; fail honestly for catastrophic corruption or unsupported link types.

Live capture is optional, opt-in, interface-specific, and passive. Permission failure produces setup guidance, not an unsafe fallback.

## 7. Parser and flow engine

Support agreed Ethernet/cooked/raw-IP link types; IPv4/IPv6; TCP, UDP, ICMP; DNS metadata; and observable TLS/QUIC handshake metadata. Handle IPv6 extensions sufficiently to locate observable upper-layer protocols. Document fragment behavior; incomplete reassembly lowers quality rather than inventing values.

Flow requirements:

- canonical bidirectional five-tuple identity;
- explicit direction and initiator uncertainty;
- TCP FIN/RST, protocol-specific idle timeouts, capture-end flush;
- bounded inactive expiry and least-recently-used eviction;
- deterministic output for identical capture, config, and versions;
- counters for parsed, unsupported, malformed, dropped, truncated, and evicted data.

Raw payload retention is off by default. Evidence uses packet number/time and derived metadata, not copied sensitive payloads.

## 8. One shared feature implementation

One production feature package serves training, evaluation, offline replay, and live inference. A separate “equivalent” implementation is forbidden.

Behavior candidates: duration, directional packets/bytes/rates, length and inter-arrival statistics, TCP flags, direction ratios, peer/port fan-out, failed/short connection ratios, periodicity, burstiness, and rolling-volume changes.

DNS candidates: normalized query length, label counts/lengths, entropy and character ratios, unique-subdomain/query rates, NXDOMAIN and response-code distribution, answer counts, TTL statistics, record type, and repetition. Use a maintained public-suffix representation and consistent IDN normalization.

Encrypted-session candidates: observable protocol/version, handshake presence, SNI presence/length, ALPN category, cipher/extension counts, exposed certificate metadata, packet-length sequence summaries, direction changes, timing, duration, byte ratios, and QUIC long-header/version metadata. No decrypted data may be required.

Each family defines minimum packet count, duration, required fields, completeness, window width/stride, warm-up, and late-packet policy. Below the quality gate, return `INSUFFICIENT_EVIDENCE`. Missing values are explicit; silent zero-filling is forbidden unless zero has that documented meaning.

## 9. Data and label governance

Every dataset has a committed manifest with origin/source URL, license, acquisition date, checksums, raw schema, label meanings, approved detector family, known leakage risks, allowed use, preprocessing version, and approval. Raw data remains outside Git.

Labels map only when source semantics defensibly support the target. Never narrow a broad label into a specific threat. Ambiguous records are excluded or placed in an explicit review bucket.

Splits are deterministic and group-aware by capture, scenario/day, host, or campaign as appropriate, so related flows cannot cross train/validation/test. Fit preprocessing and calibration on training/disjoint calibration data only. Freeze model and thresholds before one final held-out test evaluation.

Class weighting or training-only resampling must be documented. Synthetic samples, if approved, remain inside training folds and are disclosed. Precomputed CSV features are deployable only when reproducible through the shared packet feature package.

## 10. Training, evaluation, and artifacts

Each detector family is independently versioned. Start with interpretable tabular baselines; accept complexity only when reproducible evaluation demonstrates worthwhile benefit under laptop constraints.

Pipeline:

1. Validate dataset manifests, licenses, and checksums.
2. Audit and normalize labels.
3. Produce fixed-seed group split manifests.
4. Extract ordered features through the shared contract.
5. Fit preprocessing on training partitions only.
6. Train bounded, recorded baseline searches.
7. Select using validation quality and operational false-positive cost.
8. Calibrate on a valid disjoint scheme.
9. Freeze per-class thresholds.
10. Evaluate once on held-out test data.
11. Export artifact, manifest, model card, metrics, confusion matrix, and environment lock.

Report per-class precision/recall/F1/support, confusion matrix, macro/weighted summaries, false-positive rate, PR-AUC where appropriate, Brier/calibration error, coverage versus selective risk, inference latency distribution, and memory footprint. Values come from saved outputs. Targets are never described as measurements.

An artifact manifest records model ID/family/version, source commit, dataset and split checksums, exact feature schema/version/order, preprocessing graph, label map, dependencies, calibration, thresholds, quality gates, evaluation reference, provenance/license, and SHA-256 for each file. Reject incompatibility or checksum failure. Never silently replace an unavailable real model with hard-coded detection rules.

## 11. Confidence, abstention, and evidence

Confidence is a calibrated estimate for the displayed label, not an accuracy claim. An alert requires a passed quality gate, a supported malicious score above its frozen threshold, and acceptable ambiguity. `UNKNOWN_SUSPICIOUS` handles meaningful anomalies/conflicts; `INSUFFICIENT_EVIDENCE` handles weak or unsupported observations.

Distribution-support checks may use evaluated missingness/range, distance/density, or conformal/nonconformity signals. Do not market them as universal unknown-attack detection.

Evidence states observed facts without causal overclaiming: for example elevated destination fan-out, unusual query entropy, periodic connections, directional byte imbalance, or uncommon handshake metadata. Each item includes feature/value, model-derived reference context, contribution direction, observation window, and packet/time references.

## 12. Fusion, severity, and alert lifecycle

Version 1 fusion is deterministic:

1. Preserve errors in diagnostics but exclude them from security voting.
2. Preserve insufficient evidence as a limitation.
3. Create a class alert when a validated family crosses its threshold.
4. Raise confidence/severity only for semantically compatible corroboration.
5. Represent incompatible high-confidence findings as parallel alerts or `UNKNOWN_SUSPICIOUS`; never invent a class.
6. Store all contributors and the fusion-policy version.

Severity ranks operational importance from calibrated confidence band, affected scope, persistence/volume, compatible agreement, and user-configured asset criticality. It does not imply certainty. Deduplicate by session, entity, threat, policy/model version, and time bucket. Repetition updates last-seen/count/evidence; replay after seek remains idempotent.

## 13. Persistence and exports

Use migration-controlled SQLite with at least: captures, flow summaries, feature-window references, detector results, alerts, evidence, replay checkpoints, model registry, application events, and schema migrations. Use transactions and a bounded single-writer strategy. Retention is configurable by age and size; raw packet bytes are not stored by default.

JSON/CSV and optional printable exports include generation time, application version, capture identity/hash, active model/feature versions, configuration fingerprint, limitations, and mock status. Sanitize filenames and escape spreadsheet formulas.

## 14. Local API and event stream

Bind to `127.0.0.1` by default and restrict origins. Remote binding/authentication/TLS requires a separate explicit deployment profile.

Minimum API:

```text
GET  /api/v1/health              GET  /api/v1/readiness
GET  /api/v1/models              GET  /api/v1/captures
POST /api/v1/captures/validate   GET  /api/v1/replay/status
POST /api/v1/replay/start        POST /api/v1/replay/pause
POST /api/v1/replay/resume       POST /api/v1/replay/seek
POST /api/v1/replay/stop         GET  /api/v1/flows
GET  /api/v1/alerts              GET  /api/v1/alerts/{alert_id}
POST /api/v1/alerts/{id}/acknowledge
GET  /api/v1/telemetry           POST /api/v1/exports
WS or SSE /api/v1/events
```

Use typed requests/responses, stable error codes, bounded pagination, input limits, cancellation, correlation IDs, and idempotent controls where possible. Never accept an arbitrary server filesystem path from the browser; use controlled import/upload or an allow-listed capture directory.

Health means process alive. Readiness separately reports database, parser, stream, and each model family as `ready | degraded | unavailable`, with a reason.

## 15. Dashboard

All branding is **Custodian**. Required areas:

- Header: connectivity, mode, replay state, model readiness, and limitations.
- Replay: validated file, position/duration, speed, start/pause/resume/stop, backward/forward seek, and rebuild progress.
- Summary: packets, bytes, flows, alerts, malformed/unsupported counts, CPU, memory, and measured latency.
- Alerts: sortable/filterable, color-coded rows for seven threats plus unknown/insufficient states.
- Detail: severity, calibrated confidence, entities, detector/model/feature versions, reason codes, evidence, limitations, and references.
- Host timeline: traffic/connection measurements with evidence accumulation and alert-fire markers.
- Model status and diagnostics: readiness, versions, validation, warnings, drops, and reconnect state.

Color is never the only cue. Require text/icons, accessible contrast, keyboard navigation, visible focus, semantic tables, reduced-motion support, and responsive laptop layouts.

Distinguish `OFFLINE` (backend unreachable), `IDLE` (connected), `DEGRADED`, `RUNNING`, `PAUSED`, and `FAILED`. Disabled actions show reasons. Event streaming reconnects with backoff and resynchronizes state.

## 16. Configuration, observability, and privacy

Precedence: command line, `CUSTODIAN_` environment variables, selected YAML profile, defaults. Unknown keys fail in production. Redact secrets/sensitive paths in displayed effective configuration.

Configuration covers input limits, formats, flow timeouts/memory, feature windows, model paths/thresholds, replay speed/checkpoints, database/retention, API origin/bind, logs, and privacy.

Logs are structured in production and include UTC time, level, component/event, correlation/capture ID, duration, and error category. Never log raw payloads or secrets. Privacy mode redacts sensitive address/domain/query details.

Local telemetry measures ingest rate, queue depth/drops, flows/evictions, detector calls/errors/latency, alerts, CPU, resident memory, database latency, and stream clients. Measure duration with monotonic clocks and expose count plus p50/p95/p99 over a named window. No samples means unavailable, not zero.

Security requirements: treat all imported data as untrusted; enforce size/time/memory limits; prevent traversal/symlink escape; escape UI/export content; use parameterized SQL; never shell out with untrusted arguments; apply least privilege; lock dependencies; scan vulnerabilities/licenses/secrets; document lawful capture/consent; support export anonymization and explicit retention/deletion.

## 17. Performance and reliability targets

These are acceptance targets, not measured claims:

- Streaming, bounded ingestion without loading an entire capture.
- Responsive UI for an approved demo-sized capture on one laptop.
- Bounded queues with visible backpressure/drop counters.
- Malformed packets cannot crash the replay worker.
- Pause/stop become observable at safe boundaries.
- Identical input/config/version produces equivalent flow and alert IDs.
- Browser recovers from backend loss without full reload.
- A failed detector is isolated and visibly unavailable.

Phase 0 measures the actual demo laptop and approved captures, then records numeric throughput, latency, memory, and file-size targets with methodology. Do not invent them beforehand.

## 18. Implementation phases

Each phase ends with tests and an acceptance record. Do not advertise a phase before its exit criteria pass.

### Phase 0 — Inventory and decisions

Inventory current modules, teammate code, tests, artifacts, datasets, licenses, commands, and defects. Measure the laptop baseline. Approve schemas, label semantics, feature policy, privacy defaults, manifests, migration map, and quality commands.

**Exit:** inventory/gap analysis and decisions are committed; useful behavior has regression coverage; no unverified artifact is deployable.

### Phase 1 — Naming and packaging

Migrate user-facing strings, package namespace, entry points, environment keys, tests, docs, and artifact metadata to Custodian, with a one-release warning shim only if necessary.

**Exit:** clean install/start works under Custodian naming and checks pass.

### Phase 2 — Contracts and configuration

Implement typed domain/API schemas, feature/artifact manifests, strict layered configuration, and fingerprints.

**Exit:** valid, missing, extended, and incompatible contract fixtures pass.

### Phase 3 — Ingestion and parsing

Implement format validation, bounded streaming, capture identity, protocol support, accounting, and deterministic corruption fixtures.

**Exit:** supported captures parse repeatably; unsupported/malformed input fails or degrades honestly.

### Phase 4 — Flows and replay checkpoints

Implement canonical flows, closure/expiry/eviction, capture-end flush, checkpoints, and deterministic seek rebuild.

**Exit:** golden flow, bounded-memory, and seek-idempotency tests pass.

### Phase 5 — Shared features

Implement versioned family schemas, one extractor, explicit missingness/quality gates, and golden training/runtime parity tests.

**Exit:** identical observations yield identical ordered features everywhere.

### Phase 6 — Data preparation

Acquire approved data outside Git; verify provenance/license/checksums; audit mappings/leakage; generate grouped split manifests.

**Exit:** each planned class has defensible data or is explicitly unavailable.

### Phases 7–9 — Detector families

Train, calibrate, threshold, held-out evaluate, export, and validate behavior first, DNS second, encrypted-session third. Enable only outcomes supported by evidence.

**Exit per family:** saved held-out report, model card, artifact manifest/checksum, calibration, and packet-to-feature runtime parity exist.

### Phase 10 — Abstention and explanations

Implement quality, ambiguity, distribution-support checks, reason codes, evidence, and coverage/selective-risk evaluation.

**Exit:** weak/unsupported/conflicting samples abstain predictably and evidence traces to observations.

### Phase 11 — Fusion and alerts

Implement versioned fusion/severity, deduplication, lifecycle, and host timelines.

**Exit:** agreement, conflict, repetition, and seek/replay behavior is deterministic.

### Phase 12 — Persistence and export

Implement migrations, repositories, transactions, retention, restart recovery, and provenance-complete safe exports.

**Exit:** completed runs survive restart and migration/export tests pass.

### Phase 13 — API and events

Implement endpoints, detailed readiness, replay commands, pagination, event delivery/reconnect, input bounds, and cancellation.

**Exit:** API contract/integration tests pass for normal, invalid, disconnected, and concurrent-control cases.

### Phase 14 — Dashboard

Implement responsive status, controls, table/detail, timeline, model status, diagnostics, reconnect, export, and accessibility.

**Exit:** browser tests cover replay, pause, seek, alert detail, reconnect, and export.

### Phase 15 — Optional passive live mode

Use the exact parser/flow/feature/detector/alert pipeline and document OS permission behavior.

**Exit:** no active packets are generated and offline/live parity passes for equivalent observations.

### Phase 16 — Hardening and release

Run performance, soak, fuzz/property, security, privacy, dependency, and recovery tests. Finish model cards, architecture, governance, setup, limitations, and demo runbook. Rehearse on a clean machine.

**Exit:** the definition of done is satisfied and release artifacts are reproducible.

## 19. Test matrix

- **Unit:** flow identity, timing/statistics, normalization, missingness, quality gates, threshold edges, fusion/severity, dedupe, config, redaction, export escaping.
- **Contract/golden:** packet metadata, flows, ordered features, detector results, alerts, events, and exports. Synthetic protocol fixtures test software behavior, never model quality.
- **Integration:** capture-to-alert, restart, controls/seek, invalid artifact isolation, partial readiness, pagination, reconnect/resync, retention.
- **ML:** split-group isolation, preprocessing boundaries, reproducibility tolerance, feature parity, calibration, frozen thresholds, coverage, drift/range checks, checksum rejection.
- **Robustness/security:** malformed/truncated files, oversized fields, traversal/symlinks, hostile names, formula/script injection, database contention, event floods, queue saturation, corruption, missing permissions, parser fuzzing, dependency scanning.
- **UI/accessibility:** keyboard/focus, non-color cues, laptop widths, reduced motion, loading/empty/error states, disabled reasons, long values, large alert sets, reconnect.

## 20. Definition of done

The full build is complete only when:

- Custodian naming is consistent in supported user-facing and internal interfaces.
- Offline replay is passive, deterministic, bounded, validated, and supports start/pause/resume/stop/seek.
- Optional live mode is passive and shares the production pipeline.
- Training, evaluation, replay, and live inference share versioned extraction.
- Every enabled outcome has approved provenance, defensible mapping, group-safe held-out evaluation, calibration, validated artifacts, and saved results.
- Unsupported outcomes are visibly unavailable and never simulated by hidden rules.
- Unknown and insufficient-evidence decisions work as specified.
- Alerts include provenance, versions, evidence, limitations, and timeline references.
- Storage migration/retention/recovery/export, API/event reconnect, and UI controls pass tests.
- Accessibility, privacy, security, performance, and failure-recovery checks pass on the demo laptop.
- Clean-machine setup and demo runs succeed with documented commands and approved captures.
- No raw/private data, secrets, model binaries, databases, build output, or temporary files are accidentally committed.
- README, architecture, governance, model cards, limitations, and runbook match shipped behavior.

## 21. Demonstration contract

Use only approved captures with provenance and known expected observations. Verify checksums, models, ports, disk, permissions, and browser/API connectivity before presenting. Keep an approved benign example, a validated-alert example if a real supported artifact exists, and malformed input for honest failure behavior.

Always distinguish observed facts, calibrated assessments, abstentions, synthetic test fixtures, measured performance, and future targets. If a detector lacks defensible data or a validated artifact, show it as unavailable. Never substitute fabricated evidence for a missing capability.

## 22. Implementation handoff

Before code changes, read this document and inspect the repository. Produce a Phase 0 gap analysis listing current structure, reusable teammate modules, missing modules, conflicts, available datasets/artifacts and their validation status, required dependencies, implementation order, and exact files proposed for the first approved change.

Proceed in phase order with small reviewable commits and evidence for every exit criterion. Changes to threat semantics, passive-only behavior, data provenance, feature parity, artifact trust, or privacy defaults require explicit product-owner approval and a blueprint revision before implementation.

## 23. Observation-integrity layer

The following layer is mandatory to carry the original full design's central differentiator into Custodian. It sits after parsing/feature extraction and before detector invocation. It changes how every detector behaves; it is not a decorative post-processing feature.

### 23.1 ObservationFrame

Every candidate flow, host window, domain, session, or flow export has an `ObservationFrame`. It records the actual evidence visible to the system rather than assuming every input is a complete packet capture.

Required capability fields include:

- `has_packet_timestamps`, `has_packet_sizes`, `has_directionality`, and `has_bidirectional_flow_stats`;
- `has_tcp_flags` and payload length only when observable as a length;
- `has_dns_query_name` and `has_dns_query_type`;
- `has_tls_metadata`, `has_tls_fingerprint`, and `has_quic_metadata`;
- source type and parser/link-layer limitations.

Required quality fields include sampling-known flag/rate, timestamp resolution, capture completeness, packet-loss indication, usable sample count, parse-error rate, and evidence mask. Evidence availability is ternary where needed: `AVAILABLE(value)`, `UNAVAILABLE`, or `NOT_APPLICABLE`. It must never be collapsed into numeric zero without documented semantics.

### 23.2 Capability-aware routing

Before invoking a detector, the router evaluates its declared required capabilities against the `ObservationFrame`.

Examples:

- A flow-only export can run a behavior detector using available flow/directional fields but cannot run lexical DGA detection or TLS-fingerprint analysis.
- Encrypted DNS without an observable query name can contribute timing/volume evidence but cannot claim lexical DGA evidence.
- A one-connection observation cannot make a trusted periodic-beaconing determination because recurrence and timing evidence are absent.

Every disabled, degraded, or abstained path records its reason in the result, alert detail, detector-status page, and event stream. The router must not invoke a detector using fabricated defaults merely because a model accepts the feature shape.

### 23.3 Evidence contracts

An Evidence Contract is deterministic, versioned policy per detector/outcome. It specifies required capabilities, minimum sample/observation duration, required feature quality, and prohibited claims. It produces `ACCEPT`, `BENIGN`, `UNKNOWN_SUSPICIOUS`, or `INSUFFICIENT_EVIDENCE` before an alert is finalized.

Minimum examples:

- `C2` needs repeated observations, usable timing, destination recurrence, and enough samples for periodicity.
- lexical `DGA` needs a visible DNS query name.
- `RECON` needs enough recent observations for host/port fan-out.
- `EXFILTRATION` needs directional-volume evidence and a meaningful comparison window.

Evidence contracts are configuration, test fixtures, and alert provenance—not untracked code branches.

### 23.4 Two distinct confidence signals

Each verdict and alert must expose both:

- **Threat confidence** — calibrated probability that the observed pattern matches the selected known class.
- **Observation confidence** — transparent quality/coverage score for the passive evidence: required-capability coverage, sample count, completeness, sampling, timing quality, and missing optional evidence.

Observation confidence is not a probability or a claim of calibration unless it has been separately validated as one. Severity policy may use both signals but never substitutes observation quality for threat probability.

### 23.5 Shadow Observation Testing and robustness

For candidate alerts, high-severity findings, and a sampled validation fraction—not every ordinary flow—run passive shadow observation tests. The test creates controlled degraded copies of already extracted in-memory features/evidence, masks selected optional evidence, reruns the same detector, and records class stability, confidence retention, and decision stability.

From that test derive a deterministic, documented `observation_robustness` score. It is an assessment of stability under reduced visibility, not another threat detector. The procedure never alters network traffic or raw captures and must have a configurable CPU/latency budget.

Offline evaluation also produces observation-degradation curves at configured visibility levels, for example full observable metadata, reduced metadata, and flow-only representation. Report detection metrics, calibration, abstention rate, insufficient-evidence rate, and alert stability for each level. These curves are evaluated artifacts, not assumed claims.

### 23.6 Common detector verdict and ProofStream alert

Every detector returns one typed `DetectorVerdict` contract containing detector ID/family, threat class, raw score, calibrated threat confidence, observation confidence, candidate flag, required/available/missing evidence, evidence, model/feature versions, observation frame ID, timings, decision, and limitations.

The single final structured alert contract is named `ProofStreamAlert`. It extends the alert schema with source type, flow/window identifiers, threat confidence, observation confidence, optional observation robustness, available/missing evidence, detector/model/schema details, stage timings, correlation context, and policy versions. Pydantic validation guarantees structure and types; it does not prove model correctness.

## 24. Expanded runtime, adapter, and state requirements

### 24.1 Adapter order and common boundary

Implementation order is PCAP replay, Zeek/derived-metadata replay, live passive capture, NetFlow/IPFIX, then sFlow. All adapters implement one `IngestAdapter` boundary that emits canonical raw observations; downstream components must not depend on where observations originated.

Canonical internal event families are `PacketEvent`, `DNSObservation`, `TLSObservation`, `QUICObservation`, and `FlowExportObservation`. Packet events contain only observed metadata such as timestamp, addresses/ports, transport protocol, packet length, TCP flags, and observable payload length. They never carry decrypted application payloads.

### 24.2 Temporal state engine

In addition to per-flow data, maintain bounded multi-timescale state keyed by source, destination, source-destination pair, source-destination-port tuple, domain, and TLS/QUIC destination. Configurable initial windows may include 5 seconds, 30 seconds, 60 seconds, and 5 minutes; no window is hard-coded in feature formulas.

State contains recent timestamps, packet/byte/flow counts, unique destination/port/source/domain sets, recurrence, and directional ratios. Use deques/ring buffers, counter maps, rolling aggregates, and TTL-expiring maps. Do not retain the complete traffic history in memory.

### 24.3 Runtime modes and replay pacing

Custodian supports:

1. Offline feature preparation: authorized capture or dataset input through parser, flow/state, and shared features into Parquet or another versioned analysis table.
2. Replay mode: paced incremental input with 1x, faster-than-real-time, and unpaced benchmark modes.
3. Optional live passive mode: a selected passive interface through the same downstream pipeline.

Replay and live must converge before flow reconstruction; training preparation uses the same parser/feature contracts wherever raw/replayable data exists. The first end-to-end demo uses a PCAP before any live or export adapter is considered complete.

## 25. Complete model and data requirements

### 25.1 Model choices and LLM boundary

Preferred V1 models are XGBoost or LightGBM with Random Forest as a baseline. Start with engineered tabular features; do not make CNN, GRU, LSTM, Transformer, or character-CNN architectures mandatory. Consider them only after measured improvement and streaming-budget validation.

An LLM is not a network-traffic classifier and must not receive raw traffic as its detection path. A future disabled-by-default LLM may summarize an already validated `ProofStreamAlert` or draft analyst notes. It must never change class/confidence, invent evidence, or perform network actions.

Hybrid statistical-plus-ML design is required: entropy, periodicity, fan-out, byte asymmetry, recurrence, and rate change are deterministic features/supporting evidence; ML evaluates their learned combination. Do not create a separate neural model for each statistical signal.

### 25.2 Dataset adapters, labels, and targets

Public research datasets, authorized isolated-lab captures, and replayed captures may be used only with documented license/provenance and adapter mapping into the shared Custodian schema. Dataset-specific CSVs are not concatenated blindly. Controlled scenarios must pass through the same parser and feature engine when possible; no operational attack-generation instructions belong in the project.

Labels record `label`, `label_source`, `scenario_id`, `capture_id`, `time_range`, and `dataset_name`. Leakage prevention explicitly excludes exact IP addresses, exact domain labels, static capture IDs, attack-schedule timestamps, and dataset row identifiers unless their use is justified as a deployable feature.

Suggested split roles are training 60–70%, validation 10–15%, calibration 10–15%, final test 10–20%, subject to group separation. These are planning guidance, not measured guarantees or a reason to force data into proportions that violate group integrity.

Planning-scale ranges for behavior, DNS, and encrypted-session examples are optional capacity targets only. They must never be represented as collected data until manifests and counts prove them.

## 26. Operations, tooling, and failure policy

### 26.1 Recommended stack and machine profile

Use Python 3.11+ with Pydantic/Pydantic Settings, NumPy, one primary dataframe library, scikit-learn, XGBoost or LightGBM, YAML support, a bounded PCAP parser such as `dpkt`, FastAPI/Uvicorn, WebSocket support, SQLite/SQLAlchemy or equivalent, PyArrow for offline tables, and `psutil`. Zeek may be an optional external metadata tool; Scapy and tshark/pyshark may assist development or validation but are not mandatory core runtime dependencies.

Recommended development hardware is a modern multicore CPU, 16 GB RAM workable and 32 GB preferred, SSD storage with space for captures, and an optional RTX 3050-class GPU. CPU must remain sufficient for V1; likely bottlenecks are parsing, state maintenance, preprocessing, and disk I/O rather than GPU inference.

### 26.2 CLI boundary

Provide a stable CLI boundary equivalent to:

```text
custodian replay --config <replay-config> --pcap <authorized-capture>
custodian live --config <live-config> --interface <passive-interface>
custodian prepare-data --manifest <manifest>
custodian train behavior|dns|encrypted-session
custodian evaluate --all
custodian benchmark --pcap <authorized-capture>
custodian api
```

Exact flags may evolve, but commands must remain local, authorized, and incapable of triggering active network behavior.

### 26.3 Failure behavior

- Corrupt capture: reject or safely skip affected records, log reason, and retain counts.
- Unsupported protocol: mark unsupported and continue where safe.
- Missing/corrupt/incompatible artifact: disable only that detector with visible readiness reason.
- Missing optional evidence: update the observation mask.
- Missing required evidence: abstain; do not crash.
- Dashboard unavailable: detection continues; events may buffer only within configured bounds.
- Temporary storage failure: apply configured bounded buffering/retry policy and make data-loss risk visible.

Optimize only after profiling in this order: parser, flow/state update, feature extraction, inference, storage, dashboard. Possible later optimization includes short micro-batches, offline vectorization, compact aggregators, reduced allocations, safe multiprocessing, and optional external metadata extraction.

### 26.4 Coding standards and delivery order

Use type hints, small modules, public-interface documentation, deterministic tests, formatter/linter/type checking, explicit exceptions, and configuration rather than magic paths/thresholds. Avoid global mutable state, giant entry files, hidden feature transformations, duplicated preprocessing, and dashboard logic inside detection.

Priority when time is constrained:

1. Mandatory core: replay, parser, flows, temporal state, shared features, three-family architecture, standardized alerts, dashboard, measurement, passive/no-decryption guarantee.
2. Evidence-integrity core: ObservationFrame, capability routing, evidence contracts, calibration, two confidence signals, ProofStream alerts.
3. Advanced evidence work: shadow testing, robustness, degradation curves, unknown/open-set path.
4. Later work: complete export adapters, advanced sequence models, optional LLM summaries, distributed deployment.

Never sacrifice the mandatory passive streaming pipeline for later tiers.

## 27. Additional completion checks inherited from the full blueprint

Before final completion, additionally verify:

- incremental replay can emit alerts before a long capture finishes;
- input source capability sets are accurate for PCAP, derived metadata, and flow-only input;
- flow identity uses a stable canonical endpoint/protocol key plus a session discriminator and never a process-randomized hash;
- feature-regression changes bump schema versions and trigger model retraining/compatibility review;
- the dashboard consumes typed API/event contracts, never detector internals;
- throughput includes packets/sec, flows/sec, and Mbps when packet ingestion makes it meaningful;
- stage latency separately covers ingest, parse, flow/state update, feature extraction, routing, inference, evidence, shadow testing, and alert creation;
- detector status exposes enabled/disabled/degraded state, required evidence, available evidence, artifact/schema version, and reason;
- the demo includes a reduced-evidence representation showing honest disabling or abstention;
- the repository includes data-directory instructions, lockfiles, reproducibility metadata, and model-card/evaluation-report locations.
