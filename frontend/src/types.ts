export type Decision = "ACCEPT" | "UNKNOWN_SUSPICIOUS" | "INSUFFICIENT_EVIDENCE";

export interface Endpoint {
  ip: string;
  port?: number | null;
}

export interface AlertRecord {
  alert_id: string;
  capture_id?: string | null;
  source_type: string;
  timestamp: string;
  first_seen?: string | null;
  last_seen?: string | null;
  status: "open" | "acknowledged" | "closed";
  occurrence_count: number;
  flow_id?: string | null;
  window_id?: string | null;
  threat_class: string;
  severity: "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  decision: Decision;
  calibrated_confidence: number;
  threat_confidence?: number | null;
  observation_confidence?: number | null;
  observation_robustness?: number | null;
  observation_frame_id?: string | null;
  raw_score?: number | null;
  class_threshold?: number | null;
  emitted_at?: string | null;
  evidence_quality: "STRONG" | "ADEQUATE" | "WEAK" | "INSUFFICIENT";
  source?: Endpoint | null;
  destination?: Endpoint | null;
  evidence: Record<string, unknown>;
  missing_evidence: string[];
  available_evidence: string[];
  limitations: string[];
  capabilities?: Record<string, boolean> | null;
  detector_id: string;
  model_version: string;
  feature_schema_version: string;
  inference_latency_ms: number;
  total_pipeline_latency_ms: number;
}

export interface CaptureCandidate {
  display_name: string;
  size_bytes: number;
  capture_id?: string | null;
  status?: "queued" | "validating" | "ready" | "running" | "paused" | "completed" | "stopped" | "failed";
  sha256?: string | null;
}

export interface NumericStats {
  count: number;
  minimum?: number | null;
  maximum?: number | null;
  mean?: number | null;
  variance?: number | null;
}

export interface FlowRecord {
  flow_id: string;
  start_time: string;
  last_seen: string;
  endpoint_a: Endpoint;
  endpoint_b: Endpoint;
  protocol: string;
  ip_version: 4 | 6;
  initiator_direction: "a" | "b" | "unknown";
  close_reason?: "fin" | "rst" | "idle_timeout" | "active_timeout" | "capture_end" | "evicted" | null;
  packets_a_to_b: number;
  packets_b_to_a: number;
  bytes_a_to_b: number;
  bytes_b_to_a: number;
  packet_size_stats: NumericStats;
}

export interface Readiness {
  status: "ready" | "degraded" | "unavailable";
  passive_only: boolean;
  outbound_traffic_path: boolean;
  components: Record<string, unknown>;
}

export interface Diagnostics {
  routing: Array<{ family: string; decision: string; reason: string; missing_evidence: string[] }>;
  model_load_errors: Record<string, string>;
  inputs: Array<{ source_type: string; status: string; passive: boolean; opens_network_interface: boolean; reason: string | null }>;
}

export interface DetectorStatus {
  id: "behaviour" | "dns" | "tls_quic";
  enabled: boolean;
  reason: string | null;
  status: "READY" | "DEGRADED" | "UNAVAILABLE";
  model_version: string | null;
  schema_version: string;
  classes: string[];
  artifact_trusted: boolean;
  required_evidence: string[];
  available_evidence: string[];
  distribution_support: "available" | "unavailable";
}

export interface HostTimelinePoint {
  observed_at: string;
  host: string | null;
  peer: string | null;
  window_seconds: number | null;
  packet_count: number | null;
  byte_count: number | null;
  flow_count: number | null;
  unique_destinations: number | null;
  unique_destination_ports: number | null;
  outbound_bytes: number | null;
  inbound_bytes: number | null;
  alert_id: string | null;
  threat_class: string | null;
}

export interface RuntimeStatus {
  passive_monitor: boolean;
  return_path: string;
  replay_running: boolean;
  replay_paused: boolean;
  capture: string | null;
  active_flows: number;
  source_type: string;
  mode: string;
  speed_multiplier: number;
  replay_state: string;
  progress: number | null;
  rebuilding: boolean;
  rebuild_progress: number | null;
  progress_basis: string;
  checkpoint_origin_progress: number | null;
  error: string | null;
  run_id: number;
  telemetry_interval_ms: number;
}

export interface LatencyPercentiles {
  p50: number;
  p95: number;
}

export interface RuntimeMetrics {
  packets: number;
  flow_updates: number;
  flows: number;
  parsed_packets: number;
  skipped_frames: number;
  malformed_frames: number;
  unsupported_frames: number;
  truncated_frames: number;
  dropped_frames: number;
  feature_vectors: number;
  inference_vectors: number;
  inference_batches: number;
  evidence_decisions: number;
  decisions: Record<string, number>;
  bytes: number;
  alerts: number;
  cpu_percent: number;
  memory_bytes: number;
  latency_ms: Record<string, LatencyPercentiles | null>;
  processing_rates: { mbps: number; packets_per_second: number; flows_per_second: number };
  average_processing_rates: { mbps: number | null; packets_per_second: number | null; flows_per_second: number | null };
  elapsed_seconds: number;
  active_seconds: number;
  observed_average_mbps: number | null;
  sampled_at: number;
  rate_samples: Array<{ observed_at: number; bytes: number; packets: number; flows: number; flow_updates: number; mbps: number; packets_per_second: number; flows_per_second: number }>;
}

export interface TimelinePoint {
  observedAt: number;
  bytes: number;
  packets: number;
  flowUpdates: number;
  flows: number;
  featureVectors: number;
  inferenceVectors: number;
  evidenceDecisions: number;
  activeFlows: number;
  mbps: number;
  packetsPerSecond: number;
  flowsPerSecond: number;
  cpuPercent: number;
  memoryBytes: number;
  p50LatencyMs: number | null;
  p95LatencyMs: number | null;
}

export interface RuntimeSnapshot {
  status: RuntimeStatus | null;
  metrics: RuntimeMetrics | null;
  detectors: DetectorStatus[];
  alerts: AlertRecord[];
  history: TimelinePoint[];
  connected: boolean;
  error: string | null;
  captures: CaptureCandidate[];
  flows: FlowRecord[];
  hostTimeline: HostTimelinePoint[];
  readiness: Readiness | null;
  diagnostics: Diagnostics | null;
}

export interface TelemetryEnvelope {
  status: RuntimeStatus;
  metrics: RuntimeMetrics;
  detectors: DetectorStatus[];
}

export type Role = "Admin" | "Analyst" | "Auditor";

export interface User {
  user_id: string;
  username: string;
  display_name: string;
  role: Role;
  created_at: string;
}

export interface DemoCredential {
  username: string;
  display_name: string;
  role: Role;
  password: string;
}

