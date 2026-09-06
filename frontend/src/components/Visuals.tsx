import type { ReactNode } from "react";

import { formatDecimal, formatNumber } from "../runtime";
import type { AlertRecord, DetectorStatus, RuntimeMetrics, TimelinePoint } from "../types";

export function StatusBadge({ label, tone = "neutral" }: { label: string; tone?: "good" | "warning" | "danger" | "unknown" | "neutral" }) {
  return (
    <span className={`status-badge status-badge--${tone}`}>
      <span className="status-badge__dot" aria-hidden="true">●</span>
      {label}
    </span>
  );
}

function MetricChipIcon({ tone }: { tone: string }) {
  switch (tone) {
    case "magenta":
      // Pulse / Rate icon
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
      );
    case "teal":
      // Packet / Storage cube icon
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
          <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
          <line x1="12" y1="22.08" x2="12" y2="12" />
        </svg>
      );
    case "orange":
      // Reconstructed flow arrows
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <polyline points="17 1 21 5 17 9" />
          <path d="M3 11V9a4 4 0 0 1 4-4h14" />
          <polyline points="7 23 3 19 7 15" />
          <path d="M21 13v2a4 4 0 0 1-4 4H3" />
        </svg>
      );
    case "gold":
      // Active sessions / node
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <circle cx="12" cy="12" r="10" />
          <line x1="2" y1="12" x2="22" y2="12" />
          <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
        </svg>
      );
    case "pink":
      // Timer / latency clock
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
      );
    case "purple":
    default:
      // Bar chart telemetry icon
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <line x1="18" y1="20" x2="18" y2="10" />
          <line x1="12" y1="20" x2="12" y2="4" />
          <line x1="6" y1="20" x2="6" y2="14" />
        </svg>
      );
  }
}

export function MetricCard({
  label,
  value,
  detail,
  history,
  unit,
  tone = "purple",
}: {
  label: string;
  value: string;
  detail: string;
  history?: number[];
  unit?: string;
  tone?: "purple" | "magenta" | "teal" | "orange" | "gold" | "pink";
  icon?: string;
}) {
  return (
    <article className="metric-card">
      <div>
        <div className={`metric-card__chip metric-card__chip--${tone}`}>
          <MetricChipIcon tone={tone} />
        </div>
        <div className="eyebrow">{label}</div>
        <div className="metric-card__value">
          {value}
          {unit ? <small>{unit}</small> : null}
        </div>
      </div>
      <div>
        {history && history.length > 1 ? (
          <BarSparkline values={history} label={`${label} recent activity`} tone={tone} />
        ) : null}
        <div className="metric-card__detail">{detail}</div>
      </div>
    </article>
  );
}

export function BarSparkline({
  values,
  label,
  tone = "purple",
}: {
  values: number[];
  label: string;
  tone?: string;
}) {
  const width = 240;
  const height = 36;
  const samples = values.length > 0 ? values.slice(-18) : [10, 20, 30, 40, 50];
  const max = Math.max(...samples, 1);
  const barWidth = Math.max(Math.floor((width - (samples.length - 1) * 3) / samples.length), 4);
  const gap = 3;

  const gradientId = `bar-grad-${tone}`;

  const palette: Record<string, { start: string; end: string; highlight: string }> = {
    purple:  { start: "#c084fc", end: "#7c3aed", highlight: "#e9d5ff" },
    magenta: { start: "#f43f5e", end: "#be123c", highlight: "#fecdd3" },
    pink:    { start: "#f472b6", end: "#db2777", highlight: "#fbcfe8" },
    teal:    { start: "#22d3ee", end: "#0891b2", highlight: "#a5f3fc" },
    orange:  { start: "#fb923c", end: "#ea580c", highlight: "#fed7aa" },
    gold:    { start: "#fbbf24", end: "#d97706", highlight: "#fef3c7" },
    blue:    { start: "#38bdf8", end: "#0284c7", highlight: "#bae6fd" },
    green:   { start: "#34d399", end: "#059669", highlight: "#a7f3d0" },
  };
  const colors = palette[tone] ?? palette.purple;

  return (
    <svg
      className="bar-sparkline"
      role="img"
      aria-label={label}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={colors.start} />
          <stop offset="100%" stopColor={colors.end} stopOpacity="0.4" />
        </linearGradient>
      </defs>
      {samples.map((val, idx) => {
        const barHeight = Math.max(Math.round((val / max) * (height - 6)), 4);
        const x = idx * (barWidth + gap);
        const y = height - barHeight;
        const isLast = idx === samples.length - 1;

        return (
          <rect
            key={idx}
            x={x}
            y={y}
            width={barWidth}
            height={barHeight}
            rx={2.5}
            fill={isLast ? colors.highlight : `url(#${gradientId})`}
            opacity={isLast ? 1 : 0.85}
          />
        );
      })}
    </svg>
  );
}

