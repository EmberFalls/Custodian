# Custodian Phase 0 gap analysis

**Recorded:** 2026-09-05  
**Governing plan:** `docs/CUSTODIAN_FULL_IMPLEMENTATION_BLUEPRINT.md`  
**Baseline:** commit `1b985be`; Python unit suite 42/42 passing; frontend production build passing.

## Safety boundary

Implementation may proceed on the application, but model training, dataset acquisition, untrusted artifact loading, active network operations, and live-interface testing are not approved in this phase. Training and raw-capture analysis must later happen in the user-approved isolated VM workflow. The runtime remains passive, read-only, bound to `127.0.0.1`, and has no traffic-transmission feature.

## Current repository

- Baseline `src/sentinelx` package: working prototype for PCAP replay, parsing, flows, bounded temporal state, shared feature extraction, a behavior-model adapter, evidence gating, alert building, telemetry, and a local FastAPI service. Phase 1 migrates this package to `src/custodian`.
- `frontend`: working React/Vite dashboard with replay controls and telemetry.
- `training`: CIC-IDS2017 preparation and behavior-model training plus early generic DNS/TLS training modules.
- `tests`: 42 passing unit tests and API/PCAP/model integration tests.
- `configs`: strict YAML configuration for replay, models, evidence, severity, and bounded runtime settings.
- `data`, `model_artifacts`, `reports`: ignored local/generated content with committed placeholders.

## Reusable modules

- Deterministic canonical flow identity and bidirectional flow aggregation.
- Incremental DPkt capture reader, passive replay modes, pause/resume/stop, and progress.
- IPv4/IPv6 TCP/UDP/ICMP metadata parsing plus observable DNS/TLS/QUIC metadata parsing.
- Bounded temporal state and three versioned feature extractor families.
- Strict Pydantic contracts and explicit feature availability.
- Artifact checksum/feature compatibility validation and calibrated batch inference.
- Evidence gate, severity, deduplication, telemetry, API controls, and dashboard foundation.
- Dataset preparation and evaluation utilities, which remain disabled pending isolated training approval.

## Missing or incomplete

- At the recorded baseline the internal namespace was still `sentinelx`; the blueprint requires `custodian` everywhere.
- Capture identity/manifest contract, richer ObservationFrame, capability router, evidence-contract provenance, dual confidence signals, and ProofStreamAlert are incomplete.
- Replay lacks validate/ready states, seek/checkpoint rebuild, capture listing, stable event stream, and idempotent persistence.
- SQLite migrations/repositories, alert lifecycle, exports, retention, restart recovery, and correlation timelines are absent.
- API v1 coverage/readiness/pagination/correlation errors is partial.
- DNS and encrypted-session detectors have no approved trained artifacts and must remain unavailable.
- Behavior artifact is locally present but was created before the newly confirmed isolation policy; it must not be loaded or represented as approved until provenance and VM handling are reviewed.
- Zeek, NetFlow/IPFIX, sFlow, and optional passive live adapters are not implemented.
- Shadow observation testing, degradation evaluation, drift/OOD support, model cards, architecture/governance/threat-model/runbook documents, and release hardening are incomplete.

## Conflicts with the governing plan

- README describes a presentation prototype and gives host-side training commands.
- Old `BOT_OR_C2_LIKE`, `SUSPICIOUS_ENCRYPTED`, and `UNKNOWN` labels conflict with the authoritative full-build semantics.
- API uses `/health`, `/api/v1/status`, and prototype websocket routes rather than the complete v1 contract.
- Current code can deserialize a configured Joblib artifact during normal startup; artifact loading needs an explicit trust gate.
- Repository contains tracked PyCharm project metadata even though `.idea/` is ignored.

## Local data and artifacts

The workspace contains ignored local demo captures, large CSVs, one processed Parquet table, a dataset manifest, and a behavior XGBoost package. Their presence is not evidence of safety, provenance, approval, or model validity. No training or artifact deserialization is authorized by this analysis. Git correctly ignores generated data and model files; the committed placeholders remain safe.

## Dependencies

Current core dependencies cover Python 3.11+, Pydantic, DPkt, FastAPI/Uvicorn, NumPy/pandas/PyArrow, scikit-learn/XGBoost, psutil, YAML, Joblib, and websockets. Full implementation additionally needs a migration-controlled SQLite layer, structured event transport, frontend tests, type checking, property/fuzz testing, dependency auditing, and reproducible lock metadata. New dependencies will be added only when a phase needs them and after reviewing their network and artifact implications.

## Implementation order

1. Custodian namespace, safe defaults, trust gate, documentation, and clean baseline.
2. Full contracts/configuration and capture validation.
3. Parser/input accounting and canonical adapter boundary.
4. Flow lifecycle, checkpoints, deterministic seek, and bounded state.
5. Shared feature/observation integrity and capability routing.
6. Persistence, fusion, alert lifecycle, export, API/events, and dashboard.
7. Robustness, packaging, and release hardening.
8. Dataset preparation and model training only after explicit approval inside the isolated VM.
9. Optional passive live mode only after replay completion and separate explicit approval.

## Exact Phase 1 change scope

- Create `src/custodian/**` by migrating the existing package without architectural redesign.
- Update imports in `training/**`, `tests/**`, and `tools/**` to the Custodian namespace.
- Modify `pyproject.toml`, `README.md`, configuration, and artifact compatibility metadata.
- Add `docs/data-governance.md`, `docs/threat-model.md`, `docs/architecture.md`, and `docs/demo-runbook.md`.
- Add a model-artifact trust setting that defaults to disabled and reports unavailable rather than loading unapproved serialized artifacts.
- Remove tracked `.idea/**` workspace metadata and keep it ignored.
- Preserve all existing reusable behavior and require the unit suite and frontend build to remain green.
