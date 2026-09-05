"""Convert evidence-gated detector verdicts into standard AlertRecords."""

from __future__ import annotations

from datetime import UTC, datetime

from custodian.alerts.severity import select_severity
from custodian.core.ids import make_alert_id
from custodian.core.schemas import AlertRecord, CapabilityProfile, DetectorVerdict, FlowRecord
from custodian.evidence.gate import GateResult


def build_alert(
    verdict: DetectorVerdict,
    gate: GateResult,
    flow: FlowRecord,
    *,
    severity_rules: dict[str, str],
    total_pipeline_latency_ms: float,
    window_id: str | None = None,
    capabilities: CapabilityProfile | None = None,
    class_threshold: float | None = None,
    evidence_policy_version: str = "evidence.v1",
    severity_policy_version: str = "severity.v1",
    fusion_policy_version: str = "fusion.v1",
    capture_id: str | None = None,
) -> AlertRecord | None:
    """Build an alert only for accepted, unknown, or insufficient-evidence outcomes."""

    if gate.decision is None:
        return None
    return AlertRecord(
        alert_id=make_alert_id(
            verdict.detector_id,
            verdict.threat_class,
            flow.last_seen,
            flow_id=flow.flow_id,
            window_id=window_id,
        ),
        capture_id=capture_id,
        timestamp=flow.last_seen,
        first_seen=flow.start_time,
        last_seen=flow.last_seen,
        flow_id=flow.flow_id,
        window_id=window_id,
        threat_class=verdict.threat_class,
        severity=select_severity(verdict.threat_class, severity_rules),
        decision=gate.decision,
        calibrated_confidence=verdict.calibrated_confidence,
        threat_confidence=verdict.threat_confidence,
        observation_confidence=verdict.observation_confidence,
        observation_frame_id=verdict.observation_frame_id,
        raw_score=verdict.raw_score,
        class_threshold=class_threshold,
        emitted_at=datetime.now(UTC),
        evidence_quality=gate.evidence_quality,
        source=flow.initiator or flow.endpoint_a,
        destination=flow.endpoint_b
        if (flow.initiator or flow.endpoint_a) == flow.endpoint_a
        else flow.endpoint_a,
        evidence=verdict.evidence,
        missing_evidence=gate.missing_evidence,
        available_evidence=verdict.available_evidence,
        limitations=verdict.limitations,
        capabilities=capabilities,
        detector_id=verdict.detector_id,
        model_version=verdict.model_version,
        feature_schema_version=verdict.feature_schema_version,
        inference_latency_ms=verdict.inference_latency_ms,
        total_pipeline_latency_ms=total_pipeline_latency_ms,
        stage_timings_ms=verdict.stage_timings_ms,
        policy_versions={
            "evidence": evidence_policy_version,
            "severity": severity_policy_version,
            "fusion": fusion_policy_version,
        },
    )