/** Fortexa-style diagonal-striped risk/confidence bar */
export function RiskBar({
  value,
  max = 100,
  width = 110,
  level = "medium",
}: {
  value: number;
  max?: number;
  width?: number;
  level?: "high" | "medium" | "low" | "neutral";
}) {
  const pct = Math.min(Math.max((value / max) * 100, 0), 100);
  const patternId = `stripe-${level}`;

  const fillColors: Record<string, string> = {
    high:    "#f72585",
    medium:  "#9b5de5",
    low:     "#06b6d4",
    neutral: "#5a5a80",
  };

  return (
    <svg
      width={width}
      height={8}
      viewBox={`0 0 ${width} 8`}
      aria-label={`Risk: ${Math.round(pct)}%`}
      style={{ display: "inline-block", verticalAlign: "middle", flexShrink: 0 }}
    >
      <defs>
        <pattern id={patternId} x="0" y="0" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">
          <rect width="4" height="8" fill={fillColors[level]} />
          <rect x="4" width="4" height="8" fill={fillColors[level]} fillOpacity="0.55" />
        </pattern>
        <clipPath id={`clip-${patternId}`}>
          <rect x="0" y="0" width={`${pct}%`} height="8" rx="4" />
        </clipPath>
      </defs>
      {/* Track */}
      <rect x="0" y="0" width={width} height="8" rx="4" fill="rgba(255,255,255,0.06)" />
      {/* Striped fill */}
      <rect
        x="0" y="0"
        width={`${pct}%`}
        height="8"
        rx="4"
        fill={`url(#${patternId})`}
        clipPath={`url(#clip-${patternId})`}
      />
    </svg>
  );
}

export function RadialGauge({
  score,
  label = "Risk Score",
  size = 130,
}: {
  score: number;
  label?: string;
  size?: number;
}) {
  const normalized = Math.min(Math.max(score, 0), 100);
  const radius = (size - 18) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (normalized / 100) * circumference * 0.75;

  return (
    <div className="radial-gauge" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <defs>
          <linearGradient id="gaugeGradient" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#f72585" />
            <stop offset="50%" stopColor="#9b5de5" />
            <stop offset="100%" stopColor="#06b6d4" />
          </linearGradient>
        </defs>
        <circle
          cx={size / 2} cy={size / 2} r={radius} fill="none"
          stroke="rgba(255,255,255,0.07)" strokeWidth="10"
          strokeDasharray={`${circumference * 0.75} ${circumference}`}
          strokeDashoffset={0} strokeLinecap="round"
          transform={`rotate(135 ${size / 2} ${size / 2})`}
        />
        <circle
          cx={size / 2} cy={size / 2} r={radius} fill="none"
          stroke="url(#gaugeGradient)" strokeWidth="10"
          strokeDasharray={`${circumference * 0.75} ${circumference}`}
          strokeDashoffset={strokeDashoffset} strokeLinecap="round"
          transform={`rotate(135 ${size / 2} ${size / 2})`}
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
      </svg>
      <div className="radial-gauge__value">{Math.round(normalized)}%</div>
      <div className="radial-gauge__label">{label}</div>
    </div>
  );
}

