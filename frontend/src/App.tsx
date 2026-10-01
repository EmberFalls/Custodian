import { useEffect, useState } from "react";
import { LandingPage } from "./LandingPage";
import { Sidebar } from "./components/dashboard/Sidebar";
import { TopHeader } from "./components/dashboard/TopHeader";
import { LiveMonitorPage } from "./components/dashboard/LiveMonitorPage";
import { AlertsPage } from "./components/dashboard/AlertsPage";
import { TrafficPage } from "./components/dashboard/TrafficPage";
import { DetectorsPage } from "./components/dashboard/DetectorsPage";
import { PerformancePage } from "./components/dashboard/PerformancePage";
import { DockedReplayPlayer } from "./components/dashboard/DockedReplayPlayer";
import { LoginModal } from "./components/LoginModal";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { DashboardTelemetryProvider, useDashboard } from "./context/DashboardTelemetryContext";
import "./styles/dashboard-shadcn.css";

function DashboardInner({ onNavigateHome, onSignOut }: { onNavigateHome: () => void; onSignOut: () => void }) {
  const { activeTab, presentationMode, setPresentationMode } = useDashboard();

  // Keyboard shortcut: P toggles presentation mode
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (
        event.key.toLowerCase() === "p" &&
        !(event.target instanceof HTMLInputElement) &&
        !(event.target instanceof HTMLTextAreaElement) &&
        !(event.target instanceof HTMLSelectElement)
      ) {
        setPresentationMode((c) => !c);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [setPresentationMode]);

  return (
    <div className={`shadcn-dashboard ${presentationMode ? "shad-presentation-mode" : ""}`}>
      {/* 1. Sleek Left Sidebar (Screenshot 1 & 2) */}
      <Sidebar onNavigateHome={onNavigateHome} onSignOut={onSignOut} />

      {/* 2. Main Content Area */}
      <div className="shad-main-area">
        {/* Top Header */}
        <TopHeader />

        {/* Page Content with smooth tab transition */}
        <main key={activeTab} className="shad-page-content">
          {activeTab === "monitor" && <LiveMonitorPage />}
          {activeTab === "alerts" && <AlertsPage />}
          {activeTab === "traffic" && <TrafficPage />}
          {activeTab === "detectors" && <DetectorsPage />}
          {activeTab === "performance" && <PerformancePage />}
        </main>
      </div>

      {/* 3. Docked Bottom Replay Player */}
      <DockedReplayPlayer />

      {/* Auth modal if needed */}
      <LoginModal />
    </div>
  );
}

function MainView() {
  const [view, setView] = useState<"landing" | "dashboard">("landing");
  const { user, logout, openAuthModal } = useAuth();

  const handleLaunchDashboard = () => {
    if (!user) {
      openAuthModal();
    } else {
      setView("dashboard");
    }
  };

  const handleSignOut = async () => {
    await logout();
    setView("landing");
  };

  if (view === "landing") {
    return (
      <>
        <LandingPage onLaunchDashboard={handleLaunchDashboard} />
        <LoginModal onSuccess={() => setView("dashboard")} />
      </>
    );
  }

  return (
    <DashboardTelemetryProvider onNavigateHome={() => setView("landing")} onSignOut={handleSignOut}>
      <DashboardInner onNavigateHome={() => setView("landing")} onSignOut={handleSignOut} />
    </DashboardTelemetryProvider>
  );
}

export function App() {
  return (
    <AuthProvider>
      <MainView />
    </AuthProvider>
  );
}
