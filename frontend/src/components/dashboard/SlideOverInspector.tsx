import React from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X, ShieldAlert, ShieldCheck, Terminal, Copy, Check, Ban, AlertTriangle } from "lucide-react";
import { useDashboard } from "../../context/DashboardTelemetryContext";
import { formatEndpoint, formatTime } from "../../runtime";

export function SlideOverInspector() {
  const { selectedAlert, setSelectedAlert } = useDashboard();
  const [copied, setCopied] = React.useState(false);

  if (!selectedAlert) return null;

  const isCritical = selectedAlert.decision === "ACCEPT" || selectedAlert.severity === "CRITICAL" || selectedAlert.severity === "HIGH";
  const isSuspicious = selectedAlert.decision === "UNKNOWN_SUSPICIOUS" || selectedAlert.severity === "MEDIUM";

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(selectedAlert, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Dialog.Root open={Boolean(selectedAlert)} onOpenChange={(open) => !open && setSelectedAlert(null)}>
      <Dialog.Portal>
        <Dialog.Overlay className="shad-sheet-overlay" />
        <Dialog.Content className="shad-sheet-content" aria-describedby="alert-description">
          {/* Header */}
          <div className="shad-sheet-header">
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <ShieldAlert size={20} className={isCritical ? "text-red-400" : "text-amber-400"} />
              <div>
                <Dialog.Title className="shad-sheet-title">
                  {selectedAlert.threat_class ? selectedAlert.threat_class.toUpperCase() : selectedAlert.detector_id || "Incident Analysis"}
                </Dialog.Title>
                <span style={{ fontSize: "0.72rem", color: "#71717a", fontFamily: "monospace" }}>
                  ID: {selectedAlert.alert_id}
                </span>
              </div>
            </div>

            <Dialog.Close asChild>
              <button className="shad-sheet-close" aria-label="Close panel">
                <X size={16} />
              </button>
            </Dialog.Close>
          </div>

          <div id="alert-description" style={{ display: "none" }}>
            Security incident detail inspection drawer for alert {selectedAlert.alert_id}
          </div>

          {/* Severity & Confidence Summary */}
          <div className="shad-sheet-well">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontSize: "0.75rem", color: "#a1a1aa", fontWeight: 500 }}>TRIAGE STATUS</span>
              {isCritical ? (
                <span className="shad-badge shad-badge--critical">
                  <span className="shad-badge__dot" />
                  CRITICAL / MALICIOUS
                </span>
              ) : isSuspicious ? (
                <span className="shad-badge shad-badge--warning">
                  <span className="shad-badge__dot" />
                  SUSPICIOUS BEHAVIOR
                </span>
              ) : (
                <span className="shad-badge shad-badge--clean">
                  <span className="shad-badge__dot" />
                  INSUFFICIENT EVIDENCE
                </span>
              )}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginTop: "8px" }}>
              <div>
                <span style={{ fontSize: "0.7rem", color: "#71717a" }}>CALIBRATED CONFIDENCE</span>
                <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#f4f4f5" }}>
                  {selectedAlert.calibrated_confidence != null ? `${Math.round(selectedAlert.calibrated_confidence * 100)}%` : "95%"}
                </div>
              </div>
              <div>
                <span style={{ fontSize: "0.7rem", color: "#71717a" }}>TIMESTAMP</span>
                <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "#f4f4f5", marginTop: "2px" }}>
                  {formatTime(selectedAlert.timestamp)}
                </div>
              </div>
            </div>
          </div>

          {/* Network Packet Correlation */}
          <div>
            <h3 style={{ fontSize: "0.8rem", fontWeight: 600, color: "#a1a1aa", marginBottom: "8px" }}>
              NETWORK FLOW CORRELATION
            </h3>
            <div className="shad-sheet-well">
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem" }}>
                <span style={{ color: "#71717a" }}>Source Endpoint:</span>
                <span style={{ fontFamily: "monospace", color: "#f4f4f5" }}>
                  {formatEndpoint(selectedAlert.source)}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem" }}>
                <span style={{ color: "#71717a" }}>Target Destination:</span>
                <span style={{ fontFamily: "monospace", color: "#f4f4f5" }}>
                  {formatEndpoint(selectedAlert.destination)}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem" }}>
                <span style={{ color: "#71717a" }}>Detector Engine:</span>
                <span style={{ color: "#8b5cf6", fontWeight: 600 }}>
                  {selectedAlert.detector_id || "StatisticalThresholdDetector"}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem" }}>
                <span style={{ color: "#71717a" }}>Evidence Quality:</span>
                <span style={{ color: "#f4f4f5", fontWeight: 600 }}>
                  {selectedAlert.evidence_quality || "STRONG"}
                </span>
              </div>
            </div>
          </div>

          {/* Raw Evidence / Payload */}
          <div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
              <h3 style={{ fontSize: "0.8rem", fontWeight: 600, color: "#a1a1aa" }}>
                EVIDENCE PAYLOAD (JSON)
              </h3>
              <button
                onClick={handleCopyJson}
                className="shad-btn shad-btn--ghost"
                style={{ fontSize: "0.7rem", padding: "2px 8px" }}
              >
                {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
            <pre
              style={{
                background: "#09090b",
                border: "1px solid var(--dash-border)",
                borderRadius: "6px",
                padding: "12px",
                fontSize: "0.72rem",
                color: "#e4e4e7",
                fontFamily: "monospace",
                overflowX: "auto",
                maxHeight: "220px",
              }}
            >
              {JSON.stringify(selectedAlert, null, 2)}
            </pre>
          </div>

          {/* Mitigation Actions */}
          <div style={{ marginTop: "auto", display: "flex", gap: "10px" }}>
            <button className="shad-btn shad-btn--danger" style={{ flex: 1 }}>
              <Ban size={14} />
              Block Source IP
            </button>
            <button
              onClick={() => setSelectedAlert(null)}
              className="shad-btn shad-btn--secondary"
              style={{ flex: 1 }}
            >
              Dismiss
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
