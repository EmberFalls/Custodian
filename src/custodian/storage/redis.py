"""Optional short-lived live-state cache backed by loopback Redis.

Redis is never the source of truth. PostgreSQL remains durable; this cache
stores only bounded, structured runtime metadata with an explicit TTL so the
dashboard can read live telemetry without replaying durable history. Every
operation is best-effort: an unavailable Redis must never stop replay, alerting,
feature extraction, or model inference, so failures are swallowed and surfaced
only through :meth:`RedisLiveStateCache.readiness`.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from custodian.config import RedisSettings

logger = logging.getLogger(__name__)

try:  # Redis is an optional pilot dependency; the demo must import without it.
    import redis as redis_module
except ImportError:  # pragma: no cover - exercised only without the extra installed
    redis_module = None

# Key suffixes under the configured namespace. Values here are metadata/JSON only.
REPLAY_STATUS_KEY = "replay_status"
TELEMETRY_KEY = "telemetry"
DETECTORS_KEY = "detectors"
LATEST_EVENT_KEY = "latest_event"
RECENT_EVENTS_KEY = "recent_events"
RECENT_ALERTS_KEY = "recent_alerts"
HOST_TIMELINE_KEY = "host_timeline"


class RedisLiveStateCache:
    """Best-effort bounded JSON cache with TTL, disabled unless configured."""

    def __init__(self, settings: RedisSettings, *, client: Any | None = None) -> None:
        self.settings = settings
        self.enabled = bool(settings.enabled)
        self.namespace = settings.namespace
        self.ttl_seconds = settings.ttl_seconds
        self.max_history = settings.max_history
        self._client = client
        self._last_error: str | None = None
        self._unavailable_reason: str | None = None
        if self.enabled and self._client is None:
            if redis_module is None:
                self._unavailable_reason = (
                    "redis package is not installed; install the 'pilot' extra"
                )
            else:
                try:
                    self._client = redis_module.Redis.from_url(
                        settings.url,
                        socket_connect_timeout=settings.connect_timeout_seconds,
                        socket_timeout=settings.socket_timeout_seconds,
                        decode_responses=True,
                    )
                except Exception as exc:  # pragma: no cover - defensive client setup
                    self._unavailable_reason = f"could not configure Redis client: {exc}"

    @property
    def url(self) -> str:
        return self.settings.url

    def key(self, suffix: str) -> str:
        return f"{self.namespace}:{suffix}"

    def _execute(self, operation: Callable, *args: Any, **kwargs: Any) -> Any:
        """Run one Redis command, recording failures instead of raising them."""

        try:
            result = operation(*args, **kwargs)
        except Exception as exc:
            self._last_error = str(exc)
            logger.warning("Redis live-state operation failed: %s", exc)
            return None
        self._last_error = None
        return result

    def _active(self) -> bool:
        return self.enabled and self._client is not None

    def ping(self) -> bool:
        if not self._active():
            return False
        try:
            return bool(self._client.ping())
        except Exception as exc:
            self._last_error = str(exc)
            return False

    def readiness(self) -> dict[str, str | None]:
        """Report ready, unavailable, degraded, or disabled without raising."""

        if not self.enabled:
            return {
                "status": "disabled",
                "reason": "Redis live-state cache is disabled by configuration",
            }
        if self._client is None:
            return {
                "status": "unavailable",
                "reason": self._unavailable_reason or "Redis client is not configured",
            }
        if not self.ping():
            return {
                "status": "unavailable",
                "reason": self._last_error or "Redis did not respond to ping",
            }
        if self._last_error:
            return {"status": "degraded", "reason": self._last_error}
        return {"status": "ready", "reason": None}

    def _set_json(self, suffix: str, payload: Any) -> bool:
        if not self._active():
            return False
        serialized = json.dumps(payload, default=str, sort_keys=True)
        result = self._execute(
            self._client.set, self.key(suffix), serialized, ex=self.ttl_seconds
        )
        return result is not None

    def _append_bounded(self, suffix: str, payload: Any) -> bool:
        if not self._active():
            return False
        key = self.key(suffix)
        serialized = json.dumps(payload, default=str, sort_keys=True)
        result = self._execute(self._client.lpush, key, serialized)
        if result is None:
            return False
        self._execute(self._client.ltrim, key, 0, self.max_history - 1)
        self._execute(self._client.expire, key, self.ttl_seconds)
        return True

    def set_replay_status(self, payload: dict) -> bool:
        return self._set_json(REPLAY_STATUS_KEY, payload)

    def set_telemetry(self, payload: dict) -> bool:
        return self._set_json(TELEMETRY_KEY, payload)

    def set_detectors(self, payload: dict) -> bool:
        return self._set_json(DETECTORS_KEY, payload)

    def set_latest_event(self, payload: dict) -> bool:
        return self._set_json(LATEST_EVENT_KEY, payload)

    def set_host_timeline(self, payload: Any) -> bool:
        """Store an optional bounded host-timeline summary when enabled."""

        if not self.settings.host_timeline:
            return False
        return self._set_json(HOST_TIMELINE_KEY, payload)

    def append_recent_event(self, payload: dict) -> bool:
        return self._append_bounded(RECENT_EVENTS_KEY, payload)

    def append_recent_alert(self, payload: dict) -> bool:
        return self._append_bounded(RECENT_ALERTS_KEY, payload)

    def get_json(self, suffix: str) -> Any | None:
        if not self._active():
            return None
        raw = self._execute(self._client.get, self.key(suffix))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return None

    def get_recent(self, suffix: str, *, limit: int | None = None) -> list[Any]:
        if not self._active():
            return []
        end = (limit if limit is not None else self.max_history) - 1
        if end < 0:
            return []
        raw = self._execute(self._client.lrange, self.key(suffix), 0, end)
        if not raw:
            return []
        records = []
        for item in raw:
            try:
                records.append(json.loads(item))
            except (TypeError, ValueError):
                continue
        return records

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # pragma: no cover - best-effort shutdown
                pass
