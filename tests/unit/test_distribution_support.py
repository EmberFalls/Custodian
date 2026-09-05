"""Distribution support checks operate only on extracted synthetic features."""

from custodian.core.enums import FeatureFamily
from custodian.core.schemas import FeatureVector
from custodian.observation.support import assess_distribution_support


def vector(value: float | None, available: bool = True) -> FeatureVector:
    return FeatureVector(
        family=FeatureFamily.BEHAVIOUR,
        schema_version="behaviour.v1",
        entity_id="flow-test",
        window_id="window-test",
        values={"packets_per_second": value},
        availability={"packets_per_second": available},
    )


def test_missing_profile_is_reported_as_not_evaluated() -> None:
    result = assess_distribution_support(vector(10), {})

    assert result.supported is None
    assert "does not declare" in result.reason


def test_out_of_range_observation_is_not_claimed_as_supported() -> None:
    result = assess_distribution_support(
        vector(200),
        {"packets_per_second": {"minimum": 0, "maximum": 100}},
    )

    assert result.supported is False
    assert result.out_of_range_fields == ("packets_per_second",)


def test_unavailable_feature_is_not_silently_zero_filled() -> None:
    result = assess_distribution_support(
        vector(None, available=False),
        {"packets_per_second": {"minimum": 0, "maximum": 100}},
    )

    assert result.supported is None
    assert result.evaluated_fields == ()
