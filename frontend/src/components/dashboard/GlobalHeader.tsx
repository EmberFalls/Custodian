import { CustodianShieldIcon } from "../landing/icons/CustodianShieldIcon";
import { StatusBadge } from "../Visuals";
import type { useRuntimeTelemetry } from "../../hooks/useRuntimeTelemetry";
import { useAuth } from "../../context/AuthContext";

export type DashboardPage = "monitor" | "alerts" | "traffic" | "detectors" | "performance";

interface GlobalHeaderProps {
  runtime: ReturnType<typeof useRuntimeTelemetry>;
  activePage: DashboardPage;
  onPageChange: (page: DashboardPage) => void;
  onNavigateHome: () => void;
  presentationMode: boolean;
  onTogglePresentation: () => void;
  onSignOut: () => void;
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
  onSignOut,
}: GlobalHeaderProps) {
  const { user } = useAuth();
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

          {/* User Info + Sign Out — always visible in dashboard (auth is required) */}
          {user && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "4px 12px",
                borderRadius: "8px",
                backgroundColor: "rgba(24, 24, 27, 0.9)",
                border: "1px solid rgba(255, 255, 255, 0.12)",
                fontSize: "12px",
                whiteSpace: "nowrap",
                boxShadow: "0 2px 8px rgba(0, 0, 0, 0.3)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span style={{ fontSize: "14px" }}>
                  {user.role === "Admin" ? "🛡️" : user.role === "Analyst" ? "🔍" : "👁️"}
                </span>
                <span style={{ fontWeight: 600, color: "#f4f4f5", letterSpacing: "-0.01em" }}>{user.display_name}</span>
                <span
                  style={{
                    fontSize: "10px",
                    fontWeight: 700,
                    padding: "2px 7px",
                    borderRadius: "4px",
                    fontFamily: "'IBM Plex Mono', monospace",
                    backgroundColor:
                      user.role === "Admin"
                        ? "rgba(239, 68, 68, 0.2)"
                        : user.role === "Analyst"
                        ? "rgba(56, 189, 248, 0.2)"
                        : "rgba(168, 85, 247, 0.2)",
                    color:
                      user.role === "Admin"
                        ? "#f87171"
                        : user.role === "Analyst"
                        ? "#38bdf8"
                        : "#c084fc",
                    border: `1px solid ${
                      user.role === "Admin"
                        ? "rgba(239, 68, 68, 0.35)"
                        : user.role === "Analyst"
                        ? "rgba(56, 189, 248, 0.35)"
                        : "rgba(168, 85, 247, 0.35)"
                    }`,
                  }}
                >
                  {user.role}
                </span>
              </div>

              {/* Sign Out — takes user back to landing page */}
              <button
                onClick={onSignOut}
                title="Sign out of Custodian"
                style={{
                  background: "rgba(239, 68, 68, 0.16)",
                  border: "1px solid rgba(239, 68, 68, 0.4)",
                  borderRadius: "5px",
                  color: "#fca5a5",
                  cursor: "pointer",
                  fontSize: "11px",
                  fontWeight: 600,
                  padding: "4px 10px",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                  transition: "all 0.15s ease",
                  fontFamily: "'IBM Plex Sans', -apple-system, sans-serif",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = "rgba(239, 68, 68, 0.32)";
                  e.currentTarget.style.color = "#ffffff";
                  e.currentTarget.style.borderColor = "rgba(239, 68, 68, 0.6)";
                  e.currentTarget.style.transform = "translateY(-1px)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = "rgba(239, 68, 68, 0.16)";
                  e.currentTarget.style.color = "#fca5a5";
                  e.currentTarget.style.borderColor = "rgba(239, 68, 68, 0.4)";
                  e.currentTarget.style.transform = "none";
                }}
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                  <polyline points="16 17 21 12 16 7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
                Sign Out
              </button>
            </div>
          )}

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
