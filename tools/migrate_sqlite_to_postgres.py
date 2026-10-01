"""Copy a legacy Custodian SQLite database into PostgreSQL without deleting it."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from custodian.config import load_config_bundle
from custodian.storage.postgres import PostgresRepository

TABLE_COLUMNS = {
    "captures": ("capture_id", "display_name", "sha256", "status", "payload_json", "updated_at"),
    "flow_summaries": ("flow_id", "capture_id", "payload_json"),
    "feature_window_references": (
        "window_id", "capture_id", "feature_version", "payload_json"
    ),
    "detector_results": ("result_id", "capture_id", "payload_json"),
    "alerts": ("alert_id", "capture_id", "status", "payload_json", "updated_at"),
    "evidence": ("evidence_id", "alert_id", "payload_json"),
    "replay_checkpoints": (
        "checkpoint_id", "capture_id", "position", "payload_json"
    ),
    "model_registry": ("model_id", "trusted", "payload_json"),
    "application_events": ("event_id", "event_type", "payload_json", "created_at"),
    "users": ("user_id", "username", "display_name", "password_hash", "role", "created_at"),
    "processed_event_ids": ("event_id", "processed_at"),
}
JSON_COLUMNS = {"payload_json"}


def migrate(source_path: Path, repository: PostgresRepository) -> dict[str, int]:
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    repository.initialize()
    copied: dict[str, int] = {}
    with sqlite3.connect(source_path) as source, repository._lock, repository._connect() as target:
        existing = {
            row[0]
            for row in source.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        for table, allowed_columns in TABLE_COLUMNS.items():
            if table not in existing:
                continue
            source_columns = {row[1] for row in source.execute(f"PRAGMA table_info({table})")}
            columns = tuple(column for column in allowed_columns if column in source_columns)
            if not columns:
                continue
            casts = ["%s::jsonb" if column in JSON_COLUMNS else "%s" for column in columns]
            column_sql = ", ".join(columns)
            values_sql = ", ".join(casts)
            statement = (
                f"INSERT INTO {table} ({column_sql}) VALUES ({values_sql}) ON CONFLICT DO NOTHING"
            )
            count = 0
            for source_row in source.execute(f"SELECT {column_sql} FROM {table}"):
                row = list(source_row)
                if table == "model_registry" and "trusted" in columns:
                    row[columns.index("trusted")] = bool(row[columns.index("trusted")])
                cursor = target.execute(statement, row)
                count += max(cursor.rowcount, 0)
            copied[table] = count
    return copied


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="legacy SQLite database file")
    parser.add_argument(
        "--config-dir", type=Path, default=Path("configs"), help="Custodian config directory"
    )
    args = parser.parse_args()
    settings = load_config_bundle(args.config_dir).storage
    try:
        result = migrate(args.source, PostgresRepository(settings.database_url))
    except Exception as exc:
        parser.exit(2, f"Migration stopped; the source database was left unchanged: {exc}\n")
    print("Copied rows (conflicts skipped):")
    for table, count in result.items():
        print(f"  {table}: {count}")
    print("Source database was left unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
