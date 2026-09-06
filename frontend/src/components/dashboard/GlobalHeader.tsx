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

const navigationItems: Array<{ id: DashboardPage; num: string; label: string }> = [
  { id: "monitor",     num: "01", label: "LIVE MONITOR" },
  { id: "alerts",      num: "02", label: "ALERTS" },
  { id: "traffic",     num: "03", label: "TRAFFIC" },
  { id: "detectors",   num: "04", label: "DETECTORS" },
  { id: "performance", num: "05", label: "PERFORMANCE" },
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
  const returnPath = runtime.status?.return_path ?? "NONE";
  const sourceText = runtime.status?.source_type
    ? runtime.status.source_type.replaceAll("_", " ").toUpperCase()
    : "PCAP REPLAY";
  const modeText = runtime.status?.mode
    ? runtime.status.mode.toUpperCase()
    : "PACED";
  const progressText =
    runtime.status?.progress != null && runtime.status.progress >= 0
      ? `${Math.round(runtime.status.progress * 100)}%`
      : "—";
  const readinessState = runtime.readiness?.status?.toUpperCase() ?? "UNAVAILABLE";

  const replayState = !runtime.connected
    ? "TELEMETRY LOST"
    : runtime.status?.replay_state ?? "IDLE";

  return (
    <header className="dash-header">
      {/* 1. Global Safety & Operational Status Bar */}
      <div className="dash-header__top">
        {/* Brand */}
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
            <CustodianShieldIcon size={22} />
            <div>
              <div className="dash-brand-name font-sans">
                CUSTODIAN <span className="dash-brand-badge font-mono">PASSIVE</span>
              </div>
            </div>
          </div>
        </div>

        {/* 6 Core Global Status Questions */}
        <div className="dash-status-strip" aria-label="Global runtime telemetry status">
          <div className="dash-status-item">
            <span className="dash-status-label">MONITOR</span>
            <StatusBadge
              label={monitorState}
              tone={monitorState === "ACTIVE" ? "good" : "danger"}
            />
          </div>
          <div className="dash-status-item">
            <span className="dash-status-label">RETURN PATH</span>
            <span className="dash-status-val font-mono">{returnPath}</span>
          </div>
          <div className="dash-status-item">
            <span className="dash-status-label">SOURCE</span>
            <span className="dash-status-val font-mono">{sourceText}</span>
          </div>
          <div className="dash-status-item">
            <span className="dash-status-label">MODE</span>
            <span className="dash-status-val font-mono">{modeText}</span>
          </div>
          <div className="dash-status-item">
            <span className="dash-status-label">PROGRESS</span>
            <span className="dash-status-val font-mono">{progressText}</span>
          </div>
          <div className="dash-status-item">
            <span className="dash-status-label">READINESS</span>
            <StatusBadge
              label={readinessState}
              tone={readinessState === "READY" ? "good" : readinessState === "DEGRADED" ? "warning" : "neutral"}
            />
          </div>
        </div>

        {/* Right Actions: Replay State + Presentation */}
        <div className="dash-header__actions">
          <div className="dash-connection-badge">
            <StatusBadge
              label={replayState}
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
            <span className="dash-pres-key font-mono">P</span> Pres {presentationMode ? "ON" : "OFF"}
          </button>
        </div>
      </div>

      {/* 2. Numbered Pill Navigation Rail */}
      <div className="dash-nav-bar">
        <nav className="dash-nav-center" aria-label="Primary dashboard navigation">
          {navigationItems.map((item) => (
            <button
              key={item.id}
              className={`dash-nav__tab font-sans ${activePage === item.id ? "is-active" : ""}`}
              onClick={() => onPageChange(item.id)}
            >
              <span className="dash-nav__num font-mono">{item.num}</span>
              <span className="dash-nav__label">{item.label}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* 3. Connection & Degradation Banners (No Emojis) */}
      {!runtime.connected ? (
        <div className="dash-banner dash-banner--danger" role="alert">
          <span className="dash-banner__icon font-mono">[!]</span>
          <div>
            <strong>Telemetry connection lost.</strong>{" "}
            {runtime.error ?? "Attempting to reconnect to the local Custodian runtime at 127.0.0.1:8000..."}
          </div>
        </div>
      ) : runtime.readiness?.status === "degraded" ? (
        <div className="dash-banner dash-banner--warning" role="alert">
          <span className="dash-banner__icon font-mono">[*]</span>
          <div>
            <strong>Passive runtime degraded.</strong>{" "}
            Model checks or runtime components are reporting partial capability.
          </div>
        </div>
      ) : null}

      <div className="dash-nav" aria-hidden="true" />
    </header>
  );
}
