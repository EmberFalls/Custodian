import { useEffect, useState } from "react";

import { api } from "../runtime";
import type { CaptureCandidate, RuntimeStatus } from "../types";
import { StatusBadge } from "./Visuals";

interface CaptureInterface {
  interface_id: string;
  name: string;
  description: string;
  available: boolean;
  link_type: number | null;
}

export function ReplayControl({
  status,
  captures,
  onComplete,
}: {
  status: RuntimeStatus | null;
  captures: CaptureCandidate[];
  onComplete: () => Promise<void>;
}) {
  const [capture, setCapture] = useState("");
  const [mode, setMode] = useState("fast");
  const [speed, setSpeed] = useState(2);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [anonymizeExport, setAnonymizeExport] = useState(true);
  const [ingestMode, setIngestMode] = useState<"pcap" | "live">("pcap");
  const [interfaces, setInterfaces] = useState<CaptureInterface[]>([]);
  const [interfaceId, setInterfaceId] = useState("");
  const [captureFilter, setCaptureFilter] = useState("");
  const [backendStatus, setBackendStatus] = useState("not checked");
  const [backendError, setBackendError] = useState("");
  const [interfaceRefresh, setInterfaceRefresh] = useState(0);

  useEffect(() => {
    if (!capture && captures.length) setCapture(captures[0].display_name);
  }, [capture, captures]);

  useEffect(() => {
    if (ingestMode !== "live") return;
    let active = true;
    api<{ status: string; interfaces: CaptureInterface[]; reason: string | null }>(
      "/api/v1/live/interfaces",
    )
      .then((result) => {
        if (!active) return;
        setInterfaces(result.interfaces);
        setBackendStatus(result.status);
        setBackendError(result.reason ?? "");
      })
      .catch((error) => {
        if (!active) return;
        setInterfaces([]);
        setBackendStatus("unavailable");
        setBackendError(error instanceof Error ? error.message : "Unable to list interfaces");
      });
    return () => { active = false; };
  }, [ingestMode, interfaceRefresh]);

  const control = async (path: string, body?: object) => {
    setBusy(true);
    try {
      const result = await api<{ status: string }>(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : undefined,
      });
      setMessage(result.status.toUpperCase());
      await onComplete();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Replay control failed");
    } finally {
      setBusy(false);
    }
  };

  const replayState = status?.replay_state ?? "IDLE";
  const selectedCapture = captures.find((item) => item.display_name === capture);
  const captureReady =
    selectedCapture?.status === "ready" ||
    selectedCapture?.status === "completed" ||
    selectedCapture?.status === "stopped";
  const displayedMode = status?.replay_running ? status.mode : mode;
  const displayedSpeed = status?.replay_running ? status.speed_multiplier : speed;

  const seekBy = (delta: number) => {
    const target = Math.max(0, Math.min(1, (status?.progress ?? 0) + delta));
    return control("/api/v1/replay/seek", { target_progress: target });
  };

  const createExport = async (format: "json" | "csv") => {
    setBusy(true);
    try {
      const result = await api<{ filename: string }>("/api/v1/exports", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ format, anonymize: anonymizeExport }),
      });
      setMessage(`CREATED runtime/reports/${result.filename}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Export failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel replay-control">
      <div className="panel__heading">
        <div>
          <div className="eyebrow">APPROVED LOCAL SOURCE</div>
          <h2>Replay control center</h2>
        </div>
        <StatusBadge
          label={replayState}
          tone={replayState === "RUNNING" ? "good" : replayState === "PAUSED" ? "warning" : "neutral"}
        />
      </div>

      <div className="replay-control__body">
        <div className="control-row" role="group" aria-label="Ingestion mode">
          <button
            className={`button ${ingestMode === "pcap" ? "button--primary" : ""}`}
            onClick={() => setIngestMode("pcap")}
            disabled={busy || Boolean(status?.replay_running)}
          >
            PCAP / Offline
          </button>
          <button
            className={`button ${ingestMode === "live" ? "button--primary" : ""}`}
            onClick={() => setIngestMode("live")}
            disabled={busy || Boolean(status?.replay_running)}
          >
            Real-Time Capture
          </button>
        </div>

        {ingestMode === "pcap" ? <>
        {/* Row 1: PCAP source & replay mode */}
        <div className="replay-control__inputs">
          <label className="capture-input">
            <span className="input-label font-mono">APPROVED CAPTURE FILE</span>
            <select
              value={capture}
              onChange={(event) => setCapture(event.target.value)}
              disabled={busy || Boolean(status?.replay_running)}
              className="font-mono"
            >
              <option value="">Select a capture</option>
              {captures.map((item) => (
                <option value={item.display_name} key={item.display_name}>
                  {item.display_name} · {(item.status ?? "queued").toUpperCase()}
                </option>
              ))}
            </select>
          </label>

          <label className="capture-input" style={{ maxWidth: "260px" }}>
            <span className="input-label font-mono">REPLAY MODE</span>
            <select
              aria-label="Replay mode"
              value={displayedMode}
              onChange={(event) => setMode(event.target.value)}
              disabled={busy || Boolean(status?.replay_running)}
              className="font-mono"
            >
              <option value="paced">PACED · presentation</option>
              <option value="fast">FAST · no capture delay</option>
              <option value="benchmark">BENCHMARK · minimal updates</option>
            </select>
          </label>

          {displayedMode === "paced" ? (
            <label className="capture-input" style={{ maxWidth: "140px" }}>
              <span className="input-label font-mono">SPEED</span>
              <select
                aria-label="Replay speed"
                value={displayedSpeed}
                onChange={(event) => setSpeed(Number(event.target.value))}
                disabled={busy || Boolean(status?.replay_running)}
                className="font-mono"
              >
                {[1, 2, 5, 10].map((value) => (
                  <option key={value} value={value}>
                    {value}×
                  </option>
                ))}
              </select>
            </label>
          ) : null}
        </div>
        </> : <>
          <div className="replay-control__inputs">
            <label className="capture-input">
              <span className="input-label font-mono">CAPTURE BACKEND</span>
              <input value={`${backendStatus.toUpperCase()} · ${backendError}`} readOnly aria-label="Capture backend status" />
            </label>
            <label className="capture-input">
              <span className="input-label font-mono">SELECT ONE INTERFACE</span>
              <select
                value={interfaceId}
                onChange={(event) => setInterfaceId(event.target.value)}
                disabled={busy || Boolean(status?.replay_running)}
                aria-label="Network interface"
              >
                <option value="">Choose an interface explicitly</option>
                {interfaces.map((item) => (
                  <option key={item.interface_id} value={item.interface_id}>
                    {item.name} · {item.link_type == null ? "link type checked at start" : `link ${item.link_type}`}
                  </option>
                ))}
              </select>
            </label>
            <label className="capture-input">
              <span className="input-label font-mono">BACKEND CAPTURE FILTER</span>
              <input
                value={captureFilter}
                onChange={(event) => setCaptureFilter(event.target.value)}
                placeholder="No capture filter"
                disabled={busy || Boolean(status?.replay_running)}
                aria-label="Capture filter"
              />
            </label>
          </div>
          <p className="control-message" role="note">
            {status?.selected_interface
              ? `Selected interface: ${status.selected_interface} · Active filter: ${status.capture_filter || "None (unfiltered)"}`
              : "Capture is passive and starts only after you select one interface and press Start. No capture filter is applied by default."}
          </p>
        </>}

        {/* Replay Progress (when active) */}
        {ingestMode === "pcap" && status?.progress != null ? (
          <div className="replay-progress">
            <progress value={status.progress} max={1} aria-label="Capture processing progress" />
            <span className="font-mono">
              {status.rebuilding
                ? `Rebuilding ${((status.rebuild_progress ?? 0) * 100).toFixed(1)}%`
                : `${(status.progress * 100).toFixed(1)}% of capture processed`}
              {" · "}
              {status.mode.toUpperCase()}
              {status.mode === "paced" ? ` · ${status.speed_multiplier}×` : ""}
            </span>
          </div>
        ) : null}

        {/* Row 2: Action Buttons & Exports */}
        <div className="replay-control__actions">
          <div className="control-row">
            {ingestMode === "pcap" ? <>
            <button
              className="button button--primary"
              title={captureReady ? "Start passive replay" : "Validate this capture before starting"}
              onClick={() => void control("/api/v1/replay/start", { capture: capture.trim(), mode, speed_multiplier: speed })}
              disabled={busy || !capture.trim() || !captureReady || !status || Boolean(status?.replay_running)}
            >
              ▶ Start replay
            </button>
            <button
              className="button"
              onClick={() => void control("/api/v1/captures/validate", { capture: capture.trim() })}
              disabled={busy || !capture.trim() || Boolean(status?.replay_running)}
            >
              Validate
            </button>
            {status?.replay_running && !status.replay_paused ? (
              <button className="button" onClick={() => void control("/api/v1/replay/pause")} disabled={busy}>
                ⏸ Pause
              </button>
            ) : null}
            {status?.replay_running && status.replay_paused ? (
              <button className="button" onClick={() => void control("/api/v1/replay/resume")} disabled={busy}>
                ▶ Resume
              </button>
            ) : null}
            <button
              className="button"
              onClick={() => void control("/api/v1/replay/stop")}
              disabled={busy || !status?.replay_running}
            >
              ⏹ Stop
            </button>
            </> : <>
              {status?.source_type === "LIVE_PASSIVE" && status.replay_running ? (
                <button
                  className="button"
                  onClick={() => void control("/api/v1/live/stop")}
                  disabled={busy}
                >
                  ⏹ Stop capture
                </button>
              ) : (
                <button
                  className="button button--primary"
                  onClick={() => void control("/api/v1/live/start", {
                    interface_id: interfaceId,
                    capture_filter: captureFilter.trim() || null,
                  })}
                  disabled={busy || !interfaceId || backendStatus !== "ready" || Boolean(status?.replay_running)}
                  title={!interfaceId ? "Select one interface explicitly" : "Start passive capture"}
                >
                  ▶ Start capture
                </button>
              )}
              <button
                className="button"
                onClick={() => setInterfaceRefresh((value) => value + 1)}
                disabled={busy}
              >
                ↻ Refresh interfaces
              </button>
            </>}
            {ingestMode === "pcap" ? <>
            <button
              className="button font-mono"
              onClick={() => void seekBy(-0.1)}
              disabled={busy || !status?.capture}
            >
              ← 10%
            </button>
            <button
              className="button font-mono"
              onClick={() => void seekBy(0.1)}
              disabled={busy || !status?.capture}
            >
              10% →
            </button>
            <button
              className="button"
              onClick={() => void control("/api/v1/replay/reset")}
              disabled={busy || Boolean(status?.replay_running)}
            >
              Reset
            </button>
            </> : null}
          </div>

          <div className="control-row export-row">
            <label className="export-privacy font-sans">
              <input
                type="checkbox"
                checked={anonymizeExport}
                onChange={(event) => setAnonymizeExport(event.target.checked)}
              />
              Anonymize endpoint addresses
            </label>
            <button className="button font-sans" onClick={() => void createExport("json")} disabled={busy}>
              Export JSON
            </button>
            <button className="button font-sans" onClick={() => void createExport("csv")} disabled={busy}>
              Export CSV
            </button>
          </div>
        </div>

        {/* Row 3: Status Summary & Truthfulness Notice */}
        <div className="replay-control__footer">
          <div className="replay-source font-mono">
            <span>ACTIVE SOURCE:</span>
            <strong>{status?.capture ?? "No capture active"}</strong>
            <span>MODE:</span>
            <strong>{status?.mode?.toUpperCase() ?? "IDLE"}</strong>
          </div>
          <p className="control-message" role="status">
            {status?.error ||
              (ingestMode === "live" && backendError ? backendError : "") ||
              message ||
              "Each replay starts a fresh session. Processing throughput measures this laptop; it is separate from the capture's original traffic rate."}
          </p>
        </div>
      </div>
    </section>
  );
}
