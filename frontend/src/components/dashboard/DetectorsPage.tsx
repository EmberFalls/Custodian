import type { useRuntimeTelemetry } from "../../hooks/useRuntimeTelemetry";
import { StatusBadge } from "../Visuals";

const coverage = [
  ["DDoS", "behaviour", "Rate + target concentration"],
  ["C2", "behaviour", "Recurrence + periodicity"],
  ["Recon", "behaviour", "Destination + port diversity"],
  ["Exfiltration", "behaviour", "Directional volume + comparison window"],
  ["DGA", "dns_dga", "DNS lexical features"],
  ["DNS tunnel", "dns", "Lexical + query frequency"],
  ["Malicious encrypted session", "tls_quic", "Observable handshake and flow metadata"],
] as const;

const detectorLabels: Record<string, string> = {
  behaviour: "BEHAVIOUR",
  dns: "DNS",
  dns_dga: "DNS DGA",
  tls_quic: "TLS / QUIC",
};

interface DetectorsPageProps {
  runtime: ReturnType<typeof useRuntimeTelemetry>;
}

export function DetectorsPage({ runtime }: DetectorsPageProps) {
  const detectors = runtime.detectors;
  const activeDetectors = detectors.filter((d) => d.enabled).length;
  const coreComponents = runtime.readiness?.components
    ? Object.entries(runtime.readiness.components).filter(([name]) => !["models", "inputs"].includes(name))
    : [];

  return (
    <div className="dash-page">
      {/* Detector family cards */}
      <section className="panel detector-group">
        <div className="panel__heading">
          <div>
            <div className="eyebrow">LOCAL MODEL RUNTIME</div>
            <h2>Detector families</h2>
          </div>
          <span className="muted font-mono">{activeDetectors} / {detectors.length} loaded</span>
        </div>
        <div className="detector-cards">
          {detectors.map((d) => (
            <article className="detector-card" key={d.id}>
              <div>
                <span className="eyebrow">{detectorLabels[d.id] ?? d.id} MODEL</span>
                <StatusBadge label={d.status} tone={d.enabled ? "good" : "neutral"} />
              </div>
              <strong style={{ fontSize: "1.05rem" }}>{d.model_version ?? "No approved artifact"}</strong>
              <p>
                {d.enabled
                  ? `${d.schema_version} · ${d.classes.join(" · ")}`
                  : d.reason ?? "No complete model artifact is available."}
              </p>
              <div className="detector-card__meta font-mono">
                <span>Load gate: <strong>{d.artifact_trusted ? "OPEN (LOCAL DEMO)" : "BLOCKED"}</strong></span>
                <span>Schema: <strong>{d.schema_version}</strong></span>
                <span>Support: <strong>{d.distribution_support}</strong></span>
              </div>
              <div className="detector-card__evidence">
                <div className="detector-card__ev-label font-mono">Required evidence:</div>
                <div className="detector-card__ev-list font-mono">
                  {d.required_evidence.length > 0
                    ? d.required_evidence.join(", ")
                    : "TLS or QUIC metadata"}
                </div>
              </div>
              <div className="detector-card__evidence">
                <div className="detector-card__ev-label font-mono">Available evidence:</div>
                <div className="detector-card__ev-list font-mono">
                  {d.available_evidence.length > 0
                    ? d.available_evidence.join(", ")
                    : "None currently observed"}
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* Diagnostics & Readiness */}
      <section className="panel dash-diagnostics">
        <div className="panel__heading">
          <div>
            <div className="eyebrow">HONEST COMPONENT HEALTH</div>
            <h2>Readiness and diagnostics</h2>
          </div>
          <StatusBadge
            label={runtime.readiness?.status?.toUpperCase() ?? "UNAVAILABLE"}
            tone={runtime.readiness?.status === "ready" ? "good" : "warning"}
          />
        </div>
        <div className="diagnostic-grid">
          {coreComponents.map(([name, raw]) => {
            const comp = raw as { status?: string; reason?: string | null };
            return (
              <article key={name}>
                <strong>{name.replaceAll("_", " ")}</strong>
                <StatusBadge
                  label={(comp.status ?? "unavailable").toUpperCase()}
                  tone={comp.status === "ready" ? "good" : "warning"}
                />
                <p>{comp.reason ?? "No limitation reported."}</p>
              </article>
            );
          })}
        </div>

        <h3 style={{ marginTop: "24px" }}>Passive input adapters</h3>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Input Adapter</th>
                <th>Status</th>
                <th>Network interface opened</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {(runtime.diagnostics?.inputs ?? []).map((input) => (
                <tr key={input.source_type}>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      <span className="row-icon-badge row-icon-badge--teal" style={{ width: "32px", height: "32px", fontSize: "0.76rem" }}>
                        IN
                      </span>
                      <span className="font-mono" style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                        {input.source_type.replaceAll("_", " ")}
                      </span>
                    </div>
                  </td>
                  <td>
                    <StatusBadge
                      label={input.status.toUpperCase()}
                      tone={input.status === "ready" ? "good" : "neutral"}
                    />
                  </td>
                  <td className="font-mono">
                    <StatusBadge
                      label={input.opens_network_interface ? "YES (TRANSMIT)" : "NO (PASSIVE)"}
                      tone={input.opens_network_interface ? "danger" : "good"}
                    />
                  </td>
                  <td>{input.reason ?? "Approved local read-only adapter"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="panel-note">
          Routing abstentions: {runtime.diagnostics?.routing.length ?? 0}. Model load failures are
          isolated by family and never replaced with hard-coded threat rules.
        </p>
      </section>

      {/* Coverage matrix */}
      <section className="panel dash-coverage">
        <div className="panel__heading">
          <div>
            <div className="eyebrow">STANDARDIZED THREAT SPECIFICATION</div>
            <h2>Defensible capability matrix</h2>
          </div>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Threat Outcome</th>
                <th>Responsible detector</th>
                <th>Required evidence</th>
                <th>Current status</th>
                <th>Distribution support</th>
              </tr>
            </thead>
            <tbody>
              {coverage.map(([threat, model, evidence]) => {
                const detector = detectors.find((d) => d.id === model);
                const threatTone =
                  model === "behaviour"
                    ? "row-icon-badge--purple"
                    : model.startsWith("dns")
                    ? "row-icon-badge--teal"
                    : "row-icon-badge--pink";

                return (
                  <tr key={threat}>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        <span className={`row-icon-badge ${threatTone}`}>
                          {threat.charAt(0)}
                        </span>
                        <strong style={{ color: "var(--text-primary)" }}>{threat}</strong>
                      </div>
                    </td>
                    <td className="font-mono">
                      <span className="tag-endpoint">{model.replaceAll("_", " ")}</span>
                    </td>
                    <td>{evidence}</td>
                    <td>
                      <StatusBadge
                        label={detector?.status ?? "UNAVAILABLE"}
                        tone={detector?.enabled ? "good" : "neutral"}
                      />
                    </td>
                    <td className="font-mono">
                      <span className="tag-endpoint">{detector?.distribution_support ?? "unavailable"}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="panel-note">
          All seven outcomes are defined by the Custodian contract. They remain unavailable until a
          defensible dataset mapping, isolated training, calibration, held-out evaluation, and
          trusted artifact exist.
        </p>
      </section>
    </div>
  );
}
