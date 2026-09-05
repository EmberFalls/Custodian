"""Common boundary for passive input sources."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from custodian.core.enums import SourceType
from custodian.core.schemas import CapabilityProfile, PacketObservation


class IngestAdapter(Protocol):
    source_type: SourceType
    capabilities: CapabilityProfile

    def observations(self) -> Iterator[PacketObservation]: ...
