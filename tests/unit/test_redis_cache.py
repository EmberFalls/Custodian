"""Optional Redis live-state cache tests use a fake client, never a real server."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from custodian.config import RedisSettings, load_config_bundle
from custodian.storage import RedisLiveStateCache


class FakeRedis:
    """Minimal in-memory stand-in for the Redis commands the cache uses."""

    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.value_ttls: dict[str, int | None] = {}
        self.lists: dict[str, list[str]] = {}
        self.list_ttls: dict[str, int | None] = {}
        self.ping_calls = 0
        self.fail_ping = False
        self.fail_writes = False

    def _check_ping(self) -> None:
        if self.fail_ping:
            raise RuntimeError("redis unavailable")

    def _check_write(self) -> None:
        if self.fail_writes:
            raise RuntimeError("redis write rejected")

    def ping(self) -> bool:
        self.ping_calls += 1
        self._check_ping()
        return True

    def set(self, name: str, value: str, ex: int | None = None) -> bool:
        self._check_write()
        self.values[name] = value
        self.value_ttls[name] = ex
        return True

    def get(self, name: str) -> str | None:
        self._check_write()
        return self.values.get(name)

    def lpush(self, name: str, *values: str) -> int:
        self._check_write()
        bucket = self.lists.setdefault(name, [])
        for value in values:
            bucket.insert(0, value)
        return len(bucket)

    def ltrim(self, name: str, start: int, stop: int) -> bool:
        self._check_write()
        bucket = self.lists.get(name, [])
        self.lists[name] = bucket[start : stop + 1]
        return True

    def lrange(self, name: str, start: int, stop: int) -> list[str]:
        self._check_write()
        return self.lists.get(name, [])[start : stop + 1]

    def expire(self, name: str, ttl: int) -> bool:
        self._check_write()
        self.list_ttls[name] = ttl
        return True

    def close(self) -> None:
        return None


def enabled_settings(**overrides) -> RedisSettings:
    payload = {
        "enabled": True,
        "namespace": "custodian:pilot",
        "ttl_seconds": 60,
        "max_history": 3,
        **overrides,
    }
    return RedisSettings(**payload)


def test_disabled_by_default_never_touches_redis() -> None:
    cache = RedisLiveStateCache(RedisSettings())

    assert cache.readiness() == {
        "status": "disabled",
        "reason": "Redis live-state cache is disabled by configuration",
    }
    assert cache.set_replay_status({"state": "IDLE"}) is False
    assert cache.append_recent_event({"event_id": "e1"}) is False
    assert cache.get_json("replay_status") is None
    assert cache.get_recent("recent_events") == []


def test_non_loopback_endpoint_is_rejected() -> None:
    with pytest.raises(ValidationError, match="loopback"):
        RedisSettings(enabled=True, url="redis://10.0.0.5:6379/0")


def test_invalid_scheme_is_rejected() -> None:
    with pytest.raises(ValidationError, match="scheme"):
        RedisSettings(enabled=True, url="http://127.0.0.1:6379/0")


def test_values_are_namespaced_ttl_bounded_and_json() -> None:
    fake = FakeRedis()
    cache = RedisLiveStateCache(enabled_settings(), client=fake)

    assert cache.readiness()["status"] == "ready"
    assert cache.set_replay_status({"state": "RUNNING", "run_id": 1}) is True
    assert fake.values["custodian:pilot:replay_status"].startswith("{")
    assert fake.value_ttls["custodian:pilot:replay_status"] == 60
    assert cache.get_json("replay_status") == {"state": "RUNNING", "run_id": 1}

    for index in range(5):
        cache.append_recent_alert({"alert_id": f"a{index}"})
    recent = cache.get_recent("recent_alerts")
    assert [item["alert_id"] for item in recent] == ["a4", "a3", "a2"]
    assert fake.list_ttls["custodian:pilot:recent_alerts"] == 60


def test_host_timeline_is_optional() -> None:
    fake = FakeRedis()
    cache = RedisLiveStateCache(enabled_settings(host_timeline=False), client=fake)
    assert cache.set_host_timeline([{"host": "10.0.0.1"}]) is False
    assert "custodian:pilot:host_timeline" not in fake.values

    fake = FakeRedis()
    cache = RedisLiveStateCache(enabled_settings(host_timeline=True), client=fake)
    assert cache.set_host_timeline([{"host": "10.0.0.1"}]) is True
    assert cache.get_json("host_timeline") == [{"host": "10.0.0.1"}]


def test_outage_never_raises_and_recovers() -> None:
    fake = FakeRedis()
    cache = RedisLiveStateCache(enabled_settings(), client=fake)

    fake.fail_ping = True
    assert cache.set_replay_status({"state": "RUNNING"}) is True
    assert cache.readiness() == {
        "status": "unavailable",
        "reason": "redis unavailable",
    }

    fake.fail_ping = False
    assert cache.append_recent_event({"event_id": "e1"}) is True
    assert cache.set_telemetry({"packets": 0}) is True
    assert cache.readiness()["status"] == "ready"


def test_reachable_but_failing_writes_reports_degraded() -> None:
    fake = FakeRedis()
    cache = RedisLiveStateCache(enabled_settings(), client=fake)

    fake.fail_writes = True
    assert cache.set_replay_status({"state": "RUNNING"}) is False
    assert cache.readiness()["status"] == "degraded"

    fake.fail_writes = False
    assert cache.set_replay_status({"state": "RUNNING"}) is True
    assert cache.readiness()["status"] == "ready"


def test_redis_url_environment_override(monkeypatch) -> None:
    config_dir = Path(__file__).resolve().parents[2] / "configs"
    monkeypatch.setenv("CUSTODIAN_REDIS_URL", "redis://localhost:6380/2")

    bundle = load_config_bundle(config_dir)

    assert bundle.redis.url == "redis://localhost:6380/2"


def test_redis_config_environment_selects_local_file(tmp_path, monkeypatch) -> None:
    config_dir = Path(__file__).resolve().parents[2] / "configs"
    override = tmp_path / "redis.override.yaml"
    override.write_text(
        "enabled: true\nurl: redis://127.0.0.1:6379/1\nnamespace: custodian:pilot\n"
        "ttl_seconds: 300\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CUSTODIAN_REDIS_CONFIG", str(override))

    bundle = load_config_bundle(config_dir)

    assert bundle.redis.enabled is True
    assert bundle.redis.url == "redis://127.0.0.1:6379/1"
    assert bundle.redis.ttl_seconds == 300


def test_repository_config_is_disabled_by_default() -> None:
    config_dir = Path(__file__).resolve().parents[2] / "configs"
    bundle = load_config_bundle(config_dir)

    assert bundle.redis.enabled is False
    assert bundle.redis.url == "redis://127.0.0.1:6379/0"


def test_api_readiness_reports_redis_and_mirrors_telemetry(tmp_path) -> None:
    from fastapi.testclient import TestClient

    from custodian.api.app import create_app

    config_dir = Path(__file__).resolve().parents[2] / "configs"
    bundle = load_config_bundle(config_dir)
    for name, entry in bundle.models.models.items():
        bundle.models.models[name] = entry.model_copy(update={"artifact_path": None})
    bundle = bundle.model_copy(
        update={
            "storage": bundle.storage.model_copy(update={"enabled": False})
        }
    )
    fake = FakeRedis()
    cache = RedisLiveStateCache(enabled_settings(), client=fake)
    app = create_app(bundle, live_state=cache)

    with TestClient(app) as client:
        readiness = client.get("/api/v1/readiness").json()
        assert readiness["components"]["redis"]["status"] == "ready"
        assert set(client.get("/api/v1/telemetry").json()) == {
            "status",
            "metrics",
            "detectors",
        }
        assert "custodian:pilot:telemetry" in fake.values
        assert "custodian:pilot:detectors" in fake.values
        assert "custodian:pilot:replay_status" in fake.values
        assert all("pcap" not in key and "payload" not in key for key in fake.values)