export function Sparkline({ values, label, tone = "cyan" }: { values: number[]; label: string; tone?: "cyan" | "violet" | "amber" }) {
  const width = 260;
  const height = 48;
  const max = Math.max(...values, 0);
  const min = Math.min(...values, 0);
  const span = Math.max(max - min, 0.00001);
  const y = (value: number) => height - ((value - min) / span) * (height - 8) - 4;
  const points = values.map((value, index) => `${(index / Math.max(values.length - 1, 1)) * width},${y(value)}`).join(" ");
  return (
    <svg className={`sparkline sparkline--${tone}`} role="img" aria-label={label} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      {values.length === 1 ? (
        <circle cx={width / 2} cy={y(values[0])} r="3" fill="currentColor" />
      ) : (
        <polyline points={points} fill="none" vectorEffect="non-scaling-stroke" />
      )}
    </svg>
  );
}

export function Timeline({
  history,
  metric,
  onMetricChange,
  alerts,
  onAlert,
}: {
  history: TimelinePoint[];
  metric: "mbps" | "packets" | "flows";
  onMetricChange: (metric: "mbps" | "packets" | "flows") => void;
  alerts: AlertRecord[];
  onAlert?: (alert: AlertRecord) => void;
}) {
  const values = history.map((point) => (metric === "mbps" ? point.mbps : metric === "packets" ? point.packetsPerSecond : point.flowsPerSecond));
  const max = Math.max(...values, 0);
  const label = metric === "mbps" ? "Processing Mbps" : metric === "packets" ? "Packets / sec" : "New flows / sec";
  const first = history.at(0)?.observedAt ?? 0;
  const last = history.at(-1)?.observedAt ?? first;
  const markers = alerts.flatMap((alert) => {
    const at = new Date(alert.emitted_at ?? alert.timestamp).getTime();
    return at >= first && at <= last ? [{ alert, left: ((at - first) / Math.max(last - first, 1)) * 100 }] : [];
  });

  return (
    <section className="panel timeline-panel">
      <div className="panel__heading">
        <div>
          <div className="eyebrow">REAL RUNTIME TELEMETRY</div>
          <h2>Traffic timeline</h2>
        </div>
        <div className="segmented" aria-label="Timeline metric">
          {(["mbps", "packets", "flows"] as const).map((option) => (
            <button key={option} className={metric === option ? "is-selected" : ""} onClick={() => onMetricChange(option)}>
              {option === "mbps" ? "Mbps" : option === "packets" ? "Packets/s" : "Flows/s"}
            </button>
          ))}
        </div>
      </div>
      <div className="chart-value">
        <strong>{formatDecimal(values.at(-1) ?? 0)}</strong>
        <span>{label}</span>
      </div>
      <div className="timeline-chart">
        <Sparkline values={values} label={`${label} over backend-aggregated telemetry samples`} />
        {markers.map(({ alert, left }) => (
          <button
            key={alert.alert_id}
            className="alert-marker"
            style={{ left: `${left}%` }}
            aria-label={`Open ${alert.threat_class} alert`}
            onClick={() => onAlert?.(alert)}
            title={`${alert.threat_class} · ${formatDecimal(alert.calibrated_confidence * 100)}%`}
          />
        ))}
      </div>
      <div className="timeline-meta">
        <span>Bounded history: {history.length} samples</span>
        <span>{formatNumber(markers.length)} alert markers in view</span>
        <span>Peak: {formatDecimal(max)} {label}</span>
      </div>
    </section>
  );
}

