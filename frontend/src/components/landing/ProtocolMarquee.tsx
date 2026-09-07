const PROTOCOLS = [
  { label: "IPv4 / IPv6 Protocol Dissection", color: "#38bdf8" },
  { label: "TCP Handshake State Machine", color: "#34d399" },
  { label: "TLS 1.3 Cleartext SNI Parser", color: "#a855f7" },
  { label: "DNS Query Shannon Entropy", color: "#fbbf24" },
  { label: "Bidirectional 5-Tuple Reconstruction", color: "#c084fc" },
  { label: "Zero Payload Decryption Guarantee", color: "#f87171" },
  { label: "SHA-256 Capture Hash Sealing", color: "#34d399" },
  { label: "Deterministic Heuristic Scorer", color: "#38bdf8" },
  { label: "Local-First SQLite Forensics", color: "#a855f7" },
  { label: "QUIC Initial Packet Analysis", color: "#fbbf24" },
];

export function ProtocolMarquee() {
  const items = [...PROTOCOLS, ...PROTOCOLS];

  return (
    <div
      style={{
        width: "100%",
        borderTop: "1px solid rgba(255, 255, 255, 0.08)",
        borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
        backgroundColor: "#18181b",
        padding: "16px 0",
        overflow: "hidden",
        position: "relative",
      }}
    >
      {/* Left/Right Vignettes */}
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          bottom: 0,
          width: "100px",
          background: "linear-gradient(to right, #18181b, transparent)",
          zIndex: 2,
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "absolute",
          right: 0,
          top: 0,
          bottom: 0,
          width: "100px",
          background: "linear-gradient(to left, #18181b, transparent)",
          zIndex: 2,
          pointerEvents: "none",
        }}
      />

      <div
        className="marquee-container"
        style={{
          display: "flex",
          flexDirection: "row",
          alignItems: "center",
          flexWrap: "nowrap",
          width: "max-content",
        }}
      >
        {items.map((item, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "6px 16px",
              marginRight: "10px",
              background: "rgba(255, 255, 255, 0.03)",
              border: "1px solid rgba(255, 255, 255, 0.07)",
              borderRadius: "6px",
              whiteSpace: "nowrap",
              flexShrink: 0,
            }}
          >
            <div
              style={{
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                background: item.color,
                flexShrink: 0,
              }}
            />
            <span
              style={{
                fontFamily: "'IBM Plex Sans', sans-serif",
                fontSize: "0.8rem",
                color: "#a1a1aa",
                fontWeight: 450,
              }}
            >
              {item.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
