"""Bounded flow lifecycle with O(1) updates and ordered idle expiration."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta

from custodian.core.enums import FlowCloseReason, FlowDirection
from custodian.core.ids import make_flow_id
from custodian.core.schemas import Endpoint, FlowRecord, PacketObservation
from custodian.flow.key import FlowKey
from custodian.flow.record import MutableFlow


@dataclass(slots=True)
class FlowUpdate:
    flow: MutableFlow
    direction: FlowDirection
    is_new_flow: bool
    expired: tuple[FlowRecord, ...] = ()
    _snapshot: FlowRecord | None = None

    @property
    def flow_id(self) -> str:
        return self.flow.flow_id

    @property
    def snapshot(self) -> FlowRecord:
        if self._snapshot is None:
            self._snapshot = self.flow.snapshot()
        return self._snapshot


class FlowManager:
    def __init__(
        self,
        idle_timeout_seconds: int = 60,
        *,
        active_timeout_seconds: int = 120,
        max_flows: int = 50_000,
    ) -> None:
        if min(idle_timeout_seconds, active_timeout_seconds, max_flows) <= 0:
            raise ValueError("flow limits must be positive")
        self.idle_timeout = timedelta(seconds=idle_timeout_seconds)
        self.active_timeout = timedelta(seconds=active_timeout_seconds)
        self.max_flows = max_flows
        self._flows: OrderedDict[FlowKey, MutableFlow] = OrderedDict()
        self._generation = 0
        self.evicted_count = 0

    @property
    def active_flow_count(self) -> int:
        return len(self._flows)

    def snapshots(self, *, limit: int = 100) -> tuple[FlowRecord, ...]:
        """Return a bounded, immutable view without exposing mutable flow state."""

        if limit <= 0:
            return ()
        return tuple(flow.snapshot() for flow in list(self._flows.values())[-limit:])

    def expire(self, observed_at: datetime) -> tuple[FlowRecord, ...]:
        expired = []
        while self._flows:
            key, flow = next(iter(self._flows.items()))
            if observed_at - flow.last_seen < self.idle_timeout:
                break
            del self._flows[key]
            expired.append(flow.snapshot(FlowCloseReason.IDLE_TIMEOUT))
        return tuple(expired)

    def process(self, packet: PacketObservation, *, snapshot: bool = True) -> FlowUpdate:
        expired = list(self.expire(packet.timestamp))
        key = FlowKey.from_packet(packet)
        flow = self._flows.get(key)
        if flow and packet.timestamp - flow.start_time >= self.active_timeout:
            expired.append(self._flows.pop(key).snapshot(FlowCloseReason.ACTIVE_TIMEOUT))
            flow = None
        is_new = flow is None
        if flow is None:
            if len(self._flows) >= self.max_flows:
                _, evicted = self._flows.popitem(last=False)
                expired.append(evicted.snapshot(FlowCloseReason.EVICTED))
                self.evicted_count += 1
            flow = MutableFlow(
                flow_id=make_flow_id(
                    key.endpoint_a,
                    key.endpoint_b,
                    key.protocol,
                    packet.timestamp,
                    session_discriminator=str(self._generation),
                ),
                key=key,
                start_time=packet.timestamp,
                last_seen=packet.timestamp,
                initiator=Endpoint(ip=packet.src_ip, port=packet.src_port),
            )
            self._generation += 1
            self._flows[key] = flow
        direction = key.direction_for(packet)
        flow.add(packet, direction)
        self._flows.move_to_end(key)
        if packet.tcp_flags and ({"RST", "FIN"} & packet.tcp_flags):
            reason = FlowCloseReason.RST if "RST" in packet.tcp_flags else FlowCloseReason.FIN
            self._flows.pop(key, None)
            expired.append(flow.snapshot(reason))
        return FlowUpdate(
            flow, direction, is_new, tuple(expired), flow.snapshot() if snapshot else None
        )

    def flush(self) -> tuple[FlowRecord, ...]:
        snapshots = tuple(
            flow.snapshot(FlowCloseReason.CAPTURE_END) for flow in self._flows.values()
        )
        self._flows.clear()
        return snapshots

    def reset(self) -> None:
        self._flows.clear()
        self._generation = 0
        self.evicted_count = 0
