import { useState } from "react";
import { CustodianShieldIcon } from "./icons/CustodianShieldIcon";

interface LandingNavbarProps {
  onLaunchDashboard: () => void;
}

export function LandingNavbar({ onLaunchDashboard }: LandingNavbarProps) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 100,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 48px",
        height: "64px",
        backgroundColor: "rgba(24, 24, 27, 0.8)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
      }}
    >
      {/* Brand logo */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "10px",
          cursor: "pointer",
          userSelect: "none",
        }}
        onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
      >
        <CustodianShieldIcon size={26} />
        <span
          style={{
            fontFamily: "'IBM Plex Sans', -apple-system, sans-serif",
            fontWeight: 600,
            fontSize: "1.18rem",
            letterSpacing: "-0.03em",
            color: "#ffffff",
          }}
        >
          custodian
        </span>
      </div>

      {/* Primary navigation links (Zeabur style) */}
      <nav
        className="landing-nav-links"
        style={{
          display: "flex",
          alignItems: "center",
          gap: "28px",
          fontFamily: "'IBM Plex Sans', -apple-system, sans-serif",
          fontSize: "0.88rem",
          fontWeight: 450,
        }}
      >
        <a
          href="#architecture"
          style={{
            color: "#a1a1aa",
            textDecoration: "none",
            display: "flex",
            alignItems: "center",
            gap: "4px",
            transition: "color 0.15s ease",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = "#ffffff")}
          onMouseLeave={(e) => (e.currentTarget.style.color = "#a1a1aa")}
        >
          Platform
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M6 9l6 6 6-6" />
          </svg>
        </a>

        <a
          href="#features"
          style={{
            color: "#a1a1aa",
            textDecoration: "none",
            display: "flex",
            alignItems: "center",
            gap: "4px",
            transition: "color 0.15s ease",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = "#ffffff")}
          onMouseLeave={(e) => (e.currentTarget.style.color = "#a1a1aa")}
        >
          Forensics
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M6 9l6 6 6-6" />
          </svg>
        </a>

        <a
          href="#detectors"
          style={{
            color: "#a1a1aa",
            textDecoration: "none",
            transition: "color 0.15s ease",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = "#ffffff")}
          onMouseLeave={(e) => (e.currentTarget.style.color = "#a1a1aa")}
        >
          Detectors
        </a>

        <a
          href="#docs"
          style={{
            color: "#a1a1aa",
            textDecoration: "none",
            transition: "color 0.15s ease",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = "#ffffff")}
          onMouseLeave={(e) => (e.currentTarget.style.color = "#a1a1aa")}
        >
          Documentation
        </a>
      </nav>

      {/* Right controls: Theme, Language, Launch button */}
      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        {/* Theme pill indicator */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            background: "rgba(255, 255, 255, 0.04)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            borderRadius: "20px",
            padding: "4px 8px",
            color: "#71717a",
          }}
        >
          {/* Moon active */}
          <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" style={{ color: "#a855f7" }}>
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
          </svg>
        </div>

        {/* Solid Zeabur purple CTA */}
        <button
          onClick={onLaunchDashboard}
          style={{
            background: "#7c3aed",
            color: "#ffffff",
            border: "none",
            borderRadius: "6px",
            padding: "7px 16px",
            fontFamily: "'IBM Plex Sans', -apple-system, sans-serif",
            fontSize: "0.85rem",
            fontWeight: 500,
            cursor: "pointer",
            boxShadow: "0 2px 12px rgba(124, 58, 237, 0.45)",
            transition: "all 0.15s ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = "#8b5cf6";
            e.currentTarget.style.transform = "translateY(-1px)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = "#7c3aed";
            e.currentTarget.style.transform = "none";
          }}
        >
          Dashboard
        </button>

        {/* Mobile toggle */}
        <button
          onClick={() => setMenuOpen((v) => !v)}
          className="mobile-menu-btn"
          style={{
            display: "none",
            background: "transparent",
            border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: "5px",
            padding: "6px 8px",
            color: "#a1a1aa",
            cursor: "pointer",
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
      </div>

      {/* Mobile Drawer */}
      {menuOpen && (
        <div
          style={{
            position: "fixed",
            top: "64px",
            left: 0,
            right: 0,
            background: "rgba(24, 24, 27, 0.98)",
            backdropFilter: "blur(20px)",
            borderBottom: "1px solid rgba(255,255,255,0.08)",
            padding: "16px 24px",
            display: "flex",
            flexDirection: "column",
            gap: "14px",
            fontFamily: "'IBM Plex Sans', sans-serif",
          }}
        >
          {["Platform", "Forensics", "Detectors", "Documentation"].map((item) => (
            <a
              key={item}
              href={`#${item.toLowerCase()}`}
              onClick={() => setMenuOpen(false)}
              style={{
                color: "#d4d4d8",
                textDecoration: "none",
                fontSize: "0.95rem",
              }}
            >
              {item}
            </a>
          ))}
        </div>
      )}

      <style>{`
        @media (max-width: 768px) {
          .landing-nav-links { display: none !important; }
          .mobile-menu-btn { display: flex !important; }
        }
      `}</style>
    </header>
  );
}
