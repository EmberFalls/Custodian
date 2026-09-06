import { useState } from "react";

const SCENARIOS = [
  {
    id: "baseline",
    label: "Normal Web Traffic",
    badge: "BASELINE",
    color: "#34d399",
    metrics: { pps: "1,240 pkts/s", flows: "38 flows", confidence: "0.02", verdict: "ACCEPT", throughput: "4.2 MB/s" },
    features: [
      { name: "Flow Payload Entropy", value: 0.18 },
      { name: "Burst Transmission Ratio", value: 0.12 },
      { name: "Inter-Arrival Time Variance", value: 0.09 },
      { name: "Protocol Diversity Score", value: 0.22 },
    ],
    alert: null,
  },
  {
    id: "synflood",
    label: "SYN Flood Reconnaissance",
    badge: "PORT_SCAN",
    color: "#f87171",
    metrics: { pps: "84,200 pkts/s", flows: "4,382 flows", confidence: "0.97", verdict: "THREAT", throughput: "12.8 MB/s" },
    features: [
      { name: "Flow Payload Entropy", value: 0.72 },
      { name: "Burst Transmission Ratio", value: 0.91 },
      { name: "Inter-Arrival Time Variance", value: 0.88 },
      { name: "Protocol Diversity Score", value: 0.06 },
    ],
    alert: "Deterministic trigger fired: TCP SYN-without-ACK ratio exceeds 0.94 across >2000 unique destination ports per second.",
  },
  {
    id: "dns",
    label: "DNS Tunneling Exfiltration",
    badge: "DNS_EXFIL",
    color: "#fbbf24",
    metrics: { pps: "3,840 pkts/s", flows: "129 flows", confidence: "0.89", verdict: "SUSPICIOUS", throughput: "1.1 MB/s" },
    features: [
      { name: "Flow Payload Entropy", value: 0.84 },
      { name: "Burst Transmission Ratio", value: 0.31 },
      { name: "Inter-Arrival Time Variance", value: 0.44 },
      { name: "Protocol Diversity Score", value: 0.41 },
    ],
    alert: "High-entropy subdomain queries detected. Mean Shannon entropy of labels is 4.38 bits/char across 42 consecutive TXT lookups.",
  },
  {
    id: "c2",
    label: "C2 Periodic Beaconing",
    badge: "C2_BEACON",
    color: "#c084fc",
    metrics: { pps: "620 pkts/s", flows: "14 flows", confidence: "0.76", verdict: "SUSPICIOUS", throughput: "0.3 MB/s" },
    features: [
      { name: "Flow Payload Entropy", value: 0.55 },
      { name: "Burst Transmission Ratio", value: 0.24 },
      { name: "Inter-Arrival Time Variance", value: 0.19 },
      { name: "Protocol Diversity Score", value: 0.30 },
    ],
    alert: "Isochronous heartbeat detected. Regular inter-arrival period (T=15.00s ±0.12s) to external IP 185.220.101.5 over 18 cycles.",
  },
];

