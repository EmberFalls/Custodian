# Custodian judge demonstration runbook

This is the step-by-step presentation flow for demonstrating the current Custodian MVP on one laptop.

The main story is:

> Custodian passively reads an authorized packet capture, reconstructs network behaviour, extracts runtime-compatible features, runs trained detector models, applies an evidence gate, and presents explainable alerts—without transmitting captured traffic or sending runtime data to an external service.

## 1. What this demonstration proves

The demonstration should visibly establish that Custodian:

- processes `.cap`, `.pcap`, and `.pcapng` captures locally and passively;
- validates a capture before allowing it to run;
- reconstructs flows and temporal state from packet metadata;
- uses trained Behaviour, DNS-tunnelling, and TLS/QUIC detector packages;
- uses the same feature definitions at training and runtime;
- gates predictions using available evidence instead of blindly alerting;
- records confidence, severity, evidence, limitations, model version, and timing;
- provides replay, investigation, traffic, detector, and performance views; and
- has no packet-transmission return path.

Do not describe capture-file processing as live interface monitoring. The current showcase path is passive **PCAP replay**. A future live adapter would feed authorized interface observations into the same downstream flow, feature, model, evidence, and alert pipeline.

## 2. Files to use

Use only the prepared files already present in `data/demo/`.

| Capture | Purpose | Expected result |
|---|---|---|
| `dns.cap` | Primary DNS-tunnelling demonstration | At least one evidence-backed `DNS_TUNNEL` alert from the DNS model |
| `ddos.pcap` | Behaviour-model demonstration | Behaviour alerts from the DDoS-style synthetic fixture |
| `http.cap` | Ordinary parsing and telemetry demonstration | Packets and flows are processed; zero alerts is acceptable and does not prove the capture safe |

Avoid using these during the main presentation:

- `sample1.pcap`: its Zigbee link type is unsupported by the current Ethernet/IP parser.
- CSV files: they are model-training data, not replayable packet captures.
- Unknown captures downloaded immediately before the presentation.

The capture determines the displayed packet, flow, byte, rate, and latency values. Never promise an exact performance number before running it.

## 3. Pre-demonstration preparation

Complete this checklist before the judges arrive:

- Connect the laptop to power.
- Close unnecessary applications and disable distracting notifications.
- Confirm Python dependencies and frontend packages are installed.
- Confirm `configs/models.demo.yaml` exists from the repository clone.
- Confirm Behaviour, DNS, and TLS/QUIC model packages exist under `model_artifacts/`.
- Confirm `dns.cap`, `ddos.pcap`, and `http.cap` exist under `data/demo/`.
- Keep the website and API bound to `127.0.0.1`; do not expose either server to the LAN.
- Perform one complete rehearsal after the final reboot.
- Keep both terminal windows available in case the judges ask how the system is running.

The four reviewed model artifacts and `configs/models.demo.yaml` are included in Git. Datasets, captures, local overrides, and generated runtime files remain excluded.

## 4. Start the application

Open PowerShell terminal 1 in PyCharm and run the backend:

```powershell
Set-Location 'C:\Users\Aaryan\Documents\ChatGPT\Custodian'
$env:CUSTODIAN_MODELS_CONFIG = 'models.demo.yaml'
$env:LOKY_MAX_CPU_COUNT = '4'
& '.\.venv\Scripts\python.exe' -m uvicorn custodian.api.app:app --host 127.0.0.1 --port 8000
```

Leave this terminal running. Open PowerShell terminal 2 and run the frontend:

```powershell
Set-Location 'C:\Users\Aaryan\Documents\ChatGPT\Custodian\frontend'
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173/`.

