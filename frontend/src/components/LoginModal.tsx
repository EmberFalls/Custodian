import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { DemoCredential } from "../types";
import { BinaryWaveCanvas } from "./landing/BinaryWaveCanvas";
import { CustodianShieldIcon } from "./landing/icons/CustodianShieldIcon";

interface LoginModalProps {
  onSuccess?: () => void;
}

export const LoginModal: React.FC<LoginModalProps> = ({ onSuccess }) => {
  const { isAuthModalOpen, closeAuthModal, login, demoCredentials } = useAuth();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("CustodianAdmin2026!");
  const [selectedRole, setSelectedRole] = useState<string>("Admin");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!isAuthModalOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      setError("Please provide both username and access key.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await login(username, password);
      if (onSuccess) {
        onSuccess();
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Invalid credentials. Please verify your security profile.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleSelectProfile = (cred: DemoCredential) => {
    setUsername(cred.username);
    setPassword(cred.password);
    setSelectedRole(cred.role);
    setError(null);
  };

  const roleDescriptions: Record<string, { title: string; desc: string; icon: string }> = {
    Admin: {
      title: "Lead Administrator",
      desc: "Full system rights, model trust approvals & pipeline controls",
      icon: "🛡️",
    },
    Analyst: {
      title: "Incident Analyst",
      desc: "Upload capture files, execute replay & investigate alerts",
      icon: "🔍",
    },
    Auditor: {
      title: "Compliance Auditor",
      desc: "Read-only access to runtime telemetry & forensic reports",
      icon: "👁️",
    },
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 99999,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "rgba(9, 9, 11, 0.88)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        padding: "20px",
      }}
      onClick={closeAuthModal}
    >
      {/* Central Split SaaS Container */}
      <div
        style={{
          width: "100%",
          maxWidth: "980px",
          minHeight: "590px",
          display: "grid",
          gridTemplateColumns: "1.08fr 1fr",
          backgroundColor: "#121215",
          border: "1px solid rgba(255, 255, 255, 0.1)",
          borderRadius: "20px",
          boxShadow: "0 30px 70px -15px rgba(0, 0, 0, 0.85), 0 0 50px rgba(124, 58, 237, 0.16)",
          overflow: "hidden",
          position: "relative",
          animation: "authModalFadeIn 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── LEFT BOX: 3D Topographic Binary Wave & Brand Showcase ── */}
        <div
          style={{
            position: "relative",
            overflow: "hidden",
            backgroundColor: "#18181b",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            padding: "44px 40px",
          }}
        >
          {/* Dynamic 0 and 1 canvas filling the left box */}
          <BinaryWaveCanvas />

          {/* Vignette & color grading gradient overlay */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              background:
                "radial-gradient(ellipse 90% 75% at 30% 35%, rgba(24, 24, 27, 0.42) 0%, rgba(24, 24, 27, 0.86) 80%, rgba(18, 18, 21, 0.96) 100%)",
              pointerEvents: "none",
              zIndex: 2,
            }}
          />

          {/* Foreground Brand Elements */}
          {/* Top: Brand Header */}
          <div style={{ position: "relative", zIndex: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
              <CustodianShieldIcon size={26} />
              <span
                style={{
                  fontFamily: "'IBM Plex Sans', sans-serif",
                  fontWeight: 600,
                  fontSize: "1.2rem",
                  letterSpacing: "-0.02em",
                  color: "#ffffff",
                }}
              >
                custodian
              </span>
              <span
                style={{
                  background: "rgba(124, 58, 237, 0.22)",
                  border: "1px solid rgba(139, 92, 246, 0.4)",
                  color: "#c084fc",
                  fontFamily: "'IBM Plex Mono', monospace",
                  fontSize: "0.7rem",
                  fontWeight: 600,
                  padding: "2px 7px",
                  borderRadius: "4px",
                  letterSpacing: "0.5px",
                }}
              >
                NODE v0.1.0
              </span>
            </div>

            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "3px 10px",
                borderRadius: "20px",
                backgroundColor: "rgba(34, 197, 94, 0.12)",
                border: "1px solid rgba(34, 197, 94, 0.3)",
                fontSize: "0.72rem",
                fontFamily: "'IBM Plex Mono', monospace",
                color: "#4ade80",
              }}
            >
              <span style={{ width: "6px", height: "6px", borderRadius: "50%", backgroundColor: "#4ade80" }} />
              PASSIVE KERNEL ONLINE
            </div>
          </div>

          {/* Middle: Value Proposition */}
          <div style={{ position: "relative", zIndex: 10, margin: "36px 0" }}>
            <h2
              style={{
                fontFamily: "'IBM Plex Sans', -apple-system, sans-serif",
                fontSize: "1.75rem",
                fontWeight: 500,
                lineHeight: 1.22,
                letterSpacing: "-0.03em",
                color: "#ffffff",
                margin: "0 0 12px 0",
              }}
            >
              Passive Network Intelligence & Forensics
            </h2>
            <p
              style={{
                fontFamily: "'IBM Plex Sans', sans-serif",
                fontSize: "0.86rem",
                color: "#a1a1aa",
                lineHeight: 1.6,
                margin: 0,
                maxWidth: "380px",
              }}
            >
              Incrementally analyzes authorized packet captures, reconstructs bidirectional flows, and performs evidence-calibrated threat reasoning with zero outbound network footprint.
            </p>
          </div>

          {/* Bottom: Architecture Badges */}
          <div
            style={{
              position: "relative",
              zIndex: 10,
              display: "flex",
              flexWrap: "wrap",
              gap: "8px",
            }}
          >
            {[
              "Argon2id Salted",
              "Local SQLite Store",
              "Zero Cloud Telemetry",
              "Air-Gapped Capable",
            ].map((badge) => (
              <span
                key={badge}
                style={{
                  fontFamily: "'IBM Plex Mono', monospace",
                  fontSize: "0.7rem",
                  color: "#d4d4d8",
                  backgroundColor: "rgba(255, 255, 255, 0.05)",
                  border: "1px solid rgba(255, 255, 255, 0.08)",
                  borderRadius: "4px",
                  padding: "3px 8px",
                }}
              >
                ● {badge}
              </span>
            ))}
          </div>
        </div>

        {/* ── RIGHT BOX: Enterprise Authentication System ── */}
        <div
          style={{
            backgroundColor: "#111114",
            borderLeft: "1px solid rgba(255, 255, 255, 0.08)",
            padding: "40px 36px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            position: "relative",
          }}
        >
          {/* Close button */}
          <button
            onClick={closeAuthModal}
            title="Close authentication window"
            style={{
              position: "absolute",
              top: "20px",
              right: "20px",
              background: "rgba(255, 255, 255, 0.04)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              borderRadius: "6px",
              color: "#a1a1aa",
              width: "28px",
              height: "28px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "13px",
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = "#ffffff";
              e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.1)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = "#a1a1aa";
              e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.04)";
            }}
          >
            ✕
          </button>

          <div>
            {/* Header */}
            <div style={{ marginBottom: "22px" }}>
              <div
                style={{
                  fontFamily: "'IBM Plex Mono', monospace",
                  fontSize: "0.72rem",
                  fontWeight: 600,
                  letterSpacing: "1px",
                  color: "#c084fc",
                  textTransform: "uppercase",
                  marginBottom: "4px",
                }}
              >
                SECURITY ACCESS GATEWAY
              </div>
              <h3
                style={{
                  fontFamily: "'IBM Plex Sans', sans-serif",
                  fontSize: "1.45rem",
                  fontWeight: 600,
                  color: "#ffffff",
                  letterSpacing: "-0.02em",
                  margin: "0 0 6px 0",
                }}
              >
                Access Console
              </h3>
              <p
                style={{
                  fontFamily: "'IBM Plex Sans', sans-serif",
                  fontSize: "0.82rem",
                  color: "#71717a",
                  margin: 0,
                  lineHeight: 1.4,
                }}
              >
                Select an environment profile or provide authorized credentials to proceed.
              </p>
            </div>

            {/* Profile Selector Cards */}
            <div style={{ marginBottom: "20px" }}>
              <label
                style={{
                  display: "block",
                  fontFamily: "'IBM Plex Sans', sans-serif",
                  fontSize: "0.74rem",
                  fontWeight: 600,
                  letterSpacing: "0.5px",
                  color: "#a1a1aa",
                  textTransform: "uppercase",
                  marginBottom: "8px",
                }}
              >
                Security Profiles
              </label>

              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {demoCredentials.map((cred) => {
                  const isSelected = selectedRole === cred.role;
                  const info = roleDescriptions[cred.role] || {
                    title: cred.display_name,
                    desc: "Authorized account",
                    icon: "🔑",
                  };

                  return (
                    <div
                      key={cred.username}
                      onClick={() => handleSelectProfile(cred)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "8px 12px",
                        borderRadius: "8px",
                        backgroundColor: isSelected ? "rgba(124, 58, 237, 0.14)" : "rgba(255, 255, 255, 0.025)",
                        border: isSelected ? "1px solid rgba(139, 92, 246, 0.5)" : "1px solid rgba(255, 255, 255, 0.06)",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                      onMouseEnter={(e) => {
                        if (!isSelected) {
                          e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.05)";
                          e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.12)";
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!isSelected) {
                          e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.025)";
                          e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.06)";
                        }
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <span style={{ fontSize: "15px" }}>{info.icon}</span>
                        <div>
                          <div
                            style={{
                              fontFamily: "'IBM Plex Sans', sans-serif",
                              fontSize: "0.82rem",
                              fontWeight: 500,
                              color: isSelected ? "#ffffff" : "#d4d4d8",
                            }}
                          >
                            {info.title}
                          </div>
                          <div
                            style={{
                              fontFamily: "'IBM Plex Sans', sans-serif",
                              fontSize: "0.7rem",
                              color: isSelected ? "#c4b5fd" : "#71717a",
                            }}
                          >
                            {info.desc}
                          </div>
                        </div>
                      </div>

                      <div
                        style={{
                          width: "14px",
                          height: "14px",
                          borderRadius: "50%",
                          border: isSelected ? "4px solid #8b5cf6" : "1.5px solid #52525b",
                          backgroundColor: isSelected ? "#ffffff" : "transparent",
                          transition: "all 0.15s ease",
                          flexShrink: 0,
                        }}
                      />
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div
                style={{
                  backgroundColor: "rgba(239, 68, 68, 0.12)",
                  border: "1px solid rgba(239, 68, 68, 0.35)",
                  color: "#fca5a5",
                  padding: "8px 12px",
                  borderRadius: "6px",
                  fontSize: "0.78rem",
                  fontFamily: "'IBM Plex Sans', sans-serif",
                  marginBottom: "14px",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <span>⚠️</span>
                <span>{error}</span>
              </div>
            )}

            {/* Credentials Input Form */}
            <form onSubmit={handleSubmit}>
              <div style={{ marginBottom: "12px" }}>
                <label
                  style={{
                    display: "block",
                    fontFamily: "'IBM Plex Sans', sans-serif",
                    fontSize: "0.74rem",
                    fontWeight: 600,
                    letterSpacing: "0.4px",
                    color: "#a1a1aa",
                    textTransform: "uppercase",
                    marginBottom: "5px",
                  }}
                >
                  Username / ID
                </label>
                <div style={{ position: "relative" }}>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Enter security ID"
                    disabled={submitting}
                    style={{
                      width: "100%",
                      padding: "9px 12px",
                      borderRadius: "6px",
                      backgroundColor: "rgba(24, 24, 27, 0.8)",
                      border: "1px solid rgba(255, 255, 255, 0.12)",
                      color: "#ffffff",
                      fontFamily: "'IBM Plex Sans', sans-serif",
                      fontSize: "0.85rem",
                      outline: "none",
                      boxSizing: "border-box",
                      transition: "border-color 0.15s ease",
                    }}
                    onFocus={(e) => (e.target.style.borderColor = "rgba(139, 92, 246, 0.6)")}
                    onBlur={(e) => (e.target.style.borderColor = "rgba(255, 255, 255, 0.12)")}
                  />
                </div>
              </div>

              <div style={{ marginBottom: "20px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "5px" }}>
                  <label
                    style={{
                      fontFamily: "'IBM Plex Sans', sans-serif",
                      fontSize: "0.74rem",
                      fontWeight: 600,
                      letterSpacing: "0.4px",
                      color: "#a1a1aa",
                      textTransform: "uppercase",
                    }}
                  >
                    Access Key
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{
                      background: "none",
                      border: "none",
                      color: "#71717a",
                      fontSize: "0.72rem",
                      fontFamily: "'IBM Plex Sans', sans-serif",
                      cursor: "pointer",
                      padding: 0,
                    }}
                  >
                    {showPassword ? "Hide key" : "Show key"}
                  </button>
                </div>

                <div style={{ position: "relative" }}>
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    disabled={submitting}
                    style={{
                      width: "100%",
                      padding: "9px 12px",
                      borderRadius: "6px",
                      backgroundColor: "rgba(24, 24, 27, 0.8)",
                      border: "1px solid rgba(255, 255, 255, 0.12)",
                      color: "#ffffff",
                      fontFamily: "'IBM Plex Mono', monospace",
                      fontSize: "0.85rem",
                      outline: "none",
                      boxSizing: "border-box",
                      transition: "border-color 0.15s ease",
                    }}
                    onFocus={(e) => (e.target.style.borderColor = "rgba(139, 92, 246, 0.6)")}
                    onBlur={(e) => (e.target.style.borderColor = "rgba(255, 255, 255, 0.12)")}
                  />
                </div>
              </div>

              {/* Submit CTA */}
              <button
                type="submit"
                disabled={submitting}
                style={{
                  width: "100%",
                  padding: "11px",
                  borderRadius: "6px",
                  background: "#7c3aed",
                  border: "none",
                  color: "#ffffff",
                  fontFamily: "'IBM Plex Sans', -apple-system, sans-serif",
                  fontSize: "0.86rem",
                  fontWeight: 500,
                  cursor: submitting ? "not-allowed" : "pointer",
                  letterSpacing: "0.3px",
                  opacity: submitting ? 0.75 : 1,
                  boxShadow: "0 2px 14px rgba(124, 58, 237, 0.45)",
                  transition: "all 0.15s ease",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "8px",
                }}
                onMouseEnter={(e) => {
                  if (!submitting) {
                    e.currentTarget.style.backgroundColor = "#8b5cf6";
                    e.currentTarget.style.transform = "translateY(-1px)";
                  }
                }}
                onMouseLeave={(e) => {
                  if (!submitting) {
                    e.currentTarget.style.backgroundColor = "#7c3aed";
                    e.currentTarget.style.transform = "none";
                  }
                }}
              >
                {submitting ? (
                  <span>AUTHENTICATING SESSION...</span>
                ) : (
                  <>
                    <span>INITIALIZE CONSOLE ACCESS</span>
                    <span style={{ fontSize: "14px" }}>→</span>
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Footer note */}
          <div
            style={{
              paddingTop: "16px",
              borderTop: "1px solid rgba(255, 255, 255, 0.05)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "6px",
              color: "#52525b",
              fontSize: "0.72rem",
              fontFamily: "'IBM Plex Sans', sans-serif",
              marginTop: "16px",
            }}
          >
            <span>🔒</span>
            <span>Secured via local Argon2id verification · Zero cloud telemetry</span>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes authModalFadeIn {
          from {
            opacity: 0;
            transform: scale(0.96);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }
        @media (max-width: 820px) {
          .auth-modal-card {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  );
};
