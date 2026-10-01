import React from "react";
import { IncidentsTable } from "./IncidentsTable";
import { SlideOverInspector } from "./SlideOverInspector";
import { ShieldAlert, Info } from "lucide-react";
import { useDashboard } from "../../context/DashboardTelemetryContext";

export function AlertsPage() {
  const { kpis } = useDashboard();

  return (
    <div className="shad-content-container">
      {/* Alert Header Banner */}
      <div className="shad-card" style={{ padding: "16px 20px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <ShieldAlert size={20} className={kpis.criticalAlertsCount > 0 ? "text-red-400" : "text-emerald-400"} />
            <div>
              <h2 style={{ fontSize: "0.95rem", fontWeight: 700, color: "#f4f4f5" }}>
                Security Triage & Heuristic Attack Detection
              </h2>
              <span style={{ fontSize: "0.75rem", color: "#71717a" }}>
                All alerts correlated against MITRE ATT&CK network vectors and local statistical baselines.
              </span>
            </div>
          </div>

          <span
            className={`shad-badge ${kpis.criticalAlertsCount > 0 ? "shad-badge--critical" : "shad-badge--clean"}`}
          >
            <span className="shad-badge__dot" />
            {kpis.criticalAlertsCount} Critical Incidents Active
          </span>
        </div>
      </div>

      {/* Main Incidents Table */}
      <IncidentsTable />

      {/* Slide-over inspector */}
      <SlideOverInspector />
    </div>
  );
}
