import { Activity, Database, Radio, RadioTower } from "lucide-react";
import { useDashboard } from "../../context/DashboardTelemetryContext";
import type { KafkaHealth, LiveCaptureHealth, ServiceHealth } from "../../types";

function serviceTone(status?: string) {
  if (status === "ready" || status === "capturing") return "clean";
  if (status === "degraded" || status === "unavailable") return "warning";
  return "info";
}

function HealthBadge({ status }: { status?: string }) {
  return <span className={`shad-badge shad-badge--${serviceTone(status)}`}><span className="shad-badge__dot" />{status?.toUpperCase() ?? "UNKNOWN"}</span>;
}

export function PipelineServicesPanel() {
  const { runtime } = useDashboard();
  const readiness = runtime.readiness?.components;
  const kafka = runtime.diagnostics?.kafka ?? readiness?.kafka as KafkaHealth | undefined;
  const redis = readiness?.redis as ServiceHealth | undefined;
  const capture = runtime.diagnostics?.live_capture ?? readiness?.live_capture as LiveCaptureHealth | undefined;
  const captureSummary = capture?.running
    ? `Capturing on ${capture.selected_interface ?? "selected interface"}`
    : capture?.status === "ready"
      ? "Backend available · capture is stopped"
      : capture?.reason ?? "Capture backend status is not available";

  return (
    <section className="shad-services-panel" aria-label="Pipeline service health">
      <header className="shad-services-panel__heading">
        <div>
          <div className="shad-kicker">RUNTIME SERVICES</div>
          <h2>Pipeline connectivity</h2>
        </div>
        <span className="shad-services-panel__note">Status only · configure services in backend settings, then restart the API</span>
      </header>
      <div className="shad-services-grid">
        <article className="shad-service-card">
          <div className="shad-service-card__icon"><RadioTower size={16} /></div>
          <div className="shad-service-card__main">
            <div className="shad-service-card__title">Kafka event pipeline <HealthBadge status={kafka?.status} /></div>
            <p>{kafka?.enabled ? "Optional event bus enabled" : kafka?.status === "disabled" ? "Disabled · local processing remains active" : "Checking configured event bus"}</p>
            <div className="shad-service-card__details">
              <span>Producer <b>{kafka?.producer ?? "—"}</b></span>
              <span>Consumer <b>{kafka?.consumer ?? "—"}</b></span>
              <span>Backlog <b>{kafka?.queue_backlog ?? 0}</b></span>
              <span>Dead letters <b>{kafka?.dead_letter_count ?? 0}</b></span>
            </div>
            {kafka?.error ? <div className="shad-service-card__error">{kafka.error}</div> : null}
          </div>
        </article>

        <article className="shad-service-card">
          <div className="shad-service-card__icon"><Database size={16} /></div>
          <div className="shad-service-card__main">
            <div className="shad-service-card__title">Redis live state <HealthBadge status={redis?.status} /></div>
            <p>{redis?.status === "disabled" ? "Disabled · dashboard reads runtime state directly" : redis?.reason ?? "Short-lived dashboard cache health"}</p>
            <div className="shad-service-card__details">
              <span>Role <b>Dashboard cache</b></span>
              <span>Durable records <b>PostgreSQL</b></span>
            </div>
          </div>
        </article>

        <article className="shad-service-card">
          <div className="shad-service-card__icon"><Radio size={16} /></div>
          <div className="shad-service-card__main">
            <div className="shad-service-card__title">Passive interface capture <HealthBadge status={capture?.status} /></div>
            <p>{captureSummary}</p>
            <div className="shad-service-card__details">
              <span>Backend <b>{capture?.backend ?? "Npcap / libpcap"}</b></span>
              <span>Mode <b>Explicit selection</b></span>
              <span>Network return path <b>None</b></span>
            </div>
          </div>
        </article>
      </div>
      <div className="shad-services-panel__footnote"><Activity size={13} /> Kafka: <code>configs/kafka.local.yaml</code> · Redis: <code>configs/redis.local.yaml</code>. Both are optional; live capture requires explicit interface selection in the ingest controls.</div>
    </section>
  );
}
