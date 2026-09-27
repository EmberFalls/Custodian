import React from "react";
import {
  Activity,
  ShieldAlert,
  Network,
  Cpu,
  Gauge,
  Home,
  Monitor,
  LogOut,
} from "lucide-react";
import { useDashboard } from "../../context/DashboardTelemetryContext";
import { useAuth } from "../../context/AuthContext";

export function Sidebar({ onNavigateHome, onSignOut }: { onNavigateHome: () => void; onSignOut: () => void }) {
  const { activeTab, setActiveTab, kpis, presentationMode, setPresentationMode } = useDashboard();
  const { user } = useAuth();

  const navItems = [
    { id: "monitor" as const, label: "Live Monitor", icon: Activity },
    {
      id: "alerts" as const,
      label: "Security Alerts",
      icon: ShieldAlert,
      badge: kpis.criticalAlertsCount > 0 ? kpis.criticalAlertsCount : undefined,
    },
    { id: "traffic" as const, label: "Traffic Analysis", icon: Network },
    { id: "detectors" as const, label: "Attack Detectors", icon: Cpu },
    { id: "performance" as const, label: "Engine Performance", icon: Gauge },
  ];

  return (
    <aside className="shad-sidebar" aria-label="Dashboard Navigation">
      <div className="shad-sidebar__top">
        {/* Brand */}
        <div className="shad-sidebar__brand">
          <div className="shad-sidebar__brand-text">
            <span className="shad-sidebar__brand-name">CUSTODIAN</span>
            <span className="shad-sidebar__brand-sub">
              <span
                className="inline-block w-1.5 h-1.5 rounded-full"
                style={{ background: kpis.connected ? "#10b981" : "#ef4444" }}
              />
              {kpis.isReplaying ? "Live Ingest" : "Passive Monitor"}
            </span>
          </div>
        </div>

        {/* Navigation Group: Operations */}
        <div className="shad-sidebar__nav-group">
          <div className="shad-sidebar__nav-title">Operations</div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`shad-sidebar__nav-item ${isActive ? "is-active" : ""}`}
                aria-current={isActive ? "page" : undefined}
              >
                <div className="shad-sidebar__nav-left">
                  <Icon size={16} />
                  <span>{item.label}</span>
                </div>
                {item.badge ? (
                  <span className="shad-sidebar__count-badge">{item.badge}</span>
                ) : null}
              </button>
            );
          })}
        </div>

        {/* Navigation Group: Quick Access */}
        <div className="shad-sidebar__nav-group">
          <div className="shad-sidebar__nav-title">System</div>
          <button
            onClick={() => setPresentationMode((prev) => !prev)}
            className={`shad-sidebar__nav-item ${presentationMode ? "is-active" : ""}`}
            title="Toggle presentation view (Key: P)"
          >
            <div className="shad-sidebar__nav-left">
              <Monitor size={16} />
              <span>Presentation (P)</span>
            </div>
          </button>
          <button
            onClick={onNavigateHome}
            className="shad-sidebar__nav-item"
            title="Return to Landing Page"
          >
            <div className="shad-sidebar__nav-left">
              <Home size={16} />
              <span>Landing Page</span>
            </div>
          </button>
        </div>
      </div>

      {/* Footer: User Profile */}
      <div className="shad-sidebar__bottom">
        <div className="shad-sidebar__user-card">
          <div className="shad-sidebar__user-avatar">
            {user?.display_name ? user.display_name[0].toUpperCase() : user?.username ? user.username[0].toUpperCase() : "P"}
          </div>
          <div className="shad-sidebar__user-info">
            <span className="shad-sidebar__user-name">{user?.display_name || user?.username || "SOC Analyst"}</span>
            <span className="shad-sidebar__user-role">{user?.role || "Security Analyst"}</span>
          </div>
          <button
            onClick={onSignOut}
            className="shad-btn shad-btn--ghost"
            style={{ padding: "4px" }}
            title="Sign Out"
            aria-label="Sign Out"
          >
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </aside>
  );
}
