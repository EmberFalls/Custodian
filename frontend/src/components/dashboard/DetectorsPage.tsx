import React from "react";
import { Cpu, CheckCircle2, XCircle, ShieldCheck, Database } from "lucide-react";
import { useDashboard } from "../../context/DashboardTelemetryContext";

const detectorLabels: Record<string, string> = {
  behaviour: "Behavioral Heuristics",
  dns: "DNS Tunneling",
  dns_dga: "DNS DGA Classifier",
  tls_quic: "TLS / QUIC Metadata",
};

export function DetectorsPage() {
  const { runtime } = useDashboard();
  const detectors = runtime.detectors || [];
  const activeDetectors = detectors.filter((d) => d.enabled).length;

  return (
    <div className="shad-content-container">
      {/* Header Summary */}
      <div className="shad-card" style={{ padding: "16px 20px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "10px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Cpu size={20} className="text-zinc-100" />
            <div>
              <h2 style={{ fontSize: "0.95rem", fontWeight: 700, color: "#f4f4f5" }}>
                Active Machine Learning & Heuristic Detectors
              </h2>
              <span style={{ fontSize: "0.75rem", color: "#71717a" }}>
                Multi-model inference engine executing local statistical threat classification.
              </span>
            </div>
          </div>

          <span className="shad-badge shad-badge--clean">
            <span className="shad-badge__dot" />
            {activeDetectors} / {detectors.length} Detectors Armed
          </span>
        </div>
      </div>

      {/* Detector Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "16px" }}>
        {detectors.map((d) => (
          <article key={d.id} className="shad-card">
            <div className="shad-card__header">
              <span className="shad-card__title">{detectorLabels[d.id] ?? d.id.toUpperCase()}</span>
              {d.enabled ? (
                <span className="shad-badge shad-badge--clean">
                  <CheckCircle2 size={12} />
                  ACTIVE
                </span>
              ) : (
                <span className="shad-badge shad-badge--warning">
                  <XCircle size={12} />
                  DISABLED
                </span>
              )}
            </div>

            <div style={{ fontSize: "1.05rem", fontWeight: 700, color: "#f4f4f5" }}>
              {d.model_version ?? "Rule-based Engine"}
            </div>

            <p style={{ fontSize: "0.75rem", color: "#a1a1aa", margin: "4px 0 10px" }}>
              {d.enabled
                ? `Schema: ${d.schema_version} · Classes: ${d.classes.join(", ")}`
                : d.reason ?? "Model artifact not configured."}
            </p>

            <div className="shad-sheet-well" style={{ fontSize: "0.72rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "#71717a" }}>Artifact Trust:</span>
                <span style={{ color: d.artifact_trusted ? "#10b981" : "#ef4444", fontWeight: 600 }}>
                  {d.artifact_trusted ? "VERIFIED (LOCAL)" : "UNTRUSTED"}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "#71717a" }}>Distribution Support:</span>
                <span style={{ color: "#f4f4f5", fontFamily: "monospace" }}>{d.distribution_support}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "#71717a" }}>Required Inputs:</span>
                <span style={{ color: "#a1a1aa" }}>{d.required_evidence.join(", ") || "Raw frames"}</span>
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
