"""Passive shadow-observation helpers operating only on extracted features."""

from __future__ import annotations

from custodian.core.schemas import DetectorVerdict, FeatureVector


def mask_features(vector: FeatureVector, names: set[str]) -> FeatureVector:
    """Create a degraded copy; never alters a capture or network traffic."""

    values = dict(vector.values)
    availability = dict(vector.availability)
    for name in names & values.keys():
        values[name] = None
        availability[name] = False
    return vector.model_copy(update={"values": values, "availability": availability})


def observation_robustness(
    baseline: DetectorVerdict, shadows: list[DetectorVerdict]
) -> float | None:
    """Score class stability and confidence retention under controlled masking."""

    if not shadows or baseline.threat_confidence is None or baseline.threat_confidence <= 0:
        return None
    scores = []
    for shadow in shadows:
        class_stability = 1.0 if shadow.threat_class is baseline.threat_class else 0.0
        retention = min((shadow.threat_confidence or 0) / baseline.threat_confidence, 1.0)
        scores.append(0.7 * class_stability + 0.3 * retention)
    return round(sum(scores) / len(scores), 6)
