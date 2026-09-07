import { CustodianShieldIcon } from "./icons/CustodianShieldIcon";

const FOOTER_LINKS = {
  Architecture: ["Ingestion Pipeline", "5-Tuple Flow Engine", "Feature Extractor", "Decision Fusion"],
  Detectors: ["Statistical Behavioral", "DNS Tunneling", "TLS / QUIC SNI", "Evidence Provenance"],
  Documentation: ["System Specification", "Data Governance", "Threat Model", "Audit Log"],
  Security: ["Localhost-Only Socket", "Zero Payload Storage", "No Packet Mutation", "Model Approval"],
};

export function LandingFooter() {
  return (
    <footer
      style={{
        backgroundColor: "#18181b",
        borderTop: "1px solid rgba(255, 255, 255, 0.08)",
        padding: "72px 48px 40px",
      }}
    >
      <div
        style={{
          maxWidth: 1080,
          margin: "0 auto",
        }}
      >
        {/* Top: Logo + privacy badge */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: "32px",
            flexWrap: "wrap",
            marginBottom: "56px",
            paddingBottom: "40px",
            borderBottom: "1px solid rgba(255, 255, 255, 0.07)",
          }}
        >
          {/* Brand */}
          <div style={{ maxWidth: 360 }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
              <CustodianShieldIcon size={26} />
              <span
                style={{
                  fontFamily: "'IBM Plex Sans', -apple-system, sans-serif",
                  fontSize: "1.15rem",
                  fontWeight: 600,
                  color: "#ffffff",
                  letterSpacing: "-0.03em",
                }}
              >
                custodian
              </span>
            </div>
            <p
              style={{
                fontFamily: "'IBM Plex Sans', sans-serif",
                fontSize: "0.88rem",
                color: "#a1a1aa",
                lineHeight: 1.6,
                margin: "0 0 20px",
              }}
            >
              Local-first, passive network intelligence and threat forensics. Continuous flow reconstruction and statistical feature inference without cloud reliance.
            </p>

            {/* Privacy badge */}
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "6px 12px",
                background: "rgba(52, 211, 153, 0.08)",
                border: "1px solid rgba(52, 211, 153, 0.25)",
                borderRadius: "6px",
              }}
            >
              <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#34d399" }} />
              <span style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontSize: "0.76rem", color: "#6ee7b7" }}>
                Localhost Execution · Zero Ingress Telemetry
              </span>
            </div>
          </div>

          {/* Links grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 150px)", gap: "24px" }}>
            {Object.entries(FOOTER_LINKS).map(([category, links]) => (
              <div key={category}>
                <h4
                  style={{
                    fontFamily: "'IBM Plex Sans', sans-serif",
                    fontSize: "0.72rem",
                    fontWeight: 600,
                    letterSpacing: "0.06em",
                    textTransform: "uppercase",
                    color: "#71717a",
                    margin: "0 0 14px",
                  }}
                >
                  {category}
                </h4>
                <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: "10px" }}>
                  {links.map((link) => (
                    <li key={link}>
                      <a
                        href="#"
                        style={{
                          fontFamily: "'IBM Plex Sans', sans-serif",
                          fontSize: "0.84rem",
                          color: "#a1a1aa",
                          textDecoration: "none",
                          transition: "color 0.15s ease",
                        }}
                        onMouseEnter={(e) => ((e.target as HTMLElement).style.color = "#ffffff")}
                        onMouseLeave={(e) => ((e.target as HTMLElement).style.color = "#a1a1aa")}
                      >
                        {link}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom copyright */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "16px",
          }}
        >
          <span
            style={{
              fontFamily: "'IBM Plex Sans', sans-serif",
              fontSize: "0.78rem",
              color: "#71717a",
            }}
          >
            © 2026 Custodian · Passive link observation · Open source architecture
          </span>
          <div style={{ display: "flex", gap: "24px" }}>
            {["GitHub", "Documentation", "MIT License"].map((l) => (
              <a
                key={l}
                href="#"
                style={{
                  fontFamily: "'IBM Plex Sans', sans-serif",
                  fontSize: "0.78rem",
                  color: "#71717a",
                  textDecoration: "none",
                  transition: "color 0.15s",
                }}
                onMouseEnter={(e) => ((e.target as HTMLElement).style.color = "#a1a1aa")}
                onMouseLeave={(e) => ((e.target as HTMLElement).style.color = "#71717a")}
              >
                {l}
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}
