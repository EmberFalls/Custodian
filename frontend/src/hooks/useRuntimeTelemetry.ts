import { useCallback, useEffect, useRef, useState } from "react";

import { api, makeTimelinePoint } from "../runtime";
import type { AlertRecord, CaptureCandidate, Diagnostics, FlowRecord, HostTimelinePoint, Readiness, RuntimeSnapshot, TelemetryEnvelope, TimelinePoint } from "../types";

const HISTORY_LIMIT = 720;
const initialSnapshot: RuntimeSnapshot = {
  status: null, metrics: null, detectors: [], alerts: [], history: [], connected: false, error: null,
  captures: [], flows: [], hostTimeline: [], readiness: null, diagnostics: null,
};

export function useRuntimeTelemetry(): RuntimeSnapshot & { refresh: () => Promise<void> } {
  const [snapshot, setSnapshot] = useState<RuntimeSnapshot>(initialSnapshot);
  const alertRef = useRef<{ run_id: number; alerts: AlertRecord[] } | null>(null);
  const eventSequenceRef = useRef(0);
  const alive = useRef(true);

  const applyTelemetry = useCallback(({ status, metrics, detectors }: TelemetryEnvelope) => {
    if (!alive.current) return;
    setSnapshot((previous) => {
      const sameRun = previous.status?.run_id === status.run_id;
      const retained = sameRun ? previous.history : [];
      const byTime = new Map(retained.map((point) => [point.observedAt, point]));
      const history: TimelinePoint[] = metrics.rate_samples.slice(-HISTORY_LIMIT).map((sample) => {
        const existing = byTime.get(sample.observed_at);
        if (existing) return existing;
        const point = makeTimelinePoint(metrics, status, undefined, sample.observed_at);
        return {
          ...point, bytes: sample.bytes, packets: sample.packets, flows: sample.flows,
          flowUpdates: sample.flow_updates, mbps: sample.mbps,
          packetsPerSecond: sample.packets_per_second, flowsPerSecond: sample.flows_per_second,
        };
      });
      const alerts = alertRef.current?.run_id === status.run_id ? alertRef.current.alerts : sameRun ? previous.alerts : [];
      return { ...previous, status, metrics, detectors, alerts, history, connected: true, error: status.error };
    });
  }, []);

  const refresh = useCallback(async () => {
    try {
      const [telemetry, alerts, captures, flows, hostTimeline, readiness, diagnostics] = await Promise.all([
        api<TelemetryEnvelope>("/api/v1/telemetry"),
        api<AlertRecord[]>("/api/v1/alerts"),
        api<CaptureCandidate[]>("/api/v1/captures"),
        api<FlowRecord[]>("/api/v1/flows?limit=100"),
        api<HostTimelinePoint[]>("/api/v1/timeline?limit=500"),
        api<Readiness>("/api/v1/readiness"),
        api<Diagnostics>("/api/v1/diagnostics"),
      ]);
      alertRef.current = { run_id: telemetry.status.run_id, alerts };
      applyTelemetry(telemetry);
      setSnapshot((previous) => ({ ...previous, captures, flows, hostTimeline, readiness, diagnostics }));
    } catch (error) {
      if (alive.current) setSnapshot((previous) => ({
        ...previous, connected: false,
        error: error instanceof Error ? error.message : "Unable to reach the local runtime",
      }));
    }
  }, [applyTelemetry]);

  useEffect(() => {
    alive.current = true;
    let stopped = false;
    const sockets = new Set<WebSocket>();
    const retries = new Set<number>();
    const connect = (kind: "telemetry" | "alerts" | "events") => {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const path = kind === "events"
        ? `/api/v1/events?after_sequence=${eventSequenceRef.current}`
        : `/api/v1/stream/${kind}`;
      const socket = new WebSocket(`${protocol}//${window.location.host}${path}`);
      sockets.add(socket);
      socket.onmessage = (event) => {
        if (stopped) return;
        try {
          const payload = JSON.parse(event.data);
          if (kind === "telemetry") applyTelemetry(payload as TelemetryEnvelope);
          else if (kind === "alerts") {
            alertRef.current = payload;
            setSnapshot((previous) => previous.status?.run_id === payload.run_id
              ? { ...previous, alerts: payload.alerts } : previous);
          } else {
            eventSequenceRef.current = Math.max(
              eventSequenceRef.current,
              Number(payload.latest_sequence ?? 0),
            );
            void refresh();
          }
        } catch {
          setSnapshot((previous) => ({ ...previous, error: "Received invalid runtime telemetry." }));
        }
      };
      socket.onclose = () => {
        sockets.delete(socket);
        if (stopped) return;
        if (kind === "telemetry") setSnapshot((previous) => ({
          ...previous, connected: false, error: "Telemetry connection lost. Reconnecting to the local API…",
        }));
        const timer = window.setTimeout(() => { retries.delete(timer); connect(kind); }, 1000);
        retries.add(timer);
      };
      socket.onerror = () => socket.close();
    };
    void refresh();
    connect("telemetry");
    connect("alerts");
    connect("events");
    return () => {
      stopped = true;
      alive.current = false;
      retries.forEach(window.clearTimeout);
      sockets.forEach((socket) => socket.close());
    };
  }, [applyTelemetry, refresh]);

  return { ...snapshot, refresh };
}
