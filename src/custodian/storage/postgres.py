"""Transactional PostgreSQL repository for Custodian runtime records."""

from __future__ import annotations

import json
from threading import RLock

import psycopg

from custodian.core.schemas import AlertRecord, CaptureRecord, DetectorVerdict, FlowRecord

MIGRATIONS = (
    """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version INTEGER PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS captures (
        capture_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, sha256 TEXT,
        status TEXT NOT NULL, payload_json JSONB NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS flow_summaries (
        flow_id TEXT PRIMARY KEY, capture_id TEXT, payload_json JSONB NOT NULL
    );
    CREATE TABLE IF NOT EXISTS feature_window_references (
        window_id TEXT PRIMARY KEY, capture_id TEXT, feature_version TEXT NOT NULL,
        payload_json JSONB NOT NULL
    );
    CREATE TABLE IF NOT EXISTS detector_results (
        result_id TEXT PRIMARY KEY, capture_id TEXT, payload_json JSONB NOT NULL
    );
    CREATE TABLE IF NOT EXISTS alerts (
        alert_id TEXT PRIMARY KEY, capture_id TEXT, status TEXT NOT NULL DEFAULT 'open',
        payload_json JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS evidence (
        evidence_id TEXT PRIMARY KEY, alert_id TEXT NOT NULL, payload_json JSONB NOT NULL
    );
    CREATE TABLE IF NOT EXISTS replay_checkpoints (
        checkpoint_id TEXT PRIMARY KEY, capture_id TEXT NOT NULL, position DOUBLE PRECISION NOT NULL,
        payload_json JSONB NOT NULL
    );
    CREATE TABLE IF NOT EXISTS model_registry (
        model_id TEXT PRIMARY KEY, trusted BOOLEAN NOT NULL DEFAULT FALSE, payload_json JSONB NOT NULL
    );
    CREATE TABLE IF NOT EXISTS application_events (
        event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, payload_json JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS alerts_updated_at_idx ON alerts(updated_at DESC);
    CREATE INDEX IF NOT EXISTS application_events_created_at_idx ON application_events(created_at DESC);
    INSERT INTO schema_migrations(version) VALUES (1) ON CONFLICT DO NOTHING;
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, display_name TEXT NOT NULL,
        password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'Analyst',
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    INSERT INTO schema_migrations(version) VALUES (2) ON CONFLICT DO NOTHING;
    """,
    """
    CREATE TABLE IF NOT EXISTS processed_event_ids (
        event_id TEXT PRIMARY KEY, processed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    INSERT INTO schema_migrations(version) VALUES (3) ON CONFLICT DO NOTHING;
    """,
)


