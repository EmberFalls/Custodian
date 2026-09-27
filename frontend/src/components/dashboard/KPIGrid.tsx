import React from "react";
import { ShieldAlert, Activity, ArrowUpRight, ArrowDownRight, Layers, Zap } from "lucide-react";
import { useDashboard } from "../../context/DashboardTelemetryContext";
import { formatBytes, formatDecimal, formatNumber } from "../../runtime";
import { useCountUp } from "../../hooks/useCountUp";

export function KPIGrid() {
  const { kpis } = useDashboard();
  const animatedFlows = useCountUp(kpis.activeFlows, 600, kpis.connected);
  const animatedPackets = useCountUp(kpis.totalPackets, 700, kpis.connected);

  // Loading skeleton state
  if (!kpis.connected && !kpis.error) {
    return (
      <div className="shad-kpi-grid">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="shad-card shad-skeleton" style={{ height: "130px" }} />
        ))}
      </div>
    );
  }

  return (
    <section className="shad-kpi-grid" aria-label="Key Performance Indicators">
      {/* 1. Threat Severity */}
      <article className="shad-card anim-fade-up is-visible" style={{ transitionDelay: "0ms" }}>
        <div className="shad-card__header">
          <span className="shad-card__title">THREAT SEVERITY</span>
          {kpis.criticalAlertsCount > 0 ? (
            <span className="shad-trend shad-trend--up">
              <ArrowUpRight size={12} />
              +{kpis.criticalAlertsCount} Critical
            </span>
          ) : (
            <span className="shad-trend shad-trend--down">
              <ArrowDownRight size={12} />
              0 Attacks
            </span>
          )}
        </div>
        <div className="shad-card__value">
          {kpis.criticalAlertsCount > 0
            ? `${kpis.criticalAlertsCount} Alert${kpis.criticalAlertsCount > 1 ? "s" : ""}`
            : "Protected"}
        </div>
        <div className="shad-card__detail">
          <ShieldAlert size={13} className="text-zinc-400" />
          <span>
            {kpis.totalAlertsCount > 0
              ? `${kpis.totalAlertsCount} total heuristics triggered`
              : "No active threat signatures"}
          </span>
        </div>
      </article>

      {/* 2. Active Flows */}
      <article className="shad-card anim-fade-up is-visible" style={{ transitionDelay: "60ms" }}>
        <div className="shad-card__header">
          <span className="shad-card__title">ACTIVE FLOWS</span>
          <span className="shad-trend shad-trend--neutral">Live Sessions</span>
        </div>
        <div className="shad-card__value">{formatNumber(animatedFlows)}</div>
        <div className="shad-card__detail">
          <Layers size={13} className="text-zinc-400" />
          <span>Open bidirectional TCP/UDP sessions</span>
        </div>
      </article>

      {/* 3. Ingest Throughput */}
      <article className="shad-card anim-fade-up is-visible" style={{ transitionDelay: "120ms" }}>
        <div className="shad-card__header">
          <span className="shad-card__title">INGEST THROUGHPUT</span>
          <span className="shad-trend shad-trend--neutral">
            {kpis.isReplaying ? "Processing" : "Idle"}
          </span>
        </div>
        <div className="shad-card__value">
          {formatDecimal(kpis.throughputMbps)}{" "}
          <small style={{ fontSize: "0.85rem", color: "#a1a1aa", fontWeight: 500 }}>Mbps</small>
        </div>
        <div className="shad-card__detail">
          <Zap size={13} className="text-zinc-400" />
          <span>{formatDecimal(kpis.packetRatePerSec)} packets / sec rate</span>
        </div>
      </article>

      {/* 4. Total Packets & Bytes */}
      <article className="shad-card anim-fade-up is-visible" style={{ transitionDelay: "180ms" }}>
        <div className="shad-card__header">
          <span className="shad-card__title">TOTAL DATA INSPECTED</span>
          <span className="shad-trend shad-trend--neutral">PCAP Frame</span>
        </div>
        <div className="shad-card__value">{formatBytes(kpis.totalBytes)}</div>
        <div className="shad-card__detail">
          <Activity size={13} className="text-zinc-400" />
          <span>{formatNumber(animatedPackets)} packets analyzed</span>
        </div>
      </article>
    </section>
  );
}

