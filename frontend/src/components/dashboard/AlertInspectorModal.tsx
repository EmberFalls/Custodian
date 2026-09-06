import { useEffect, useRef, useState } from "react";
import { api, formatDecimal, formatEndpoint, formatTime } from "../../runtime";
import type { AlertRecord } from "../../types";
import { KeyValue, StatusBadge } from "../Visuals";

const capabilityLabels: Record<string, string> = {
  has_packet_timestamps: "Packet timing & inter-arrival",
  has_packet_sizes: "Packet length distribution",
  has_directionality: "Bidirectional flow direction",
  has_tcp_flags: "TCP flags & state transitions",
  has_dns_query_name: "DNS query name",
  has_dns_query_type: "DNS query record type",
  has_tls_metadata: "TLS handshake metadata",
  has_tls_fingerprint: "JA3/JA4 fingerprinting",
  has_quic_metadata: "QUIC frame metadata",
  has_bidirectional_stats: "Bidirectional packet statistics",
};

interface AlertInspectorProps {
  alert: AlertRecord | null;
  onClose: () => void;
  onChanged?: () => Promise<void>;
  isDrawer?: boolean;
}

export function AlertInspectorModal({ alert, onClose, onChanged, isDrawer = false }: AlertInspectorProps) {
  const [lifecycleMessage, setLifecycleMessage] = useState("");
  const [isUpdating, setIsUpdating] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    if (containerRef.current) {
      containerRef.current.focus();
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!alert) {
    return (
      <aside className={`inspector inspector--empty ${isDrawer ? "inspector--drawer" : ""}`}>
        <div className="eyebrow font-mono">ALERT FORENSICS</div>
        <h3>No Alert Selected</h3>
        <p>Only verified, evidence-backed AlertRecords appear here. Select a row from the alert feed or a marker on the timeline to inspect evidence provenance.</p>
      </aside>
    );
  }

  const evidenceEntries = Object.entries(alert.evidence ?? {});
  const capabilities = Object.entries(alert.capabilities ?? {});
  const thresholdPercent = alert.class_threshold != null ? alert.class_threshold * 100 : null;
  const confidencePercent = alert.calibrated_confidence * 100;

  const updateLifecycle = async (action: "acknowledge" | "close") => {
    setIsUpdating(true);
    try {
      await api(`/api/v1/alerts/${alert.alert_id}/${action}`, { method: "POST" });
      setLifecycleMessage(action === "acknowledge" ? "Alert acknowledged" : "Alert closed");
      await onChanged?.();
    } catch (error) {
      setLifecycleMessage(error instanceof Error ? error.message : "Alert update failed");
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <aside
      ref={containerRef}
      tabIndex={-1}
      className={`inspector ${isDrawer ? "inspector--drawer" : ""}`}
      aria-label="Selected alert forensics inspector"
    >
      {/* 1. Header with threat name, close button, and badges */}
      <div className="inspector__header">
        <div>
          <div className="eyebrow font-mono">STANDARDIZED ALERT RECORD</div>
          <h2 className="inspector__title">{alert.threat_class}</h2>
          <div className="inspector__id font-mono">ID: {alert.alert_id}</div>
        </div>
        <button
          className="btn-tactile-secondary icon-close-btn"
          onClick={onClose}
          aria-label="Close alert inspector"
          title="Close (Esc)"
        >
          ✕
        </button>
      </div>

      <div className="inspector__badges">
        <StatusBadge
          label={`SEVERITY: ${alert.severity}`}
          tone={alert.severity === "CRITICAL" ? "danger" : alert.severity === "HIGH" ? "warning" : "neutral"}
        />
        <StatusBadge
          label={`DECISION: ${alert.decision.replaceAll("_", " ")}`}
          tone={
            alert.decision === "ACCEPT"
              ? "good"
              : alert.decision === "UNKNOWN_SUSPICIOUS"
              ? "unknown"
              : "warning"
          }
        />
        <StatusBadge
          label={`LIFECYCLE: ${alert.status.toUpperCase()}`}
          tone={alert.status === "open" ? "warning" : "neutral"}
        />
        <StatusBadge
          label={`EVIDENCE: ${alert.evidence_quality}`}
          tone={alert.evidence_quality === "STRONG" ? "good" : "warning"}
        />
      </div>

      {/* 2. Plain-language summary */}
      <div className="inspector__summary-callout">
        <div className="inspector__summary-text">
          {alert.decision === "ACCEPT" ? (
            <>Candidate met configured confidence and observation capability criteria for <strong>{alert.threat_class}</strong>.</>
          ) : alert.decision === "UNKNOWN_SUSPICIOUS" ? (
            <>Anomalous traffic observed, but evidence does not support narrow classification into a known threat family.</>
          ) : (
            <>Candidate observed, but required telemetry was missing or insufficient to satisfy the Evidence Gate.</>
          )}
        </div>
      </div>

      {/* 3. Observed Endpoints and Timings */}
      <section className="inspector__section">
        <div className="inspector__sec-title font-mono">OBSERVED ENDPOINTS & DURATION</div>
        <div className="inspector__keyval-grid">
          <KeyValue label="SOURCE">{formatEndpoint(alert.source)}</KeyValue>
          <KeyValue label="DESTINATION">{formatEndpoint(alert.destination)}</KeyValue>
          <KeyValue label="FIRST OBSERVED">{formatTime(alert.first_seen ?? alert.timestamp)}</KeyValue>
          <KeyValue label="LAST OBSERVED">{formatTime(alert.last_seen ?? alert.timestamp)}</KeyValue>
          <KeyValue label="DEDUPLICATED OCCURRENCES">{alert.occurrence_count.toString()}</KeyValue>
          <KeyValue label="SOURCE TYPE">{alert.source_type?.toUpperCase() ?? "PCAP REPLAY"}</KeyValue>
        </div>
      </section>

      {/* 4. Confidence & Acceptance Threshold */}
      <section className="inspector__section">
        <div className="inspector__sec-title font-mono">CALIBRATED CONFIDENCE VS THRESHOLD</div>
        <div className="confidence-meter-container">
          <div className="confidence-meter-labels font-mono">
            <span>Calibrated: <strong>{formatDecimal(confidencePercent, 1)}%</strong></span>
            {thresholdPercent != null ? (
              <span>Threshold: <strong>{formatDecimal(thresholdPercent, 1)}%</strong></span>
            ) : (
              <span>Threshold: <em>Not defined</em></span>
            )}
          </div>
          <div className="confidence-scale" aria-label="Calibrated confidence vs acceptance threshold">
            <span
              style={{
                width: `${Math.min(100, Math.max(0, confidencePercent))}%`,
                background: alert.decision === "ACCEPT" ? "var(--landing-emerald)" : alert.decision === "UNKNOWN_SUSPICIOUS" ? "var(--landing-purple)" : "var(--landing-amber)",
              }}
            />
            {thresholdPercent != null ? (
              <div
                className="confidence-threshold-marker"
                style={{ left: `${Math.min(100, Math.max(0, thresholdPercent))}%` }}
                title={`Acceptance threshold: ${thresholdPercent.toFixed(1)}%`}
              >
                <div className="confidence-threshold-label font-mono">THR</div>
              </div>
            ) : null}
          </div>
        </div>

        <div className="inspector__keyval-grid">
          <KeyValue label="RAW MODEL SCORE">
            {alert.raw_score != null ? `${formatDecimal(alert.raw_score * 100, 1)}%` : "Unavailable"}
          </KeyValue>
          <KeyValue label="THREAT CONFIDENCE">
            {alert.threat_confidence != null ? `${formatDecimal(alert.threat_confidence * 100, 1)}%` : `${formatDecimal(confidencePercent, 1)}%`}
          </KeyValue>
          <KeyValue label="OBSERVATION CONFIDENCE">
            {alert.observation_confidence != null ? `${formatDecimal(alert.observation_confidence * 100, 1)}%` : "Unavailable"}
          </KeyValue>
          <KeyValue label="DETECTOR ID">{alert.detector_id}</KeyValue>
        </div>
      </section>

      {/* 5. Evidence Gate & Limitations */}
      <section className="inspector__section">
        <div className="inspector__sec-title font-mono">EVIDENCE GATE EVALUATION</div>
        <div className="inspector__keyval-grid">
          <KeyValue label="EVIDENCE QUALITY">{alert.evidence_quality}</KeyValue>
          <KeyValue label="GATE DECISION">{alert.decision}</KeyValue>
        </div>

        {alert.missing_evidence && alert.missing_evidence.length > 0 ? (
          <div className="inspector__missing-evidence">
            <span className="font-mono">MISSING REQUIRED EVIDENCE:</span>
            <ul>
              {alert.missing_evidence.map((item) => (
                <li key={item} className="font-mono">{item}</li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="inspector__evidence-ok font-mono">✓ No required evidence was reported missing.</div>
        )}

        {alert.limitations && alert.limitations.length > 0 ? (
          <div className="inspector__limitations">
            <span className="font-mono">RECORD LIMITATIONS:</span>
            <p>{alert.limitations.join("; ")}</p>
          </div>
        ) : null}
      </section>

      {/* 6. Why this was flagged */}
      <section className="inspector__section">
        <div className="inspector__sec-title font-mono">OBSERVED EVIDENCE METRICS ("WHY FLAGGED")</div>
        {evidenceEntries.length > 0 ? (
          <ul className="evidence-list font-mono">
            {evidenceEntries.map(([key, value]) => (
              <li key={key}>
                <span className="evidence-key">{key.replaceAll("_", " ")}</span>
                <strong className="evidence-val">{typeof value === "object" ? JSON.stringify(value) : String(value)}</strong>
              </li>
            ))}
          </ul>
        ) : (
          <p className="inspector__empty-p">No specific evidence properties were serialized with this record.</p>
        )}
      </section>

      {/* 7. Observation capabilities */}
      <section className="inspector__section">
        <div className="inspector__sec-title font-mono">OBSERVATION CAPABILITY PROFILE</div>
        {capabilities.length > 0 ? (
          <ul className="capability-list font-mono">
            {capabilities.map(([key, available]) => (
              <li key={key}>
                <span>{capabilityLabels[key] ?? key.replaceAll("_", " ")}</span>
                <StatusBadge label={available ? "OBSERVABLE" : "ABSENT"} tone={available ? "good" : "neutral"} />
              </li>
            ))}
          </ul>
        ) : (
          <p className="inspector__empty-p">Capability profile was not provided with this alert.</p>
        )}
      </section>

      {/* 8. Model / Schema / Latency Metadata */}
      <section className="inspector__section">
        <div className="inspector__sec-title font-mono">PROVENANCE & ENGINE LATENCY</div>
        <div className="inspector__keyval-grid">
          <KeyValue label="MODEL VERSION">{alert.model_version || "Untrained / Heuristic"}</KeyValue>
          <KeyValue label="FEATURE SCHEMA">{alert.feature_schema_version || "v1.0"}</KeyValue>
          <KeyValue label="INFERENCE LATENCY">{alert.inference_latency_ms != null ? `${formatDecimal(alert.inference_latency_ms, 2)} ms` : "—"}</KeyValue>
          <KeyValue label="TOTAL PIPELINE LATENCY">{alert.total_pipeline_latency_ms != null ? `${formatDecimal(alert.total_pipeline_latency_ms, 2)} ms` : "—"}</KeyValue>
        </div>
      </section>

      {/* 9. Lifecycle Actions */}
      <div className="inspector__actions">
        {alert.status === "open" ? (
          <button
            className="btn-tactile-primary font-mono"
            onClick={() => updateLifecycle("acknowledge")}
            disabled={isUpdating}
          >
            Acknowledge Alert
          </button>
        ) : null}
        {alert.status !== "closed" ? (
          <button
            className="btn-tactile-secondary font-mono"
            onClick={() => updateLifecycle("close")}
            disabled={isUpdating}
          >
            Close Alert
          </button>
        ) : null}
        {lifecycleMessage ? (
          <span className="inspector__lifecycle-msg font-mono" role="status">
            {lifecycleMessage}
          </span>
        ) : null}
      </div>

      {/* 10. Collapsed Raw JSON */}
      <details className="inspector__raw-json">
        <summary className="font-mono">▶ View Raw Structured AlertRecord JSON</summary>
        <pre className="font-mono">{JSON.stringify(alert, null, 2)}</pre>
      </details>
    </aside>
  );
}
