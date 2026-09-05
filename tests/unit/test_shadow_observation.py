"""Shadow tests degrade in-memory features only."""

from custodian.core.enums import FeatureFamily, ThreatClass
from custodian.core.schemas import DetectorVerdict, FeatureVector
from custodian.observation.shadow import mask_features, observation_robustness


def verdict(threat: ThreatClass, confidence: float) -> DetectorVerdict:
    return DetectorVerdict(
        detector_id="TEST_ONLY",
        threat_class=threat,
        raw_score=confidence,
        calibrated_confidence=confidence,
        model_version="TEST_ONLY",
        feature_schema_version="behaviour.v1",
        inference_latency_ms=0,
    )


def test_masking_never_mutates_original_vector() -> None:
    original = FeatureVector(
        family=FeatureFamily.BEHAVIOUR,
        schema_version="behaviour.v1",
        entity_id="flow-test",
        window_id="window-test",
        values={"timing": 1.0, "bytes": 4.0},
        availability={"timing": True, "bytes": True},
    )
    degraded = mask_features(original, {"timing"})

    assert original.values["timing"] == 1.0
    assert degraded.values["timing"] is None
    assert degraded.availability["timing"] is False


def test_robustness_penalizes_class_instability() -> None:
    baseline = verdict(ThreatClass.DDOS, 0.9)
    stable = observation_robustness(baseline, [verdict(ThreatClass.DDOS, 0.8)])
    changed = observation_robustness(baseline, [verdict(ThreatClass.RECON, 0.8)])

    assert stable is not None and changed is not None and stable > changed
