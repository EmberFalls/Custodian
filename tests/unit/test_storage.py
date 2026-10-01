"""PostgreSQL repository contract checks that require no running database."""

import pytest
from pydantic import ValidationError

from custodian.config import StorageSettings
from custodian.storage.postgres import MIGRATIONS, PostgresRepository
from tools.migrate_sqlite_to_postgres import migrate


def test_repository_rejects_non_postgresql_dsn():
    with pytest.raises(ValueError, match="PostgreSQL"):
        PostgresRepository("sqlite:///custodian.db")


def test_migrations_cover_durable_project_entities():
    schema = "\n".join(MIGRATIONS)
    for table in (
        "captures",
        "flow_summaries",
        "feature_window_references",
        "detector_results",
        "alerts",
        "evidence",
        "replay_checkpoints",
        "model_registry",
        "application_events",
        "users",
        "processed_event_ids",
        "schema_migrations",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in schema
    assert "JSONB" in schema


def test_storage_settings_reject_remote_postgres_host():
    with pytest.raises(ValidationError, match="loopback"):
        StorageSettings(database_url="postgresql://db.example:5432/custodian")


def test_api_degrades_when_postgres_is_unavailable(monkeypatch):
    from fastapi.testclient import TestClient

    from custodian.api.app import create_app
    from custodian.config import load_config_bundle

    class UnavailablePostgres:
        def __init__(self, *args, **kwargs):
            raise ConnectionError("test database unavailable")

    monkeypatch.setattr("custodian.api.app.PostgresRepository", UnavailablePostgres)
    config = load_config_bundle("configs")
    for family, entry in config.models.models.items():
        config.models.models[family] = entry.model_copy(update={"artifact_path": None})
    app = create_app(config)
    with TestClient(app) as client:
        readiness = client.get("/api/v1/readiness").json()
        assert readiness["status"] == "degraded"
        assert readiness["components"]["database"]["status"] == "unavailable"
        assert client.get("/health").status_code == 200
        assert client.get("/api/v1/events").status_code == 200


def test_sqlite_importer_copies_rows_without_deleting_source(tmp_path):
    statements = []

    class Cursor:
        rowcount = 1

    class Connection:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, statement, params=None):
            statements.append((statement, params))
            return Cursor()

    source = tmp_path / "legacy.sqlite3"
    import sqlite3

    with sqlite3.connect(source) as connection:
        connection.execute(
            "CREATE TABLE alerts (alert_id TEXT, capture_id TEXT, status TEXT, payload_json TEXT, updated_at TEXT)"
        )
        connection.execute(
            "INSERT INTO alerts VALUES (?, ?, ?, ?, ?)",
            ("a-1", "cap-1", "open", '{"alert_id":"a-1"}', "2026-01-01T00:00:00+00:00"),
        )

    repository = PostgresRepository("postgresql://test", connection_factory=Connection)
    copied = migrate(source, repository)
    assert copied == {"alerts": 1}
    assert source.is_file()
    assert any("INSERT INTO alerts" in statement for statement, _ in statements)
