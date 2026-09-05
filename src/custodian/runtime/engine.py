"""Incremental flow snapshots and short batched inference on one laptop."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import perf_counter

from custodian.alerts.builder import build_alert
from custodian.alerts.dedupe import AlertDeduplicator
from custodian.config import ConfigBundle
from custodian.core.enums import (
    AlertDecision,
    EvidenceAvailability,
    EvidenceQuality,
    FeatureFamily,
    ReplayMode,
    TransportProtocol,
)
from custodian.core.schemas import CapabilityProfile, FeatureVector, FlowRecord, ObservationFrame
from custodian.detection.behaviour import BehaviourDetector
from custodian.detection.dns import DNSDetector
from custodian.detection.tls_quic import TLSQUICDetector
from custodian.evidence.gate import EvidenceGate, GateResult
from custodian.features.behaviour import BehaviourFeatureExtractor
from custodian.features.dns import DNSFeatureExtractor
from custodian.features.tls_quic import TLSQUICFeatureExtractor
from custodian.flow.manager import FlowManager
from custodian.ingest.pcap import CaptureReader
from custodian.ingest.replay import ReplayController
from custodian.models.loader import load_model_package
from custodian.observation.capabilities import flow_capabilities
from custodian.observation.integrity import CapabilityRouter, build_observation_frame
from custodian.observation.support import assess_distribution_support
from custodian.parsing.packet import PacketParser
from custodian.state.manager import TemporalStateManager
from custodian.telemetry.metrics import MetricsCollector


@dataclass(slots=True)
class PendingInference:
    vector: FeatureVector
    flow: FlowRecord
    capabilities: CapabilityProfile
    observation_frame: ObservationFrame
    observation_confidence: float
    queued_at: float


class CustodianEngine:
    def __init__(self, config: ConfigBundle) -> None:
        self.config = config
        self.parser = PacketParser()
        settings = config.defaults
        self.flows = FlowManager(
            settings.flow_idle_timeout_seconds,
            active_timeout_seconds=settings.flow_active_timeout_seconds,
            max_flows=settings.max_active_flows,
        )
        self.state = TemporalStateManager(
            settings.temporal_windows_seconds, max_events=settings.max_temporal_events
        )
        self.behaviour_features = BehaviourFeatureExtractor()
        self.dns_features = DNSFeatureExtractor()
        self.tls_features = TLSQUICFeatureExtractor()
        self.metrics = MetricsCollector()
        self.dedupe = AlertDeduplicator(max_entries=settings.max_alerts * 2)
        self.evidence_gate = EvidenceGate(
            config.evidence.requirements, config.evidence.unknown_min_confidence
        )
        self.capability_router = CapabilityRouter()
        self.alerts = deque(maxlen=settings.max_alerts)
        self.recent_flows = deque(maxlen=min(settings.max_active_flows, 5000))
        self.host_timeline = deque(maxlen=min(settings.max_temporal_events, 5000))
        self.routing_diagnostics = deque(maxlen=settings.max_alerts)
        self._available_capabilities: set[str] = set()
        self.alert_revision = 0
        self._load_errors = {}
        self.detectors = self._load_detectors()
        self._dirty = {}
        self._last_packets = {}
        self._last_snapshot_counts = {}
        self._pending = {family: [] for family in self.detectors}
        self._next_snapshot = None
        self._watermark: datetime | None = None
        self.mode = config.replay.mode
        self.capture_id: str | None = None

    def _package(self, family: str):
        entry = self.config.models.models[family]
        if not entry.enabled or entry.artifact_path is None:
            return None
        if not entry.trusted:
            self._load_errors[family] = (
                "Artifact loading is blocked until its provenance and isolated-VM workflow "
                "are explicitly approved (set trusted: true only after that review)"
            )
            return None
        try:
            package = load_model_package(entry.artifact_path)
            if package.feature_schema.get("family") != family:
                raise ValueError("configured model belongs to a different feature family")
            return package
        except Exception as exc:
            # A missing/broken optional artifact must not prevent parser-only replay.
            self._load_errors[family] = str(exc)
            return None

    def _load_detectors(self):
        return {
            "behaviour": BehaviourDetector(self._package("behaviour")),
            "dns": DNSDetector(self._package("dns")),
            "tls_quic": TLSQUICDetector(self._package("tls_quic")),
        }

    def detector_status(self) -> list[dict]:
        statuses = []
        for name, detector in self.detectors.items():
            package = detector.package
            entry = self.config.models.models[name]
            statuses.append(
                {
                    "id": name,
                    "enabled": detector.available,
                    "status": "READY" if detector.available else "UNAVAILABLE",
                    "reason": None
                    if detector.available
                    else self._load_errors.get(
                        name,
                        "No approved trained model package is configured"
                        if not entry.enabled
                        else "No complete trusted model package is available",
                    ),
                    "model_version": package.model_version if package else None,
                    "schema_version": package.feature_schema["schema_version"]
                    if package
                    else f"{name}.v1",
                    "classes": list(package.classes) if package else [],
                    "artifact_trusted": entry.trusted,
                    "required_evidence": list(self.capability_router.REQUIRED[FeatureFamily(name)]),
                    "available_evidence": sorted(self._available_capabilities),
                    "distribution_support": (
                        "available"
                        if package and getattr(package, "manifest", {}).get("feature_support")
                        else "unavailable"
                    ),
                }
            )
        return statuses

    def _queue_flow(self, flow: FlowRecord, observed_at: datetime) -> list:
        packet_count = flow.packets_a_to_b + flow.packets_b_to_a
        if packet_count == self._last_snapshot_counts.get(flow.flow_id):
            return []
        self._last_snapshot_counts[flow.flow_id] = packet_count
        started = perf_counter()
        source = flow.initiator or flow.endpoint_a
        destination = flow.endpoint_b if source == flow.endpoint_a else flow.endpoint_a
        window = 60 if 60 in self.state.windows_seconds else self.state.windows_seconds[0]
        state = self.state.snapshot(str(source.ip), str(destination.ip), observed_at, window)
        self.host_timeline.append(
            {
                "observed_at": observed_at.isoformat(),
                "host": str(source.ip),
                "peer": str(destination.ip),
                "window_seconds": window,
                "packet_count": state.packet_count,
                "byte_count": state.byte_count,
                "flow_count": state.flow_count,
                "unique_destinations": state.unique_destinations,
                "unique_destination_ports": state.unique_destination_ports,
                "outbound_bytes": state.outbound_bytes,
                "inbound_bytes": state.inbound_bytes,
                "alert_id": None,
                "threat_class": None,
            }
        )
        capabilities = flow_capabilities(flow)
        self._available_capabilities.update(
            name for name, available in capabilities.model_dump().items() if available
        )
        vectors = [("behaviour", self.behaviour_features.extract(flow, state, capabilities))]
        packet = self._last_packets.get(flow.flow_id)
        if self.detectors["dns"].available and packet is not None and flow.dns_metadata:
            vectors.append(
                (
                    "dns",
                    self.dns_features.extract(
                        packet.model_copy(update={"dns_metadata": flow.dns_metadata}),
                        state,
                        capabilities,
                    ),
                )
            )
        if self.detectors["tls_quic"].available and (flow.tls_metadata or flow.quic_metadata):
            vectors.append(("tls_quic", self.tls_features.extract(flow, state, capabilities)))
        self.metrics.feature_vectors += len(vectors)
        self.metrics.record_latency("features", (perf_counter() - started) * 1000)
        emitted = []
        for family, vector in vectors:
            if not self.detectors[family].available:
                continue
            if family == "behaviour" and flow.protocol not in {
                TransportProtocol.TCP,
                TransportProtocol.UDP,
            }:
                continue
            observation_frame = build_observation_frame(flow, vector, capabilities)
            route = self.capability_router.route(vector.family, observation_frame)
            if not route.allowed:
                self.routing_diagnostics.append(
                    {
                        "observation_frame_id": observation_frame.observation_frame_id,
                        "family": vector.family.value,
                        "decision": "INSUFFICIENT_EVIDENCE",
                        "missing_evidence": list(route.missing_capabilities),
                        "reason": route.reason,
                    }
                )
                continue
            self._pending[family].append(
                PendingInference(
                    vector,
                    flow,
                    capabilities,
                    observation_frame,
                    route.observation_confidence,
                    started,
                )
            )
            if len(self._pending[family]) >= self.config.defaults.inference_batch_size:
                emitted.extend(self._flush_family(family))
        return emitted

    def _flush_family(self, family: str) -> list:
        pending = self._pending[family]
        if not pending:
            return []
        self._pending[family] = []
        detector = self.detectors[family]
        started = perf_counter()
        verdicts = detector.detect_batch([job.vector for job in pending])
        feature_support = getattr(detector.package, "manifest", {}).get("feature_support", {})
        support_assessments = [
            assess_distribution_support(job.vector, feature_support) for job in pending
        ]
        elapsed_ms = (perf_counter() - started) * 1000
        self.metrics.inference_batches += 1
        self.metrics.inference_vectors += len(pending)
        self.metrics.record_latency("inference_batch", elapsed_ms)
        self.metrics.record_latency("inference", elapsed_ms / len(pending))
        emitted = []
        for job, verdict, support in zip(pending, verdicts, support_assessments, strict=True):
            support_limitations = (support.reason,) if support.supported is not True else ()
            verdict = verdict.model_copy(
                update={
                    "observation_frame_id": job.observation_frame.observation_frame_id,
                    "observation_confidence": job.observation_confidence,
                    "available_evidence": tuple(
                        name
                        for name, state in job.observation_frame.evidence_mask.items()
                        if state is EvidenceAvailability.AVAILABLE
                    ),
                    "limitations": tuple(
                        dict.fromkeys(
                            verdict.limitations
                            + job.observation_frame.limitations
                            + support_limitations
                        )
                    ),
                    "evidence": {
                        **verdict.evidence,
                        "distribution_support": (
                            "supported"
                            if support.supported is True
                            else "outside_evaluated_support"
                            if support.supported is False
                            else "not_evaluated"
                        ),
                        "out_of_range_features": list(support.out_of_range_fields),
                    },
                }
            )
            started = perf_counter()
            threshold = detector.package.thresholds.get(verdict.threat_class.value)
            gate = self.evidence_gate.evaluate(verdict, job.capabilities, threshold)
            if support.supported is False and gate.decision is AlertDecision.ACCEPT:
                gate = GateResult(
                    AlertDecision.UNKNOWN_SUSPICIOUS,
                    EvidenceQuality.WEAK,
                    (),
                )
            self.metrics.evidence_decisions += 1
            self.metrics.decisions[gate.decision.value if gate.decision else "NO_ALERT"] += 1
            self.metrics.record_latency("evidence", (perf_counter() - started) * 1000)
            started = perf_counter()
            alert = build_alert(
                verdict,
                gate,
                job.flow,
                severity_rules=self.config.severity.rules,
                total_pipeline_latency_ms=(perf_counter() - job.queued_at) * 1000,
                window_id=job.vector.window_id,
                capabilities=job.capabilities,
                class_threshold=threshold,
                evidence_policy_version=self.config.evidence.policy_version,
                severity_policy_version=self.config.severity.policy_version,
                capture_id=self.capture_id,
            )
            if alert:
                alert, is_new = self.dedupe.merge(alert)
                if is_new:
                    self.alerts.append(alert)
                    self.metrics.record_alert()
                else:
                    replaced = False
                    for index, current in enumerate(self.alerts):
                        if current.alert_id == alert.alert_id:
                            self.alerts[index] = alert
                            replaced = True
                            break
                    if not replaced:
                        self.alerts.append(alert)
                self.host_timeline.append(
                    {
                        "observed_at": alert.timestamp.isoformat(),
                        "host": str(alert.source.ip) if alert.source else None,
                        "peer": str(alert.destination.ip) if alert.destination else None,
                        "window_seconds": None,
                        "packet_count": None,
                        "byte_count": None,
                        "flow_count": None,
                        "unique_destinations": None,
                        "unique_destination_ports": None,
                        "outbound_bytes": None,
                        "inbound_bytes": None,
                        "alert_id": alert.alert_id,
                        "threat_class": alert.threat_class.value,
                    }
                )
                self.alert_revision += 1
                emitted.append(alert)
            self.metrics.record_latency("alert", (perf_counter() - started) * 1000)
            self.metrics.record_latency("total_pipeline", (perf_counter() - job.queued_at) * 1000)
        return emitted

    def flush_due(self, *, force: bool = False) -> list:
        now, emitted = perf_counter(), []
        for family, pending in self._pending.items():
            if pending and (
                force
                or (now - pending[0].queued_at) * 1000
                >= self.config.defaults.inference_batch_timeout_ms
            ):
                emitted.extend(self._flush_family(family))
        return emitted

    def process_frame(self, timestamp: float, frame: bytes, datalink: int = 1):
        if self.metrics._started is None:
            self.metrics.begin()
        sampled = self.mode is not ReplayMode.BENCHMARK or self.metrics.packet_count % 32 == 0
        started = perf_counter() if sampled else 0
        self.metrics.record_packet(len(frame), timestamp)
        packet, parse_status = self.parser.parse_with_status(timestamp, frame, datalink)
        if sampled:
            self.metrics.record_latency("parse", (perf_counter() - started) * 1000)
        if packet is None:
            self.metrics.skipped_frames += 1
            self.metrics.record_parse_failure(parse_status)
            return self.flush_due()
        if self._watermark is not None and packet.timestamp < self._watermark:
            self.metrics.out_of_order_packets += 1
            return self.flush_due()
        self._watermark = packet.timestamp
        self.metrics.parsed_packets += 1
        self.metrics.protocol_packets[packet.protocol.value] += 1
        started = perf_counter() if sampled else 0
        update = self.flows.process(packet, snapshot=False)
        if sampled:
            self.metrics.record_latency("flow", (perf_counter() - started) * 1000)
        self.metrics.record_flow_update(update.is_new_flow)
        started = perf_counter() if sampled else 0
        self.state.observe(packet, update)
        if sampled:
            self.metrics.record_latency("state", (perf_counter() - started) * 1000)
        self._last_packets[update.flow_id] = packet
        self._dirty[update.flow_id] = update.flow
        emitted = []
        for flow in update.expired:
            self.recent_flows.append(flow)
            emitted.extend(self._queue_flow(flow, packet.timestamp))
            self._forget(flow.flow_id)
        current_time = packet.timestamp.timestamp()
        if self._next_snapshot is None:
            self._next_snapshot = current_time + self.config.defaults.snapshot_interval_seconds
        if current_time >= self._next_snapshot:
            for flow_id, flow in list(self._dirty.items()):
                if flow.packet_count >= self.config.defaults.snapshot_min_packets:
                    emitted.extend(self._queue_flow(flow.snapshot(), packet.timestamp))
                    self._dirty.pop(flow_id, None)
            self._next_snapshot = current_time + self.config.defaults.snapshot_interval_seconds
        emitted.extend(self.flush_due())
        if self.metrics.packet_count % 64 == 0:
            self.metrics.sample_rates()
        return emitted

    def _forget(self, flow_id):
        self._dirty.pop(flow_id, None)
        self._last_packets.pop(flow_id, None)
        self._last_snapshot_counts.pop(flow_id, None)

    def finish(self) -> list:
        emitted = []
        for flow in self.flows.flush():
            self.recent_flows.append(flow)
            emitted.extend(self._queue_flow(flow, self._watermark or flow.last_seen))
            self._forget(flow.flow_id)
        emitted.extend(self.flush_due(force=True))
        self.metrics.finish()
        return emitted

    def run_controller(self, controller: ReplayController):
        self.mode = controller.mode
        self.metrics.telemetry_interval = (
            self.config.replay.benchmark_telemetry_interval_ms
            if self.mode is ReplayMode.BENCHMARK
            else self.config.replay.telemetry_interval_ms
        ) / 1000
        self.metrics.begin()
        idle_emitted = []

        def on_idle():
            idle_emitted.extend(self.flush_due())

        try:
            for frame in controller.frames(on_idle=on_idle):
                yield from idle_emitted
                idle_emitted.clear()
                yield from self.process_frame(frame.timestamp, frame.data, frame.datalink)
            yield from idle_emitted
            yield from self.finish()
        except Exception:
            self.metrics.finish()
            raise

    def replay(
        self,
        capture: str | Path,
        *,
        mode: ReplayMode | None = None,
        speed_multiplier: float | None = None,
    ):
        controller = ReplayController(
            CaptureReader(capture),
            mode=mode or self.config.replay.mode,
            speed_multiplier=speed_multiplier or self.config.replay.speed_multiplier,
        )
        yield from self.run_controller(controller)

    def reset(self) -> None:
        self.flows.reset()
        self.state.reset()
        self.dedupe.reset()
        self.alerts.clear()
        self.recent_flows.clear()
        self.host_timeline.clear()
        self.routing_diagnostics.clear()
        self._available_capabilities.clear()
        self.alert_revision += 1
        self._dirty.clear()
        self._last_packets.clear()
        self._last_snapshot_counts.clear()
        for pending in self._pending.values():
            pending.clear()
        self._next_snapshot = self._watermark = None
        self.metrics = MetricsCollector()
        self.capture_id = None