Optional pre-flight checks:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/health'
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/readiness' | ConvertTo-Json -Depth 10
```

The readiness response should report `ready`, and the Behaviour, DNS, and TLS/QUIC entries should each report `ready`.

## 5. Login

On the landing page:

1. Briefly show the passive-monitoring value proposition.
2. Click **Sign In** or **Launch Dashboard**.
3. Select **Lead Security Administrator** from the supplied local demo accounts.
4. Sign in and enter the dashboard.

If credentials must be entered manually:

```text
Username: admin
Password: CustodianAdmin2026!
```

Say:

> This login is the local MVP presentation boundary. The application, model inference, database, and telemetry all remain on this laptop.

Do not describe the demo login as production-grade identity and access management.

## 6. Begin with safety and readiness

Before starting a capture, point to the top header and explain:

- **MONITOR ACTIVE**: the local API and telemetry stream are responding.
- **RETURN PATH NONE**: Custodian has no mechanism that sends packets back onto the network.
- **SOURCE PCAP REPLAY**: the current input is a saved capture, not a live interface.
- **READINESS READY**: the core runtime and all three configured detector packages loaded successfully.
- **PASSIVE**: capture contents are observed and classified, never executed.

Press `P` or click **Pres ON** if presentation mode improves projector visibility.

Suggested narration:

> The critical safety property is visible at all times: return path none. Custodian reads observations, but it does not scan hosts, inject traffic, block connections, decrypt encrypted payloads, or replay packets onto the network.

## 7. Show the detector architecture

Open **04 DETECTORS** before replay.

Point out:

1. The **Behaviour** detector covers flow-based outcomes such as DDoS, reconnaissance, and C2-like behaviour.
2. The **DNS** detector package contains the trained DNS-tunnelling classifier.
3. The **TLS/QUIC** detector uses observable encrypted-session metadata and does not decrypt payloads.
4. Each card shows its model version, schema version, class mapping, and required evidence.
5. The local load gate is open because the exact hash-verified artifacts were approved for this laptop demonstration.
6. Model failures are isolated by detector family; the runtime does not replace a missing model with hard-coded rules.

The current DNS package contains `BENIGN_DNS` and `DNS_TUNNEL`. Do not claim that a DGA classifier is integrated unless the separate DGA contribution has actually been merged, configured, and verified.

Suggested narration:

> These are serialized, trained estimators—not frontend rules. The backend validates each artifact package, feature schema, class mapping, thresholds, and hashes before it reports the detector ready.

## 8. Primary demonstration: DNS tunnelling

Return to **01 LIVE MONITOR**.

### 8.1 Reset previous state

If an older run is visible, click **Reset** and wait for the dashboard to return to idle.

### 8.2 Select and validate the capture

1. Select `dns.cap`.
2. Select **PACED** mode.
3. Select `2×` or `5×` speed.
4. Click **Validate**.
5. Wait for the capture to show as ready.

Explain:

> Validation confines the resolved path to `data/demo`, checks the supported extension, capture magic, file size, and link-layer type. Merely renaming an arbitrary file does not make it a valid PCAP.

### 8.3 Start replay

Click **Start replay**. While it runs, show:

- **Data inspected**: capture-frame bytes read locally;
- **Packets**: frames accepted by the parser;
- **Packet rate**: packets processed per wall-clock second;
- **Flows analysed**: reconstructed sessions, not simply packet count;
- **Active flows**: currently open bidirectional sessions;
- **Throughput**: this laptop's processing rate, not necessarily the capture's original network rate;
- **Traffic timeline**: bounded telemetry history; and
- **Inspection pipeline**: ingest → flows → features → detect → evidence → alert.

If useful, demonstrate **Pause** and **Resume** once. Do not overuse controls; the investigation story is more important.

### 8.4 Open the generated alert

When the `DNS_TUNNEL` row appears, select it and explain:

- source and destination identify the observed flow;
- destination port `53` indicates DNS traffic;
- `DNS_TUNNEL` is the trained model's selected class;
- calibrated confidence is the model confidence after calibration;
- class threshold is the configured MVP operating point;
- severity communicates prioritization;
- `ACCEPT` means the prediction also passed the evidence gate;
- evidence quality describes how complete the required passive metadata was;
- evidence lists the lexical and temporal values used for the decision;
- limitations disclose what the capture and model cannot establish; and
- model and schema versions make the decision reproducible.

For the prepared `dns.cap` verification run, Custodian generated a real `DNS_TUNNEL` alert with strong evidence. Mention the confidence shown on the current screen; do not memorize or fabricate it because a regenerated artifact can change the value.

Suggested narration:

> A model prediction alone does not automatically become an alert. Custodian checks that the required DNS evidence is observable, applies the configured class threshold, records limitations, and then emits a structured alert.

## 9. Investigate the alert

Open **02 ALERTS** and show:

- the colour-coded severity and threat class;
- timestamp and source/destination context;
- calibrated confidence and decision;
- the complete evidence-backed detail panel;
- alert status and occurrence count; and
- acknowledgement or closure controls if demonstrating the analyst workflow.

Do not say that an alert proves compromise. It is a prioritized, evidence-backed model assessment for analyst investigation.

## 10. Show traffic context

Open **03 TRAFFIC** and explain:

- flow summaries are reconstructed from replayed packets;
- host timelines show behaviour accumulating over time;
- the alert marker connects a decision to preceding observations; and
- payload contents are not displayed, resolved, enriched, or sent to reputation services.

Use this page to answer: “What happened before the alert fired?”

## 11. Show measured performance

Open **05 PERFORMANCE** after replay completes. Show:

- processing throughput;
- packet and new-flow rates;
- P50 and P95 total-pipeline latency;
- CPU and memory consumption;
- elapsed and active-processing time;
- feature snapshot, inference, and evidence-decision counts; and
- the stage-by-stage latency table.

Suggested narration:

> These values are measured from this run on this laptop. We distinguish local processing throughput from the original capture's network rate, so the dashboard does not manufacture a live-bandwidth claim.

## 12. Optional second demonstration: Behaviour detector

If time permits:

1. Return to **01 LIVE MONITOR** and click **Reset**.
2. Select `ddos.pcap`.
3. Validate it.
4. Select **FAST** mode.
5. Start replay.
6. Open the resulting Behaviour alerts.

Explain that the Behaviour model reasons over flow and temporal features, including packet/byte rates, directionality, and target concentration. This demonstrates that Custodian is not only matching suspicious DNS names.

FAST remains passive; it only removes capture-timestamp waiting.

## 13. Optional no-alert demonstration

Only if a judge asks what zero alerts means:

1. Reset the runtime.
2. Validate and run `http.cap` in FAST mode.
3. Show that packets, bytes, flows, features, and performance values still update.
4. Point to the explicit no-alert message.

Say:

> No evidence-backed alert was emitted for this run. That does not prove the capture is safe; it means no configured detector crossed its threshold with sufficient observable evidence.

## 14. Optional API demonstration

Open `http://127.0.0.1:8000/docs` only if requested.

