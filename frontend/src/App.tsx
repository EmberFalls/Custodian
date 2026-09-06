import { useEffect, useState } from "react";
import { LandingPage } from "./LandingPage";

import { GlobalHeader } from "./components/dashboard/GlobalHeader";
import type { DashboardPage } from "./components/dashboard/GlobalHeader";
import { LiveMonitorPage } from "./components/dashboard/LiveMonitorPage";
import { AlertsPage } from "./components/dashboard/AlertsPage";
import { TrafficPage } from "./components/dashboard/TrafficPage";
import { DetectorsPage } from "./components/dashboard/DetectorsPage";
import { PerformancePage } from "./components/dashboard/PerformancePage";

import { useRuntimeTelemetry } from "./hooks/useRuntimeTelemetry";
import type { AlertRecord } from "./types";

export function App() {
  const [view, setView] = useState<"landing" | "dashboard">("landing");
  const runtime = useRuntimeTelemetry();
  const [page, setPage] = useState<DashboardPage>("monitor");
  const [selectedAlert, setSelectedAlert] = useState<AlertRecord | null>(null);
  const [presentationMode, setPresentationMode] = useState(false);

  // Keyboard: P toggles presentation mode
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (
        event.key.toLowerCase() === "p" &&
        !(event.target instanceof HTMLInputElement) &&
        !(event.target instanceof HTMLTextAreaElement) &&
        !(event.target instanceof HTMLSelectElement)
      ) {
        setPresentationMode((current) => !current);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  // Clear selected alert when run_id changes (new replay session)
  useEffect(() => {
    setSelectedAlert(null);
  }, [runtime.status?.run_id]);

  // Keep selected alert in sync with updated alert data
  useEffect(() => {
    setSelectedAlert((current) =>
      current
        ? runtime.alerts.find((alert) => alert.alert_id === current.alert_id) ?? current
        : null,
    );
  }, [runtime.alerts]);

  if (view === "landing") {
    return <LandingPage onLaunchDashboard={() => setView("dashboard")} />;
  }

  return (
    <div className={`dash-shell ${presentationMode ? "dash-presentation" : ""}`}>
      <GlobalHeader
        runtime={runtime}
        activePage={page}
        onPageChange={setPage}
        onNavigateHome={() => setView("landing")}
        presentationMode={presentationMode}
        onTogglePresentation={() => setPresentationMode((c) => !c)}
      />

      <main className="dash-main">
        {page === "monitor" ? (
          <LiveMonitorPage
            runtime={runtime}
            selectedAlert={selectedAlert}
            onSelectAlert={setSelectedAlert}
          />
        ) : null}

        {page === "alerts" ? (
          <AlertsPage
            alerts={runtime.alerts}
            selectedAlert={selectedAlert}
            onSelectAlert={setSelectedAlert}
            onChanged={runtime.refresh}
          />
        ) : null}

        {page === "traffic" ? <TrafficPage runtime={runtime} /> : null}

        {page === "detectors" ? <DetectorsPage runtime={runtime} /> : null}

        {page === "performance" ? <PerformancePage runtime={runtime} /> : null}
      </main>
    </div>
  );
}
