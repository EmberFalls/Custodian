# Optional Kafka-compatible event transport

Kafka is an opt-in metadata transport for local pilot experiments. The normal
one-laptop replay stays in-process; Kafka is not needed to parse a PCAP, and
enabling it does not enable live capture or any active network behavior.

## Contract

The envelope is JSON with `event_id`, `event_type`, `schema_version`
(`custodian.v1`), `occurred_at`, `run_id`, `capture_id`, `correlation_id`, and
`payload`. Every event type has a closed payload schema; extra properties,
binary data, secret-like values, and prohibited fields are rejected. Encoded
events are bounded by `max_event_bytes` (default 262144).
- `custodian.v1.packet_observation`
- `custodian.v1.flow_update`
- `custodian.v1.feature_vector`
- `custodian.v1.detector_verdict`
- `custodian.v1.alert`
- `custodian.v1.runtime_event`
- `custodian.v1.dead_letter`

Kafka partition keys use `capture_id` to preserve per-capture ordering. During
authorized PCAP replay, Custodian publishes minimized flow snapshots, feature
vectors, detector verdicts, and alert summaries. Raw packet bytes, extracted
files, credentials, tokens, full model artifacts, and raw model binaries are
not accepted by event contracts. Packet observations have a metadata-only
contract for future passive inputs; the replay engine does not serialize frame
contents.

## Configuration and local broker

Kafka config resolves from `CUSTODIAN_KAFKA_CONFIG`, then ignored
`configs/kafka.local.yaml`, then `configs/kafka.yaml`. Environment overrides
are `CUSTODIAN_KAFKA_ENABLED`, `CUSTODIAN_KAFKA_BOOTSTRAP_SERVERS` (comma
separated), `CUSTODIAN_KAFKA_TOPIC_PREFIX`, and
`CUSTODIAN_KAFKA_CONSUMER_GROUP`, plus `CUSTODIAN_KAFKA_MAX_EVENT_BYTES`,
`CUSTODIAN_KAFKA_RETRIES`, and `CUSTODIAN_KAFKA_RETRY_BACKOFF_SECONDS`. The
shipped config is disabled and restricts
broker addresses to loopback. `pip install -e ".[pilot]"` installs the optional
`confluent-kafka` client along with Redis support.

Start only the local compatible broker with
`docker compose -f docker-compose.pilot.yml up -d kafka`. The only published
broker port binds to `127.0.0.1:9092`; the service has a health check and a
small single-core memory budget. Set `enabled: true` in the ignored local YAML
to opt in. Stop it with `docker compose -f docker-compose.pilot.yml stop kafka`
or remove pilot services with `docker compose -f docker-compose.pilot.yml down`.
No public or remote broker is accepted by configuration.

The first Kafka run downloads the Redpanda Docker image if it is not cached;
installing Python or npm dependencies does not install Docker images. To pull
it explicitly ahead of a test or startup, run
`docker compose -f docker-compose.pilot.yml pull kafka` once. Later runs reuse
the cached image unless its configured tag changes.

## Runtime and operational limits

When disabled, the bounded in-process path remains the default and no broker is
required. On Kafka startup, Custodian creates all seven versioned topics if
they do not already exist, then subscribes its consumer. When enabled, the API
starts a Kafka consumer worker, validates each event, applies its durable PostgreSQL effect in the same transaction as its
event-ID claim, and mirrors alert summaries to Redis after commit. Duplicate
event IDs do not repeat durable writes. Successful messages are committed only
after processing. Invalid and unprocessable events are sent once to the
dead-letter topic with a static error code (never exception text or message
body); a failed dead-letter write pauses consumption and marks readiness
degraded. Producer retries are bounded with backoff. Producer queue backlog,
consumer status, last sanitized error category, and dead-letter count appear in
readiness and diagnostics. Kafka publish failure does not enable any live or
active network behavior; local extraction/inference remains passive and the
failure is visible as degraded health.

The replay engine currently performs feature extraction, inference, and
evidence/alert decisions synchronously in its existing engine, then publishes
those validated stage outputs for independently idempotent downstream
PostgreSQL/Redis processing. Kafka is therefore an optional metadata backbone
for persisted stage results, not a distributed inference scheduler. PostgreSQL
is required for enabled Kafka mode; replay start is rejected if PostgreSQL is
unavailable so that a Kafka consumer cannot silently acknowledge events without
durable storage.

Unit contract tests use fakes and require no broker. The Docker service is
optional and the standard application/test workflow does not start it. A real
broker integration check requires the local Docker service. The integration
test in `tests/integration/test_kafka_broker.py` verifies publish/consume, and
when `CUSTODIAN_TEST_DATABASE_URL` is also set it checks Kafka-to-PostgreSQL
alert persistence and duplicate delivery. See `docs/POSTGRES_PILOT.md` for the
local database setup.

On Windows PowerShell, start Docker Desktop, create an ignored `.env` from
`.env.pilot.example`, replace the placeholder with a local password, then run:

```powershell
docker compose -f docker-compose.pilot.yml up -d postgres
docker compose -f docker-compose.pilot.yml ps
docker compose -f docker-compose.pilot.yml exec -T postgres pg_isready -U custodian -d custodian
docker compose -f docker-compose.pilot.yml exec -T postgres createdb -U custodian custodian_test
docker compose -f docker-compose.pilot.yml pull kafka
$env:CUSTODIAN_TEST_DATABASE_URL = 'postgresql://custodian:YOUR_LOCAL_PASSWORD@127.0.0.1:5432/custodian_test'
$env:CUSTODIAN_TEST_KAFKA = '1'
& '.\.venv\Scripts\python.exe' -m pytest tests/integration/test_postgres_storage.py tests/integration/test_kafka_broker.py -q
docker compose -f docker-compose.pilot.yml stop postgres
```

The Kafka integration test starts and stops only the `kafka` Compose service;
PostgreSQL remains running until the explicit stop command. The test database
should be dedicated to integration checks because the test applies migrations
and creates temporary records. To remove that database permanently, first stop
PostgreSQL and use `docker compose -f docker-compose.pilot.yml down -v` only if
you also intend to delete the pilot's persisted database volume.
