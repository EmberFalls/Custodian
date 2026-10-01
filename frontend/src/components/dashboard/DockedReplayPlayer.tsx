import { useEffect, useState } from "react";
import type { MouseEvent } from "react";
import { HardDrive, Pause, Play, Radio, RefreshCw, Square } from "lucide-react";
import { useDashboard } from "../../context/DashboardTelemetryContext";
import { api } from "../../runtime";

interface CaptureInterface {
  interface_id: string;
  name: string;
  description: string;
  available: boolean;
  link_type: number | null;
}

interface InterfaceResponse {
  status: string;
  reason: string | null;
  interfaces: CaptureInterface[];
}

type IngestMode = "pcap" | "live";

export function DockedReplayPlayer() {
  const { runtime } = useDashboard();
  const status = runtime.status;
  const captures = runtime.captures || [];
  const [mode, setMode] = useState<IngestMode>("pcap");
  const [capture, setCapture] = useState("");
  const [replayMode, setReplayMode] = useState<"paced" | "fast" | "benchmark">("fast");
  const [speed, setSpeed] = useState<1 | 2 | 5 | 10>(1);
  const [interfaceId, setInterfaceId] = useState("");
  const [captureFilter, setCaptureFilter] = useState("");
  const [interfaces, setInterfaces] = useState<CaptureInterface[]>([]);
  const [backendStatus, setBackendStatus] = useState("not checked");
  const [backendError, setBackendError] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [interfaceRefresh, setInterfaceRefresh] = useState(0);

  useEffect(() => {
    if (!capture && captures.length) setCapture(captures[0].display_name);
  }, [capture, captures]);

  useEffect(() => {
    if (mode !== "live") return;
    let active = true;
    setBackendStatus("checking");
    api<InterfaceResponse>("/api/v1/live/interfaces")
      .then((result) => {
        if (!active) return;
        setInterfaces(result.interfaces);
        setBackendStatus(result.status);
        setBackendError(result.reason ?? "");
        setInterfaceId((current) => result.interfaces.some((item) => item.interface_id === current) ? current : "");
      })
      .catch((error) => {
        if (!active) return;
        setInterfaces([]);
        setBackendStatus("unavailable");
        setBackendError(error instanceof Error ? error.message : "Unable to list interfaces");
      });
    return () => { active = false; };
  }, [mode, interfaceRefresh]);

  const request = async (path: string, body?: object) => {
    setBusy(true);
    setMessage("");
    try {
      await api(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : undefined,
      });
      await runtime.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Request failed");
    } finally {
      setBusy(false);
    }
  };

  const selectedCapture = captures.find((item) => item.display_name === capture);
  const captureReady = ["ready", "completed", "stopped"].includes(selectedCapture?.status ?? "");
  const isLiveSession = status?.source_type === "LIVE_PASSIVE";
  const isRunning = Boolean(status?.replay_running);
  const progress = Math.round((status?.progress ?? 0) * 100);

  const startPcap = async () => {
    if (!captureReady) {
      setMessage("Validate this capture before starting replay.");
      return;
    }
    await request("/api/v1/replay/start", {
      capture,
      mode: replayMode,
      speed_multiplier: speed,
    });
  };

  const startLive = () => request("/api/v1/live/start", {
    interface_id: interfaceId,
    capture_filter: captureFilter.trim() || null,
  });

  const stop = () => request(isLiveSession ? "/api/v1/live/stop" : "/api/v1/replay/stop");

  const seekReplay = (event: MouseEvent<HTMLDivElement>) => {
    if (!isRunning || isLiveSession || mode !== "pcap") return;
    const bounds = event.currentTarget.getBoundingClientRect();
    const target = Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width));
    void request("/api/v1/replay/seek", { target_progress: target });
  };

  return (
    <div className="shad-docked-player" role="region" aria-label="Passive ingest controls">
      <div className="shad-player__left">
        <div className="shad-ingest-mode" role="group" aria-label="Input mode">
          <button className={mode === "pcap" ? "is-active" : ""} onClick={() => setMode("pcap")} disabled={busy || isRunning}>
            <HardDrive size={13} /> PCAP
          </button>
          <button className={mode === "live" ? "is-active" : ""} onClick={() => setMode("live")} disabled={busy || isRunning}>
            <Radio size={13} /> Live
          </button>
        </div>

        {mode === "pcap" ? (
          <>
            <label className="shad-player-field">
              <span>CAPTURE</span>
              <select value={capture} onChange={(event) => setCapture(event.target.value)} disabled={busy || isRunning}>
                <option value="">Choose PCAP</option>
                {captures.map((item) => (
                  <option value={item.display_name} key={item.display_name}>
                    {item.display_name} · {(item.status ?? "queued").toUpperCase()}
                  </option>
                ))}
              </select>
            </label>
            <label className="shad-player-field shad-player-field--mode">
              <span>REPLAY</span>
              <select value={replayMode} onChange={(event) => setReplayMode(event.target.value as typeof replayMode)} disabled={busy || isRunning}>
                <option value="fast">Fast</option>
                <option value="paced">Paced</option>
                <option value="benchmark">Benchmark</option>
              </select>
            </label>
            {replayMode === "paced" ? (
              <label className="shad-player-field shad-player-field--speed">
                <span>SPEED</span>
                <select value={speed} onChange={(event) => setSpeed(Number(event.target.value) as typeof speed)} disabled={busy || isRunning}>
                  {[1, 2, 5, 10].map((value) => <option key={value} value={value}>{value}×</option>)}
                </select>
              </label>
            ) : null}
          </>
        ) : (
          <>
            <label className="shad-player-field shad-player-field--interface">
              <span>ONE INTERFACE</span>
              <select value={interfaceId} onChange={(event) => setInterfaceId(event.target.value)} disabled={busy || isRunning}>
                <option value="">{backendStatus === "ready" ? "Select interface" : backendStatus.toUpperCase()}</option>
                {interfaces.map((item) => (
                  <option key={item.interface_id} value={item.interface_id}>
                    {item.name} · {item.link_type == null ? "link checked on start" : `link ${item.link_type}`}
                  </option>
                ))}
              </select>
            </label>
            <label className="shad-player-field shad-player-field--filter">
              <span>BPF FILTER · OPTIONAL</span>
              <input value={captureFilter} onChange={(event) => setCaptureFilter(event.target.value)} placeholder="All visible traffic" maxLength={512} disabled={busy || isRunning} />
            </label>
            <button className="shad-btn shad-btn--ghost shad-interface-refresh" onClick={() => setInterfaceRefresh((value) => value + 1)} disabled={busy || isRunning} title="Refresh interfaces" aria-label="Refresh interfaces">
              <RefreshCw size={14} />
            </button>
          </>
        )}
      </div>

      <div className="shad-player__center">
        <div className="shad-player-status-line">
          <span className={isRunning ? "shad-replay-badge--live" : ""}>
            {isRunning ? (isLiveSession ? "CAPTURING" : status?.replay_state) : status?.replay_state ?? "IDLE"}
            {isLiveSession && status?.selected_interface ? ` · ${status.selected_interface}` : ""}
          </span>
          {mode === "pcap" && !isLiveSession ? <span>{progress}%</span> : <span>{mode === "live" ? backendStatus.toUpperCase() : "LOCAL REPLAY"}</span>}
        </div>
        {mode === "pcap" && !isLiveSession ? (
          <div className="shad-scrubber" onClick={seekReplay} title={isRunning ? "Click to rebuild replay at this point" : "Replay progress"}>
            <div className="shad-scrubber__fill" style={{ width: `${progress}%` }} />
          </div>
        ) : (
          <div className="shad-player-hint" title={backendError || "Passive; no outbound network action"}>
            {message || backendError || (isLiveSession ? `Passive capture · ${status?.capture_filter || "no filter"}` : "Live capture starts only after explicit interface selection.")}
          </div>
        )}
      </div>

      <div className="shad-player__right">
        {isRunning ? (
          <>
            {!isLiveSession && !status?.replay_paused ? (
              <button className="shad-btn shad-btn--secondary" onClick={() => void request("/api/v1/replay/pause")} disabled={busy} title="Pause replay"><Pause size={15} /> Pause</button>
            ) : null}
            {!isLiveSession && status?.replay_paused ? (
              <button className="shad-btn shad-btn--secondary" onClick={() => void request("/api/v1/replay/resume")} disabled={busy} title="Resume replay"><Play size={15} /> Resume</button>
            ) : null}
            <button className="shad-btn shad-btn--danger" onClick={() => void stop()} disabled={busy} title={isLiveSession ? "Stop live capture" : "Stop replay"}>
              <Square size={13} /> Stop
            </button>
          </>
        ) : mode === "live" ? (
          <button className="shad-btn shad-btn--primary" onClick={() => void startLive()} disabled={busy || backendStatus !== "ready" || !interfaceId} title={!interfaceId ? "Select one interface explicitly" : "Start passive capture"}>
            <Play size={15} /> Start capture
          </button>
        ) : (
          <button className="shad-btn shad-btn--primary" onClick={() => void startPcap()} disabled={busy || !capture || !captureReady} title={!captureReady ? "Validate the PCAP first" : "Start local replay"}>
            <Play size={15} /> Start replay
          </button>
        )}
        {mode === "pcap" && !captureReady && capture ? (
          <button className="shad-btn shad-btn--outline" onClick={() => void request("/api/v1/captures/validate", { capture })} disabled={busy || isRunning}>
            Validate
          </button>
        ) : null}
      </div>
    </div>
  );
}
