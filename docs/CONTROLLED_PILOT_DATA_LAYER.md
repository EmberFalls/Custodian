# Controlled Pilot Data Layer: Redis live-state cache

Custodian is local-first and passive. This document covers the **optional**
short-lived live-state layer used by the controlled pilot. It does not enable
live capture, does not change authentication, and does not add Kafka or Grafana.

## Purpose and boundaries

PostgreSQL is the durable database. Redis only caches current runtime
state so the dashboard can read live telemetry without querying durable history
on every refresh.

```text
Passive replay / future passive sensor
        ↓
Custodian runtime
        ├─ PostgreSQL: durable users, captures, flows, alerts, evidence, audit events
        └─ Redis: temporary live state for dashboard/API
```

Redis is **not** the source of truth. It must never contain raw PCAP payloads,
reconstructed files, model binaries, secrets, passwords, JWT tokens, or
long-term evidence. All values are bounded structured JSON with a TTL. If Redis
is unavailable, Custodian keeps using the in-memory event hub and the durable
database; replay, alerting, feature extraction, and model inference continue.

### Key namespace

| Key | Contents |
| --- | --- |
| `custodian:pilot:replay_status` | Latest replay/runtime status |
| `custodian:pilot:telemetry` | Latest dashboard telemetry snapshot |
| `custodian:pilot:detectors` | Detector readiness summary |
| `custodian:pilot:latest_event` | Most recent application event |
| `custodian:pilot:recent_events` | Bounded recent event history |
| `custodian:pilot:recent_alerts` | Bounded recent alert summaries |
| `custodian:pilot:host_timeline` | Optional bounded host-timeline summary |

Lists are trimmed to `max_history` entries (default 500) and expire after
`ttl_seconds` (default 900).

## Configuration

`configs/redis.yaml` ships disabled by default:

```yaml
enabled: false
url: redis://127.0.0.1:6379/0
namespace: custodian:pilot
ttl_seconds: 900
max_history: 500
connect_timeout_seconds: 1.0
socket_timeout_seconds: 1.0
host_timeline: false
```

Resolution order for the configuration file:

1. `CUSTODIAN_REDIS_CONFIG` (absolute path, or relative to `configs/`)
2. `configs/redis.local.yaml` when present (git-ignored)
3. `configs/redis.yaml`

`CUSTODIAN_REDIS_URL` overrides only the URL. Non-loopback hosts
(`127.0.0.1`, `localhost`, `::1`) are rejected at validation so the default
controlled pilot cannot point at an external Redis.

## Install

Redis support is optional; PostgreSQL is required for durable API records:

```bash
pip install -e ".[pilot]"
```

## Start the cache

```bash
docker compose -f docker-compose.pilot.yml up -d postgres redis
cp configs/redis.pilot.example.yaml configs/redis.local.yaml
```

See [PostgreSQL pilot storage](POSTGRES_PILOT.md) to configure the durable
database. The Redis Compose service binds only `127.0.0.1:6379`, disables persistence
(`--save "" --appendonly no`) because it is a cache, and includes a health check.
Never commit real passwords or a `.env.pilot` file.

## Verify readiness

```bash
curl http://127.0.0.1:8000/api/v1/readiness
```

`components.redis.status` reports one of:

- `ready` — enabled, reachable, and no recent operation failed
- `degraded` — enabled and reachable, but a recent cache operation failed
- `unavailable` — enabled but unreachable, misconfigured, or the `redis` package is missing
- `disabled` — Redis is off; PostgreSQL persistence remains active

Redis status never changes the overall readiness decision or stops processing.

## Shutdown

```bash
docker compose -f docker-compose.pilot.yml down
```

Stop the API first if you want the cache to flush the final snapshot; both orders
are safe because replay never depends on Redis.

## Fallback: run without Redis

Leave `enabled: false` (the default), remove `configs/redis.local.yaml`, or unset
`CUSTODIAN_REDIS_URL`. Custodian uses the in-memory event hub and durable
database exactly as in the PostgreSQL-backed demo. You can also stop the Redis
container while Custodian is running: writes fail open, readiness shows
`unavailable`, and replay and alerts continue.

## Rollback

1. Remove `configs/redis.local.yaml` (or set `enabled: false`).
2. Unset `CUSTODIAN_REDIS_CONFIG` and `CUSTODIAN_REDIS_URL`.
3. `docker compose -f docker-compose.pilot.yml down`.
4. Restart the API. PostgreSQL remains the durable store.

## Tests

Unit tests use an in-memory fake Redis client and require no running service:

```bash
pytest tests/unit/test_redis_cache.py -q
```
