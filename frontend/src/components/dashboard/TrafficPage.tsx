import React from "react";
import { formatBytes, formatDecimal, formatNumber, formatTime, formatEndpoint } from "../../runtime";
import { useDashboard } from "../../context/DashboardTelemetryContext";
import { TelemetryWaveform } from "./TelemetryWaveform";
import { Network, Activity, Layers } from "lucide-react";

export function TrafficPage() {
  const { runtime } = useDashboard();
  const metrics = runtime.metrics;
  const flows = runtime.flows || [];
  const latest = runtime.history.at(-1);

  return (
    <div className="shad-content-container">
      {/* Waveform Telemetry */}
      <TelemetryWaveform />

      {/* Traffic KPI Row */}
      <div className="shad-kpi-grid">
        <article className="shad-card">
          <div className="shad-card__header">
            <span className="shad-card__title">TOTAL BYTES ANALYZED</span>
            <span className="shad-trend shad-trend--neutral">Network Volume</span>
          </div>
          <div className="shad-card__value">{formatBytes(metrics?.bytes ?? 0)}</div>
          <div className="shad-card__detail">
            <Activity size={13} className="text-zinc-400" />
            <span>Capture-frame bytes processed locally</span>
          </div>
        </article>

        <article className="shad-card">
          <div className="shad-card__header">
            <span className="shad-card__title">PACKET RATE</span>
            <span className="shad-trend shad-trend--neutral">Throughput</span>
          </div>
          <div className="shad-card__value">
            {formatDecimal(latest?.packetsPerSecond ?? 0)}{" "}
            <small style={{ fontSize: "0.85rem", color: "#a1a1aa" }}>pkt/s</small>
          </div>
          <div className="shad-card__detail">
            <Network size={13} className="text-zinc-400" />
            <span>Derived from real-time telemetry stream</span>
          </div>
        </article>

        <article className="shad-card">
          <div className="shad-card__header">
            <span className="shad-card__title">FLOW CREATION RATE</span>
            <span className="shad-trend shad-trend--neutral">Reconstruction</span>
          </div>
          <div className="shad-card__value">
            {formatDecimal(latest?.flowsPerSecond ?? 0)}{" "}
            <small style={{ fontSize: "0.85rem", color: "#a1a1aa" }}>flows/s</small>
          </div>
          <div className="shad-card__detail">
            <Layers size={13} className="text-zinc-400" />
            <span>New sessions tracked per wall-clock second</span>
          </div>
        </article>

        <article className="shad-card">
          <div className="shad-card__header">
            <span className="shad-card__title">ACTIVE SESSIONS</span>
            <span className="shad-trend shad-trend--neutral">Concurrent</span>
          </div>
          <div className="shad-card__value">{formatNumber(runtime.status?.active_flows ?? 0)}</div>
          <div className="shad-card__detail">
            <Layers size={13} className="text-zinc-400" />
            <span>Open bidirectional TCP/UDP sockets</span>
          </div>
        </article>
      </div>

      {/* Reconstructed Flows Table */}
      <div className="shad-table-container">
        <div className="shad-table-toolbar">
          <div>
            <h3 style={{ fontSize: "0.9rem", fontWeight: 700, color: "#f4f4f5" }}>
              Active Flow Table (Recent 100 Sessions)
            </h3>
            <span style={{ fontSize: "0.75rem", color: "#71717a" }}>
              Session state tracking, packet counters, and protocol identifiers.
            </span>
          </div>
        </div>

        <div className="shad-table-wrapper">
          <table className="shad-table">
            <thead>
              <tr>
                <th>FLOW ID / PROTOCOL</th>
                <th>SOURCE ➔ DESTINATION</th>
                <th>PACKETS (A ➔ B / B ➔ A)</th>
                <th>BYTES (A ➔ B / B ➔ A)</th>
                <th>LAST SEEN</th>
                <th>DIRECTION</th>
              </tr>
            </thead>
            <tbody>
              {flows.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: "center", padding: "32px", color: "#71717a" }}>
                    No active flow sessions observed in current replay window.
                  </td>
                </tr>
              ) : (
                flows.slice(0, 15).map((flow) => (
                  <tr key={flow.flow_id}>
                    <td>
                      <div style={{ display: "flex", flexDirection: "column" }}>
                        <span style={{ fontWeight: 600, color: "#f4f4f5" }}>
                          {flow.protocol ? flow.protocol.toUpperCase() : "TCP"}
                        </span>
                        <span style={{ fontSize: "0.7rem", color: "#71717a", fontFamily: "monospace" }}>
                          {flow.flow_id.slice(0, 14)}...
                        </span>
                      </div>
                    </td>
                    <td style={{ fontFamily: "monospace", fontSize: "0.75rem", color: "#a1a1aa" }}>
                      {formatEndpoint(flow.endpoint_a)} ➔ {formatEndpoint(flow.endpoint_b)}
                    </td>
                    <td>
                      {formatNumber(flow.packets_a_to_b)} / {formatNumber(flow.packets_b_to_a)}
                    </td>
                    <td>
                      {formatBytes(flow.bytes_a_to_b)} / {formatBytes(flow.bytes_b_to_a)}
                    </td>
                    <td style={{ color: "#71717a", fontSize: "0.75rem" }}>
                      {formatTime(flow.last_seen)}
                    </td>
                    <td>
                      <span className="shad-badge shad-badge--clean">
                        <span className="shad-badge__dot" />
                        {flow.initiator_direction ? flow.initiator_direction.toUpperCase() : "BIDIRECTIONAL"}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
