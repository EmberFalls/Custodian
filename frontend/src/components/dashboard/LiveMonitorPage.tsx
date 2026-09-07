import { useMemo, useState } from "react";
import { formatBytes, formatDecimal, formatNumber } from "../../runtime";
import type { useRuntimeTelemetry } from "../../hooks/useRuntimeTelemetry";
import type { AlertRecord, DetectorStatus } from "../../types";
import { InspectionPipeline, MetricCard, RadialGauge, RiskBar, StatusBadge, Timeline } from "../Visuals";
import { ReplayControl } from "../ReplayControl";
import { AlertInspectorModal } from "./AlertInspectorModal";
import { FirstRunGuidance } from "./FirstRunGuidance";
import { alertDecisionCounts, formatEndpoint, formatTime } from "../../runtime";

type TimelineMetric = "mbps" | "packets" | "flows";
type LiveDetail = "detectors" | "evidence" | null;

interface LiveMonitorPageProps {
  runtime: ReturnType<typeof useRuntimeTelemetry>;
  selectedAlert: AlertRecord | null;
  onSelectAlert: (alert: AlertRecord | null) => void;
}

export function LiveMonitorPage({ runtime, selectedAlert, onSelectAlert }: LiveMonitorPageProps) {
  const [timelineMetric, setTimelineMetric] = useState<TimelineMetric>("mbps");
  const [liveDetail, setLiveDetail] = useState<LiveDetail>(null);
  const history = runtime.history;
  const decisions = useMemo(
    () => runtime.metrics?.decisions ?? alertDecisionCounts(runtime.alerts),
    [runtime.metrics?.decisions, runtime.alerts],
  );
  const activeDetectors = runtime.detectors.filter((d) => d.enabled).length;
  const hasRunHistory = (runtime.metrics?.packets ?? 0) > 0 || runtime.status?.replay_state === "COMPLETED";
  const hasReadyCapture = runtime.captures.some(
    (c) => c.status === "ready" || c.status === "completed" || c.status === "stopped",
  );

  return (
    <div className="dash-page">
      {/* First-run guidance */}
      <FirstRunGuidance
        connected={runtime.connected}
        hasRunHistory={hasRunHistory}
        hasReadyCapture={hasReadyCapture}
      />

      {/* 1. Live ingest metric strip — Fortexa 6 stat tiles without emojis */}
      <section className="dash-metrics-strip" aria-label="Live ingest telemetry">
        <MetricCard
          label="DATA INSPECTED"
          value={formatBytes(runtime.metrics?.bytes ?? 0)}
          detail="Capture-frame bytes read locally"
          history={history.map((p) => p.bytes)}
          tone="purple"
        />
        <MetricCard
          label="PACKETS"
          value={formatNumber(runtime.metrics?.packets ?? 0)}
          detail={`${formatDecimal(runtime.metrics?.processing_rates.packets_per_second ?? 0)} pkt/s`}
          history={history.map((p) => p.packetsPerSecond)}
          tone="teal"
        />
        <MetricCard
          label="PACKET RATE"
          value={formatDecimal(runtime.metrics?.processing_rates.packets_per_second ?? 0)}
          unit="/ sec"
          detail="Frames processed per wall-clock second"
          history={history.map((p) => p.packetsPerSecond)}
          tone="magenta"
        />
        <MetricCard
          label="FLOWS ANALYSED"
          value={formatNumber(runtime.metrics?.flows ?? 0)}
          detail={`${formatNumber(runtime.status?.active_flows ?? 0)} currently active`}
          history={history.map((p) => p.flowsPerSecond)}
          tone="orange"
        />
        <MetricCard
          label="ACTIVE FLOWS"
          value={formatNumber(runtime.status?.active_flows ?? 0)}
          detail="Open bidirectional sessions"
          tone="gold"
        />
        <MetricCard
          label="THROUGHPUT"
          value={formatDecimal(
            runtime.status?.replay_running
              ? (runtime.metrics?.processing_rates.mbps ?? 0)
              : (runtime.metrics?.average_processing_rates.mbps ?? 0),
          )}
          unit="Mbps"
          detail={
            runtime.status?.replay_running
              ? "Current local processing rate"
              : "Last replay average (if available)"
          }
          history={history.map((p) => p.mbps)}
          tone="teal"
        />
      </section>

      {/* 2. Timeline + Pipeline side-by-side */}
      <section className="dash-monitor-grid">
        <Timeline
          history={history}
          metric={timelineMetric}
          onMetricChange={setTimelineMetric}
          alerts={runtime.alerts}
          onAlert={onSelectAlert}
        />
        <InspectionPipeline
          replayActive={Boolean(runtime.status?.replay_running && !runtime.status?.replay_paused)}
          detectors={runtime.detectors}
          metrics={runtime.metrics}
          onOpenDetails={setLiveDetail}
        />
      </section>

      {/* 3. Recent alerts — Fortexa styled table with avatars + risk bars */}
      <section className="dash-recent-alerts">
        <CompactAlertTable
          alerts={runtime.alerts}
          selected={selectedAlert}
          onSelect={onSelectAlert}
        />
      </section>

      {/* 4. Replay control center */}
      <ReplayControl
        status={runtime.status}
        captures={runtime.captures}
        onComplete={runtime.refresh}
      />

      {/* Drawers */}
      {liveDetail ? (
        <aside className="dash-drawer" role="dialog" aria-label="Detail drawer">
          <button
            className="dash-drawer__close font-mono"
            onClick={() => setLiveDetail(null)}
            aria-label="Close details"
          >
            [X]
          </button>
          {liveDetail === "detectors" ? (
            <DetectorSummaryCards detectors={runtime.detectors} activeDetectors={activeDetectors} />
          ) : (
            <EvidenceGateSummary decisions={decisions} alerts={runtime.alerts} activeDetectors={activeDetectors} />
          )}
        </aside>
      ) : null}

      {selectedAlert ? (
        <div className="dash-alert-drawer">
          <AlertInspectorModal
            alert={selectedAlert}
            onClose={() => onSelectAlert(null)}
            onChanged={runtime.refresh}
            isDrawer
          />
        </div>
      ) : null}
    </div>
  );
}

