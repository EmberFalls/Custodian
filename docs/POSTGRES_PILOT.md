# PostgreSQL pilot storage

PostgreSQL is Custodian's only durable runtime database. Users, captures,
alerts, flow summaries, detector results, checkpoints, events and processed
event IDs use PostgreSQL. Redis remains an optional cache; it is never the
source of truth. The API reports database failure as degraded readiness and
keeps passive PCAP replay and in-memory telemetry available.

## Local setup

Install the project dependencies (psycopg is a core dependency), copy
`.env.pilot.example` to `.env`, and replace the placeholder password. Copy
`configs/storage.pilot.example.yaml` to `configs/storage.local.yaml` and use
the same local password in its URL. Both local files are ignored by Git.

Start PostgreSQL:

```powershell
docker compose -f docker-compose.pilot.yml up -d postgres
```

The PostgreSQL image has a health check, persists data in the
`custodian-postgres` Docker volume, and publishes port 5432 only on
`127.0.0.1`. Custodian applies versioned schema migrations during API startup.
`CUSTODIAN_DATABASE_URL` overrides the configured URL; the connection host is
validated as loopback for this controlled pilot. The default URL has no
password and is intended only for a locally configured PostgreSQL instance;
use the ignored local YAML with the Compose service.

Stop the database without deleting its data:

```powershell
docker compose -f docker-compose.pilot.yml stop postgres
```

The API can be stopped independently. A database outage affects durable
operations and readiness, but does not enable network activity or prevent
passive parsing from continuing in memory.

## Storage contract

The repository uses parameterized psycopg queries, JSONB for structured
records, unique primary keys for idempotent upserts, bounded connection
timeouts, and age-based retention for alerts and application events.
`process_event_once` commits the processed-event marker in the same transaction
as callback writes, so a failed handler can be retried without reserving its ID.
Raw packet payloads are not stored. PostgreSQL data volume sizing and backups are
managed as database operations; the former SQLite file-size cap is not applied
to PostgreSQL's physical data files.

Existing ignored SQLite files are not opened by the application. To copy their
records, start PostgreSQL, configure the destination URL, and run the one-time
importer. It skips rows whose primary keys already exist and leaves the source
file untouched:

```powershell
& '.\.venv\Scripts\python.exe' tools/migrate_sqlite_to_postgres.py --source runtime/custodian.sqlite3
```

The PostgreSQL integration tests run when `CUSTODIAN_TEST_DATABASE_URL` points to a dedicated
local test database:

```powershell
$env:CUSTODIAN_TEST_DATABASE_URL = 'postgresql://custodian:...@127.0.0.1:5432/custodian_test'
& '.\.venv\Scripts\python.exe' -m pytest tests/integration/test_postgres_storage.py -q
```
