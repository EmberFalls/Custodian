# Real-time passive packet capture

Custodian can optionally read packets from one explicitly selected network interface. The existing PCAP replay path remains the default and requires no capture privileges or packet-capture driver. Live capture does not activate automatically, does not open every interface, and does not transmit traffic.

## Data path

```text
selected interface (non-promiscuous by default)
  -> bounded libpcap/Npcap capture (65,535-byte snapshot ceiling)
  -> existing PacketParser
  -> PacketObservation metadata
  -> existing flow, feature, detector, alert, PostgreSQL, Redis and optional Kafka paths
```

Only one interface is opened, after an operator selects it and requests **Start live capture**. The optional BPF filter is applied by the capture backend before packets reach the parser. An empty filter means all traffic visible to that interface. The filter expression is limited to 512 characters. The parser rejects malformed and unsupported link/network formats.

The adapter passes a validated `PacketObservation` to the same `CustodianEngine.process_observation` path used by PCAP parsing downstream. It does not add an alternate inference or alert implementation. Live mode uses a generated capture ID and increments the runtime run ID. PostgreSQL stores supported durable records, Redis mirrors bounded current dashboard state when configured, and Kafka publishes the existing validated metadata stage events only when Kafka is enabled.

## Payload and privacy boundary

Custodian does not save captured frames, publish frames to Kafka, persist raw packet bytes, decrypt TLS/QUIC application data, or inspect extracted files. The existing parser does inspect selected protocol bytes after the transport header to derive approved DNS metadata (including query names) and TLS/QUIC handshake metadata/fingerprints. Those derived fields support the documented DNS and encrypted-session detection features. The source releases the frame after parsing; only structured observations enter the shared engine.

Therefore the implementation does **not** claim that the process never reads any transport-payload byte. If policy requires zero payload-byte reads, DNS query-name and TLS/QUIC fingerprint extraction must be disabled or supplied by an upstream metadata exporter; this is not the current behavior.

The capture API does not provide an active response path. It cannot scan, inject, block, mitigate, complete handshakes, or send commands to observed endpoints. Capture is passive observation of traffic available to the selected interface; it does not make encrypted application content visible.

## Install the optional capture backend

The Python dependency is optional and not installed by the standard setup:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,capture]"
```

Install the platform packet-capture dependency separately:

- **Windows:** install Npcap and enable its WinPcap-compatible API if required by the Python binding. Run Custodian with an account that has permission to capture on the selected adapter.
- **Linux:** install libpcap and grant the process the minimum capture permission required by the distribution (for example, an approved capture group or narrowly scoped capabilities). Avoid running the full dashboard as root.
- **macOS:** install the libpcap/BPF prerequisites and grant capture-device access according to local policy.

Backend packaging and capture permissions vary by platform and adapter. Custodian reports backend enumeration, permission, link-type, and runtime failures through live-input status, readiness, diagnostics, and the live status endpoint. Interface enumeration alone does not prove that capture permission is available; the explicit start operation verifies that.

## Start and stop

Start the API as usual with the normal local configuration. Kafka, Redis, and live capture remain independently optional; no broker or capture backend is required for ordinary PCAP replay. In the dashboard, select **Real-Time Capture**, refresh the available interfaces, select exactly one interface, optionally enter a BPF filter, and click **Start live capture**. Click **Stop** to end it. The UI does not choose an interface or start capture automatically.

The equivalent local API operations are:

```powershell
# List available interfaces; listing does not open them.
Invoke-RestMethod http://127.0.0.1:8000/api/v1/live/interfaces

# Start only the explicitly selected adapter. Replace the interface ID.
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/live/start `
  -ContentType "application/json" `
  -Body '{"interface_id":"<interface-id>","capture_filter":""}'

# Inspect state, including selected interface, filter, and error.
Invoke-RestMethod http://127.0.0.1:8000/api/v1/live/status
Invoke-RestMethod http://127.0.0.1:8000/api/v1/readiness
Invoke-RestMethod http://127.0.0.1:8000/api/v1/diagnostics

# Request a clean stop.
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/live/stop
```

If the optional dependency is absent, use PCAP replay as before. Live capture reports unavailable and does not silently switch to another interface or source. If a capture session fails after starting, status becomes `ERROR`; readiness and diagnostics report the failure.

## Safer test setup and limits

For adversarial traffic experiments, run Custodian and the generator in an isolated VM/lab network. Prefer a dedicated virtual NIC or mirrored lab interface and use an explicit BPF selector when practical. Do not select a production adapter unless authorized. Promiscuous mode is disabled by the adapter; whether the operating system/NIC exposes traffic not addressed to the host depends on the platform and network configuration. A normal laptop interface generally sees its own traffic, broadcasts/multicasts, and traffic explicitly mirrored to it, not every peer's unicast traffic.

Live capture has not been benchmarked here against a physical NIC or installed platform backend. No throughput figure is claimed. Report throughput only from a reproducible replay or isolated capture/load test with the interface, packet mix, filter, capture drops, host hardware, and duration recorded. A high rate can exceed one laptop's capture, parsing, inference, PostgreSQL, Redis, or Kafka capacity; monitor packet/drop counters and resource telemetry rather than assuming Kafka alone guarantees throughput.

The automated tests use fake capture backends and do not launch the full Custodian service or require administrator/root capture privileges. A real interface integration check requires a separately installed backend and an authorized isolated test interface.
