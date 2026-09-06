import { useEffect, useRef, useState } from "react";

/* ──────────────────────────────────────────────
   Card 1: Animated Bidirectional Flow Assembler
   ─────────────────────────────────────────────── */
function FlowAssemblerCard() {
  const [step, setStep] = useState(0);

  const STEPS = [
    { flag: "SYN", dir: "→", color: "#c084fc", label: "Initiating handshake" },
    { flag: "SYN-ACK", dir: "←", color: "#34d399", label: "Server acknowledges" },
    { flag: "ACK", dir: "→", color: "#c084fc", label: "Connection established" },
    { flag: "DATA", dir: "⇄", color: "#60a5fa", label: "Bidirectional transfer" },
    { flag: "FIN", dir: "→", color: "#a78bfa", label: "Graceful close" },
    { flag: "FIN-ACK", dir: "←", color: "#a78bfa", label: "Flow archived" },
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setStep((s) => (s + 1) % STEPS.length);
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bento-card" style={{ gridColumn: "span 2" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px" }}>
        <div>
          <h3
            style={{
              margin: 0,
              fontFamily: "'IBM Plex Sans', -apple-system, sans-serif",
              fontSize: "1.1rem",
              fontWeight: 500,
              letterSpacing: "-0.02em",
              color: "#ffffff",
            }}
          >
            5-Tuple Bidirectional Flow Reconstructor
          </h3>
          <p
            style={{
              margin: "3px 0 0",
              fontFamily: "'IBM Plex Sans', sans-serif",
              fontSize: "0.82rem",
              color: "#a1a1aa",
            }}
          >
            Stateful TCP session tracking with microsecond inter-arrival timestamps and lifecycle accounting.
          </p>
        </div>

        <span
          style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: "0.7rem",
            color: "#c084fc",
            background: "rgba(124, 58, 237, 0.12)",
            border: "1px solid rgba(139, 92, 246, 0.3)",
            padding: "3px 8px",
            borderRadius: "4px",
          }}
        >
          LIVE RECONSTRUCTION
        </span>
      </div>

      {/* Reconstructed flow interactive strip */}
      <div
        style={{
          background: "rgba(18, 18, 21, 0.8)",
          border: "1px solid rgba(255, 255, 255, 0.07)",
          borderRadius: "8px",
          padding: "20px 24px",
          marginBottom: "16px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px" }}>
          {/* Client Node */}
          <div
            style={{
              background: "rgba(255, 255, 255, 0.03)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              borderRadius: "6px",
              padding: "10px 16px",
              fontFamily: "'IBM Plex Mono', monospace",
              textAlign: "left",
              minWidth: "150px",
            }}
          >
            <div style={{ fontSize: "0.65rem", color: "#71717a", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Origin Host
            </div>
            <div style={{ fontSize: "0.86rem", color: "#e4e4e7", fontWeight: 500, marginTop: "2px" }}>
              192.168.1.104
            </div>
            <div style={{ fontSize: "0.72rem", color: "#a1a1aa" }}>:54218</div>
          </div>

          {/* Flow vector visualization */}
          <div style={{ flex: 1, textAlign: "center" }}>
            <div
              style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: "1.4rem",
                color: STEPS[step].color,
                transition: "color 0.3s ease",
              }}
            >
              {STEPS[step].dir}
            </div>
            <div
              style={{
                display: "inline-block",
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: "0.72rem",
                fontWeight: 600,
                color: STEPS[step].color,
                background: "rgba(255, 255, 255, 0.04)",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                borderRadius: "4px",
                padding: "2px 8px",
                marginTop: "4px",
              }}
            >
              {STEPS[step].flag}
            </div>
            <div
              style={{
                fontFamily: "'IBM Plex Sans', sans-serif",
                fontSize: "0.74rem",
                color: "#71717a",
                marginTop: "4px",
              }}
            >
              {STEPS[step].label}
            </div>
          </div>

          {/* Destination Node */}
          <div
            style={{
              background: "rgba(255, 255, 255, 0.03)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              borderRadius: "6px",
              padding: "10px 16px",
              fontFamily: "'IBM Plex Mono', monospace",
              textAlign: "right",
              minWidth: "150px",
            }}
          >
            <div style={{ fontSize: "0.65rem", color: "#71717a", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Remote Peer
            </div>
            <div style={{ fontSize: "0.86rem", color: "#c084fc", fontWeight: 500, marginTop: "2px" }}>
              104.244.42.1
            </div>
            <div style={{ fontSize: "0.72rem", color: "#a1a1aa" }}>:443 (TLS 1.3)</div>
          </div>
        </div>

        {/* Telemetry Metrics */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: "12px",
            marginTop: "16px",
            paddingTop: "14px",
            borderTop: "1px solid rgba(255, 255, 255, 0.06)",
          }}
        >
          {[
            { label: "Forward Packets", value: "312 pkts" },
            { label: "Reverse Packets", value: "194 pkts" },
            { label: "Mean Inter-Arrival", value: "3.84 ms" },
            { label: "Active Duration", value: "1.62 s" },
          ].map((m) => (
            <div key={m.label} style={{ textAlign: "center" }}>
              <div style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontSize: "0.72rem", color: "#71717a" }}>
                {m.label}
              </div>
              <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: "0.88rem", color: "#f4f4f5", marginTop: "2px" }}>
                {m.value}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ──────────────────────────────────────────────
   Card 2: Dual-Confidence Decision Graph (SVG)
   ─────────────────────────────────────────────── */
