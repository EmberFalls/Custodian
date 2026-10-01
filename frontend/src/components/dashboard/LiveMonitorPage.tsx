import React from "react";
import { KPIGrid } from "./KPIGrid";
import { TelemetryWaveform } from "./TelemetryWaveform";
import { IncidentsTable } from "./IncidentsTable";
import { SlideOverInspector } from "./SlideOverInspector";

export function LiveMonitorPage() {
  return (
    <div className="shad-content-container">
      {/* 1. KPI Cards Row (Matching Screenshot 1) */}
      <KPIGrid />

      {/* 2. Waveform Spline Area Chart (Matching Screenshot 1) */}
      <TelemetryWaveform />

      {/* 3. Incidents & Alerts Table (Matching Screenshot 2) */}
      <IncidentsTable />

      {/* 4. Slide-Over Inspector Drawer */}
      <SlideOverInspector />
    </div>
  );
}
