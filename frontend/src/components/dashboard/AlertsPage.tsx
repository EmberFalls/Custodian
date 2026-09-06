import { useMemo, useState } from "react";
import { formatDecimal, formatEndpoint, formatTime, formatNumber } from "../../runtime";
import type { AlertRecord } from "../../types";
import { RiskBar, StatusBadge } from "../Visuals";
import { AlertInspectorModal } from "./AlertInspectorModal";

interface AlertsPageProps {
  alerts: AlertRecord[];
  selectedAlert: AlertRecord | null;
  onSelectAlert: (alert: AlertRecord | null) => void;
  onChanged: () => Promise<void>;
}

const AVATAR_COLORS = [
  "row-avatar",
  "row-avatar--teal",
  "row-avatar--orange",
  "row-avatar--green",
  "row-avatar--purple",
];

export function AlertsPage({ alerts, selectedAlert, onSelectAlert, onChanged }: AlertsPageProps) {
  const [decision, setDecision] = useState("ALL");
  const [status, setStatus] = useState("ALL");
  const [sort, setSort] = useState("newest");

  const filtered = useMemo(
    () =>
      [...alerts]
        .filter((a) => decision === "ALL" || a.decision === decision)
        .filter((a) => status === "ALL" || a.status === status)
        .sort((a, b) =>
          sort === "confidence"
            ? b.calibrated_confidence - a.calibrated_confidence
            : sort === "oldest"
            ? new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
            : new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
        ),
    [alerts, decision, sort, status],
  );

  return (
    <div className="dash-page">
      {/* Filter bar */}
      <section className="dash-alert-filters" aria-label="Alert filters">
        <label className="dash-filter-label">
          <span>DECISION</span>
          <select
            value={decision}
            onChange={(e) => setDecision(e.target.value)}
            className="dash-filter-select font-mono"
          >
            <option value="ALL">All decisions</option>
            <option value="ACCEPT">Accept</option>
            <option value="UNKNOWN_SUSPICIOUS">Unknown suspicious</option>
            <option value="INSUFFICIENT_EVIDENCE">Insufficient evidence</option>
          </select>
        </label>
        <label className="dash-filter-label">
          <span>LIFECYCLE</span>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="dash-filter-select font-mono"
          >
            <option value="ALL">All status</option>
            <option value="open">Open</option>
            <option value="acknowledged">Acknowledged</option>
            <option value="closed">Closed</option>
          </select>
        </label>
        <label className="dash-filter-label">
          <span>SORT ORDER</span>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            className="dash-filter-select font-mono"
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
            <option value="confidence">Highest confidence</option>
          </select>
        </label>
        <div className="dash-filter-count font-mono">
          {formatNumber(filtered.length)} of {formatNumber(alerts.length)} records
        </div>
      </section>

      {/* Table + Inspector */}
      <div className="dash-alerts-layout">
        {/* Full alert table — Fortexa style */}
        <section className="panel dash-alert-feed">
          <div className="panel__heading">
            <div>
              <div className="eyebrow">EVIDENCE-BACKED ALERT RECORDS</div>
              <h2>Alert feed</h2>
            </div>
            <span className="muted font-mono">{formatNumber(filtered.length)} visible</span>
          </div>
          {filtered.length === 0 ? (
            <div className="empty-state" style={{ padding: "40px 24px", textAlign: "center" }}>
              <strong style={{ color: "var(--text-primary)", fontSize: ".9rem" }}>
                {alerts.length === 0 ? "No evidence-backed alerts" : "No matching alerts"}
              </strong>
              <p style={{ color: "var(--text-muted)", marginTop: "8px", fontSize: ".78rem", lineHeight: 1.6 }}>
                {alerts.length === 0
                  ? "No evidence-backed alert was emitted; this does not prove the capture is safe."
                  : "No alerts match the current filter criteria. Adjust filters to see available records."}
              </p>
            </div>
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Threat & ID</th>
                    <th>Time</th>
                    <th>Severity</th>
                    <th>Source</th>
                    <th>Destination</th>
                    <th>Confidence</th>
                    <th>Evidence</th>
                    <th>Decision</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((alert, idx) => {
                    const avatarClass = AVATAR_COLORS[idx % AVATAR_COLORS.length];
                    const initials = alert.threat_class.slice(0, 2).toUpperCase();
                    const confidence = alert.calibrated_confidence * 100;
                    const riskLevel: "high" | "medium" | "low" =
                      alert.severity === "CRITICAL" || alert.severity === "HIGH"
                        ? "high"
                        : alert.severity === "MEDIUM"
                        ? "medium"
                        : "low";

                    return (
                      <tr
                        key={alert.alert_id}
                        data-decision={alert.decision}
                        className={selectedAlert?.alert_id === alert.alert_id ? "is-selected" : ""}
                        onClick={() => onSelectAlert(alert)}
                        tabIndex={0}
                        onKeyDown={(e) => { if (e.key === "Enter") onSelectAlert(alert); }}
                      >
                        {/* Threat & ID with avatar */}
                        <td>
                          <div className="row-entity">
                            <div className={avatarClass}>{initials}</div>
                            <div className="row-entity__text">
                              <strong className="row-entity__name">{alert.threat_class}</strong>
                              <span className="row-entity__sub font-mono">{alert.alert_id.slice(0, 8)}</span>
                            </div>
                          </div>
                        </td>
                        {/* Time */}
                        <td className="font-mono" style={{ fontSize: ".76rem" }}>
                          {formatTime(alert.emitted_at ?? alert.timestamp)}
                        </td>
                        {/* Severity */}
                        <td>
                          <StatusBadge
                            label={alert.severity}
                            tone={
                              alert.severity === "CRITICAL"
                                ? "danger"
                                : alert.severity === "HIGH"
                                ? "warning"
                                : "neutral"
                            }
                          />
                        </td>
                        {/* Source */}
                        <td>
                          <span className="tag-endpoint font-mono">{formatEndpoint(alert.source)}</span>
                        </td>
                        {/* Destination */}
                        <td>
                          <span className="tag-endpoint font-mono">{formatEndpoint(alert.destination)}</span>
                        </td>
                        {/* Confidence with RiskBar */}
                        <td>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <RiskBar value={confidence} max={100} width={75} level={riskLevel} />
                            <span className="font-mono" style={{ fontSize: ".72rem", color: riskLevel === "high" ? "var(--accent-magenta)" : "var(--accent-purple)", fontWeight: 700 }}>
                              {formatDecimal(confidence)}%
                            </span>
                          </div>
                        </td>
                        {/* Evidence Quality */}
                        <td>
                          <StatusBadge
                            label={alert.evidence_quality}
                            tone={alert.evidence_quality === "STRONG" ? "good" : "warning"}
                          />
                        </td>
                        {/* Decision */}
                        <td>
                          <StatusBadge
                            label={alert.decision.replaceAll("_", " ")}
                            tone={
                              alert.decision === "ACCEPT"
                                ? "good"
                                : alert.decision === "UNKNOWN_SUSPICIOUS"
                                ? "unknown"
                                : "warning"
                            }
                          />
                        </td>
                        {/* Status */}
                        <td>
                          <StatusBadge
                            label={alert.status.toUpperCase()}
                            tone={
                              alert.status === "open"
                                ? "good"
                                : alert.status === "acknowledged"
                                ? "warning"
                                : "neutral"
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

        {/* Side Inspector */}
        <AlertInspectorModal
          alert={selectedAlert}
          onClose={() => onSelectAlert(null)}
          onChanged={onChanged}
        />
      </div>
    </div>
  );
}