function DualConfidenceCard() {
  const svgRef = useRef<SVGSVGElement>(null);
  const W = 320, H = 150;
  const padding = { top: 16, right: 16, bottom: 24, left: 36 };

  const heuristicPoints: [number, number][] = [];
  const mlPoints: [number, number][] = [];
  const threshold = 0.65;

  for (let i = 0; i <= 20; i++) {
    const t = i / 20;
    const x = padding.left + t * (W - padding.left - padding.right);
    const h = 0.28 + 0.38 * Math.sin(t * Math.PI * 1.25 + 0.4) + 0.06 * Math.sin(t * 8);
    const m = 0.22 + 0.44 * Math.sin(t * Math.PI * 1.15) + 0.08 * Math.cos(t * 6);
    heuristicPoints.push([x, H - padding.bottom - h * (H - padding.top - padding.bottom)]);
    mlPoints.push([x, H - padding.bottom - m * (H - padding.top - padding.bottom)]);
  }

  const pointsToPath = (pts: [number, number][]) =>
    pts.map((p, i) => (i === 0 ? `M ${p[0]} ${p[1]}` : `L ${p[0]} ${p[1]}`)).join(" ");

  const thresholdY = H - padding.bottom - threshold * (H - padding.top - padding.bottom);

  return (
    <div className="bento-card">
      <div style={{ marginBottom: "16px" }}>
        <h3
          style={{
            margin: 0,
            fontFamily: "'IBM Plex Sans', -apple-system, sans-serif",
            fontSize: "1.05rem",
            fontWeight: 500,
            color: "#ffffff",
          }}
        >
          Dual-Engine Confidence Scoring
        </h3>
        <p style={{ margin: "3px 0 0", fontFamily: "'IBM Plex Sans', sans-serif", fontSize: "0.8rem", color: "#a1a1aa" }}>
          Deterministic rule heuristics cross-validated with tree-based anomaly inference.
        </p>
      </div>

      <div style={{ background: "rgba(18, 18, 21, 0.8)", border: "1px solid rgba(255, 255, 255, 0.07)", borderRadius: "8px", padding: "8px" }}>
        <svg ref={svgRef} width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: "block" }}>
          <rect
            x={padding.left}
            y={padding.top}
            width={W - padding.left - padding.right}
            height={thresholdY - padding.top}
            fill="rgba(239, 68, 68, 0.04)"
          />
          <line
            x1={padding.left}
            y1={thresholdY}
            x2={W - padding.right}
            y2={thresholdY}
            stroke="rgba(239, 68, 68, 0.45)"
            strokeWidth="1"
            strokeDasharray="4 3"
          />
          <text
            x={W - padding.right - 4}
            y={thresholdY - 4}
            fill="#ef4444"
            fontSize="8"
            textAnchor="end"
            fontFamily="IBM Plex Mono"
          >
            ALERT THRESHOLD (0.65)
          </text>

          {/* ML Line (Purple) */}
          <path d={pointsToPath(mlPoints)} fill="none" stroke="#a855f7" strokeWidth="2" strokeLinecap="round" />

          {/* Heuristic Line (Slate / White) */}
          <path d={pointsToPath(heuristicPoints)} fill="none" stroke="#38bdf8" strokeWidth="1.8" strokeLinecap="round" />

          {/* Grid labels */}
          {[0.25, 0.5, 0.75].map((v) => {
            const y = H - padding.bottom - v * (H - padding.top - padding.bottom);
            return (
              <g key={v}>
                <line x1={padding.left} y1={y} x2={W - padding.right} y2={y} stroke="rgba(255, 255, 255, 0.04)" strokeWidth="0.5" />
                <text x={padding.left - 6} y={y + 3} fill="#71717a" fontSize="7.5" textAnchor="end" fontFamily="IBM Plex Mono">
                  {v.toFixed(2)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <div style={{ display: "flex", gap: "20px", marginTop: "12px", justifyContent: "flex-end" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <div style={{ width: "16px", height: "2px", background: "#38bdf8" }} />
          <span style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontSize: "0.75rem", color: "#a1a1aa" }}>Rule Engine</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <div style={{ width: "16px", height: "2px", background: "#a855f7" }} />
          <span style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontSize: "0.75rem", color: "#a1a1aa" }}>ML Classifier</span>
        </div>
      </div>
    </div>
  );
}

/* ──────────────────────────────────────────────
   Card 3: Observable DNS & TLS Inspector
   ─────────────────────────────────────────────── */
function DnsTlsCard() {
  const records = [
    { type: "TLS SNI", value: "api.cloudflare.com", detail: "TLS 1.3 · AES-256", status: "ok" },
    { type: "DNS A", value: "auth.internal.corp", detail: "RTT: 1.8ms", status: "ok" },
    { type: "DNS CNAME", value: "telemetry.edge.net", detail: "TTL: 300s", status: "ok" },
    { type: "TLS SNI", value: "unknown-staging.xyz", detail: "Risk: 0.84", status: "flag" },
  ];

  return (
    <div className="bento-card">
      <div style={{ marginBottom: "16px" }}>
        <h3
          style={{
            margin: 0,
            fontFamily: "'IBM Plex Sans', -apple-system, sans-serif",
            fontSize: "1.05rem",
            fontWeight: 500,
            color: "#ffffff",
          }}
        >
          Zero-Decryption Protocol Parsing
        </h3>
        <p style={{ margin: "3px 0 0", fontFamily: "'IBM Plex Sans', sans-serif", fontSize: "0.8rem", color: "#a1a1aa" }}>
          Inspects transport layer headers and cleartext handshake SNI without TLS termination.
        </p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        {records.map((r, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              padding: "9px 12px",
              background: "rgba(18, 18, 21, 0.8)",
              border: `1px solid ${r.status === "flag" ? "rgba(245, 158, 11, 0.3)" : "rgba(255, 255, 255, 0.06)"}`,
              borderRadius: "6px",
            }}
          >
            <span
              style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: "0.68rem",
                fontWeight: 500,
                padding: "2px 6px",
                background: r.type.startsWith("TLS") ? "rgba(124, 58, 237, 0.12)" : "rgba(56, 189, 248, 0.1)",
                border: `1px solid ${r.type.startsWith("TLS") ? "rgba(139, 92, 246, 0.28)" : "rgba(56, 189, 248, 0.25)"}`,
                borderRadius: "3px",
                color: r.type.startsWith("TLS") ? "#c084fc" : "#7dd3fc",
                minWidth: "56px",
                textAlign: "center",
              }}
            >
              {r.type}
            </span>
            <span
              style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: "0.78rem",
                color: "#e4e4e7",
                flex: 1,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {r.value}
            </span>
            <span style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontSize: "0.72rem", color: r.status === "flag" ? "#fbbf24" : "#71717a" }}>
              {r.detail}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ──────────────────────────────────────────────
   Card 4: Capture Ingestion Gatekeeper
   ─────────────────────────────────────────────── */
