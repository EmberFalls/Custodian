"""Shared pytest fixtures for Custodian tests."""

from __future__ import annotations

from datetime import UTC, datetime
from importlib import import_module

import pytest

from custodian.core.schemas import Endpoint


class MemoryPostgresRepository:
    """API test double; real SQL behavior is covered by the Docker-gated test."""

    def __init__(self, database_url="", **kwargs):
        self.users = {}
        self.alerts = {}
        self.flows = {}
        self.events = {}
        self.captures = {}

    def initialize(self):
        pass

    def health_check(self):
        pass

    def apply_retention(self, **kwargs):
        return {"alerts": 0, "events": 0}

    def list_users(self):
        return list(self.users.values())

    def upsert_user(self, user_id, username, display_name, password_hash, role):
        self.users[username.lower()] = {
            "user_id": user_id,
            "username": username.lower(),
            "display_name": display_name,
            "password_hash": password_hash,
            "role": role,
            "created_at": "2026-09-25T00:00:00+00:00",
        }

    def get_user_by_username(self, username):
        return self.users.get(username.lower())

    def get_user_by_id(self, user_id):
        return next((user for user in self.users.values() if user["user_id"] == user_id), None)

    def record_event(self, event_id, event_type, payload):
        self.events[event_id] = {"event_type": event_type, "payload": payload}

    def upsert_capture(self, capture):
        self.captures[capture.capture_id] = capture.model_dump(mode="json")

    def save_checkpoint(self, *args, **kwargs):
        pass

    def upsert_alert(self, alert, *, capture_id=None):
        payload = alert.model_dump(mode="json")
        payload["capture_id"] = capture_id or payload.get("capture_id")
        self.alerts[alert.alert_id] = payload

    def upsert_flow(self, *args, **kwargs):
        flow = args[0]
        self.flows[flow.flow_id] = flow.model_dump(mode="json")

    def list_alerts(self, *, limit=100, offset=0):
        ordered = list(self.alerts.values())[::-1]
        return ordered[offset : offset + limit]

    def list_flows(self, *, limit=100):
        return list(self.flows.values())[:limit]

    def get_alert(self, alert_id):
        return self.alerts.get(alert_id)

    def set_alert_status(self, alert_id, status):
        alert = self.alerts.get(alert_id)
        if alert is None:
            return False
        alert["status"] = status
        return True

    def acknowledge_alert(self, alert_id):
        return self.set_alert_status(alert_id, "acknowledged")

    def alert_count(self):
        return len(self.alerts)

    def export_alerts(self):
        return list(self.alerts.values())


@pytest.fixture(autouse=True)
def use_memory_postgres_for_api_tests(monkeypatch):
    api_module = import_module("custodian.api.app")
    monkeypatch.setattr(api_module, "PostgresRepository", MemoryPostgresRepository)


@pytest.fixture
def observed_at() -> datetime:
    return datetime(2026, 9, 1, 10, 0, tzinfo=UTC)


@pytest.fixture
def client_endpoint() -> Endpoint:
    return Endpoint(ip="10.0.0.15", port=49152)


@pytest.fixture
def server_endpoint() -> Endpoint:
    return Endpoint(ip="10.0.0.20", port=443)
