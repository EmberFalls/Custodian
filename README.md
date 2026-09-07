# Custodian

Custodian is a local-first, passive network-analysis system. It incrementally reads authorized packet captures, reconstructs bidirectional flows, extracts observable metadata, and presents evidence-aware results in a local dashboard. It does not scan, inject, block, exploit, replay traffic onto a network, or decrypt TLS/QUIC payloads.

The governing implementation contract is [docs/CUSTODIAN_FULL_IMPLEMENTATION_BLUEPRINT.md](docs/CUSTODIAN_FULL_IMPLEMENTATION_BLUEPRINT.md). Current gaps and the approved phase order are recorded in [docs/PHASE_0_GAP_ANALYSIS.md](docs/PHASE_0_GAP_ANALYSIS.md).
The current application/deferred-scope ledger is [docs/IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md).
The complete HTTP and WebSocket reference is [docs/api.md](docs/api.md).
The reusable hosted-Colab environment workflow is documented in [docs/colab-training.md](docs/colab-training.md); it deliberately stops before dataset handling or model fitting.

## Current safety state

- API and dashboard are localhost-only.
- Offline capture replay means reading a file into the local analysis pipeline; it never transmits captured packets.
- Model artifacts are untrusted by default and are not deserialized during startup.
- The reviewed Behaviour, DNS-tunnelling, DNS DGA, and TLS/QUIC model packages are distributed with the repository for local inference.
- The DNS-tunnelling candidate can be loaded through the explicit local showcase override.
- DNS DGA has a safety-gated HGB preparation/training/integration path and a locally exported DRIFT26DSN MVP candidate; it remains disabled by default and is enabled only by the operator-approved local demo configuration.
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

### Full four-model demo from a fresh clone

The repository contains the reviewed `behaviour-colab-v1`,
`dns-tunnelling-colab-v1`, `dns-dga-drift26dsn-hgb-v1`, and
`tls-quic-colab-v1` packages under `model_artifacts/`. They are hash-verified
before loading and use only relative repository paths through
`configs/models.demo.yaml`.

```powershell
Set-Location 'C:\Users\Aaryan\Documents\ChatGPT\Custodian'
$env:CUSTODIAN_MODELS_CONFIG = 'models.demo.yaml'
& '.\.venv\Scripts\python.exe' -m custodian.cli demo-check
& '.\.venv\Scripts\python.exe' -m uvicorn custodian.api.app:app --host 127.0.0.1 --port 8000
```

The readiness report must show all four configured detectors as `READY`.
CICIDS2017 is not needed to run these trained models; it is needed only for
approved retraining.

### Local showcase with the additional model candidates

`configs/models.demo.local.yaml` remains ignored for machine-specific local
overrides. It is not needed for a standard clone because the tracked
`configs/models.demo.yaml` is the full showcase configuration.

```powershell
Set-Location 'C:\Users\Aaryan\Documents\ChatGPT\Custodian'
$env:CUSTODIAN_MODELS_CONFIG = 'models.demo.local.yaml'
$env:LOKY_MAX_CPU_COUNT = '4'
& '.\.venv\Scripts\python.exe' -m uvicorn custodian.api.app:app --host 127.0.0.1 --port 8000
```

Start the frontend in a second PowerShell terminal using the normal command above. The Behaviour, DNS tunnelling, DNS DGA, and TLS/QUIC detector packages should all report `READY`. This override is for the localhost-only MVP demonstration and is not an external-validation or production-readiness claim.

Before starting the showcase, run the lightweight readiness check. It does not open a capture, train a model, or access the network:

```powershell
Set-Location 'C:\Users\Aaryan\Documents\ChatGPT\Custodian'
$env:CUSTODIAN_MODELS_CONFIG = 'models.demo.local.yaml'
& '.\.venv\Scripts\python.exe' -m custodian.cli demo-check
```

The command exits successfully only when the pinned demo dependencies match and all four configured detector packages load as `READY`. Its `artifact_serialization_versions` and `artifact_version_warning_count` fields also report known serialization-version differences instead of hiding them; these are compatibility debt for later artifact re-export, even when the locally verified packages load successfully.

## Install and verify application dependencies

Dependency installation requires temporary internet access. Do it only in an environment you approve. Dataset handling and training remain separate and offline.

```powershell
Set-Location 'C:\Users\Aaryan\Documents\ChatGPT\Custodian'
& 'E:\Python\python.exe' -m pip install -e '.[dev]'
Set-Location frontend
& 'E:\Node\npm.cmd' ci
```

For the model-compatible project environment used by the showcase:

```powershell
Set-Location 'C:\Users\Aaryan\Documents\ChatGPT\Custodian'
& 'E:\Python\python.exe' -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -c constraints-demo.txt -e '.[dev]'
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

The four final reviewed inference packages are intentionally tracked. Raw
captures, CICIDS2017 CSVs, other research datasets, processed tables,
experimental model binaries, local databases, reports, caches, secrets, virtual
environments, and frontend build output are ignored by default. See
`data/README.md` for dataset policy.