function CaptureGateCard() {
  const [validating, setValidating] = useState(false);
  const [validated, setValidated] = useState(false);

  const runValidation = () => {
    setValidated(false);
    setValidating(true);
    setTimeout(() => {
      setValidating(false);
      setValidated(true);
    }, 1800);
  };

  const checks = [
    { label: "Magic Bytes Verification (pcap/pcapng)", pass: validated },
    { label: "Filesize Bounds Guard (≤ 2.0 GB)", pass: validated },
    { label: "Path Traversal & Symlink Check", pass: validated },
    { label: "SHA-256 Forensic Integrity Hash", pass: validated },
  ];

  return (
    <div className="bento-card">
      <div style={{ marginBottom: "16px" }}>
        <h3
          style={{
            margin: 0,
            fontFamily: "'IBM Plex Sans', -apple-system, sans-serif",
            fontSize: "1.05rem",
            fontWeight: 500,
            color: "#ffffff",
          }}
        >
          Capture Ingestion Gatekeeper
        </h3>
        <p style={{ margin: "3px 0 0", fontFamily: "'IBM Plex Sans', sans-serif", fontSize: "0.8rem", color: "#a1a1aa" }}>
          Deterministic pre-validation prevents malformed parser exploits before file parsing.
        </p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginBottom: "14px" }}>
        {checks.map((c, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "8px 12px",
              background: "rgba(18, 18, 21, 0.8)",
              border: "1px solid rgba(255, 255, 255, 0.06)",
              borderRadius: "6px",
            }}
          >
            <span style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontSize: "0.78rem", color: "#d4d4d8" }}>
              {c.label}
            </span>
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: "0.72rem" }}>
              {c.pass ? (
                <span style={{ color: "#34d399" }}>PASSED</span>
              ) : validating ? (
                <span style={{ color: "#fbbf24" }}>CHECKING...</span>
              ) : (
                <span style={{ color: "#71717a" }}>STANDBY</span>
              )}
            </span>
          </div>
        ))}
      </div>

      <button
        onClick={runValidation}
        disabled={validating}
        style={{
          width: "100%",
          padding: "9px 16px",
          background: validated ? "rgba(52, 211, 153, 0.12)" : "rgba(255, 255, 255, 0.05)",
          border: `1px solid ${validated ? "rgba(52, 211, 153, 0.3)" : "rgba(255, 255, 255, 0.1)"}`,
          borderRadius: "6px",
          color: validated ? "#34d399" : "#e4e4e7",
          fontFamily: "'IBM Plex Sans', sans-serif",
          fontSize: "0.82rem",
          fontWeight: 500,
          cursor: "pointer",
          transition: "all 0.15s ease",
        }}
      >
        {validating ? "Running Verification..." : validated ? "Capture Sealed with SHA-256" : "Run Ingestion Integrity Check"}
      </button>
    </div>
  );
}

