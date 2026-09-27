import React, { useState, useEffect } from "react";
import {
  Play,
  Pause,
  RotateCcw,
  StepForward,
  Square,
  HardDrive,
  FastForward,
  Layers,
  ChevronDown
} from "lucide-react";
import { useDashboard } from "../../context/DashboardTelemetryContext";
import { api } from "../../runtime";

export function DockedReplayPlayer() {
  const { runtime } = useDashboard();
  const status = runtime.status;
  const captures = runtime.captures || [];

  const [capture, setCapture] = useState("");
  const [speed, setSpeed] = useState(1);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!capture && captures.length) {
      setCapture(captures[0].display_name);
    }
  }, [capture, captures]);

  const control = async (path: string, body?: object) => {
    setBusy(true);
    try {
      await api<{ status: string }>(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : undefined,
      });
      await runtime.refresh();
    } catch (error) {
      console.error("Replay control error:", error);
    } finally {
      setBusy(false);
    }
  };

  const isRunning = Boolean(status?.replay_running && !status?.replay_paused);
  const isPaused = Boolean(status?.replay_paused);
  const progressPercent = Math.round((status?.progress ?? 0) * 100);

  const handleTogglePlay = () => {
    if (!status?.replay_running) {
      control("/api/v1/replay/start", {
        source_type: "pcap",
        capture_name: capture,
        mode: "paced",
        speed_multiplier: speed,
      });
    } else if (isRunning) {
      control("/api/v1/replay/pause");
    } else if (isPaused) {
      control("/api/v1/replay/resume");
    }
  };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!status?.replay_running) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const targetProgress = Math.max(0, Math.min(1, clickX / rect.width));
    control("/api/v1/replay/seek", { target_progress: targetProgress });
  };

  return (
    <div className="shad-docked-player" role="region" aria-label="Replay Media Player">
      {/* Left: Playback Triggers & Status */}
      <div className="shad-player__left">
        {/* Play/Pause Button */}
        <button
          onClick={handleTogglePlay}
          disabled={busy || (!capture && !status?.replay_running)}
          className="shad-btn shad-btn--primary"
          style={{ width: "36px", height: "36px", borderRadius: "9999px", padding: 0 }}
          title={isRunning ? "Pause (Space)" : "Start Replay (Space)"}
          aria-label={isRunning ? "Pause Replay" : "Start Replay"}
        >
          {isRunning ? <Pause size={16} fill="currentColor" /> : <Play size={16} fill="currentColor" style={{ marginLeft: "2px" }} />}
        </button>

        {/* Step Forward */}
        <button
          onClick={() => control("/api/v1/replay/step")}
          disabled={busy || !status?.replay_running}
          className="shad-btn shad-btn--ghost"
          style={{ padding: "6px" }}
          title="Step Next Frame"
          aria-label="Step Next Frame"
        >
          <StepForward size={16} />
        </button>

        {/* Reset / Stop */}
        <button
          onClick={() => control("/api/v1/replay/stop")}
          disabled={busy || !status?.replay_running}
          className="shad-btn shad-btn--ghost"
          style={{ padding: "6px" }}
          title="Stop Replay"
          aria-label="Stop Replay"
        >
          <Square size={14} />
        </button>

        {/* Active Capture Dropdown */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <HardDrive size={14} className="text-zinc-400" />
          <select
            value={capture}
            onChange={(e) => setCapture(e.target.value)}
            disabled={busy || Boolean(status?.replay_running)}
            style={{
              background: "#18181b",
              border: "1px solid var(--dash-border)",
              borderRadius: "6px",
              color: "#f4f4f5",
              fontSize: "0.75rem",
              padding: "4px 8px",
              fontFamily: "monospace",
              outline: "none",
            }}
          >
            {captures.length === 0 ? (
              <option value="">No PCAP captures available</option>
            ) : (
              captures.map((c) => (
                <option key={c.display_name} value={c.display_name}>
                  {c.display_name}
                </option>
              ))
            )}
          </select>
        </div>
      </div>

      {/* Center: Interactive Scrubber Timeline */}
      <div className="shad-player__center">
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.7rem", color: "#71717a" }}>
          <span className={isRunning ? "shad-replay-badge--live" : ""}>
            {status?.replay_state || "IDLE"}
          </span>
          <span style={{ fontFamily: "monospace", color: "#f4f4f5" }}>{progressPercent}%</span>
        </div>
        <div className="shad-scrubber" onClick={handleSeek} title="Click to scrub replay timeline">
          <div className="shad-scrubber__fill" style={{ width: `${progressPercent}%` }} />
        </div>
      </div>

      {/* Right: Speed Multiplier Pills */}
      <div className="shad-player__right">
        <div className="shad-segmented-control" role="group" aria-label="Replay Speed">
          {[0.5, 1, 2, 5].map((s) => (
            <button
              key={s}
              onClick={() => {
                setSpeed(s);
                if (status?.replay_running) {
                  control("/api/v1/replay/speed", { speed_multiplier: s });
                }
              }}
              className={`shad-segment-btn ${speed === s ? "is-active" : ""}`}
              style={{ fontSize: "0.7rem", padding: "3px 8px" }}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
