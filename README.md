# Custodian

Custodian is a local-first, passive network-analysis system. It incrementally reads authorized packet captures, reconstructs bidirectional flows, extracts observable metadata, and presents evidence-aware results in a local dashboard. It does not scan, inject, block, exploit, replay traffic onto a network, or decrypt TLS/QUIC payloads.

The governing implementation contract is [docs/CUSTODIAN_FULL_IMPLEMENTATION_BLUEPRINT.md](docs/CUSTODIAN_FULL_IMPLEMENTATION_BLUEPRINT.md). Current gaps and the approved phase order are recorded in [docs/PHASE_0_GAP_ANALYSIS.md](docs/PHASE_0_GAP_ANALYSIS.md).
The current application/deferred-scope ledger is [docs/IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md).

## Current safety state

- API and dashboard are localhost-only.
- Offline capture replay means reading a file into the local analysis pipeline; it never transmits captured packets.
- Model artifacts are untrusted by default and are not deserialized during startup.
- DNS and encrypted-session models remain unavailable until approved data, isolated training, calibration, and artifact validation exist.
- Model training and passive live-interface testing are intentionally deferred until the user completes and approves the documented isolation checklist.

## Run the application

Use two PowerShell terminals from this repository.

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

Open <http://127.0.0.1:5173/>. Put only an authorized `.cap`, `.pcap`, or `.pcapng` file in `data/demo/`. A filename extension is only a hint; Custodian validates the file format before processing. CSV datasets belong to the isolated preparation/training workflow and cannot be started from replay controls.

Stop each server with `Ctrl+C` in the terminal that started it. PyCharm needs no special web setting: select `E:\Python\python.exe` as the interpreter and use the repository root as the backend working directory.

## Install and verify application dependencies

Dependency installation requires temporary internet access. Do it only in an environment you approve. Dataset handling and training remain separate and offline.

```powershell
Set-Location 'C:\Users\Aaryan\Documents\ChatGPT\Custodian'
& 'E:\Python\python.exe' -m pip install -e '.[dev]'
Set-Location frontend
& 'E:\Node\npm.cmd' ci
```

Verification does not train a model:

```powershell
Set-Location 'C:\Users\Aaryan\Documents\ChatGPT\Custodian'
& 'E:\Python\python.exe' -m pytest -q tests\unit tests\integration\test_api.py tests\integration\test_pcap_to_flow.py
& 'E:\Python\python.exe' -m ruff check src tests training
Set-Location frontend
& 'E:\Node\npm.cmd' run build
```

Do not enable `trusted: true` in `configs/models.yaml` merely to make an alert appear. Approval requires verified provenance, checksums, compatible feature metadata, and the isolated-VM training/review process described in [docs/data-governance.md](docs/data-governance.md).

## Repository hygiene

Raw captures, dataset files, processed tables, model binaries, local databases, reports, caches, secrets, virtual environments, and frontend build output are ignored by default. Commit manifests and documentation, not private or generated data.
