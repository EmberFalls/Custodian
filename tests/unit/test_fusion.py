"""Fusion tests use synthetic typed verdicts, not model claims."""

from custodian.core.enums import AlertDecision, EvidenceQuality, ThreatClass
from custodian.core.schemas import DetectorVerdict
from custodian.evidence.gate import GateResult
from custodian.fusion import FusionPolicy


def verdict(detector: str, threat: ThreatClass, confidence: float) -> DetectorVerdict:
    return DetectorVerdict(
        detector_id=detector,
        threat_class=threat,
        raw_score=confidence,
        calibrated_confidence=confidence,
        observation_confidence=0.8,
        model_version="TEST_ONLY",
        feature_schema_version="behaviour.v1",
        inference_latency_ms=0,
    )


def accepted():
    return GateResult(AlertDecision.ACCEPT, EvidenceQuality.ADEQUATE, ())


def test_fusion_preserves_one_supported_class_without_false_confidence_boost() -> None:
    result = FusionPolicy().fuse(
        [
            (verdict("one", ThreatClass.DDOS, 0.8), accepted()),
            (verdict("two", ThreatClass.DDOS, 0.9), accepted()),
        ]
    )

    assert result.decision is AlertDecision.ACCEPT
    assert result.threat_class is ThreatClass.DDOS
    assert result.threat_confidence == 0.9


def test_conflicting_accepted_classes_become_unknown() -> None:
    result = FusionPolicy().fuse(
        [
            (verdict("one", ThreatClass.DDOS, 0.9), accepted()),
            (verdict("two", ThreatClass.RECON, 0.9), accepted()),
        ]
    )

    assert result.decision is AlertDecision.UNKNOWN_SUSPICIOUS
    assert result.threat_class is None
    assert result.limitations
