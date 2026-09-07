# Custodian implementation status

**Updated:** 2026-09-05  
**Governing plan:** `docs/CUSTODIAN_FULL_IMPLEMENTATION_BLUEPRINT.md`

## Implemented application scope

- Custodian package/branding migration and removal of tracked IDE metadata.
- Strict shared contracts for captures, observations, flows, features, verdicts, alerts, events, and lifecycle status.
- Allow-listed, size-bounded `.cap`, `.pcap`, and `.pcapng` validation with SHA-256 identity and path/symlink protection.
- Incremental read-only Ethernet, Linux cooked, and raw-IP capture ingestion.
- IPv4/IPv6 TCP, UDP, ICMP, observable DNS, TLS, and QUIC metadata parsing without decryption or raw-payload retention.
- Bidirectional flow tracking with explicit initiator direction and FIN/RST/timeout/capture-end/eviction close reasons.
- Bounded temporal state, shared feature extraction, ObservationFrame capability routing, dual confidence fields, and explicit missing evidence.
- Trusted-artifact loading gate, per-family readiness isolation, feature-range distribution-support checks, passive shadow-observation helpers, and conservative fusion policy.
- Deterministic replay modes, pause/resume/stop, forward/backward seek, visible rebuild state, and an honest origin checkpoint strategy.
- Alert repetition upserts, first/last seen, occurrence count, acknowledge/close lifecycle, and deterministic policy provenance.
- Migration-controlled local SQLite persistence, bounded retention, restart recovery, events, flow summaries, checkpoints, and parameterized queries.
- JSON/CSV exports with timestamp, application/version, capture/config/model provenance, limitations, mock status, bounded output location, and spreadsheet-formula escaping.
- Versioned localhost API, stable validation errors with correlation IDs, bounded queries, capture browser, flows, alerts, diagnostics, readiness, host timeline, and resumable application events.
- Responsive dashboard with validated capture selection, replay/seek controls, measured telemetry, filterable/sortable color-and-text alert table, alert inspector/lifecycle, host evidence timeline, detector readiness, input-adapter diagnostics, and reconnect/resynchronization behavior.
- Stable local CLI whose training, dataset preparation, and live-capture commands remain explicitly gated.
- DRIFT26DSN DGA preparation and HGB training path with shared DNS lexical features, whole-family held-out groups, explicit runtime decision policy, hashed artifact export, and optional parallel DNS detector configuration.

## Deliberately not activated

- Independent external model evaluation and final production approval. A real DRIFT26DSN DGA candidate and measured internal results now exist locally, but held-out-family DGA recall remains weak and the package is an MVP candidate rather than a production-approved detector.
- Deserialization of the existing local behavior artifact, whose trust setting remains `false`.
- DNS or encrypted-session trained artifacts and any claimed detection metrics.
- Live network capture or interface access.
- Zeek, NetFlow/IPFIX, and sFlow input implementations; they are declared visibly unavailable.
- Active scanning, attack generation, mitigation, packet transmission, traffic injection, payload execution, or TLS/QUIC decryption.
- Release-hardening claims such as fuzz coverage, dependency/security audits, packaging certification, and laptop acceptance benchmarks.

The model/training phase may begin only after the user explicitly approves the isolated offline VM workflow. The live passive phase requires a separate explicit approval and interface review even after model work is complete.
