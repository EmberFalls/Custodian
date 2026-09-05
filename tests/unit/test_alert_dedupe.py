"""Repeat alerts update lifecycle fields without creating alert storms."""

from datetime import timedelta

from custodian.alerts.dedupe import AlertDeduplicator
from custodian.core.enums import (
    AlertDecision,
    AlertStatus,
    EvidenceQuality,
    Severity,
    ThreatClass,
)
from custodian.core.schemas import AlertRecord, Endpoint


def alert(observed_at, *, confidence: float, suffix: str) -> AlertRecord:
    return AlertRecord(
        alert_id=f"alert-{suffix}",
        timestamp=observed_at,
        first_seen=observed_at,
        last_seen=observed_at,
        flow_id="flow-test",
        threat_class=ThreatClass.RECON,
        severity=Severity.MEDIUM,
        decision=AlertDecision.ACCEPT,
        calibrated_confidence=confidence,
        observation_confidence=None,
        evidence_quality=EvidenceQuality.ADEQUATE,
        source=Endpoint(ip="10.0.0.1", port=50000),
        destination=Endpoint(ip="10.0.0.2", port=443),
        evidence={"unique_destination_ports": 4},
        detector_id="behaviour",
        model_version="test-only",
        feature_schema_version="behaviour.v1",
        inference_latency_ms=0,
        total_pipeline_latency_ms=1,
    )


def test_repeat_updates_count_last_seen_and_preserves_unavailable_confidence(
    observed_at,
) -> None:
    dedupe = AlertDeduplicator(cooldown_seconds=60)
    first, is_new = dedupe.merge(alert(observed_at, confidence=0.8, suffix="first"))
    repeated = alert(observed_at + timedelta(seconds=10), confidence=0.9, suffix="repeat")
    merged, repeat_is_new = dedupe.merge(repeated)

    assert is_new is True and repeat_is_new is False
    assert merged.alert_id == first.alert_id
    assert merged.occurrence_count == 2
    assert merged.last_seen == repeated.last_seen
    assert merged.calibrated_confidence == 0.9
    assert merged.observation_confidence is None


def test_repeat_after_cooldown_is_a_new_record(observed_at) -> None:
    dedupe = AlertDeduplicator(cooldown_seconds=60)
    dedupe.merge(alert(observed_at, confidence=0.8, suffix="first"))
    _, is_new = dedupe.merge(
        alert(observed_at + timedelta(seconds=61), confidence=0.8, suffix="later")
    )

    assert is_new is True


def test_analyst_status_survives_repeat_merge(observed_at) -> None:
    dedupe = AlertDeduplicator(cooldown_seconds=60)
    first, _ = dedupe.merge(alert(observed_at, confidence=0.8, suffix="first"))
    dedupe.set_status(first.alert_id, AlertStatus.ACKNOWLEDGED)

    merged, _ = dedupe.merge(
        alert(observed_at + timedelta(seconds=5), confidence=0.9, suffix="repeat")
    )

    assert merged.status is AlertStatus.ACKNOWLEDGED
