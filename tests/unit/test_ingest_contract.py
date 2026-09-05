"""Future adapters remain disabled and never access the network."""

import pytest

from custodian.core.enums import SourceType
from custodian.ingestion.adapters import DisabledPassiveAdapter, disabled_live_adapter


def test_live_adapter_is_an_explicit_non_operational_boundary() -> None:
    adapter = disabled_live_adapter()

    assert adapter.source_type is SourceType.LIVE_PASSIVE
    with pytest.raises(RuntimeError, match="disabled pending explicit user approval"):
        next(adapter.observations())


def test_pcap_source_cannot_use_disabled_adapter() -> None:
    with pytest.raises(ValueError, match="PCAPObservationAdapter"):
        DisabledPassiveAdapter(SourceType.PCAP_REPLAY, "wrong adapter")
