"""Bounded event history supports reconnect cursors."""

from custodian.runtime.events import EventHub


def test_event_hub_is_bounded_and_resumable() -> None:
    hub = EventHub(max_events=2)
    first = hub.publish("one", {"value": 1}, run_id=0)
    hub.publish("two", {"value": 2}, run_id=0)
    third = hub.publish("three", {"value": 3}, run_id=1)

    assert [event.event_type for event in hub.since(first.sequence)] == ["two", "three"]
    assert hub.latest_sequence == third.sequence
    assert [event.event_type for event in hub.since(0)] == ["two", "three"]
    assert hub.earliest_sequence == 2
    assert hub.cursor_requires_resync(0) is True
    assert hub.cursor_requires_resync(99) is True
    assert hub.cursor_requires_resync(2) is False
