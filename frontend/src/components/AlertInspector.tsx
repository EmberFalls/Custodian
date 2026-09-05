import { useState } from "react";

import { api, formatDecimal, formatEndpoint, formatTime } from "../runtime";
import type { AlertRecord } from "../types";
import { KeyValue, StatusBadge } from "./Visuals";

const capabilityLabels: Record<string, string> = {
  has_packet_timestamps: "Packet timing",
  has_packet_sizes: "Packet sizes",
  has_directionality: "Directionality",
  has_tcp_flags: "TCP flags",
  has_dns_query_name: "DNS query name",
  has_dns_query_type: "DNS query type",
  has_tls_metadata: "TLS metadata",
  has_tls_fingerprint: "TLS fingerprint",
  has_quic_metadata: "QUIC metadata",
  has_bidirectional_stats: "Bidirectional stats",
};

export function AlertInspector({ alert, onClose, onChanged }: { alert: AlertRecord | null; onClose: () => void; onChanged?: () => Promise<void> }) {
  const [lifecycleMessage, setLifecycleMessage] = useState("");
  if (!alert) return <aside className="inspector inspector--empty"><div className="eyebrow">ALERT INSPECTOR</div><h2>No alert selected</h2><p>Only real evidence-backed AlertRecords appear here. The current replay has not produced a selected record.</p></aside>;
  const evidenceEntries = Object.entries(alert.evidence);
  const capabilities = Object.entries(alert.capabilities ?? {});
  return <aside className="inspector" aria-label="Selected alert inspector">
    <div className="inspector__heading"><div><div className="eyebrow">ALERT INSPECTOR</div><h2>{alert.threat_class}</h2></div><button className="icon-button" onClick={onClose} aria-label="Close alert inspector">×</button></div>
    <div className="inspector__badges"><StatusBadge label={alert.severity} tone={alert.severity === "CRITICAL" ? "danger" : alert.severity === "HIGH" ? "warning" : "neutral"} /><StatusBadge label={alert.decision.replaceAll("_", " ")} tone={alert.decision === "ACCEPT" ? "good" : alert.decision === "UNKNOWN_SUSPICIOUS" ? "unknown" : "warning"} /><StatusBadge label={alert.status.toUpperCase()} tone={alert.status === "open" ? "warning" : "neutral"} /></div>
    <section><h3>Summary</h3><KeyValue label="First seen">{formatTime(alert.first_seen ?? alert.timestamp)}</KeyValue><KeyValue label="Last seen">{formatTime(alert.last_seen ?? alert.timestamp)}</KeyValue><KeyValue label="Occurrences">{alert.occurrence_count}</KeyValue><KeyValue label="Source">{formatEndpoint(alert.source)}</KeyValue><KeyValue label="Destination">{formatEndpoint(alert.destination)}</KeyValue></section>
    <section><h3>Model decision</h3><KeyValue label="Detector">{alert.detector_id}</KeyValue><KeyValue label="Threat confidence">{formatDecimal((alert.threat_confidence ?? alert.calibrated_confidence) * 100)}%</KeyValue><KeyValue label="Observation confidence">{alert.observation_confidence != null ? `${formatDecimal(alert.observation_confidence * 100)}%` : "Unavailable"}</KeyValue>
      <div className="confidence-scale" aria-label="Calibrated confidence and acceptance threshold"><span style={{ width: `${alert.calibrated_confidence * 100}%` }} />{alert.class_threshold != null ? <i style={{ left: `${alert.class_threshold * 100}%` }} /> : null}</div>
      <KeyValue label="Raw model score">{alert.raw_score != null ? `${formatDecimal(alert.raw_score * 100)}%` : "Unavailable"}</KeyValue>
      <KeyValue label="Acceptance threshold">{alert.class_threshold != null ? `${formatDecimal(alert.class_threshold * 100)}%` : "Unavailable"}</KeyValue>
      <KeyValue label="Model">{alert.model_version}</KeyValue><KeyValue label="Feature schema">{alert.feature_schema_version}</KeyValue></section>
    <section><h3>Evidence gate</h3><KeyValue label="Evidence quality">{alert.evidence_quality}</KeyValue><KeyValue label="Decision">{alert.decision}</KeyValue>{alert.missing_evidence.length > 0 ? <KeyValue label="Missing evidence">{alert.missing_evidence.join(", ")}</KeyValue> : <KeyValue label="Missing evidence">None reported</KeyValue>}<KeyValue label="Limitations">{alert.limitations.length ? alert.limitations.join("; ") : "None reported"}</KeyValue></section>
    <section><h3>Why this was flagged</h3>{evidenceEntries.length ? <ul className="evidence-list">{evidenceEntries.map(([key, value]) => <li key={key}><span>{key.replaceAll("_", " ")}</span><strong>{String(value)}</strong></li>)}</ul> : <p>No evidence fields were supplied with this record.</p>}</section>
    <section><h3>Observation capabilities</h3>{capabilities.length ? <ul className="capability-list">{capabilities.map(([key, available]) => <li key={key}><span>{capabilityLabels[key] ?? key}</span><StatusBadge label={available ? "AVAILABLE" : "UNAVAILABLE"} tone={available ? "good" : "neutral"} /></li>)}</ul> : <p>Capability profile was not included with this alert.</p>}</section>
    <div className="control-row alert-actions">{alert.status === "open" ? <button className="button" onClick={() => void updateLifecycle(alert.alert_id, "acknowledge", setLifecycleMessage, onChanged)}>Acknowledge alert</button> : null}{alert.status !== "closed" ? <button className="button button--quiet" onClick={() => void updateLifecycle(alert.alert_id, "close", setLifecycleMessage, onChanged)}>Close alert</button> : null}</div><p className="control-message" role="status">{lifecycleMessage}</p>
    <details><summary>Raw alert JSON</summary><pre>{JSON.stringify(alert, null, 2)}</pre></details>
  </aside>;
}

async function updateLifecycle(alertId: string, action: "acknowledge" | "close", setMessage: (message: string) => void, onChanged?: () => Promise<void>) {
  try {
    await api(`/api/v1/alerts/${alertId}/${action}`, { method: "POST" });
    setMessage(action === "acknowledge" ? "Alert acknowledged" : "Alert closed");
    await onChanged?.();
  } catch (error) {
    setMessage(error instanceof Error ? error.message : "Alert update failed");
  }
}