Useful read-only endpoints include:

- `GET /api/v1/readiness`
- `GET /api/v1/status`
- `GET /api/v1/telemetry`
- `GET /api/v1/detectors`
- `GET /api/v1/alerts`
- `GET /api/v1/flows`

Explain that the React frontend consumes these real endpoints and the telemetry WebSocket. The alert and performance values are backend records, not hard-coded dashboard cards.

## 15. Recommended five-minute sequence

| Time | Action | Message |
|---|---|---|
| 0:00–0:30 | Landing page and login | Passive, local, evidence-aware network monitoring |
| 0:30–1:00 | Header and Detectors | Return path none; three trained model packages loaded |
| 1:00–1:30 | Select and validate `dns.cap` | Input confinement and format validation |
| 1:30–2:30 | PACED replay | Real packets, flows, features, inference, and pipeline telemetry |
| 2:30–3:30 | Select DNS alert | Confidence, threshold, evidence gate, limitations, versioning |
| 3:30–4:15 | Traffic | Behaviour buildup and flow context |
| 4:15–4:45 | Performance | Measured laptop throughput, latency, CPU, and memory |
| 4:45–5:00 | Closing statement | Same pipeline can accept a future authorized live passive adapter |

Closing statement:

> Custodian turns passive network observations into reproducible, evidence-backed alerts on one laptop. The MVP connects capture ingestion, flow reconstruction, shared features, trained detectors, evidence gating, analyst views, and measured performance. Our next step is to feed the same bounded pipeline from an explicitly authorized passive live interface and continue improving model generalization.

