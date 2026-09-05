"""Deterministic feature-range support checks for approved model manifests."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from custodian.core.schemas import FeatureVector


@dataclass(frozen=True, slots=True)
class DistributionSupportAssessment:
    """Result of comparing observable numeric features with evaluated ranges."""

    supported: bool | None
    evaluated_fields: tuple[str, ...]
    out_of_range_fields: tuple[str, ...]
    reason: str


def assess_distribution_support(
    vector: FeatureVector,
    feature_ranges: dict[str, dict[str, float]],
    *,
    maximum_out_of_range_fraction: float = 0.2,
) -> DistributionSupportAssessment:
    """Assess manifest-declared support without treating it as attack detection."""

    if not 0 <= maximum_out_of_range_fraction <= 1:
        raise ValueError("maximum_out_of_range_fraction must be between 0 and 1")
    if not feature_ranges:
        return DistributionSupportAssessment(
            None,
            (),
            (),
            "approved model manifest does not declare evaluated feature ranges",
        )
    evaluated: list[str] = []
    outside: list[str] = []
    for name, limits in feature_ranges.items():
        value = vector.values.get(name)
        if not vector.availability.get(name, False) or not isinstance(value, (int, float)):
            continue
        minimum = limits.get("minimum")
        maximum = limits.get("maximum")
        if (
            minimum is None
            or maximum is None
            or not all(isfinite(float(item)) for item in (minimum, maximum))
        ):
            continue
        if minimum > maximum:
            continue
        evaluated.append(name)
        if not minimum <= float(value) <= maximum:
            outside.append(name)
    if not evaluated:
        return DistributionSupportAssessment(
            None,
            (),
            (),
            "no available numeric feature matched the manifest support profile",
        )
    fraction = len(outside) / len(evaluated)
    supported = fraction <= maximum_out_of_range_fraction
    reason = (
        "observation is within the evaluated feature-range support profile"
        if supported
        else "observation falls outside the evaluated feature-range support profile"
    )
    return DistributionSupportAssessment(
        supported,
        tuple(evaluated),
        tuple(outside),
        reason,
    )
