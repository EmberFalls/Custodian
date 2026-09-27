import React, { useMemo, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { useDashboard } from "../../context/DashboardTelemetryContext";
import { Radio, Info } from "lucide-react";

type MetricChoice = "mbps" | "packetsPerSecond" | "flowsPerSecond";
type TimeRangeChoice = "30s" | "5m" | "all";

export function TelemetryWaveform() {
  const { waveformHistory, kpis } = useDashboard();
  const [metric, setMetric] = useState<MetricChoice>("mbps");
  const [timeRange, setTimeRange] = useState<TimeRangeChoice>("all");

  const filteredData = useMemo(() => {
    if (!waveformHistory || waveformHistory.length === 0) return [];
    if (timeRange === "30s") return waveformHistory.slice(-30);
    if (timeRange === "5m") return waveformHistory.slice(-300);
    return waveformHistory;
  }, [waveformHistory, timeRange]);

  const metricLabels: Record<MetricChoice, { label: string; unit: string }> = {
    mbps: { label: "Throughput", unit: "Mbps" },
    packetsPerSecond: { label: "Packet Ingestion Rate", unit: "pkt/s" },
    flowsPerSecond: { label: "Flow Analysis Rate", unit: "flows/s" },
  };

  // Custom Dark Tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="shad-chart-tooltip">
          <div className="shad-chart-tooltip__time">Timestamp: {data.timeFormatted}</div>
          <div className="shad-chart-tooltip__row">
            <span>{metricLabels[metric].label}:</span>
            <span>
              {data[metric]} {metricLabels[metric].unit}
            </span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <section className="shad-chart-card anim-fade-up anim-delay-2" aria-label="Telemetry Ingestion Waveform">
      <div className="shad-chart-header">
        <div>
          <h2 className="shad-chart-title">Real-time Telemetry Ingestion</h2>
          <span className="shad-chart-subtitle">
            Monochrome packet stream throughput and flow reconstruction rates
          </span>
        </div>

        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          {/* Metric Selector */}
          <div className="shad-segmented-control" role="group" aria-label="Select metric">
            <button
              onClick={() => setMetric("mbps")}
              className={`shad-segment-btn ${metric === "mbps" ? "is-active" : ""}`}
            >
              Mbps
            </button>
            <button
              onClick={() => setMetric("packetsPerSecond")}
              className={`shad-segment-btn ${metric === "packetsPerSecond" ? "is-active" : ""}`}
            >
              Packets/s
            </button>
            <button
              onClick={() => setMetric("flowsPerSecond")}
              className={`shad-segment-btn ${metric === "flowsPerSecond" ? "is-active" : ""}`}
            >
              Flows/s
            </button>
          </div>

          {/* Time Range Selector */}
          <div className="shad-segmented-control" role="group" aria-label="Select time range">
            <button
              onClick={() => setTimeRange("30s")}
              className={`shad-segment-btn ${timeRange === "30s" ? "is-active" : ""}`}
            >
              30s
            </button>
            <button
              onClick={() => setTimeRange("5m")}
              className={`shad-segment-btn ${timeRange === "5m" ? "is-active" : ""}`}
            >
              5m
            </button>
            <button
              onClick={() => setTimeRange("all")}
              className={`shad-segment-btn ${timeRange === "all" ? "is-active" : ""}`}
            >
              All
            </button>
          </div>
        </div>
      </div>

      {/* Chart Body */}
      <div style={{ width: "100%", height: "240px", position: "relative" }}>
        {filteredData.length === 0 ? (
          <div
            style={{
              height: "100%",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              border: "1px dashed var(--dash-border)",
              borderRadius: "8px",
              color: "var(--dash-text-muted)",
              gap: "8px",
            }}
          >
            <Radio size={22} className="text-zinc-500 animate-pulse" />
            <span style={{ fontSize: "0.82rem" }}>
              {kpis.isReplaying
                ? "Collecting initial telemetry telemetry frames..."
                : "Awaiting PCAP replay stream. Start playback in the bottom controller."}
            </span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={filteredData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="shadGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f4f4f5" stopOpacity={0.28} />
                  <stop offset="95%" stopColor="#f4f4f5" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
              <XAxis
                dataKey="timeFormatted"
                stroke="#71717a"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: "#27272a" }}
              />
              <YAxis
                stroke="#71717a"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: "#27272a" }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey={metric}
                stroke="#f4f4f5"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#shadGradient)"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </section>
  );
}
