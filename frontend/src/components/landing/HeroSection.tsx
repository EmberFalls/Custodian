import { useEffect, useState, useRef } from "react";
import { BinaryWaveCanvas } from "./BinaryWaveCanvas";

interface HeroSectionProps {
  onLaunchDashboard: () => void;
}

const WORDS = ["captures", "protocols", "traffic", "forensics", "tunnels"];
const SCRAMBLE_CHARS = "010101ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!@#$%^&*";

export function HeroSection({ onLaunchDashboard }: HeroSectionProps) {
  const [wordIndex, setWordIndex] = useState(0);
  const [displayText, setDisplayText] = useState(WORDS[0]);
  const [promptInput, setPromptInput] = useState("");
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Scramble decrypt animation between rotating words (Zeabur style)
  useEffect(() => {
    const nextInterval = setInterval(() => {
      setWordIndex((prev) => {
        const next = (prev + 1) % WORDS.length;
        const targetWord = WORDS[next];
        let frame = 0;
        const maxFrames = 12;

        if (timerRef.current) clearInterval(timerRef.current);

        timerRef.current = setInterval(() => {
          frame++;
          if (frame >= maxFrames) {
            setDisplayText(targetWord);
            if (timerRef.current) clearInterval(timerRef.current);
          } else {
            const scrambled = targetWord
              .split("")
              .map((char, i) => {
                if (frame > (i / targetWord.length) * maxFrames) {
                  return char;
                }
                return SCRAMBLE_CHARS[Math.floor(Math.random() * SCRAMBLE_CHARS.length)];
              })
              .join("");
            setDisplayText(scrambled);
          }
        }, 45);

        return next;
      });
    }, 3800);

    return () => {
      clearInterval(nextInterval);
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const handleInspect = (e: React.FormEvent) => {
    e.preventDefault();
    onLaunchDashboard();
  };

  return (
    <section
      id="hero"
      style={{
        position: "relative",
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        overflow: "hidden",
        backgroundColor: "#18181b", // Zeabur dark base
        padding: "0 64px",
      }}
    >
      {/* ── 3D Topographic Binary Wave Background ── */}
      <BinaryWaveCanvas />

      {/* ── Subtle reading vignette gradient ── */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(ellipse 90% 70% at 20% 50%, rgba(24,24,27,0.85) 0%, rgba(24,24,27,0.4) 65%, transparent 100%)",
          zIndex: 2,
          pointerEvents: "none",
        }}
      />
      {/* Bottom blend gradient */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: "180px",
          background: "linear-gradient(to bottom, transparent, #18181b)",
          zIndex: 2,
          pointerEvents: "none",
        }}
      />

      {/* ── Main Hero Content Box ── */}
      <div
        style={{
          position: "relative",
          zIndex: 10,
          maxWidth: 960,
          paddingTop: "60px",
        }}
      >
        {/* News Announcement Pill */}
        <a
          href="#architecture"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "10px",
            background: "rgba(30, 30, 36, 0.7)",
            border: "1px solid rgba(255, 255, 255, 0.12)",
            padding: "4px 14px 4px 5px",
            borderRadius: "6px",
            textDecoration: "none",
            marginBottom: "32px",
            backdropFilter: "blur(12px)",
            transition: "border-color 0.2s ease, background-color 0.2s ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = "rgba(168, 85, 247, 0.5)";
            e.currentTarget.style.backgroundColor = "rgba(39, 39, 48, 0.85)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.12)";
            e.currentTarget.style.backgroundColor = "rgba(30, 30, 36, 0.7)";
          }}
        >
          <span
            style={{
              background: "rgba(124, 58, 237, 0.22)",
              border: "1px solid rgba(139, 92, 246, 0.4)",
              color: "#c084fc",
              fontFamily: "'IBM Plex Sans', sans-serif",
              fontSize: "0.74rem",
              fontWeight: 600,
              padding: "2px 8px",
              borderRadius: "4px",
            }}
          >
            New
          </span>
          <span
            style={{
              fontFamily: "'IBM Plex Sans', sans-serif",
              fontSize: "0.82rem",
              color: "#e4e4e7",
              fontWeight: 400,
              letterSpacing: "-0.01em",
            }}
          >
            Meet Custodian v0.1.0: Passive Network Intelligence & Threat Forensics
          </span>
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#a1a1aa"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ marginLeft: 2 }}
          >
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </a>

        {/* ── Primary Headline (Zeabur IBM Plex Sans Typography) ── */}
        <h1
          style={{
            fontFamily: "'IBM Plex Sans', 'Geist', -apple-system, sans-serif",
            fontSize: "clamp(2.5rem, 5.8vw, 4.4rem)",
            fontWeight: 500,
            lineHeight: 1.08,
            letterSpacing: "-0.03em",
            color: "#ffffff",
            margin: 0,
          }}
        >
          Passive Network Intelligence
        </h1>

        <div
          style={{
            fontFamily: "'IBM Plex Sans', 'Geist', -apple-system, sans-serif",
            fontSize: "clamp(2.5rem, 5.8vw, 4.4rem)",
            fontWeight: 500,
            lineHeight: 1.08,
            letterSpacing: "-0.03em",
            marginTop: "6px",
          }}
        >
          <span style={{ color: "#a1a1aa" }}>handling all your </span>
          <span
            style={{
              color: "#ffffff",
              display: "inline-block",
              minWidth: "220px",
              fontFamily: displayText !== WORDS[wordIndex] ? "'IBM Plex Mono', monospace" : "'IBM Plex Sans', sans-serif",
            }}
          >
            {displayText}
          </span>
        </div>

        {/* ── Sleek Zeabur Agent Input Bar ── */}
        <form
          onSubmit={handleInspect}
          style={{
            marginTop: "42px",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            background: "rgba(24, 24, 27, 0.75)",
            border: "1px solid rgba(139, 92, 246, 0.35)",
            borderRadius: "8px",
            padding: "8px 10px 8px 16px",
            maxWidth: "520px",
            boxShadow: "0 8px 32px rgba(0, 0, 0, 0.45), 0 0 16px rgba(139, 92, 246, 0.12)",
            backdropFilter: "blur(16px)",
          }}
        >
          <span
            style={{
              fontFamily: "'IBM Plex Sans', sans-serif",
              fontSize: "0.85rem",
              fontWeight: 500,
              color: "#c084fc",
              flexShrink: 0,
            }}
          >
            Ask Custodian
          </span>

          <input
            type="text"
            value={promptInput}
            onChange={(e) => setPromptInput(e.target.value)}
            placeholder="to inspect capture / pcap..."
            style={{
              flex: 1,
              background: "transparent",
              border: "none",
              outline: "none",
              fontFamily: "'IBM Plex Sans', sans-serif",
              fontSize: "0.85rem",
              color: "#e4e4e7",
              caretColor: "#c084fc",
            }}
          />

          {/* Upload icon button */}
          <button
            type="button"
            onClick={onLaunchDashboard}
            title="Upload .pcap or .pcapng"
            style={{
              background: "rgba(255, 255, 255, 0.05)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              borderRadius: "5px",
              width: "32px",
              height: "32px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#a1a1aa",
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = "#ffffff";
              e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.25)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = "#a1a1aa";
              e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.1)";
            }}
          >
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </button>

          {/* Solid Zeabur purple up-arrow action button */}
          <button
            type="submit"
            style={{
              background: "#7c3aed",
              border: "none",
              borderRadius: "5px",
              width: "32px",
              height: "32px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#ffffff",
              cursor: "pointer",
              boxShadow: "0 2px 10px rgba(124, 58, 237, 0.5)",
              transition: "transform 0.15s ease, background-color 0.15s ease",
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
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="12" y1="19" x2="12" y2="5" />
              <polyline points="5 12 12 5 19 12" />
            </svg>
          </button>
        </form>
      </div>
    </section>
  );
}
