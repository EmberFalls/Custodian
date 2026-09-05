# Custodian threat model

## Protected assets

The primary assets are the user's Windows host, personal files, credentials, local network, authorized captures, dataset provenance, trained model integrity, and the honesty of displayed findings.

## Trust boundaries

- Capture, CSV, archive, model, and manifest files are untrusted inputs until verified.
- Browser input is untrusted and may identify only files inside the allow-listed capture directory.
- Serialized Python artifacts are executable-equivalent and must not be deserialized without explicit trust approval.
- The dashboard and API share one local trust boundary and bind to loopback by default.
- Dataset preparation and model training occur in a separate disposable VM trust boundary.

## Required controls

- Never execute dataset contents or extracted payloads.
- Validate capture magic, size, resolved path, supported link type, and parser behavior before replay.
- Do not retain raw payloads; evidence contains derived metadata and safe references.
- Run without administrator privileges and with bounded memory, queues, flow tables, and histories.
- Keep CORS and listening addresses local. No runtime feature may transmit capture traffic or initiate network connections.
- Verify model manifests and every artifact checksum before loading. Loading is also blocked unless configuration explicitly marks the reviewed package trusted.
- Escape exported spreadsheet cells, sanitize names, and avoid exposing arbitrary filesystem paths.
- Record missing or unsupported evidence and abstain instead of fabricating defaults.

## VM and dataset phase gate

Before any training, the user must confirm host and Defender updates, create or restore a clean VM snapshot, disable shared clipboard/drag-and-drop and broad shared folders, install pinned libraries while temporary NAT is enabled, verify and scan datasets, disconnect the VM network, mount inputs read-only where practical, train as a non-administrator, and export only verified model, metric, and manifest files. PCAP processing stays inside that isolated environment. No workflow can honestly promise absolute safety; this defense-in-depth process is mandatory.

## Explicitly excluded behavior

Active scanning, probing, exploitation, attack generation, traffic injection, packet transmission, autonomous mitigation, payload execution, TLS/QUIC decryption, and hidden mock detections are outside the product boundary.
