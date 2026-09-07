import { useEffect, useMemo, useState } from "react";
import { formatBytes, formatDecimal, formatEndpoint, formatNumber, formatTime } from "../../runtime";
import type { useRuntimeTelemetry } from "../../hooks/useRuntimeTelemetry";
import type { HostTimelinePoint } from "../../types";
import { MetricCard, Sparkline, StatusBadge, Timeline } from "../Visuals";

type TimelineMetric = "mbps" | "packets" | "flows";

interface TrafficPageProps {
  runtime: ReturnType<typeof useRuntimeTelemetry>;
}

export function TrafficPage({ runtime }: TrafficPageProps) {
  const [timelineMetric, setTimelineMetric] = useState<TimelineMetric>("mbps");
  const latest = runtime.history.at(-1);

  return (
    <div className="dash-page">
      {/* Traffic timeline */}
      <Timeline
        history={runtime.history}
        metric={timelineMetric}
        onMetricChange={setTimelineMetric}
        alerts={runtime.alerts}
      />

      {/* Rate stat cards — Fortexa multi-accent styled */}
      <section className="dash-traffic-stats">
        <MetricCard
          label="TOTAL BYTES"
          value={formatBytes(runtime.metrics?.bytes ?? 0)}
          detail="Capture frames processed locally"
          history={runtime.history.map((p) => p.bytes)}
          tone="purple"
        />
        <MetricCard
          label="PACKET RATE"
          value={formatDecimal(latest?.packetsPerSecond ?? 0)}
          unit="/ sec"
          detail="Derived from real telemetry samples"
          history={runtime.history.map((p) => p.packetsPerSecond)}
          tone="teal"
        />
        <MetricCard
          label="NEW FLOW RATE"
          value={formatDecimal(latest?.flowsPerSecond ?? 0)}
          unit="/ sec"
          detail="Distinct sessions reconstructed per second"
          history={runtime.history.map((p) => p.flowsPerSecond)}
          tone="orange"
        />
      </section>

      {/* Bounded host behaviour */}
      <HostBehaviourTimeline points={runtime.hostTimeline} />

      {/* Flow summary table */}
      <section className="panel">
        <div className="panel__heading">
          <div>
            <div className="eyebrow">READ-ONLY FLOW SUMMARIES</div>
            <h2>Recent and active flows</h2>
          </div>
          <span className="muted font-mono">{runtime.flows.length} retained</span>
        </div>
        {runtime.flows.length > 0 ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Protocol</th>
                  <th>IP Version</th>
                  <th>Endpoint A</th>
                  <th>Endpoint B</th>
                  <th>A → B</th>
                  <th>B → A</th>
                  <th>Total Bytes</th>
                  <th>Close reason</th>
                  <th>Last seen</th>
                </tr>
              </thead>
              <tbody>
                {runtime.flows.map((flow) => {
                  const protoClass =
                    flow.protocol.toUpperCase() === "TCP"
                      ? "row-icon-badge--purple"
                      : flow.protocol.toUpperCase() === "UDP"
                      ? "row-icon-badge--teal"
                      : "row-icon-badge--orange";

                  return (
                    <tr key={flow.flow_id}>
                      <td>
                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          <span className={`row-icon-badge ${protoClass}`} style={{ width: "30px", height: "30px", fontSize: "0.72rem" }}>
                            {flow.protocol.slice(0, 3)}
                          </span>
                          <span className="font-mono" style={{ fontWeight: 600, color: "var(--text-primary)" }}>{flow.protocol}</span>
                        </div>
                      </td>
                      <td className="font-mono">
                        <span className="tag-endpoint">IPv{flow.ip_version}</span>
                      </td>
                      <td>
                        <span className="tag-endpoint">{formatEndpoint(flow.endpoint_a)}</span>
                      </td>
                      <td>
                        <span className="tag-endpoint">{formatEndpoint(flow.endpoint_b)}</span>
                      </td>
                      <td className="font-mono">{formatNumber(flow.packets_a_to_b)} pkts</td>
                      <td className="font-mono">{formatNumber(flow.packets_b_to_a)} pkts</td>
                      <td className="font-mono">
                        <strong style={{ color: "var(--accent-purple)" }}>
                          {formatBytes(flow.bytes_a_to_b + flow.bytes_b_to_a)}
                        </strong>
                      </td>
                      <td>
                        <StatusBadge
                          label={flow.close_reason ? flow.close_reason.replaceAll("_", " ") : "ACTIVE"}
                          tone={flow.close_reason ? "neutral" : "good"}
                        />
                      </td>
                      <td className="font-mono">{formatTime(flow.last_seen)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="panel-note">
            No supported IP flow summaries are available for this run. Start an approved capture
            replay to observe reconstructed bidirectional flows.
          </p>
        )}
      </section>
    </div>
  );
}

/* ---------- Host Behaviour Timeline ---------- */
function HostBehaviourTimeline({ points }: { points: HostTimelinePoint[] }) {
  const hosts = useMemo(
    () => [...new Set(points.flatMap((p) => (p.host ? [p.host] : [])))].sort(),
    [points],
  );
  const [selectedHost, setSelectedHost] = useState("");

  useEffect(() => {
    if ((!selectedHost || !hosts.includes(selectedHost)) && hosts.length) {
      setSelectedHost(hosts[0]);
    }
  }, [hosts, selectedHost]);

  const selected = points.filter((p) => p.host === selectedHost);
  const measurements = selected.filter((p) => p.packet_count != null);
  const alerts = selected.filter((p) => p.alert_id != null);

  return (
    <section className="panel dash-host-timeline">
      <div className="panel__heading">
        <div>
          <div className="eyebrow">BOUNDED HOST BEHAVIOUR</div>
          <h2>Evidence accumulation timeline</h2>
        </div>
        <label className="dash-host-selector">
          <span className="font-mono">HOST</span>
          <select
            value={selectedHost}
            onChange={(e) => setSelectedHost(e.target.value)}
            className="dash-filter-select font-mono"
          >
            <option value="">No observed host</option>
            {hosts.map((host) => (
              <option key={host} value={host}>
                {host}
              </option>
            ))}
          </select>
        </label>
      </div>

      {measurements.length > 0 ? (
        <>
          <div className="host-chart-grid">
            <div>
              <span className="font-mono">Packets in window</span>
              <Sparkline
                values={measurements.map((p) => p.packet_count ?? 0)}
                label={`Packet observations for ${selectedHost}`}
              />
            </div>
            <div>
              <span className="font-mono">Destination-port fan-out</span>
              <Sparkline
                values={measurements.map((p) => p.unique_destination_ports ?? 0)}
                label={`Destination port diversity for ${selectedHost}`}
                tone="amber"
              />
            </div>
            <div>
              <span className="font-mono">Outbound bytes</span>
              <Sparkline
                values={measurements.map((p) => p.outbound_bytes ?? 0)}
                label={`Outbound bytes for ${selectedHost}`}
                tone="violet"
              />
            </div>
          </div>
          <div className="timeline-meta font-mono">
            <span>{measurements.length} bounded evidence snapshots</span>
            <span>{alerts.length} alert-fire markers</span>
            <span>Latest window {measurements.at(-1)?.window_seconds ?? "—"} seconds</span>
          </div>
          {alerts.length > 0 ? (
            <ul className="host-alert-markers">
              {alerts.map((p) => (
                <li key={`${p.alert_id}-${p.observed_at}`}>
                  <StatusBadge label="ALERT FIRED" tone="warning" />
                  <span className="font-mono">{formatTime(p.observed_at)}</span>
                  <strong>{p.threat_class}</strong>
                </li>
              ))}
            </ul>
          ) : (
            <p className="panel-note">
              No evidence-backed alert has fired for this host. The charts show the measured
              behaviour that was available to the pipeline.
            </p>
          )}
        </>
      ) : (
        <p className="panel-note">
          No host-window snapshots are available. Snapshots appear after a valid replay produces
          eligible flow observations.
        </p>
      )}
    </section>
  );
}
