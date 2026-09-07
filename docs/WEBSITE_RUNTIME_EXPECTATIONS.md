# Custodian website: expected runtime experience

## Purpose

This document defines what a user should see, what each value means, and what must never be implied when the Custodian website is running. It is both a product acceptance guide and a truthfulness contract for frontend work.

Custodian is a local-first, passive network-analysis system. In the current application, "replay" means reading an authorized capture file into the local analysis pipeline. It does not transmit captured packets, scan a network, block traffic, inject traffic, exploit hosts, or decrypt TLS/QUIC payloads.

## Starting the application

The backend and frontend run in separate terminals.

Backend:

```powershell
Set-Location 'C:\Users\Aaryan\Documents\ChatGPT\Custodian'
& 'E:\Python\python.exe' -m uvicorn custodian.api.app:app --app-dir src --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
Set-Location 'C:\Users\Aaryan\Documents\ChatGPT\Custodian\frontend'
& 'E:\Node\npm.cmd' run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

The user opens <http://127.0.0.1:5173/>. Both processes are localhost-only. The backend's interactive OpenAPI pages are available at <http://127.0.0.1:8000/docs> and <http://127.0.0.1:8000/redoc>.

## Global status bar

The global status bar must remain visible and should answer six immediate questions.

| Field | Expected value | Meaning |
| --- | --- | --- |
| Monitor | `ACTIVE` or `OFFLINE` | `ACTIVE` means the browser is connected and the passive runtime is available. It does not mean a capture is currently running. |
| Return path | `NONE` | Custodian has no traffic-transmission path back into the observed network. |
| Source | `PCAP REPLAY` | The active input is an offline capture file. |
| Mode | `PACED`, `FAST`, or `BENCHMARK` | How quickly the local file is processed. It is not a network mode. |
| Progress | `0%` through `100%`, or `—` | Fraction of capture-file bytes processed. It is not a percentage of threats found. |
| Readiness | `READY` or `DEGRADED` | `DEGRADED` normally means one or more approved detector models are unavailable; parsing and replay may still work. |

The connection badge should show the replay state when connected: `IDLE`, `VALIDATING`, `READY`, `RUNNING`, `PAUSED`, `STOPPING`, `STOPPED`, `REBUILDING`, `COMPLETED`, `FAILED`, or `ERROR`. When browser telemetry is disconnected, it should show `TELEMETRY LOST` and a reconnecting banner.

## Navigation

The website has five primary pages:

1. **Live monitor** — overall replay, telemetry, pipeline, alerts, and controls.
2. **Alerts** — filterable alert records and evidence inspection.
3. **Traffic** — traffic rates, bounded host behaviour, and flow summaries.
4. **Detectors** — model availability, trust, schema, classes, and evidence requirements.
5. **Performance** — measured processing throughput, resource use, and stage latency.

Pressing `P` outside an input toggles presentation mode. This changes presentation only; it must not change analysis or results.

## Information architecture and visual hierarchy

The frontend should be understandable in three passes:

1. **Five-second pass:** Is the local runtime connected, is processing active, is the system passive, and did an alert fire?
2. **Thirty-second pass:** What capture is being processed, how far has it progressed, which detectors are available, and what evidence was observed?
3. **Investigation pass:** Why was a specific alert produced, what information was missing, which model/schema produced it, and what raw structured record supports the display?

The visual hierarchy should follow this order on every page:

1. Global safety/connectivity state.
2. Current replay state and progress.
3. Page-specific primary information.
4. Evidence and diagnostic detail.
5. Raw JSON or low-level implementation detail.

Raw JSON, full identifiers, feature-schema metadata, and detailed stage timings should remain available but should not visually compete with the primary operational state.

## Overall page shell

### Desktop layout

The recommended desktop layout is:

```text
┌─────────────────────────────────────────────────────────────────────┐
│ CUSTODIAN   MONITOR / RETURN PATH / SOURCE / MODE / PROGRESS       │
│             READINESS                         CONNECTION / PRESENT  │
├─────────────────────────────────────────────────────────────────────┤
│ 01 LIVE MONITOR  02 ALERTS  03 TRAFFIC  04 DETECTORS  05 PERFORMANCE│
├─────────────────────────────────────────────────────────────────────┤
│ Optional connection, readiness, validation, or error banner         │
├─────────────────────────────────────────────────────────────────────┤
│ Page content                                                        │
└─────────────────────────────────────────────────────────────────────┘
```

The header should remain stable while navigating so the user never loses the passive-safety indicator or runtime state. Page content should use a consistent maximum width, alignment grid, spacing scale, and panel treatment.

### Mobile and narrow layouts

Below approximately 1180 px, two-column monitor and inspector layouts should collapse to one column. Below approximately 720 px:

- status fields should form a compact two-column grid;
- metric cards should stack;
- tables should scroll horizontally instead of squeezing or dropping columns;
- controls should wrap while preserving logical order;
- drawers should use nearly the full viewport width; and
- important text labels must not be replaced by colour-only icons.

The mobile layout must preserve all information. Hiding performance sparklines or secondary descriptions is acceptable only when the same values remain reachable.

## Visual language

### Colour semantics

Use colour consistently and always pair it with a text label or symbol.

| Meaning | Recommended treatment | Examples |
| --- | --- | --- |
| Healthy/active/accepted | Green | Runtime connected, replay running, trusted model ready, `ACCEPT` |
| Waiting/neutral/inactive | Muted grey | Idle replay, unavailable optional metric, no selected alert |
| Caution/partial | Amber | Paused, degraded readiness, weak evidence, high severity |
| Suspicious but unclassified | Distinct violet or purple | `UNKNOWN_SUSPICIOUS` |
| Missing evidence | Amber/orange distinct from severity | `INSUFFICIENT_EVIDENCE` |
| Failure/critical | Red | Telemetry lost, validation failure, critical severity, runtime error |

Do not use green to mean “traffic is safe.” In Custodian, green means the displayed system/component state is operating or a policy decision was accepted.

### Typography

- Use a strong, compact heading style for page and panel titles.
- Use monospace text for IP addresses, ports, hashes, IDs, filenames, and raw JSON.
- Use tabular numerals where possible so live metrics do not visually jump as digits change.
- Keep operational labels short and uppercase when used as eyebrow labels.
- Use sentence case for explanations, empty states, errors, and guidance.

### Panels and density

- Primary panels should have stronger borders/contrast than supporting panels.
- Dense tables are appropriate, but row height must still support keyboard focus and accurate clicking.
- Avoid decorative charts without units, scale context, or a current value.
- Use progressive disclosure: overview first, inspector/drawer second, raw JSON last.

### Motion

- Update counters without distracting bounce or count-up animation.
- Use brief transitions for drawer opening, selected rows, and state changes.
- Do not continuously pulse all active elements.
- Respect `prefers-reduced-motion`.
- An alert may briefly highlight when first received, but it must remain readable after the animation finishes.

## Data formatting rules

All pages should use the same formatting rules.

| Data | Display rule |
| --- | --- |
| Bytes | Human-readable IEC/SI value such as `24.6 KB`, with exact bytes available in tooltip/detail where useful. |
| Rates | Include units: `Mbps`, `packets/s`, or `flows/s`. Use consistent decimal precision. |
| Percentages | Convert API probabilities from `0–1` into `0–100%`. Confidence should normally show one decimal place. |
| Latency | Display milliseconds with sensible precision; do not show excessive floating-point digits. |
| Time | Use the user's local time for primary display and preserve the ISO timestamp in raw detail/title. |
| Duration | Use `ms`, `s`, `min`, or `h` according to magnitude. |
| Endpoints | Show `IP:port`; render IPv6 unambiguously, preferably `[IPv6]:port`. |
| Missing values | Show `Unavailable` or `—`; never coerce missing values to zero. |
| Counts | Use grouped digits where large; do not abbreviate audit-critical totals without exposing the exact number. |
| Filenames | Show the safe display name, not an unrestricted host filesystem path. |
| Hashes/IDs | Truncate visually only if the full value is available through copy/detail. |

Every chart must identify its metric and unit. Tooltips should show exact value and timestamp. A chart with no samples should show a meaningful empty state rather than a flat fabricated zero line.

## Common component requirements

### Status badge

A status badge should contain:

- a text label;
- an optional status dot/icon;
- a semantic colour; and
- an accessible name that does not depend on colour.

Badges must use stable meanings across pages. For example, `DEGRADED` should not appear green in one place and red in another.

### Metric card

Each metric card should contain:

1. concise metric name;
2. large current value;
3. visible unit;
4. one-line definition or time basis; and
5. optional small recent-history sparkline.

If a metric is unavailable, show `Unavailable` and explain why. A disabled detector's inference rate should not be shown as a meaningful `0` without context.

### Tables

All operational tables should support:

- a clear header row;
- keyboard-focusable/selectable rows where applicable;
- hover and selected states;
- horizontal scrolling on narrow screens;
- a record count;
- explicit empty state;
- stable sorting; and
- textual status/severity labels in addition to colour.

Do not add pagination controls unless the backend supports the intended pagination behaviour. If only a bounded recent set is available, label it as retained/recent rather than “all records.”

### Banners and messages

Use banners only for states requiring attention:

- telemetry disconnected;
- runtime degraded;
- capture validation failure;
- replay failure;
- persistence unavailable for alert lifecycle/export; or
- incompatible/untrusted model artifact.

A banner should say what happened, what still works, and what the user can safely do next. Do not show a generic red “Something went wrong” when a stable API message is available.

### Drawers and inspectors

- Opening a drawer should move keyboard focus into it.
- Escape and an explicit close button should close it.
- Focus should return to the originating row/marker/button.
- Important headings and badges should remain visible near the top.
- Long content should scroll inside the drawer without moving the entire application unexpectedly.
- Raw JSON should be collapsed by default.

## Live monitor

### Recommended layout

The Live Monitor should show, in order:

1. four live ingest metric cards;
2. traffic timeline and inspection pipeline side-by-side on wide screens;
3. recent alerts directly below the timeline;
4. replay control center; and
5. optional detector, evidence, or alert detail drawers.

This order answers “is it running?”, then “what is it processing?”, then “did anything happen?”, and finally “what can I control?” The replay controls should remain easy to find but should not visually overpower live alerts.

### Live ingest metrics

The top metric strip should show:

| Metric | Definition | Important interpretation |
| --- | --- | --- |
| Data inspected | Total capture-frame bytes read by the current replay. | This is processed capture data, not data transmitted. |
| Packets | Total observed capture frames/packets accounted for by the runtime. | A nonzero count proves parsing activity, not that traffic is benign. |
| Packet processing rate | Frames processed per wall-clock second during the current telemetry interval. | In FAST mode this can be much faster than the original capture rate. |
| Flows analysed | Number of reconstructed bidirectional flows retained/observed. | This is not the same as `flow_updates`; one flow can be updated many times. |
| Active flows | Flow records that have not yet been closed or finalized. | This commonly falls to zero when replay completes. |
| Processing throughput | Megabits processed per wall-clock second. | This measures laptop pipeline speed, not original network bandwidth. |

Every replay begins a fresh runtime session, represented by a new `run_id`. The frontend should not mix alerts or charts from different run IDs.

### Traffic timeline

The timeline can display:

- processing Mbps;
- packets processed per second; or
- new flows processed per second.

It should show bounded recent history, the latest value, the peak visible value, and alert markers whose timestamps fall inside the visible interval. Selecting a marker should open the associated alert. Empty history must be presented as waiting/empty state rather than fabricated activity.

Recommended presentation:

- Put the current value above or beside the plot.
- Provide a three-option segmented control: `Mbps`, `Packets/s`, and `Flows/s`.
- Show the visible sample count and peak beneath the chart.
- Use point/line tooltips with timestamp, exact value, and unit.
- Render alert markers above the line and make them keyboard accessible.
- Avoid implying the horizontal axis is capture time when it is actually telemetry observation time.
- If samples are downsampled or bounded, say so.

### Inspection pipeline

The pipeline represents these stages:

1. `INGEST` — read and validate capture records.
2. `FLOWS` — reconstruct bidirectional flow state.
3. `FEATURES` — create versioned feature snapshots.
4. `DETECT` — run available, trusted model artifacts.
5. `EVIDENCE` — evaluate capability and evidence sufficiency.
6. `ALERT` — emit standardized alert records.

Each stage should show its state and a real counter. If no trusted model is available, `DETECT` must show `UNAVAILABLE`; downstream zeroes must not be presented as proof of safety. Clicking detector/evidence nodes may open details, but it must not enable an untrusted model.

Recommended presentation for every stage:

- stage name and short verb;
- `ACTIVE`, `IDLE`, `WAITING`, `OBSERVED`, `EVALUATED`, or `UNAVAILABLE` badge;
- relevant cumulative counter;
- short explanation on hover/focus; and
- visually connected directional sequence without implying packets leave the local process.

When a stage is unavailable, preserve it in the pipeline instead of removing it. This makes the limitation visible and prevents users from assuming detection occurred.

### Recent alerts

The compact table shows up to the latest six alert records with:

- time;
- threat class;
- severity;
- source and destination;
- calibrated confidence; and
- evidence quality.

When no alerts exist, the correct message is that no evidence-backed alert was emitted. The UI must not say that the capture is safe or clean.

New alerts should appear consistently—prefer newest first in the full alert page, while the compact monitor can show a chronological latest-six slice. A row selection should open the same standardized inspector used by the Alerts page.

## Replay control center

The capture selector lists supported candidates from `data/demo/`. Supported filename extensions are `.cap`, `.pcap`, and `.pcapng`, but the backend validates file magic, size, resolved path, and supported link-layer type. Renaming an arbitrary file does not convert its format.

### Recommended control layout

- Show current source filename, mode, and state above the controls.
- Put capture selection and validation before Start.
- Disable Start until a capture is selected and ready.
- Place Pause/Resume and Stop together as active-run controls.
- Show seek controls only after a capture has a known progress value.
- Show Reset as a quiet/destructive-adjacent action and disable it while running.
- Put the latest action result or error immediately beneath the buttons using `role="status"` or `role="alert"` as appropriate.
- Do not use browser file upload wording when the API actually selects a server-side file from `data/demo/`.

### Controls

| Control | Expected behaviour |
| --- | --- |
| Validate | Performs passive validation and records identity/checksum information. No packets are transmitted. |
| Start replay | Starts a fresh analysis run for a validated or valid capture. |
| Pause | Pauses local file processing. |
| Resume | Continues a paused replay. |
| Stop | Requests safe termination of the active replay. |
| Seek backward/forward | Rebuilds deterministic state from the start of the capture up to the selected file-progress point, then continues. It is not random access into saved mutable detector state. |
| Reset telemetry | Clears current in-memory runtime state when no replay is running. It does not delete the source capture. |

### Replay modes

- **PACED:** follows capture timestamps at `1×`, `2×`, `5×`, or `10×`.
- **FAST:** ignores original inter-packet delays and processes as quickly as the local pipeline permits.
- **BENCHMARK:** measures local processing performance with reduced telemetry overhead.

The progress bar is based on capture-file bytes. During a seek, the UI should distinguish `REBUILDING` progress from ordinary processing progress.

Progress should show a percentage and textual state. For long paced captures, optionally show elapsed time, but do not invent an ETA unless it is derived and labelled as an estimate.

## Alerts page

### Recommended layout and emphasis

Use a filter bar followed by a table and inspector. On wide screens the inspector may remain beside the table; on narrow screens it should become a drawer or stacked detail panel.

Recommended visual priority within a row:

1. threat class and decision;
2. severity;
3. source → destination;
4. calibrated confidence and evidence quality;
5. time and lifecycle status.

Severity and decision are separate concepts and must remain separate columns. A high-severity candidate can still be insufficiently evidenced.

The complete alert table should support:

- decision filtering: `ACCEPT`, `UNKNOWN_SUSPICIOUS`, and `INSUFFICIENT_EVIDENCE`;
- lifecycle filtering: `OPEN`, `ACKNOWLEDGED`, and `CLOSED`;
- newest, oldest, and highest-confidence sorting; and
- keyboard selection with Enter.

Each row should show time, threat class, severity, source, destination, calibrated confidence, evidence quality, decision, and lifecycle status. Colour is supplementary; the text label must always remain visible.

### Decision meanings

- `ACCEPT` means the candidate passed configured confidence, capability, and evidence checks. It does not prove malicious intent with certainty.
- `UNKNOWN_SUSPICIOUS` means observed behaviour is suspicious but does not support a narrower known threat classification.
- `INSUFFICIENT_EVIDENCE` means a candidate exists but required observable evidence is missing or inadequate.

### Alert inspector

Selecting an alert should show:

- first and last seen times;
- occurrence count after deduplication;
- source and destination;
- detector ID and model version;
- raw score, calibrated confidence, and class threshold;
- threat confidence and observation confidence;
- evidence quality and Evidence Gate decision;
- missing and available evidence;
- limitations;
- the evidence fields that caused the flag;
- the observation capability profile;
- feature-schema version;
- acknowledgement/closure controls when persistence is available; and
- expandable raw JSON for audit and troubleshooting.

The interface must distinguish model confidence from observation quality. High model confidence based on weak or missing observation evidence must not be visually represented as an accepted high-certainty alert.

Recommended inspector order:

1. threat name, severity, decision, and lifecycle badges;
2. plain-language summary of what was observed;
3. source, destination, first/last seen, and occurrences;
4. confidence visualization with the acceptance threshold marked;
5. Evidence Gate result and missing evidence;
6. “Why this was flagged” evidence list;
7. observation capabilities;
8. model/schema/policy metadata;
9. timing information;
10. lifecycle buttons; and
11. collapsed raw JSON.

The confidence bar must label both confidence and threshold. It must not resemble a certainty-of-maliciousness meter without the accompanying decision/evidence context.

Evidence keys should be translated into readable labels while preserving the raw key in JSON. Numeric evidence must include units or a clear definition where one exists.

## Traffic page

The Traffic page should contain:

- the selectable traffic timeline;
- total processed bytes;
- current packet-processing rate;
- current new-flow rate;
- per-host bounded evidence timelines; and
- retained recent/active flow summaries.

For a selected host, the bounded evidence view should show packet count, destination-port fan-out, and outbound bytes over rolling windows. Alert-fire markers should appear only for real alert records associated with that host.

Flow rows should show IP version, protocol, both canonical endpoints, directional packet counts, combined bytes, close reason, and last-seen time. Payload contents must never be displayed.

### Host behaviour presentation

The host selector should list only hosts present in retained timeline data. For the selected host, use three aligned small charts:

- packets in window;
- unique destination ports (fan-out); and
- outbound bytes.

All three should cover the same ordered observation windows. Show window duration, snapshot count, and alert-marker count beneath them. Mark alert firing points and provide a path to the full alert inspector.

Avoid labelling a rise as an attack in the chart itself. The chart shows observed behaviour; an alert marker represents the separate model/evidence decision.

### Flow table presentation

- Keep endpoint values monospace.
- Show directional arrows explicitly.
- Use friendly close-reason text while retaining the raw enum in detail.
- Distinguish active flows from finalized flows.
- State that the table is bounded/retained.
- Provide a meaningful empty state before replay or when no supported IP flows exist.

## Detectors page

Custodian exposes three detector families:

| Detector | Intended coverage | Initial availability expectation |
| --- | --- | --- |
| Behaviour | DDoS, recon, C2-like recurrence, and exfiltration-like flow behaviour | Available only when an approved compatible artifact is trusted and loaded. |
| DNS | DGA-like and DNS-tunnelling metadata | Unavailable until approved DNS training, calibration, review, and configuration are complete. |
| TLS/QUIC | Suspicious encrypted-session metadata | Unavailable until an approved metadata-only model exists. |

Each detector card should show readiness, artifact trust, model version, feature-schema version, classes, required evidence, available evidence, and an unavailability reason. `No approved artifact` is a valid and safer state.

The coverage matrix describes intended detection coverage. It must not imply that an unavailable detector is currently providing protection.

### Recommended detector card

Each detector card should present:

1. family name;
2. `READY`, `DEGRADED`, or `UNAVAILABLE`;
3. model version or `No approved artifact`;
4. artifact trust (`APPROVED` or `BLOCKED`);
5. feature-schema version;
6. class list;
7. required evidence;
8. currently available evidence;
9. distribution-support status; and
10. exact unavailability/load-error reason.

Show `N / 3 loaded` at page level. Planned coverage should be visibly separated from active coverage, for example with columns `Threat`, `Responsible detector`, `Required evidence`, and `Current status`.

Do not provide a frontend switch that bypasses artifact trust. Enabling or approving a model is a reviewed configuration/deployment operation.

## Performance page

The performance page should show measured values from the current or most recent replay:

- processing throughput in Mbps;
- packet-processing rate;
- new-flow rate;
- p50 and p95 total-pipeline latency;
- CPU percentage for the local process;
- memory bytes used by the local process;
- elapsed and active processing time;
- original-capture average Mbps when it can be derived;
- feature-vector count;
- inference vector and batch counts;
- unsupported frame count;
- malformed and truncated frame count; and
- per-stage p50/p95 timing for parse, flow, state, features, inference, inference batch, evidence, alert, and total pipeline.

These are runtime measurements, not benchmark guarantees. A measurement should identify the machine/configuration/capture when exported or quoted externally.

### Recommended performance layout

Use four primary cards for throughput, packet rate, flow rate, and total-pipeline latency. Follow them with:

- a throughput history chart;
- a local process resources panel;
- a pipeline-stage timing table; and
- capture/parser quality counters.

The timing table should show stage, p50, and p95 in milliseconds. Sort stages in pipeline order rather than by value. Missing stage timing should show `Unavailable`, not `0 ms`.

Performance displays should state whether they represent the current interval, current run, or last completed replay average. CPU percentage and memory are local-process measurements and should be labelled accordingly.

## Diagnostics and operational transparency

Diagnostics may be part of the Detectors page or an expandable advanced panel. Show:

- model-load errors by family;
- feature-routing decisions;
- missing-evidence reasons;
- supported input-adapter status;
- whether an adapter is passive;
- whether an adapter opens a network interface; and
- storage/persistence readiness.

Diagnostic text should be copyable. Do not expose secrets, unrestricted local paths, raw payloads, or stack traces to ordinary users. A correlation ID should be shown with API errors where available.

## First-run guidance

When the website first loads with no captures and no replay history, display a compact onboarding state:

1. Confirm the backend is connected.
2. Explain that only authorized `.cap`, `.pcap`, or `.pcapng` files placed in `data/demo/` appear.
3. Tell the user to select and validate a capture.
4. Explain PACED versus FAST in one sentence.
5. Warn that zero alerts does not prove safety, especially if models are unavailable.

This guidance should disappear or collapse after the user has a ready capture or completed run. It must not obscure runtime errors.

## Loading, empty, degraded, and error states

Every data-bearing component needs all four states where applicable:

| State | What to show |
| --- | --- |
| Loading | Stable skeleton or short `Connecting…`/`Loading…` label without fake values. |
| Empty | Explain why no data exists and the safe next action. |
| Degraded | Show available data plus the exact unavailable component/reason. |
| Error | Show action, reason, correlation ID when present, and a safe retry path. |

Specific examples:

- No captures: `No supported captures found in data/demo/.`
- Unvalidated capture: `Select Validate before replay.`
- No flows: `No supported IP flow summaries are available for this run.`
- No alerts: `No evidence-backed alert was emitted; this does not prove the capture is safe.`
- DNS model absent: `DNS detector unavailable — no approved dns.v1 artifact is configured.`
- Persistence absent: `Alert lifecycle changes and exports are unavailable; replay remains usable.`
- Invalid capture: display the validator's reason without offering to rename the extension as a fix.

## Interaction and feedback rules

- A button must enter a busy state after activation to prevent duplicate requests.
- Disabled buttons need an accessible reason through nearby text or a tooltip.
- Successful actions should update both the control message and relevant status badge.
- API errors should remain visible until corrected or dismissed; do not clear them immediately on a polling refresh.
- Changing pages must not restart or stop a replay.
- Selecting an alert in a timeline or table should identify the same record by `alert_id`.
- A new `run_id` should clear stale run-specific alerts and history from the active view.
- Acknowledge and Close should confirm success and refresh the record state.
- Export actions should state local filename, format, anonymization status, and directory.

## Accessibility requirements

- All functionality must work with keyboard only.
- Use semantic headings in a logical order.
- Give navigation an accessible label and active-page indication.
- Use real buttons for actions and real table markup for tabular data.
- Every chart needs an accessible label and a textual numeric summary.
- Do not encode state using colour alone.
- Maintain WCAG AA colour contrast for text and controls.
- Provide visible focus states.
- Associate every form control with a label.
- Announce control results and connection changes through appropriate live regions without excessive repetition.
- Drawers must manage focus and support Escape.
- Respect reduced-motion settings.
- Keep click targets usable on touch screens.

## Privacy and safe display requirements

- Do not display packet payloads.
- Do not provide links that make observed domains/IPs directly clickable.
- Do not automatically resolve, enrich, geolocate, or query reputation services for observed indicators.
- Do not send telemetry to analytics or third-party services.
- Keep capture paths confined to safe display names.
- Warn before exporting non-anonymized alert data.
- Never place access tokens, model secrets, or full machine paths in frontend logs.
- Preserve `RETURN PATH: NONE` and passive-only messaging.

## Recommended demonstration sequence

For a reliable presentation, the website should support this visible story:

1. Show `MONITOR: ACTIVE`, `RETURN PATH: NONE`, and current detector readiness.
2. Select an authorized capture and validate it.
3. Start PACED or FAST replay.
4. Watch bytes, packets, flows, progress, and processing rates increase.
5. Show the inspection pipeline progressing through available stages.
6. Open Traffic and explain host behaviour accumulation without claiming it is automatically malicious.
7. If a real approved model emits an alert, select its timeline marker/table row.
8. Explain confidence, threshold, evidence quality, decision, limitations, and model version.
9. Show Performance and distinguish processing throughput from original network rate.
10. Complete or stop the replay and show retained final measurements.

If no approved model is loaded, the demonstration should explicitly show that parsing and measurement work while detection remains unavailable. A mock may be used only in a separately labelled presentation environment and must never be presented as a trained-model result.

## Frontend definition of done

A frontend change is complete only when:

- the visible data originates from real API responses or is clearly labelled test fixture data;
- every new metric has a name, unit, time basis, empty state, and API source;
- every new status has defined text and colour semantics;
- desktop and narrow layouts are checked;
- keyboard navigation and focus behaviour are checked;
- connected, disconnected, degraded, no-capture, no-model, no-alert, running, paused, rebuilding, completed, and failed states are exercised;
- no safety boundary or unavailable feature is obscured;
- frontend types match API contracts; and
- the production build passes.

## Expected states and honest empty states

### Backend unavailable

- Monitor shows `OFFLINE` or `TELEMETRY LOST`.
- A reconnect message is visible.
- Buttons depending on status are disabled or fail with a clear local API error.

### Backend ready, no replay

- Monitor can be `ACTIVE` while replay state is `IDLE`.
- Packet, flow, byte, inference, and alert counters are zero.
- Capture candidates appear only when supported files exist in the configured capture directory.

### Replay working, models unavailable

- Packet, byte, flow, feature, and performance metrics can increase.
- Detector status remains unavailable/degraded.
- Inference and alert counts may remain zero.
- The UI states that zero alerts does not prove the capture safe.

### Replay working, approved model loaded

- Relevant feature and inference counters increase when eligible observations exist.
- Candidates reach the Evidence Gate.
- Alert records appear only when detector, threshold, evidence, and policy requirements permit them.

### Replay completed

- Progress reaches 100% and state becomes `COMPLETED`.
- Active flow count may become zero while retained flow summaries remain visible.
- Final totals and average processing rates remain visible until reset or the next run.

## Non-negotiable frontend rules

- Never fabricate telemetry, alerts, confidence, models, or performance values.
- Temporary mocks must be visibly marked and must not be enabled in the normal runtime path.
- Never equate zero alerts with benign or safe traffic.
- Never present capture-file replay as transmission onto a network.
- Never hide missing evidence or detector unavailability.
- Never activate an artifact merely to make the demonstration produce an alert.
- Preserve localhost-only operation and the `RETURN PATH: NONE` safety indicator.

## Website acceptance checklist

- [ ] Both servers start and the frontend connects on localhost.
- [ ] The status bar distinguishes monitor connectivity, replay state, and model readiness.
- [ ] A valid authorized capture can be validated and replayed.
- [ ] Invalid files fail with a visible, useful error.
- [ ] Packet, byte, flow, and performance values come from the API.
- [ ] FAST and PACED behaviour are clearly distinguished.
- [ ] Pause, resume, stop, seek, and reset enforce valid states.
- [ ] Empty alerts do not imply safety.
- [ ] Detector cards expose trust and compatibility failures.
- [ ] Alert details expose evidence, limitations, threshold, and model metadata.
- [ ] Traffic views never display decrypted or reconstructed payloads.
- [ ] Responsive and keyboard-accessible behaviour is retained.
