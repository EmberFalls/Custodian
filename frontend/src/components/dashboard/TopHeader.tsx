import React from "react";
import { HardDrive, RefreshCw, Radio, Shield, AlertTriangle } from "lucide-react";
import { useDashboard } from "../../context/DashboardTelemetryContext";

export function TopHeader() {
  const { activeTab, kpis, runtime } = useDashboard();

  const tabTitles: Record<string, { title: string; subtitle: string }> = {
    monitor: {
      title: "Live Threat Monitor",
      subtitle: "Real-time network packet ingestion & heuristic security pipeline",
    },
    alerts: {
      title: "Security Incident Queue",
      subtitle: "Triage, evidence correlation, and automated attack classification",
    },
    traffic: {
      title: "Network Flow Telemetry",
      subtitle: "Bidirectional active session rates and protocol bandwidth",
    },
    detectors: {
      title: "Active Attack Detectors",
      subtitle: "Heuristic classification models & rule execution state",
    },
    performance: {
      title: "Engine Performance & Latency",
      subtitle: "Pipeline throughput, ring buffers, and wall-clock execution lag",
    },
  };

  const current = tabTitles[activeTab] || tabTitles.monitor;

  return (
    <header className="shad-top-header">
      <div className="shad-top-header__left">
        <div>
          <h1 className="shad-top-header__title">{current.title}</h1>
        </div>
      </div>

      <div className="shad-top-header__status-strip">
        {/* Connection State */}
        <div className="shad-top-header__status-item">
          <Radio size={13} className={kpis.connected ? "text-emerald-400" : "text-red-400"} />
          <span>STATUS:</span>
          <span className="shad-top-header__status-val">
            {kpis.connected ? (kpis.isReplaying ? "INGESTING" : "IDLE / READY") : "OFFLINE"}
          </span>
        </div>

        {/* Source State */}
        <div className="shad-top-header__status-item">
          <HardDrive size={13} />
          <span>SOURCE:</span>
          <span className="shad-top-header__status-val">
            {runtime.status?.source_type ? runtime.status.source_type.toUpperCase() : "PCAP REPLAY"}
          </span>
        </div>

        {/* Replay State Badge */}
        {kpis.threatLevel === "CRITICAL" ? (
          <span className="shad-badge shad-badge--critical">
            <span className="shad-badge__dot" />
            {kpis.criticalAlertsCount} Critical Attacks Active
          </span>
        ) : (
          <span className="shad-badge shad-badge--clean">
            <span className="shad-badge__dot" />
            Normal Operation
          </span>
        )}

        {/* Refresh button */}
        <button
          onClick={() => runtime.refresh()}
          className="shad-btn shad-btn--ghost"
          style={{ padding: "6px" }}
          title="Refresh Telemetry"
          aria-label="Refresh Telemetry"
        >
          <RefreshCw size={14} />
        </button>
      </div>
    </header>
  );
}
