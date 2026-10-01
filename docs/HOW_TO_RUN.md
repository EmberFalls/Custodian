# How to run Custodian

This guide covers the local Windows demo in PowerShell. It has two paths:

1. Set up and run Custodian for the first time.
2. Run Custodian again after setup is complete.

The normal demo uses authorized PCAP files, PostgreSQL for durable storage, the
in-process event path, and a local React dashboard. Kafka and Redis are optional;
Kafka remains disabled unless you deliberately enable it.

## 1. First-time setup and run

### Requirements

- Windows 10/11 with PowerShell.
- Git.
- Python 3.11 (3.12 may work, but the demo setup below uses Python 3.11).
- Node.js and npm.
- Docker Desktop, running with Linux containers, for local PostgreSQL.
- An authorized `.cap`, `.pcap`, or `.pcapng` capture for replay. Captures are
  not included in the repository.

Open PowerShell. If you are cloning the project for the first time:

```powershell
git clone https://github.com/EmberFalls/Custodian.git
Set-Location .\Custodian
```

If you already cloned it, change to the repository root instead:

```powershell
Set-Location 'C:\path\to\Custodian'
```

Confirm the required tools are available:

```powershell
git --version
py -3.11 --version
node --version
npm --version
docker --version
docker compose version
```

Start Docker Desktop before continuing.

### Create the Python environment

Run these commands from the Custodian repository root:

```powershell
py -3.11 -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install --upgrade pip
& '.\.venv\Scripts\python.exe' -m pip install -c constraints-demo.txt -e '.[dev]'
```

The constraints file keeps the ML package versions compatible with the supplied
demo model artifacts. Keep using this `.venv` for Custodian commands.

### Install the dashboard packages

```powershell
Set-Location .\frontend
npm ci
Set-Location ..
```

### Configure and start PostgreSQL

Create local configuration files from the examples:

```powershell
Copy-Item .env.pilot.example .env
Copy-Item .\configs\storage.pilot.example.yaml .\configs\storage.local.yaml
notepad .env
notepad .\configs\storage.local.yaml
```

In both files, replace `replace-with-a-strong-local-password` with the same
local password. Keep the password URL-safe (letters and numbers avoid URL
encoding problems). Save and close both files. They are ignored by Git.

Start PostgreSQL and wait for its health check:

```powershell
docker compose -f docker-compose.pilot.yml up -d postgres
docker compose -f docker-compose.pilot.yml ps
docker compose -f docker-compose.pilot.yml exec -T postgres pg_isready -U custodian -d custodian
```

The database port is published only on `127.0.0.1`. Custodian applies its
database schema when the API starts. Keep PostgreSQL running while using the
dashboard.

### Add an authorized capture

Put an authorized capture file directly in `data/demo/`:

```powershell
Copy-Item 'C:\path\to\authorized-capture.pcap' .\data\demo\
Get-ChildItem .\data\demo
```

The directory may be empty in a fresh clone. Add your own valid capture there;
do not put confidential or unapproved captures in the repository. Custodian
checks the capture format and link type before replay.

### Check model packages

In the same PowerShell terminal, select the demo model configuration and run
the package check:

```powershell
$env:CUSTODIAN_MODELS_CONFIG = 'models.demo.yaml'
$env:LOKY_MAX_CPU_COUNT = '4'
& '.\.venv\Scripts\python.exe' -m custodian.cli demo-check
```

Continue when the check reports `ready: true` and `detectors_ready: "4/4"`.

### Start the backend

Keep the model environment variables set in this terminal. Start FastAPI:

```powershell
& '.\.venv\Scripts\python.exe' -m uvicorn custodian.api.app:app --host 127.0.0.1 --port 8000
```

