"""PostgreSQL integration checks, enabled by CUSTODIAN_TEST_DATABASE_URL."""

import os
from uuid import uuid4

import pytest

from custodian.storage.postgres import PostgresRepository

DATABASE_URL = os.getenv("CUSTODIAN_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="set CUSTODIAN_TEST_DATABASE_URL to run PostgreSQL integration checks"
)


def test_postgres_schema_and_idempotency():
    repository = PostgresRepository(DATABASE_URL)
    repository.initialize()
    tables = repository.table_names()
    assert {"captures", "alerts", "application_events", "users", "processed_event_ids"} <= tables

    event_id = f"test-{uuid4().hex}"
    assert repository.process_event_once(event_id, lambda connection: None)
    assert not repository.process_event_once(event_id, lambda connection: None)

    failed_id = f"test-{uuid4().hex}"

    def fail_handler(connection):
        raise RuntimeError("test rollback")

    with pytest.raises(RuntimeError, match="test rollback"):
        repository.process_event_once(failed_id, fail_handler)
    assert repository.process_event_once(failed_id, lambda connection: None)


def test_postgres_user_upsert_is_case_insensitive():
    repository = PostgresRepository(DATABASE_URL)
    repository.initialize()
    username = f"test-{uuid4().hex}@local.invalid"
    repository.upsert_user(f"test-user-{uuid4().hex}", username, "Test User", "hash", "Analyst")
    user = repository.get_user_by_username(username.upper())
    assert user is not None and user["username"] == username
