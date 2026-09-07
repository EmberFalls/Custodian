"""Small transactional SQLite repository for local runtime provenance."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock

from custodian.core.schemas import AlertRecord, CaptureRecord, DetectorVerdict, FlowRecord

MIGRATION_1 = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS captures (
    capture_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    sha256 TEXT,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS flow_summaries (
    flow_id TEXT PRIMARY KEY, capture_id TEXT, payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS feature_window_references (
    window_id TEXT PRIMARY KEY, capture_id TEXT, feature_version TEXT NOT NULL, payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS detector_results (
    result_id TEXT PRIMARY KEY, capture_id TEXT, payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts (
    alert_id TEXT PRIMARY KEY, capture_id TEXT, status TEXT NOT NULL DEFAULT 'open', payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY, alert_id TEXT NOT NULL, payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS replay_checkpoints (
    checkpoint_id TEXT PRIMARY KEY, capture_id TEXT NOT NULL, position REAL NOT NULL, payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS model_registry (
    model_id TEXT PRIMARY KEY, trusted INTEGER NOT NULL DEFAULT 0, payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS application_events (
    event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL
);
"""

MIGRATION_2 = """
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'Analyst',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class SQLiteRepository:
    """Serialize bounded application records through one process-local writer lock."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = RLock()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self._connect() as connection:
            connection.executescript(MIGRATION_1)
            connection.execute("INSERT OR IGNORE INTO schema_migrations(version) VALUES (1)")
            connection.executescript(MIGRATION_2)
            connection.execute("INSERT OR IGNORE INTO schema_migrations(version) VALUES (2)")

    def get_user_by_username(self, username: str) -> dict | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT user_id, username, display_name, password_hash, role, created_at FROM users WHERE LOWER(username) = LOWER(?)",
                (username,),
            ).fetchone()
        if not row:
            return None
        return {
            "user_id": row[0],
            "username": row[1],
            "display_name": row[2],
            "password_hash": row[3],
            "role": row[4],
            "created_at": row[5],
        }

    def get_user_by_id(self, user_id: str) -> dict | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT user_id, username, display_name, password_hash, role, created_at FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "user_id": row[0],
            "username": row[1],
            "display_name": row[2],
            "password_hash": row[3],
            "role": row[4],
            "created_at": row[5],
        }

    def upsert_user(
        self, user_id: str, username: str, display_name: str, password_hash: str, role: str
    ) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT INTO users(user_id, username, display_name, password_hash, role)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(username) DO UPDATE SET
                   display_name=excluded.display_name,
                   password_hash=excluded.password_hash,
                   role=excluded.role""",
                (user_id, username.lower(), display_name, password_hash, role),
            )

    def list_users(self) -> list[dict]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT user_id, username, display_name, role, created_at FROM users ORDER BY username"
            ).fetchall()
        return [
            {
                "user_id": row[0],
                "username": row[1],
                "display_name": row[2],
                "role": row[3],
                "created_at": row[4],
            }
            for row in rows
        ]

    def upsert_capture(self, capture: CaptureRecord) -> None:
        payload = capture.model_dump_json()
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT INTO captures(capture_id, display_name, sha256, status, payload_json)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(capture_id) DO UPDATE SET status=excluded.status,
                   payload_json=excluded.payload_json, updated_at=CURRENT_TIMESTAMP""",
                (
                    capture.capture_id,
                    capture.display_name,
                    capture.sha256,
                    capture.status.value,
                    payload,
                ),
            )

    def upsert_alert(self, alert: AlertRecord, *, capture_id: str | None = None) -> None:
        stored = alert.model_copy(update={"capture_id": capture_id or alert.capture_id})
        payload = stored.model_dump_json()
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT INTO alerts(alert_id, capture_id, status, payload_json)
                   VALUES (?, ?, ?, ?) ON CONFLICT(alert_id) DO UPDATE SET
                   status=excluded.status, payload_json=excluded.payload_json,
                   updated_at=CURRENT_TIMESTAMP""",
                (stored.alert_id, stored.capture_id, stored.status.value, payload),
            )

    def upsert_flow(self, flow: FlowRecord, *, capture_id: str | None = None) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT INTO flow_summaries(flow_id, capture_id, payload_json) VALUES (?, ?, ?)
                   ON CONFLICT(flow_id) DO UPDATE SET payload_json=excluded.payload_json""",
                (flow.flow_id, capture_id, flow.model_dump_json()),
            )

    def upsert_verdict(
        self, result_id: str, verdict: DetectorVerdict, *, capture_id: str | None = None
    ) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT INTO detector_results(result_id, capture_id, payload_json)
                   VALUES (?, ?, ?) ON CONFLICT(result_id) DO UPDATE SET
                   payload_json=excluded.payload_json""",
                (result_id, capture_id, verdict.model_dump_json()),
            )

    def save_checkpoint(
        self, checkpoint_id: str, capture_id: str, position: float, payload: dict
    ) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT INTO replay_checkpoints(checkpoint_id, capture_id, position, payload_json)
                   VALUES (?, ?, ?, ?) ON CONFLICT(checkpoint_id) DO UPDATE SET
                   position=excluded.position, payload_json=excluded.payload_json""",
                (checkpoint_id, capture_id, position, json.dumps(payload, sort_keys=True)),
            )

    def record_event(self, event_id: str, event_type: str, payload: dict) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT OR REPLACE INTO application_events(
                   event_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?)""",
                (
                    event_id,
                    event_type,
                    json.dumps(payload, sort_keys=True),
                    datetime.now(UTC).isoformat(),
                ),
            )

    def set_alert_status(self, alert_id: str, status: str) -> bool:
        if status not in {"open", "acknowledged", "closed"}:
            raise ValueError("invalid alert status")
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM alerts WHERE alert_id=?", (alert_id,)
            ).fetchone()
            if row is None:
                return False
            payload = json.loads(row[0])
            payload["status"] = status
            cursor = connection.execute(
                """UPDATE alerts SET status=?, payload_json=?,
                   updated_at=CURRENT_TIMESTAMP WHERE alert_id=?""",
                (status, json.dumps(payload, sort_keys=True), alert_id),
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
                   LIMIT ? OFFSET ?""",
                (limit, offset),
            ).fetchall()
        return [{**json.loads(payload), "status": status} for payload, status in rows]

    def get_alert(self, alert_id: str) -> dict | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json, status FROM alerts WHERE alert_id=?", (alert_id,)
            ).fetchone()
        return None if row is None else {**json.loads(row[0]), "status": row[1]}

    def table_names(self) -> set[str]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        return {str(row[0]) for row in rows}

    def export_alerts(self) -> list[dict]:
        count = self.alert_count()
        records = []
        for offset in range(0, count, 500):
            records.extend(self.list_alerts(limit=min(500, count - offset), offset=offset))
        return records

    def apply_retention(self, *, retention_days: int, max_database_bytes: int) -> dict[str, int]:
        if retention_days <= 0 or max_database_bytes <= 0:
            raise ValueError("retention limits must be positive")
        removed_alerts = 0
        removed_events = 0
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM alerts WHERE updated_at < datetime('now', ?)",
                (f"-{retention_days} days",),
            )
            removed_alerts += max(cursor.rowcount, 0)
            cursor = connection.execute(
                "DELETE FROM application_events WHERE created_at < datetime('now', ?)",
                (f"-{retention_days} days",),
            )
            removed_events += max(cursor.rowcount, 0)
        while self.path.exists() and self.path.stat().st_size > max_database_bytes:
            with self._lock, self._connect() as connection:
                row = connection.execute(
                    "SELECT alert_id FROM alerts ORDER BY updated_at LIMIT 1"
                ).fetchone()
                if row is None:
                    break
                connection.execute("DELETE FROM alerts WHERE alert_id=?", (row[0],))
                removed_alerts += 1
                connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        return {"alerts": removed_alerts, "events": removed_events}