Leave this terminal open. In a second PowerShell window, check the API:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/health'
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/readiness' | ConvertTo-Json -Depth 10
```

The API is intentionally bound to localhost. Readiness should show the database
ready, Kafka disabled, and each configured detector ready.

### Start the dashboard

In a second (or third) PowerShell window, from the repository root:

```powershell
Set-Location 'C:\path\to\Custodian\frontend'
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open [http://127.0.0.1:5173/](http://127.0.0.1:5173/) in your browser. Sign in
with one of the local demo roles shown by the login screen.

### Validate and replay a capture

1. Open **Live Monitor**.
2. Select a capture from `data/demo/` and choose **Validate**.
3. Choose `PACED` for a timeline-oriented run or `FAST` for a quicker run.
4. Start replay and view the packet, flow, detector, and alert state.

Replay analyzes saved observations locally. It does not transmit captured
packets. If there are no captures listed, add a valid file to `data/demo/` and
refresh the page.

### Stop the first run

Press `Ctrl+C` in the dashboard terminal, then press `Ctrl+C` in the backend
terminal. Stop PostgreSQL when you are finished for now:

```powershell
docker compose -f docker-compose.pilot.yml stop postgres
```

PostgreSQL data remains in the Docker volume when the service is stopped.

## 2. Run an already set up project

These steps assume the repository is cloned, `.venv` and `frontend/node_modules`
exist, `.env` and `configs/storage.local.yaml` are configured, and Docker Desktop
is installed.

### Start PostgreSQL

Open PowerShell in the repository root and run:

```powershell
docker compose -f docker-compose.pilot.yml up -d postgres
docker compose -f docker-compose.pilot.yml ps
docker compose -f docker-compose.pilot.yml exec -T postgres pg_isready -U custodian -d custodian
```

### Start the backend

In that terminal, set the demo model configuration and start the API:

```powershell
$env:CUSTODIAN_MODELS_CONFIG = 'models.demo.yaml'
$env:LOKY_MAX_CPU_COUNT = '4'
& '.\.venv\Scripts\python.exe' -m uvicorn custodian.api.app:app --host 127.0.0.1 --port 8000
```

Leave it running. If you want a quick backend check, use another terminal:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/health'
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/readiness' | ConvertTo-Json -Depth 10
```

### Start the frontend

In another PowerShell window:

```powershell
Set-Location 'C:\path\to\Custodian\frontend'
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open [http://127.0.0.1:5173/](http://127.0.0.1:5173/), validate a capture, and
start replay.

### Stop the project

Press `Ctrl+C` in the frontend and backend terminals. Stop PostgreSQL if you do
not need it running:

```powershell
docker compose -f docker-compose.pilot.yml stop postgres
```

### Optional: run Kafka/PostgreSQL integration checks

The ordinary demo does not need Kafka. For the optional integration checks,
install the Kafka client once:

```powershell
& '.\.venv\Scripts\python.exe' -m pip install -c constraints-demo.txt -e '.[dev,pilot]'
```

Ensure PostgreSQL is running, then create a dedicated test database once:

```powershell
docker compose -f docker-compose.pilot.yml up -d postgres
docker compose -f docker-compose.pilot.yml exec -T postgres createdb -U custodian custodian_test
```

The first Kafka integration run needs the Redpanda Docker image. Python and npm
installation do not download Docker images. To download that image explicitly
before running the tests (one time per machine, or after the image version
changes), run:

```powershell
docker compose -f docker-compose.pilot.yml pull kafka
```

Set the test connection and enable the opt-in integration tests:

```powershell
$env:CUSTODIAN_TEST_DATABASE_URL = 'postgresql://custodian:YOUR_LOCAL_PASSWORD@127.0.0.1:5432/custodian_test'
$env:CUSTODIAN_TEST_KAFKA = '1'
& '.\.venv\Scripts\python.exe' -m pytest tests/integration/test_postgres_storage.py tests/integration/test_kafka_broker.py -q
```

The Kafka integration test starts and stops only the `kafka` service. PostgreSQL
remains running until stopped explicitly. The test uses the loopback broker at
`127.0.0.1:9092`. See [Kafka pilot details](KAFKA_PILOT.md) for the event
contracts and operational limits.

### Optional: verify code changes

Run the relevant project checks from the repository root:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -q
& '.\.venv\Scripts\python.exe' -m ruff check src tests training
Set-Location .\frontend
npm run build
Set-Location ..
```

The Kafka and PostgreSQL integration tests are opt-in and require their
environment variables and local services as shown above.