export function ThreatSandbox() {
  const [active, setActive] = useState(0);
  const scenario = SCENARIOS[active];

  return (
    <section
      id="detectors"
      style={{
        backgroundColor: "#18181b",
        borderTop: "1px solid rgba(255, 255, 255, 0.08)",
        padding: "96px 48px",
      }}
    >
      <div style={{ maxWidth: 1080, margin: "0 auto" }}>
        {/* Section Header */}
        <div style={{ marginBottom: "40px" }}>
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
            DETECTION INFERENCE
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
            Interactive Replay Simulation
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
            Select a sample network traffic profile to examine real-time extraction of statistical features and detector verdicts.
          </p>
        </div>

        {/* Scenario Selection Tabs */}
        <div
          style={{
            display: "flex",
            gap: "8px",
            flexWrap: "nowrap",
            overflowX: "auto",
            marginBottom: "28px",
          }}
        >
          {SCENARIOS.map((s, i) => {
            const isSelected = active === i;
            return (
              <button
                key={s.id}
                onClick={() => setActive(i)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "10px 18px",
                  background: isSelected ? "rgba(124, 58, 237, 0.15)" : "rgba(255, 255, 255, 0.03)",
                  border: `1px solid ${isSelected ? "rgba(168, 85, 247, 0.5)" : "rgba(255, 255, 255, 0.08)"}`,
                  borderRadius: "6px",
                  color: isSelected ? "#ffffff" : "#a1a1aa",
                  fontFamily: "'IBM Plex Sans', sans-serif",
                  fontSize: "0.86rem",
                  fontWeight: 500,
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                <div
                  style={{
                    width: "7px",
                    height: "7px",
                    borderRadius: "50%",
                    backgroundColor: s.color,
                  }}
                />
                <span>{s.label}</span>
                <span
                  style={{
                    fontFamily: "'IBM Plex Mono', monospace",
                    fontSize: "0.68rem",
                    color: s.color,
                    background: "rgba(255, 255, 255, 0.05)",
                    padding: "2px 6px",
                    borderRadius: "3px",
                  }}
                >
                  {s.badge}
                </span>
              </button>
            );
          })}
        </div>

        {/* Simulation Output Dashboard Container */}
        <div
          style={{
            background: "rgba(24, 24, 27, 0.6)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            borderRadius: "8px",
            padding: "32px",
            backdropFilter: "blur(16px)",
          }}
        >
          {/* Top Metric Strip */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: "20px",
              paddingBottom: "24px",
              borderBottom: "1px solid rgba(255, 255, 255, 0.07)",
            }}
          >
            {[
              { label: "PACKET RATE", val: scenario.metrics.pps },
              { label: "OBSERVED FLOWS", val: scenario.metrics.flows },
              { label: "ANOMALY CONFIDENCE", val: scenario.metrics.confidence },
              { label: "FUSION VERDICT", val: scenario.metrics.verdict, highlight: scenario.color },
            ].map((m) => (
              <div key={m.label}>
                <div
                  style={{
                    fontFamily: "'IBM Plex Sans', sans-serif",
                    fontSize: "0.72rem",
                    color: "#71717a",
                    fontWeight: 600,
                    letterSpacing: "0.05em",
                  }}
                >
                  {m.label}
                </div>
                <div
                  style={{
                    fontFamily: "'IBM Plex Mono', monospace",
                    fontSize: "1.25rem",
                    fontWeight: 600,
                    color: m.highlight ?? "#f4f4f5",
                    marginTop: "6px",
                  }}
                >
                  {m.val}
                </div>
              </div>
            ))}
          </div>

          {/* Statistical Feature Vectors */}
          <div style={{ marginTop: "28px" }}>
            <div
              style={{
                fontFamily: "'IBM Plex Sans', sans-serif",
                fontSize: "0.82rem",
                fontWeight: 500,
                color: "#e4e4e7",
                marginBottom: "16px",
              }}
            >
              Extracted CIC-IDS Observable Feature Distributions
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "16px" }}>
              {scenario.features.map((f) => (
                <div
                  key={f.name}
                  style={{
                    background: "rgba(18, 18, 21, 0.8)",
                    border: "1px solid rgba(255, 255, 255, 0.06)",
                    borderRadius: "6px",
                    padding: "12px 16px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                    <span style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontSize: "0.8rem", color: "#a1a1aa" }}>
                      {f.name}
                    </span>
                    <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: "0.8rem", color: "#f4f4f5" }}>
                      {f.value.toFixed(2)}
                    </span>
                  </div>
                  {/* Meter bar */}
                  <div style={{ height: "4px", background: "rgba(255, 255, 255, 0.06)", borderRadius: "2px", overflow: "hidden" }}>
                    <div
                      style={{
                        height: "100%",
                        width: `${Math.min(100, f.value * 100)}%`,
                        background: scenario.color,
                        borderRadius: "2px",
                        transition: "width 0.4s ease",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Alert Evidence Strip if flagged */}
          {scenario.alert && (
            <div
              style={{
                marginTop: "24px",
                padding: "14px 18px",
                background: "rgba(239, 68, 68, 0.06)",
                border: "1px solid rgba(239, 68, 68, 0.25)",
                borderRadius: "6px",
                display: "flex",
                alignItems: "flex-start",
                gap: "12px",
              }}
            >
              <span
                style={{
                  fontFamily: "'IBM Plex Mono', monospace",
                  fontSize: "0.72rem",
                  color: "#f87171",
                  fontWeight: 600,
                  background: "rgba(239, 68, 68, 0.15)",
                  padding: "2px 6px",
                  borderRadius: "3px",
                  flexShrink: 0,
                  marginTop: "1px",
                }}
              >
                PROVENANCE
              </span>
              <span
                style={{
                  fontFamily: "'IBM Plex Sans', sans-serif",
                  fontSize: "0.84rem",
                  color: "#fca5a5",
                  lineHeight: 1.5,
                }}
              >
                {scenario.alert}
              </span>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
