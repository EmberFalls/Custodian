import { CustodianShieldIcon } from "../landing/icons/CustodianShieldIcon";
import { StatusBadge } from "../Visuals";
import type { useRuntimeTelemetry } from "../../hooks/useRuntimeTelemetry";

export type DashboardPage = "monitor" | "alerts" | "traffic" | "detectors" | "performance";

interface GlobalHeaderProps {
  runtime: ReturnType<typeof useRuntimeTelemetry>;
  activePage: DashboardPage;
  onPageChange: (page: DashboardPage) => void;
  onNavigateHome: () => void;
  presentationMode: boolean;
  onTogglePresentation: () => void;
}

const navigationItems: Array<{ id: DashboardPage; label: string; number: string }> = [
  { id: "monitor", label: "Live monitor", number: "01" },
  { id: "alerts", label: "Alerts", number: "02" },
  { id: "traffic", label: "Traffic", number: "03" },
  { id: "detectors", label: "Detectors", number: "04" },
  { id: "performance", label: "Performance", number: "05" },
];

export function GlobalHeader({
  runtime,
  activePage,
  onPageChange,
  onNavigateHome,
  presentationMode,
  onTogglePresentation,
}: GlobalHeaderProps) {
  const monitorState = runtime.connected && runtime.status?.passive_monitor ? "ACTIVE" : "OFFLINE";
  const replayState = runtime.status?.replay_state ?? "IDLE";
  const progressText = runtime.status?.progress == null ? "—" : `${Math.round(runtime.status.progress * 100)}%`;
  const readinessText = runtime.readiness?.status ? runtime.readiness.status.toUpperCase() : "CONNECTING";
  const sourceText = runtime.status?.source_type ? runtime.status.source_type.replaceAll("_", " ").toUpperCase() : "PCAP REPLAY";
  const modeText = runtime.status?.mode ? runtime.status.mode.toUpperCase() : "—";

  return (
    <header className="dash-header">
      {/* Top Bar: Brand, 6 Truthfulness Questions, Connection & Actions */}
      <div className="dash-header__top">
        {/* Brand & Home button */}
        <div className="dash-header__brand">
          <button
            onClick={onNavigateHome}
            className="button button--quiet dash-home-btn font-sans"
            title="Return to Custodian Landing Page"
            aria-label="Back to Home"
          >
            ← Home
          </button>
          <div className="dash-brand-title">
            <CustodianShieldIcon size={26} />
            <div>
              <div className="dash-brand-name font-sans">
                CUSTODIAN <span className="dash-brand-badge">PASSIVE</span>
              </div>
              <div className="dash-brand-sub">PASSIVE THREAT OBSERVATION · LOCAL ONLY</div>
            </div>
          </div>
        </div>

        {/* The 6 Status Indicators (Strict Truthfulness Contract) */}
        <div
          className="dash-status-strip"
          title="Custodian receives copied traffic only and does not transmit into the monitored network."
        >
          <div className="dash-status-item">
            <span className="dash-status-label">MONITOR</span>
            <StatusBadge label={monitorState} tone={monitorState === "ACTIVE" ? "good" : "danger"} />
          </div>
          <span style={{ width: "1px", height: "14px", background: "rgba(255,255,255,0.08)", flexShrink: 0 }} aria-hidden="true" />
          <div className="dash-status-item">
            <span className="dash-status-label">RETURN PATH</span>
            <StatusBadge label={runtime.status?.return_path ?? "NONE"} tone="neutral" />
          </div>
          <span style={{ width: "1px", height: "14px", background: "rgba(255,255,255,0.08)", flexShrink: 0 }} aria-hidden="true" />
          <div className="dash-status-item">
            <span className="dash-status-label">SOURCE</span>
            <span className="dash-status-val font-mono">{sourceText}</span>
          </div>
          <span style={{ width: "1px", height: "14px", background: "rgba(255,255,255,0.08)", flexShrink: 0 }} aria-hidden="true" />
          <div className="dash-status-item">
            <span className="dash-status-label">MODE</span>
            <span className="dash-status-val font-mono">{modeText}</span>
          </div>
          <span style={{ width: "1px", height: "14px", background: "rgba(255,255,255,0.08)", flexShrink: 0 }} aria-hidden="true" />
          <div className="dash-status-item">
            <span className="dash-status-label">PROGRESS</span>
            <span className="dash-status-val font-mono">{progressText}</span>
          </div>
          <span style={{ width: "1px", height: "14px", background: "rgba(255,255,255,0.08)", flexShrink: 0 }} aria-hidden="true" />
          <div className="dash-status-item">
            <span className="dash-status-label">READINESS</span>
            <StatusBadge
              label={readinessText}
              tone={runtime.readiness?.status === "ready" ? "good" : runtime.readiness?.status === "degraded" ? "warning" : "neutral"}
            />
          </div>
        </div>

        {/* Connection State & Presentation Mode */}
        <div className="dash-header__actions">
          <div className="dash-connection-badge">
            <StatusBadge
              label={runtime.connected ? replayState : "TELEMETRY LOST"}
              tone={
                !runtime.connected
                  ? "danger"
                  : replayState === "RUNNING"
                  ? "good"
                  : replayState === "PAUSED" || replayState === "REBUILDING"
                  ? "warning"
                  : replayState === "FAILED" || replayState === "ERROR"
                  ? "danger"
                  : "neutral"
              }
            />
          </div>
          <button
            className={`dash-pres-btn font-sans ${presentationMode ? "is-active" : ""}`}
            onClick={onTogglePresentation}
            title="Press 'P' on keyboard to toggle presentation mode"
          >
            <span className="dash-pres-key">P</span> Pres {presentationMode ? "ON" : "OFF"}
          </button>
        </div>
      </div>

      {/* Navigation Bar (Fortexa Pill Navigation) */}
      <nav className="dash-nav" aria-label="Primary dashboard navigation">
        <div className="dash-nav__inner">
          {navigationItems.map((item) => (
            <button
              key={item.id}
              className={`dash-nav__tab font-sans ${activePage === item.id ? "is-active" : ""}`}
              onClick={() => onPageChange(item.id)}
            >
              <span className="dash-nav__num">{item.number}</span>
              <span className="dash-nav__label">{item.label}</span>
            </button>
          ))}
        </div>
      </nav>

      {/* Connection & Degradation Banners */}
      {!runtime.connected ? (
        <div className="dash-banner dash-banner--danger" role="alert">
          <span className="dash-banner__icon">⚠</span>
          <div>
            <strong>Telemetry connection lost.</strong>{" "}
            {runtime.error ?? "Attempting to reconnect to the local Custodian runtime at 127.0.0.1:8000..."}
          </div>
        </div>
      ) : runtime.readiness?.status === "degraded" ? (
        <div className="dash-banner dash-banner--warning" role="alert">
          <span className="dash-banner__icon">⚡</span>
          <div>
            <strong>Passive runtime degraded.</strong>{" "}
            Model checks or runtime components are reporting partial capability.
          </div>
        </div>
      ) : null}
    </header>
  );
}