class PostgresRepository:
    """Small connection-per-operation PostgreSQL repository for the local pilot."""

    def __init__(
        self, database_url: str, *, connect_timeout: int = 3, connection_factory=None
    ) -> None:
        if not database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("database_url must use PostgreSQL")
        self.database_url = database_url
        self.connect_timeout = connect_timeout
        self._connection_factory = connection_factory or psycopg.connect
        self._lock = RLock()

    def _connect(self):
        return self._connection_factory(self.database_url, connect_timeout=self.connect_timeout)

    def initialize(self) -> None:
        with self._lock, self._connect() as connection:
            for migration in MIGRATIONS:
                for statement in migration.split(";"):
                    if statement.strip():
                        connection.execute(statement)

    def health_check(self) -> None:
        """Raise if PostgreSQL is currently unavailable."""
        with self._lock, self._connect() as connection:
            connection.execute("SELECT 1")

    def process_event_once(self, event_id: str, handler) -> bool:
        """Run a durable handler once, transactionally with its event-ID claim.

        The callback receives this transaction's connection and must perform all
        durable side effects through it. Exceptions roll back both the writes
        and the event-ID insertion so Kafka can safely redeliver.
        """
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """INSERT INTO processed_event_ids(event_id) VALUES (%s)
                   ON CONFLICT DO NOTHING RETURNING event_id""",
                (event_id,),
            )
            if cursor.fetchone() is None:
                return False
            handler(connection)
            return True

    def get_user_by_username(self, username: str) -> dict | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """SELECT user_id, username, display_name, password_hash, role, created_at
                   FROM users WHERE LOWER(username) = LOWER(%s)""",
                (username,),
            ).fetchone()
        if row is None:
            return None
        return dict(
            zip(
                ("user_id", "username", "display_name", "password_hash", "role", "created_at"),
                row,
                strict=True,
            )
        )

    def get_user_by_id(self, user_id: str) -> dict | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """SELECT user_id, username, display_name, password_hash, role, created_at
                   FROM users WHERE user_id = %s""",
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return dict(
            zip(
                ("user_id", "username", "display_name", "password_hash", "role", "created_at"),
                row,
                strict=True,
            )
        )

    def upsert_user(
        self, user_id: str, username: str, display_name: str, password_hash: str, role: str
    ) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT INTO users(user_id, username, display_name, password_hash, role)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT(username) DO UPDATE SET display_name=excluded.display_name,
                   password_hash=excluded.password_hash, role=excluded.role""",
                (user_id, username.lower(), display_name, password_hash, role),
            )

    def list_users(self) -> list[dict]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT user_id, username, display_name, role, created_at FROM users ORDER BY username"
            ).fetchall()
        fields = ("user_id", "username", "display_name", "role", "created_at")
        return [dict(zip(fields, row, strict=True)) for row in rows]

    def upsert_capture(self, capture: CaptureRecord) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT INTO captures(capture_id, display_name, sha256, status, payload_json)
                   VALUES (%s, %s, %s, %s, %s::jsonb)
                   ON CONFLICT(capture_id) DO UPDATE SET status=excluded.status,
                   payload_json=excluded.payload_json, updated_at=CURRENT_TIMESTAMP""",
                (
                    capture.capture_id,
                    capture.display_name,
                    capture.sha256,
                    capture.status.value,
                    capture.model_dump_json(),
                ),
            )

    def upsert_alert(self, alert: AlertRecord, *, capture_id: str | None = None) -> None:
        stored = alert.model_copy(update={"capture_id": capture_id or alert.capture_id})
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT INTO alerts(alert_id, capture_id, status, payload_json)
                   VALUES (%s, %s, %s, %s::jsonb)
                   ON CONFLICT(alert_id) DO UPDATE SET status=excluded.status,
                   payload_json=excluded.payload_json, updated_at=CURRENT_TIMESTAMP""",
                (stored.alert_id, stored.capture_id, stored.status.value, stored.model_dump_json()),
            )

    @staticmethod
    def apply_pipeline_event(connection, event) -> dict | None:
        """Apply one validated pipeline event using the caller's event-ID transaction."""
        payload = event.payload
        if event.event_type == "flow_update":
            connection.execute(
                """INSERT INTO flow_summaries(flow_id,capture_id,payload_json)
                   VALUES (%s,%s,%s::jsonb) ON CONFLICT(flow_id) DO NOTHING""",
                (payload["flow_id"], event.capture_id, json.dumps(payload, sort_keys=True)),
            )
        elif event.event_type == "feature_vector":
            connection.execute(
                """INSERT INTO feature_window_references(window_id,capture_id,feature_version,payload_json)
                   VALUES (%s,%s,%s,%s::jsonb) ON CONFLICT(window_id) DO UPDATE
                   SET payload_json=excluded.payload_json""",
                (
                    payload["vector_id"],
                    event.capture_id,
                    payload["schema_version"],
                    json.dumps(payload, sort_keys=True),
                ),
            )
        elif event.event_type == "detector_verdict":
            connection.execute(
                """INSERT INTO detector_results(result_id,capture_id,payload_json)
                   VALUES (%s,%s,%s::jsonb) ON CONFLICT(result_id) DO UPDATE
                   SET payload_json=excluded.payload_json""",
                (payload["result_id"], event.capture_id, json.dumps(payload, sort_keys=True)),
            )
        elif event.event_type == "alert":
            summary = dict(payload)
            summary.pop("capture_id", None)
            connection.execute(
                """INSERT INTO alerts(alert_id,capture_id,status,payload_json)
                   VALUES (%s,%s,%s,%s::jsonb) ON CONFLICT(alert_id) DO NOTHING""",
                (
                    payload["alert_id"],
                    event.capture_id,
                    payload["status"],
                    json.dumps(summary, sort_keys=True),
                ),
            )
            return summary
        elif event.event_type == "runtime_event":
            connection.execute(
                """INSERT INTO application_events(event_id,event_type,payload_json)
                   VALUES (%s,%s,%s::jsonb) ON CONFLICT(event_id) DO NOTHING""",
                (payload["application_event_id"], payload["name"], json.dumps(payload)),
            )
        return None

    def upsert_flow(self, flow: FlowRecord, *, capture_id: str | None = None) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT INTO flow_summaries(flow_id, capture_id, payload_json)
                   VALUES (%s, %s, %s::jsonb) ON CONFLICT(flow_id) DO UPDATE
                   SET payload_json=excluded.payload_json""",
                (flow.flow_id, capture_id, flow.model_dump_json()),
            )

    def list_flows(self, *, limit: int = 100) -> list[dict]:
        if not 1 <= limit <= 500:
            raise ValueError("invalid flow pagination")
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """SELECT payload_json FROM flow_summaries
                   ORDER BY payload_json->>'last_seen' DESC NULLS LAST, flow_id
                   LIMIT %s""",
                (limit,),
            ).fetchall()
        return [
            payload if isinstance(payload, dict) else json.loads(payload) for (payload,) in rows
        ]

    def upsert_verdict(
        self, result_id: str, verdict: DetectorVerdict, *, capture_id: str | None = None
    ) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT INTO detector_results(result_id, capture_id, payload_json)
                   VALUES (%s, %s, %s::jsonb) ON CONFLICT(result_id) DO UPDATE
                   SET payload_json=excluded.payload_json""",
                (result_id, capture_id, verdict.model_dump_json()),
            )

    def save_checkpoint(
        self, checkpoint_id: str, capture_id: str, position: float, payload: dict
    ) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT INTO replay_checkpoints(checkpoint_id, capture_id, position, payload_json)
                   VALUES (%s, %s, %s, %s::jsonb) ON CONFLICT(checkpoint_id) DO UPDATE
                   SET position=excluded.position, payload_json=excluded.payload_json""",
                (checkpoint_id, capture_id, position, json.dumps(payload, sort_keys=True)),
            )

    def record_event(self, event_id: str, event_type: str, payload: dict) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT INTO application_events(event_id, event_type, payload_json)
                   VALUES (%s, %s, %s::jsonb) ON CONFLICT(event_id) DO UPDATE
                   SET event_type=excluded.event_type, payload_json=excluded.payload_json""",
                (event_id, event_type, json.dumps(payload, sort_keys=True)),
            )

    def set_alert_status(self, alert_id: str, status: str) -> bool:
        if status not in {"open", "acknowledged", "closed"}:
            raise ValueError("invalid alert status")
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """UPDATE alerts SET status=%s,
                   payload_json=jsonb_set(payload_json, '{status}', to_jsonb(%s::text)),
                   updated_at=CURRENT_TIMESTAMP WHERE alert_id=%s""",
                (status, status, alert_id),
            )
            return cursor.rowcount == 1

    def acknowledge_alert(self, alert_id: str) -> bool:
        return self.set_alert_status(alert_id, "acknowledged")

    def alert_count(self) -> int:
        with self._lock, self._connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM alerts").fetchone()[0])

    def list_alerts(self, *, limit: int = 100, offset: int = 0) -> list[dict]:
        if not 1 <= limit <= 500 or offset < 0:
            raise ValueError("invalid alert pagination")
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """SELECT payload_json, status FROM alerts ORDER BY updated_at DESC, alert_id
                   LIMIT %s OFFSET %s""",
                (limit, offset),
            ).fetchall()
        return [
            {**(payload if isinstance(payload, dict) else json.loads(payload)), "status": status}
            for payload, status in rows
        ]

    def get_alert(self, alert_id: str) -> dict | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json, status FROM alerts WHERE alert_id=%s", (alert_id,)
            ).fetchone()
        if row is None:
            return None
        payload = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        return {**payload, "status": row[1]}

    def table_names(self) -> set[str]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """SELECT table_name FROM information_schema.tables
                   WHERE table_schema = current_schema()"""
            ).fetchall()
        return {str(row[0]) for row in rows}

    def export_alerts(self) -> list[dict]:
        count = self.alert_count()
        records = []
        for offset in range(0, count, 500):
            records.extend(self.list_alerts(limit=min(500, count - offset), offset=offset))
        return records

    def apply_retention(self, *, retention_days: int) -> dict[str, int]:
        if retention_days <= 0:
            raise ValueError("retention_days must be positive")
        with self._lock, self._connect() as connection:
            alerts = connection.execute(
                "DELETE FROM alerts WHERE updated_at < CURRENT_TIMESTAMP - (%s * INTERVAL '1 day')",
                (retention_days,),
            ).rowcount
            events = connection.execute(
                "DELETE FROM application_events WHERE created_at < CURRENT_TIMESTAMP - (%s * INTERVAL '1 day')",
                (retention_days,),
            ).rowcount
        return {"alerts": max(alerts, 0), "events": max(events, 0)}
