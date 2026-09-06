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
      {/* Hero metric cards with Fortexa bar sparklines & tones (Zero Emojis) */}
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
            <KeyValue label="INFERENCE VECTORS">
              {formatNumber(metrics?.inference_vectors ?? 0)}
            </KeyValue>
            <KeyValue label="EVIDENCE DECISIONS">
              {formatNumber(metrics?.evidence_decisions ?? 0)}
            </KeyValue>
          </div>
        </section>
      </section>

      {/* Latency breakdown */}
      <section className="panel">
        <div className="panel__heading">
          <div>
            <div className="eyebrow">STAGE TIMING BREAKDOWN</div>
            <h2>Pipeline stage latencies</h2>
          </div>
          <span className="muted font-mono">Microsecond precision</span>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Stage</th>
                <th>P50 (Median)</th>
                <th>P95 (95th %)</th>
              </tr>
            </thead>
            <tbody>
              {stages.map((stage) => {
                const row = metrics?.latency_ms[stage];
                return (
                  <tr key={stage}>
                    <td className="font-mono">
                      <strong>{stage.replaceAll("_", " ")}</strong>
                    </td>
                    <td className="font-mono">{row ? `${formatDecimal(row.p50, 3)} ms` : "—"}</td>
                    <td className="font-mono">{row ? `${formatDecimal(row.p95, 3)} ms` : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