export function InspectionPipeline({
  replayActive,
  detectors,
  metrics,
  onOpenDetails,
}: {
  replayActive: boolean;
  detectors: DetectorStatus[];
  metrics: RuntimeMetrics | null;
  onOpenDetails: (panel: "detectors" | "evidence") => void;
}) {
  const stateLabel = replayActive ? "ACTIVE" : "IDLE";
  const modelsAvailable = detectors.some((item) => item.status === "READY");
  const featureState = (metrics?.feature_vectors ?? 0) > 0 ? "OBSERVED" : "WAITING";
  const evidenceState = (metrics?.evidence_decisions ?? 0) > 0 ? "EVALUATED" : "WAITING";

  return (
    <section className="panel pipeline-panel">
      <div className="panel__heading">
        <div>
          <div className="eyebrow">PASSIVE, READ-ONLY PROCESSING</div>
          <h2>Inspection pipeline</h2>
        </div>
        <StatusBadge label={stateLabel} tone={replayActive ? "good" : "neutral"} />
      </div>
      <div className="pipeline-flow">
        <PipelineStep step="01" label="INGEST" state={stateLabel} detail={`${formatDecimal(metrics?.processing_rates.mbps ?? 0)} Mbps`} active={replayActive} />
        <PipelineStep step="02" label="FLOWS" state={stateLabel} detail={`${formatDecimal(metrics?.processing_rates.flows_per_second ?? 0)} new/s`} active={replayActive} />
        <PipelineStep step="03" label="FEATURES" state={featureState} detail={`${formatNumber(metrics?.feature_vectors ?? 0)} snapshots`} active={featureState === "OBSERVED"} />
        <PipelineStep
          step="04" label="DETECT"
          state={modelsAvailable ? stateLabel : "UNAVAILABLE"}
          detail={`${formatNumber(metrics?.inference_vectors ?? 0)} model vectors`}
          active={modelsAvailable} unavailable={!modelsAvailable}
          onClick={() => onOpenDetails("detectors")}
        />
        <PipelineStep
          step="05" label="EVIDENCE"
          state={evidenceState}
          detail={`${formatNumber(metrics?.evidence_decisions ?? 0)} decisions`}
          active={evidenceState === "EVALUATED"}
          onClick={() => onOpenDetails("evidence")}
        />
        <PipelineStep
          step="06" label="ALERT"
          state={(metrics?.alerts ?? 0) > 0 ? "DECISIONS" : "NO DECISIONS"}
          detail={`${formatNumber(metrics?.alerts ?? 0)} alert records`}
          active={(metrics?.alerts ?? 0) > 0}
          isLast
        />
      </div>
    </section>
  );
}

function PipelineStep({
  step, label, state, detail, active = false, unavailable = false, isLast = false, onClick,
}: {
  step: string; label: string; state: string; detail: string;
  active?: boolean; unavailable?: boolean; isLast?: boolean; onClick?: () => void;
}) {
  const tone = unavailable ? "neutral" : active ? "good" : "neutral";

  const content = (
    <div className={`pipeline-step ${unavailable ? "pipeline-step--unavailable" : ""}`}>
      <div className="pipeline-step__indicator">
        <div className={`pipeline-step__dot ${active ? "pipeline-step__dot--active" : ""}`} />
        {!isLast ? <div className={`pipeline-step__line ${active ? "pipeline-step__line--active" : ""}`} /> : null}
      </div>
      <div className="pipeline-step__content">
        <div className="pipeline-step__header">
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span className="pipeline-step__num font-mono">{step}</span>
            <strong className="pipeline-step__label">{label}</strong>
          </div>
          <StatusBadge label={state} tone={tone} />
        </div>
        <div className="pipeline-step__detail font-mono">{detail}</div>
      </div>
    </div>
  );

  return onClick ? (
    <button className="pipeline-step-btn" onClick={onClick} title={`Click to inspect ${label} model and details`} type="button">
      {content}
    </button>
  ) : (
    content
  );
}

export function KeyValue({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="key-value">
      <span>{label}</span>
      <strong>{children}</strong>
    </div>
  );
}