/* ---------- Compact Alert Table — Fortexa Style (Zero Emojis) ---------- */
function CompactAlertTable({
  alerts,
  selected,
  onSelect,
}: {
  alerts: AlertRecord[];
  selected: AlertRecord | null;
  onSelect: (alert: AlertRecord) => void;
}) {
  const visible = alerts.slice(-8);
  const avatarVariants = ["", "--teal", "--orange", "--green", "--purple"];

  return (
    <section className="panel dash-alert-feed">
      <div className="panel__heading">
        <div>
          <div className="eyebrow">THREAT INTELLIGENCE</div>
          <h2>Recent alerts</h2>
        </div>
        <span className="muted font-mono">{formatNumber(alerts.length)} records</span>
      </div>
      {alerts.length === 0 ? (
        <div className="empty-state" style={{ padding: "36px 24px", textAlign: "center" }}>
          <strong style={{ color: "var(--text-primary)", fontSize: ".9rem" }}>No evidence-backed alerts</strong>
          <p style={{ color: "var(--text-muted)", marginTop: "6px", fontSize: ".78rem" }}>
            No evidence-backed alert was emitted; this does not prove the capture is safe.
          </p>
        </div>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Entity</th>
                <th>Threat class</th>
                <th>Risk level</th>
                <th>Last activity</th>
                <th>Confidence</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((alert, idx) => {
                const avatarClass = `row-avatar${avatarVariants[idx % avatarVariants.length]}`;
                const initials = alert.threat_class.slice(0, 2).toUpperCase();
                const riskLevel: "high" | "medium" | "low" =
                  alert.severity === "CRITICAL" || alert.severity === "HIGH"
                    ? "high"
                    : alert.severity === "MEDIUM"
                    ? "medium"
                    : "low";
                const confidence = alert.calibrated_confidence * 100;

                return (
                  <tr
                    key={alert.alert_id}
                    data-decision={alert.decision}
                    className={selected?.alert_id === alert.alert_id ? "is-selected" : ""}
                    onClick={() => onSelect(alert)}
                    tabIndex={0}
                    onKeyDown={(e) => { if (e.key === "Enter") onSelect(alert); }}
                  >
                    {/* Entity — avatar + source IP */}
                    <td>
                      <div className="row-entity">
                        <div className={avatarClass}>{initials}</div>
                        <div className="row-entity__text">
                          <span className="row-entity__name font-mono">{formatEndpoint(alert.source)}</span>
                          <span className="row-entity__sub">→ {formatEndpoint(alert.destination)}</span>
                        </div>
                      </div>
                    </td>
                    {/* Threat class */}
                    <td>
                      <strong style={{ color: "var(--text-primary)", fontSize: ".82rem" }}>{alert.threat_class}</strong>
                      <span className="font-mono" style={{ color: "var(--text-muted)", fontSize: ".68rem", display: "block", marginTop: "1px" }}>
                        {alert.alert_id.slice(0, 8)}
                      </span>
                    </td>
                    {/* Risk bar */}
                    <td>
                      <RiskBar value={confidence} max={100} width={100} level={riskLevel} />
                    </td>
                    {/* Last activity */}
                    <td className="font-mono" style={{ fontSize: ".76rem" }}>
                      {formatTime(alert.emitted_at ?? alert.timestamp)}
                    </td>
                    {/* Confidence % */}
                    <td className="font-mono">
                      <strong style={{ color: riskLevel === "high" ? "var(--accent-magenta)" : "var(--accent-purple)" }}>
                        {formatDecimal(confidence)}%
                      </strong>
                    </td>
                    {/* Status badge */}
                    <td>
                      <StatusBadge
                        label={alert.status ?? "open"}
                        tone={
                          alert.status === "acknowledged"
                            ? "warning"
                            : alert.status === "closed"
                            ? "neutral"
                            : "good"
                        }
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

/* ---------- Detector Summary Cards (drawer) ---------- */
function DetectorSummaryCards({
  detectors,
  activeDetectors,
}: {
  detectors: DetectorStatus[];
  activeDetectors: number;
}) {
  const labels: Record<string, string> = { behaviour: "BEHAVIOUR", dns: "DNS", tls_quic: "TLS / QUIC" };
  return (
    <section className="panel detector-group">
      <div className="panel__heading">
        <div>
          <div className="eyebrow">MODEL RUNTIME</div>
          <h2>Detector families</h2>
        </div>
        <span className="muted font-mono">{activeDetectors} / 3 loaded</span>
      </div>
      <div className="detector-cards">
        {detectors.map((d) => (
          <article className="detector-card" key={d.id}>
            <div>
              <span className="eyebrow">{labels[d.id] ?? d.id} MODEL</span>
              <StatusBadge label={d.status} tone={d.enabled ? "good" : "neutral"} />
            </div>
            <strong>{d.model_version ?? "No approved artifact"}</strong>
            <p>
              {d.enabled
                ? `${d.schema_version} · ${d.classes.join(" · ")}`
                : d.reason ?? "No complete model artifact is available."}
            </p>
            <p>
              Artifact trust: {d.artifact_trusted ? "APPROVED" : "BLOCKED"}
              <br />
              Required evidence: {d.required_evidence.join(", ") || "TLS or QUIC metadata"}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}

/* ---------- Evidence Gate Summary (drawer) ---------- */
function EvidenceGateSummary({
  decisions,
  alerts,
  activeDetectors,
}: {
  decisions: Record<string, number>;
  alerts: AlertRecord[];
  activeDetectors: number;
}) {
  const latest = alerts.at(-1);
  const gaugeScore = latest ? latest.calibrated_confidence * 100 : (activeDetectors / 3) * 100;

  return (
    <section className="panel evidence-gate">
      <div className="panel__heading">
        <div>
          <div className="eyebrow">CAPABILITY-AWARE POLICY</div>
          <h2>Evidence gate</h2>
        </div>
        <StatusBadge label={alerts.length ? "EVALUATED" : "WAITING"} tone={alerts.length ? "good" : "neutral"} />
      </div>

      <div style={{ display: "flex", justifyContent: "center", margin: "16px 0" }}>
        <RadialGauge score={gaugeScore} label={latest ? "Calibrated Risk" : "Coverage"} size={120} />
      </div>

      <div className="gate-counts">
        <div className="key-value">
          <span>ACCEPTED</span>
          <strong>{formatNumber(decisions.ACCEPT ?? 0)}</strong>
        </div>
        <div className="key-value">
          <span>UNKNOWN</span>
          <strong>{formatNumber(decisions.UNKNOWN_SUSPICIOUS ?? 0)}</strong>
        </div>
        <div className="key-value">
          <span>INSUFFICIENT</span>
          <strong>{formatNumber(decisions.INSUFFICIENT_EVIDENCE ?? 0)}</strong>
        </div>
      </div>
      {latest ? (
        <div className="gate-latest">
          <strong>{latest.threat_class} candidate</strong>
          <span>{formatDecimal(latest.calibrated_confidence * 100)}% calibrated</span>
          <StatusBadge
            label={latest.decision.replaceAll("_", " ")}
            tone={latest.decision === "ACCEPT" ? "good" : "warning"}
          />
        </div>
      ) : (
        <p className="panel-note">
          No model candidate has reached the Evidence Gate. This is expected while real model
          artifacts are unavailable.
        </p>
      )}
    </section>
  );
}
