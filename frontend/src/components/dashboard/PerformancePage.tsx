import React from "react";
import { formatBytes, formatDecimal, formatNumber } from "../../runtime";
import { useDashboard } from "../../context/DashboardTelemetryContext";
import { Gauge, Cpu, Zap, Activity, Clock } from "lucide-react";

export function PerformancePage() {
  const { runtime } = useDashboard();
  const metrics = runtime.metrics;
  const latency = metrics?.latency_ms?.total_pipeline;
  const processing = runtime.status?.replay_running
    ? metrics?.processing_rates
    : metrics?.average_processing_rates;

  return (
    <div className="shad-content-container">
      {/* Performance KPI Row */}
      <div className="shad-kpi-grid">
        <article className="shad-card">
          <div className="shad-card__header">
            <span className="shad-card__title">INGEST THROUGHPUT</span>
            <span className="shad-trend shad-trend--neutral">Processing</span>
          </div>
          <div className="shad-card__value">
            {formatDecimal(processing?.mbps ?? 0)}{" "}
            <small style={{ fontSize: "0.85rem", color: "#a1a1aa" }}>Mbps</small>
          </div>
          <div className="shad-card__detail">
            <Zap size={13} className="text-zinc-400" />
            <span>Local packet decode & feature calculation</span>
          </div>
        </article>

        <article className="shad-card">
          <div className="shad-card__header">
            <span className="shad-card__title">P50 PIPELINE LATENCY</span>
            <span className="shad-trend shad-trend--neutral">Median</span>
          </div>
          <div className="shad-card__value">
            {latency?.p50 != null ? formatDecimal(latency.p50) : "—"}{" "}
            <small style={{ fontSize: "0.85rem", color: "#a1a1aa" }}>ms</small>
          </div>
          <div className="shad-card__detail">
            <Clock size={13} className="text-zinc-400" />
            <span>Packet parse to heuristic decision lag</span>
          </div>
        </article>

        <article className="shad-card">
          <div className="shad-card__header">
            <span className="shad-card__title">P95 PIPELINE LATENCY</span>
            <span className="shad-trend shad-trend--neutral">Tail Risk</span>
          </div>
          <div className="shad-card__value">
            {latency?.p95 != null ? formatDecimal(latency.p95) : "—"}{" "}
            <small style={{ fontSize: "0.85rem", color: "#a1a1aa" }}>ms</small>
          </div>
          <div className="shad-card__detail">
            <Clock size={13} className="text-zinc-400" />
            <span>95th percentile worst-case batch delay</span>
          </div>
        </article>

        <article className="shad-card">
          <div className="shad-card__header">
            <span className="shad-card__title">ENGINE CPU / MEMORY</span>
            <span className="shad-trend shad-trend--neutral">Resource</span>
          </div>
          <div className="shad-card__value">
            {formatDecimal(metrics?.cpu_percent ?? 0)}%
          </div>
          <div className="shad-card__detail">
            <Cpu size={13} className="text-zinc-400" />
            <span>Memory: {formatBytes(metrics?.memory_bytes ?? 0)}</span>
          </div>
        </article>
      </div>

      {/* Latency Stage Breakdown Table */}
      <div className="shad-table-container">
        <div className="shad-table-toolbar">
          <div>
            <h3 style={{ fontSize: "0.9rem", fontWeight: 700, color: "#f4f4f5" }}>
              Pipeline Stage Latency Breakdown (Micro-benchmarks)
            </h3>
            <span style={{ fontSize: "0.75rem", color: "#71717a" }}>
              Granular latency percentiles across each step of the detection pipeline.
            </span>
          </div>
        </div>

        <div className="shad-table-wrapper">
          <table className="shad-table">
            <thead>
              <tr>
                <th>PIPELINE STAGE</th>
                <th>P50 (MEDIAN)</th>
                <th>P95 (TAIL LATENCY)</th>
                <th>STATUS</th>
              </tr>
            </thead>
            <tbody>
              {metrics?.latency_ms ? (
                Object.entries(metrics.latency_ms).map(([stage, l]) => (
                  <tr key={stage}>
                    <td style={{ fontWeight: 600, color: "#f4f4f5", textTransform: "capitalize" }}>
                      {stage.replaceAll("_", " ")}
                    </td>
                    <td style={{ fontFamily: "monospace" }}>{l?.p50 != null ? `${formatDecimal(l.p50)} ms` : "—"}</td>
                    <td style={{ fontFamily: "monospace", color: (l?.p95 ?? 0) > 50 ? "#ef4444" : "#f4f4f5" }}>
                      {l?.p95 != null ? `${formatDecimal(l.p95)} ms` : "—"}
                    </td>
                    <td>
                      <span className="shad-badge shad-badge--clean">
                        <span className="shad-badge__dot" />
                        OPTIMAL
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} style={{ textAlign: "center", padding: "32px", color: "#71717a" }}>
                    No latency metrics recorded yet. Start PCAP replay to capture pipeline timing.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