## 16. Questions judges may ask

### Is data being uploaded?

No. Runtime captures, inference, alerts, metrics, and SQLite records remain local. The supported servers bind to `127.0.0.1`.

### Does replay send captured packets onto the network?

No. “Replay” means replaying observations through Custodian's software pipeline. There is no packet-transmission path.

### Are these trained models or rules?

They are trained model packages loaded by the backend. Evidence and severity policies operate after model inference, but missing models are not replaced with hard-coded threat rules.

### Does TLS detection decrypt traffic?

No. It uses only observable session and handshake metadata supported by the capture.

### Is it production ready?

No. It is a local MVP. Production deployment requires further external validation, live-adapter review, production authentication/authorization, operational hardening, and monitoring.

### Did every model reach the target recall?

Do not invent a result. Say:

> The models are trained and integrated for the MVP. Validation quality differs by detector, and DNS tunnelling remains the main generalization-improvement area. Model versions and thresholds are replaceable, so later candidates can be upgraded without redesigning the runtime.

### Why can accuracy be high while recall is lower?

DNS benchmark data is highly imbalanced, with far more benign samples than tunnels. Accuracy is not sufficient on its own; precision, recall, false-positive rate, confusion matrices, and cross-dataset generalization are also tracked.

### How would live monitoring be added?

An authorized capture adapter would open a specifically selected interface in passive/promiscuous mode and emit the same `PacketObservation` records used by file replay. It would have no injection API, mitigation path, or payload execution, and would require explicit interface selection and privilege review.

## 17. Recovery guide

### Website says OFFLINE

- Confirm terminal 1 still shows Uvicorn on `127.0.0.1:8000`.
- Open `http://127.0.0.1:8000/health`.
- Confirm terminal 2 still shows Vite on `127.0.0.1:5173`.
- Refresh once after both servers respond.

### Readiness says DEGRADED

- Confirm the backend was started with `$env:CUSTODIAN_MODELS_CONFIG = 'models.demo.yaml'` in the same terminal.
- Open **Detectors** and identify the model family that failed to load.
- Restart using the prepared environment and configuration; do not conceal a genuine failure.

### Start replay is disabled

- Select a capture.
- Click **Validate** first.
- Wait until validation completes.
- Confirm no earlier replay is still running.

### Capture does not appear

- Confirm it is directly inside `data/demo/`.
- Confirm its extension is `.cap`, `.pcap`, or `.pcapng`.
- Refresh the page.
- Changing a filename extension does not convert the underlying format.

### No alert appears

- Confirm the intended capture was selected.
- Confirm the applicable detector reports `READY`.
- Let PACED replay finish or retry the prepared capture in FAST mode after resetting.
- If the run genuinely emits zero alerts, explain the result; never fabricate an alert.

### Port 8000 is already in use

An earlier backend is probably running. Reuse it if `/health` responds, or stop that known terminal with `Ctrl+C` before starting another backend. Do not use an arbitrary alternate API port without updating the frontend proxy.

## 18. End the demonstration safely

1. Stop any active replay from the dashboard.
2. Press `Ctrl+C` in the frontend terminal.
3. Press `Ctrl+C` in the backend terminal.
4. Confirm the local page no longer responds if the demonstration environment must be closed.

Do not delete model artifacts, captures, or runtime reports during ordinary shutdown.

## 19. Final operator checklist

- [ ] Backend started with `models.demo.yaml`
- [ ] Frontend started on `127.0.0.1:5173`
- [ ] Overall readiness is `READY`
- [ ] Behaviour detector is `READY`
- [ ] DNS detector is `READY`
- [ ] TLS/QUIC detector is `READY`
- [ ] `dns.cap` validates and produces the expected DNS alert
- [ ] `ddos.pcap` validates for the optional Behaviour demo
- [ ] Presentation mode is readable on the projector
- [ ] Browser zoom is appropriate
- [ ] Notifications are disabled
- [ ] The operator has rehearsed the five-minute flow
- [ ] No claim depends on fabricated metrics or unavailable functionality
