import { useMemo, useState } from "react";
import { formatDecimal, formatEndpoint, formatTime, formatNumber } from "../../runtime";
import type { AlertRecord } from "../../types";
import { StatusBadge } from "../Visuals";
import { AlertInspectorModal } from "./AlertInspectorModal";

interface AlertsPageProps {
  alerts: AlertRecord[];
  selectedAlert: AlertRecord | null;
  onSelectAlert: (alert: AlertRecord | null) => void;
  onChanged: () => Promise<void>;
}

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
          <span className="font-mono">DECISION</span>
          <select
            value={decision}
            onChange={(e) => setDecision(e.target.value)}
            className="dash-filter-select font-mono"
          >
            <option value="ALL">ALL DECISIONS</option>
            <option value="ACCEPT">ACCEPT</option>
            <option value="UNKNOWN_SUSPICIOUS">UNKNOWN SUSPICIOUS</option>
            <option value="INSUFFICIENT_EVIDENCE">INSUFFICIENT EVIDENCE</option>
          </select>
        </label>
        <label className="dash-filter-label">
          <span className="font-mono">LIFECYCLE</span>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="dash-filter-select font-mono"
          >
            <option value="ALL">ALL STATUS</option>
            <option value="open">OPEN</option>
            <option value="acknowledged">ACKNOWLEDGED</option>
            <option value="closed">CLOSED</option>
          </select>
        </label>
        <label className="dash-filter-label">
          <span className="font-mono">SORT ORDER</span>
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
        {/* Full alert table */}
        <section className="panel dash-alert-feed">
          <div className="panel__heading">
            <div>
              <div className="eyebrow">EVIDENCE-BACKED ALERT RECORDS</div>
              <h2>Alert feed</h2>
            </div>
            <span className="muted font-mono">{formatNumber(filtered.length)} visible</span>
          </div>
          {filtered.length === 0 ? (
            <div className="empty-state" style={{ padding: "36px 24px", textAlign: "center" }}>
              <strong style={{ color: "var(--text-primary)" }}>NO MATCHING ALERTS</strong>
              <p style={{ color: "var(--text-muted)", marginTop: "6px" }}>
                {alerts.length === 0
                  ? "No evidence-backed alert has been emitted. This does not prove the capture is safe."
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
                  {filtered.map((alert) => {
                    const toneClass =
                      alert.severity === "CRITICAL"
                        ? "row-icon-badge--pink"
                        : alert.severity === "HIGH"
                        ? "row-icon-badge--orange"
                        : alert.severity === "MEDIUM"
                        ? "row-icon-badge--purple"
                        : "row-icon-badge--teal";

                    return (
                      <tr
                        key={alert.alert_id}
                        data-decision={alert.decision}
                        className={selectedAlert?.alert_id === alert.alert_id ? "is-selected" : ""}
                        onClick={() => onSelectAlert(alert)}
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") onSelectAlert(alert);
                        }}
                      >
                        <td>
                          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                            <span className={`row-icon-badge ${toneClass}`}>
                              {alert.threat_class.charAt(0)}
                            </span>
                            <div>
                              <strong style={{ color: "var(--text-primary)", display: "block" }}>{alert.threat_class}</strong>
                              <span className="font-mono" style={{ color: "var(--text-muted)", fontSize: "0.72rem" }}>
                                {alert.alert_id.slice(0, 8)}
                              </span>
                            </div>
                          </div>
                        </td>
                        <td className="font-mono">
                          {formatTime(alert.emitted_at ?? alert.timestamp)}
                        </td>
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
                        <td>
                          <span className="tag-endpoint">{formatEndpoint(alert.source)}</span>
                        </td>
                        <td>
                          <span className="tag-endpoint">{formatEndpoint(alert.destination)}</span>
                        </td>
                        <td className="font-mono">
                          <strong style={{ color: "var(--accent-purple)" }}>
                            {formatDecimal(alert.calibrated_confidence * 100)}%
                          </strong>
                        </td>
                        <td>
                          <StatusBadge
                            label={alert.evidence_quality}
                            tone={alert.evidence_quality === "STRONG" ? "good" : "warning"}
                          />
                        </td>
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
                        <td className="font-mono">{alert.status.toUpperCase()}</td>
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