/* ──────────────────────────────────────────────
   BentoFeatures Section Assembler
   ─────────────────────────────────────────────── */
export function BentoFeatures() {
  return (
    <section
      id="features"
      style={{
        position: "relative",
        backgroundColor: "#18181b",
        borderTop: "1px solid rgba(255, 255, 255, 0.08)",
        padding: "96px 48px",
      }}
    >
      <div style={{ maxWidth: 1080, margin: "0 auto" }}>
        {/* Section Header */}
        <div style={{ marginBottom: "48px" }}>
          <div
            style={{
              fontFamily: "'IBM Plex Sans', sans-serif",
              fontSize: "0.8rem",
              fontWeight: 600,
              color: "#c084fc",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              marginBottom: "8px",
            }}
          >
            ARCHITECTURE SPECIFICATION
          </div>
          <h2
            style={{
              fontFamily: "'IBM Plex Sans', -apple-system, sans-serif",
              fontSize: "clamp(2rem, 3.8vw, 2.8rem)",
              fontWeight: 500,
              letterSpacing: "-0.03em",
              color: "#ffffff",
              margin: 0,
            }}
          >
            Passive observation with cryptographic provenance
          </h2>
          <p
            style={{
              fontFamily: "'IBM Plex Sans', sans-serif",
              fontSize: "1.05rem",
              color: "#a1a1aa",
              maxWidth: 620,
              marginTop: "12px",
              lineHeight: 1.6,
            }}
          >
            Every packet transition is observable and verifiable. Zero byte mutation, zero inline traffic delay, zero telemetry leakage.
          </p>
        </div>

        {/* 2-column Bento Grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, 1fr)",
            gap: "20px",
          }}
        >
          <FlowAssemblerCard />
          <DualConfidenceCard />
          <DnsTlsCard />
          <CaptureGateCard />
        </div>
      </div>
    </section>
  );
}
