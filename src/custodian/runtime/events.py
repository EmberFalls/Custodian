"""Thread-safe bounded application event history."""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from threading import RLock

from custodian.core.schemas import ApplicationEvent


class EventHub:
    def __init__(self, max_events: int = 2000) -> None:
        if max_events <= 0:
            raise ValueError("max_events must be positive")
        self._events: deque[ApplicationEvent] = deque(maxlen=max_events)
        self._sequence = 0
        self._lock = RLock()

    @property
    def latest_sequence(self) -> int:
        with self._lock:
            return self._sequence

    @property
    def earliest_sequence(self) -> int:
        with self._lock:
            return self._events[0].sequence if self._events else self._sequence + 1

    def cursor_requires_resync(self, sequence: int) -> bool:
        with self._lock:
            if sequence > self._sequence:
                return True
            return bool(self._events and sequence < self._events[0].sequence - 1)

    def publish(self, event_type: str, payload: dict, *, run_id: int) -> ApplicationEvent:
        with self._lock:
            self._sequence += 1
            event = ApplicationEvent(
                event_id=f"event-{self._sequence:016x}",
                sequence=self._sequence,
                event_type=event_type,
                created_at=datetime.now(UTC),
                run_id=run_id,
                payload=payload,
            )
            self._events.append(event)
            return event

    def since(self, sequence: int, *, limit: int = 200) -> list[ApplicationEvent]:
        if sequence < 0 or not 1 <= limit <= 500:
            raise ValueError("invalid event cursor or limit")
        with self._lock:
            return [event for event in self._events if event.sequence > sequence][:limit]
