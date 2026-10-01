import React, { createContext, useContext, useMemo, useState } from "react";
import { useRuntimeTelemetry } from "../hooks/useRuntimeTelemetry";
import type { AlertRecord } from "../types";

export interface KPIStats {
  threatLevel: "CRITICAL" | "ELEVATED" | "NORMAL";
  criticalAlertsCount: number;
  totalAlertsCount: number;
  activeFlows: number;
  throughputMbps: number;
  packetRatePerSec: number;
  totalPackets: number;
  totalBytes: number;
  replayState: string;
  isReplaying: boolean;
  connected: boolean;
  error: string | null;
}

export interface WaveformPoint {
  timestamp: number;
  timeFormatted: string;
  mbps: number;
  packetsPerSecond: number;
  flowsPerSecond: number;
}

interface DashboardContextType {
  runtime: ReturnType<typeof useRuntimeTelemetry>;
  kpis: KPIStats;
  waveformHistory: WaveformPoint[];
  selectedAlert: AlertRecord | null;
  setSelectedAlert: (alert: AlertRecord | null) => void;
  isInvestigationFrozen: boolean;
  setInvestigationFrozen: (frozen: boolean) => void;
  activeTab: "monitor" | "alerts" | "traffic" | "detectors" | "performance";
  setActiveTab: (tab: "monitor" | "alerts" | "traffic" | "detectors" | "performance") => void;
  presentationMode: boolean;
  setPresentationMode: React.Dispatch<React.SetStateAction<boolean>>;
}

const DashboardTelemetryContext = createContext<DashboardContextType | null>(null);

export function DashboardTelemetryProvider({
  children,
}: {
  children: React.ReactNode;
  onNavigateHome?: () => void;
  onSignOut?: () => void;
}) {
  const runtime = useRuntimeTelemetry();
  const [selectedAlert, setSelectedAlert] = useState<AlertRecord | null>(null);
  const [isInvestigationFrozen, setInvestigationFrozen] = useState(false);
  const [activeTab, setActiveTab] = useState<"monitor" | "alerts" | "traffic" | "detectors" | "performance">("monitor");
  const [presentationMode, setPresentationMode] = useState(false);

  // Compute KPI summary
  const kpis = useMemo<KPIStats>(() => {
    const alerts = runtime.alerts || [];
    const criticalCount = alerts.filter(
      (a) => a.decision === "ACCEPT" || a.severity === "CRITICAL" || a.severity === "HIGH"
    ).length;

    let threatLevel: "CRITICAL" | "ELEVATED" | "NORMAL" = "NORMAL";
    if (criticalCount > 0) threatLevel = "CRITICAL";
    else if (alerts.length > 0) threatLevel = "ELEVATED";

    const isReplaying = Boolean(runtime.status?.replay_running && !runtime.status?.replay_paused);
    const mbps = isReplaying
      ? (runtime.metrics?.processing_rates?.mbps ?? 0)
      : (runtime.metrics?.average_processing_rates?.mbps ?? 0);

    return {
      threatLevel,
      criticalAlertsCount: criticalCount,
      totalAlertsCount: alerts.length,
      activeFlows: runtime.status?.active_flows ?? 0,
      throughputMbps: mbps,
      packetRatePerSec: runtime.metrics?.processing_rates?.packets_per_second ?? 0,
      totalPackets: runtime.metrics?.packets ?? 0,
      totalBytes: runtime.metrics?.bytes ?? 0,
      replayState: runtime.status?.replay_state ?? "IDLE",
      isReplaying,
      connected: runtime.connected,
      error: runtime.error,
    };
  }, [runtime]);

  // Compute Waveform History for Recharts
  const waveformHistory = useMemo<WaveformPoint[]>(() => {
    if (!runtime.history || runtime.history.length === 0) {
      return [];
    }
    return runtime.history.map((point) => {
      const d = new Date(point.observedAt);
      const timeFormatted = `${String(d.getMinutes()).padStart(2, "0")}:${String(d.getSeconds()).padStart(2, "0")}`;
      return {
        timestamp: point.observedAt,
        timeFormatted,
        mbps: Number((point.mbps ?? 0).toFixed(2)),
        packetsPerSecond: Math.round(point.packetsPerSecond ?? 0),
        flowsPerSecond: Math.round(point.flowsPerSecond ?? 0),
      };
    });
  }, [runtime.history]);

  return (
    <DashboardTelemetryContext.Provider
      value={{
        runtime,
        kpis,
        waveformHistory,
        selectedAlert,
        setSelectedAlert,
        isInvestigationFrozen,
        setInvestigationFrozen,
        activeTab,
        setActiveTab,
        presentationMode,
        setPresentationMode,
      }}
    >
      {children}
    </DashboardTelemetryContext.Provider>
  );
}

export function useDashboard() {
  const context = useContext(DashboardTelemetryContext);
  if (!context) {
    throw new Error("useDashboard must be used within a DashboardTelemetryProvider");
  }
  return context;
}
