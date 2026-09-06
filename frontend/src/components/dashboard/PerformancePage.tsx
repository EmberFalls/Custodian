import { formatBytes, formatDecimal, formatNumber } from "../../runtime";
import type { useRuntimeTelemetry } from "../../hooks/useRuntimeTelemetry";
import { KeyValue, MetricCard, Timeline } from "../Visuals";

const stages = [
  "parse",
  "flow",
  "state",
  "features",
  "inference",
  "inference_batch",
  "evidence",
  "alert",
  "total_pipeline",
];

interface PerformancePageProps {
  runtime: ReturnType<typeof useRuntimeTelemetry>;
}

export function PerformancePage({ runtime }: PerformancePageProps) {
  const metrics = runtime.metrics;
  const latency = metrics?.latency_ms.total_pipeline;
  const processing = runtime.status?.replay_running
    ? metrics?.processing_rates
    : metrics?.average_processing_rates;

  return (
    <div className="dash-page">
      {/* Hero metric cards with Fortexa bar sparklines & tones */}
      <section className="dash-perf-hero">
        <MetricCard
          label="PROCESSING THROUGHPUT"
          value={formatDecimal(processing?.mbps ?? 0)}
          unit="Mbps"
          detail={
            runtime.status?.replay_running
              ? "Current processing interval"
              : "Last replay average"
          }
          history={runtime.history.map((p) => p.mbps)}
          tone="purple"
        />
        <MetricCard
          label="PACKET RATE"
          value={formatDecimal(processing?.packets_per_second ?? 0)}
          unit="/ sec"
          detail="Frames through parse stage per second"
          history={runtime.history.map((p) => p.packetsPerSecond)}
          tone="teal"
        />
        <MetricCard
          label="NEW FLOW RATE"
          value={formatDecimal(processing?.flows_per_second ?? 0)}
          unit="/ sec"
          detail="Distinct flow sessions, not packet updates"
          history={runtime.history.map((p) => p.flowsPerSecond)}
          tone="orange"
        />
        <MetricCard
          label="P50 PIPELINE"
          value={latency ? formatDecimal(latency.p50) : "—"}
          unit="ms"
          detail="Snapshot to decision median latency"
          tone="pink"
        />
        <MetricCard
          label="P95 PIPELINE"
          value={latency ? formatDecimal(latency.p95) : "—"}
          unit="ms"
          detail="95th percentile including batch wait"
          tone="purple"
        />
      </section>

      {/* Throughput chart + resources */}
      <section className="dash-perf-grid">
        <Timeline
          history={runtime.history}
          metric="mbps"
          onMetricChange={() => undefined}
          alerts={runtime.alerts}
        />
        <section className="panel dash-resource-panel">
          <div className="eyebrow">LOCAL PROCESS RESOURCES</div>
          <h2>Measured replay</h2>
          <div className="dash-resource-grid">
            <KeyValue label="CPU">{formatDecimal(metrics?.cpu_percent ?? 0)}%</KeyValue>
            <KeyValue label="MEMORY">{formatBytes(metrics?.memory_bytes ?? 0)}</KeyValue>
            <KeyValue label="ELAPSED">{formatDecimal(metrics?.elapsed_seconds ?? 0)} s</KeyValue>
            <KeyValue label="ACTIVE PROCESSING">
              {formatDecimal(metrics?.active_seconds ?? 0)} s
            </KeyValue>
            <KeyValue label="ORIGINAL CAPTURE AVERAGE">
              {metrics?.observed_average_mbps != null
                ? `${formatDecimal(metrics.observed_average_mbps, 4)} Mbps`
                : "Unavailable"}
            </KeyValue>
            <KeyValue label="FEATURE SNAPSHOTS">
              {formatNumber(metrics?.feature_vectors ?? 0)}
            </KeyValue>
            <KeyValue label="INFERENCE VECTORS / BATCHES">
              {formatNumber(metrics?.inference_vectors ?? 0)} /{" "}
              {formatNumber(metrics?.inference_batches ?? 0)}
            </KeyValue>
            <KeyValue label="UNSUPPORTED FRAMES">
              {formatNumber(metrics?.unsupported_frames ?? 0)}
            </KeyValue>
            <KeyValue label="MALFORMED / TRUNCATED">
              {formatNumber((metrics?.malformed_frames ?? 0) + (metrics?.truncated_frames ?? 0))}
            </KeyValue>
          </div>
          <p className="panel-note">
            Processing speed is measured on this laptop's CPU pipeline. It is separate from the
            original capture's real-time traffic rate.
          </p>
        </section>
      </section>

      {/* Stage latency table */}
      <section className="panel">
        <div className="panel__heading">
          <div>
            <div className="eyebrow">PIPELINE-ORDERED STAGE TIMING</div>
            <h2>Measured stage latency</h2>
          </div>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Pipeline Stage</th>
                <th>P50 Latency</th>
                <th>P95 Latency</th>
              </tr>
            </thead>
            <tbody>
              {stages.map((stage, idx) => {
                const timing = metrics?.latency_ms[stage];
                const stageTones = ["row-icon-badge--purple", "row-icon-badge--teal", "row-icon-badge--pink", "row-icon-badge--orange"];
                const badgeTone = stageTones[idx % stageTones.length];

                return (
                  <tr key={stage}>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <span className={`row-icon-badge ${badgeTone}`} style={{ width: "30px", height: "30px", fontSize: "0.72rem" }}>
                          0{idx + 1}
                        </span>
                        <span className="font-mono" style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                          {stage.replaceAll("_", " ")}
                        </span>
                      </div>
                    </td>
                    <td className="font-mono">
                      {timing ? (
                        <strong style={{ color: "var(--emerald)" }}>{formatDecimal(timing.p50, 4)} ms</strong>
                      ) : (
                        <span style={{ color: "var(--text-muted)" }}>Not measured</span>
                      )}
                    </td>
                    <td className="font-mono">
                      {timing ? (
                        <strong style={{ color: "var(--accent-purple)" }}>{formatDecimal(timing.p95, 4)} ms</strong>
                      ) : (
                        <span style={{ color: "var(--text-muted)" }}>Not measured</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="panel-note">
          Stages are displayed in pipeline order. BENCHMARK mode samples packet stages every 32
          frames. Model stages remain unmeasured until a real approved model artifact is loaded.
        </p>
      </section>
    </div>
  );
}
