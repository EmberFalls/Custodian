import React, { useMemo, useState, useEffect, useRef } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Search,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  ArrowUp
} from "lucide-react";
import { useDashboard } from "../../context/DashboardTelemetryContext";
import type { AlertRecord } from "../../types";
import { formatEndpoint, formatTime } from "../../runtime";

export function IncidentsTable() {
  const { runtime, selectedAlert, setSelectedAlert } = useDashboard();
  const alerts = runtime.alerts || [];

  const [activeFilter, setActiveFilter] = useState<"ALL" | "CRITICAL" | "SUSPICIOUS" | "CLEAN">("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [page, setPage] = useState(1);
  const rowsPerPage = 8;

  // Track stream stability
  const [displayedAlerts, setDisplayedAlerts] = useState<AlertRecord[]>(alerts);
  const [unseenAlertsCount, setUnseenAlertsCount] = useState(0);
  const prevAlertsLengthRef = useRef(alerts.length);

  // Freeze / Streaming Logic
  const isInteracting = searchQuery.trim().length > 0 || page > 1 || selectedAlert !== null;

  useEffect(() => {
    if (!isInteracting) {
      // Live stream mode: automatically update table
      setDisplayedAlerts(alerts);
      setUnseenAlertsCount(0);
    } else {
      // Freeze mode: hold table stable and increment unseen badge
      const diff = alerts.length - displayedAlerts.length;
      if (diff > 0) {
        setUnseenAlertsCount(diff);
      }
    }
    prevAlertsLengthRef.current = alerts.length;
  }, [alerts, isInteracting, displayedAlerts.length]);

  const handleApplyLatestStream = () => {
    setDisplayedAlerts(alerts);
    setUnseenAlertsCount(0);
    setPage(1);
  };

  // Filter & Search
  const filteredAlerts = useMemo(() => {
    return displayedAlerts.filter((alert) => {
      // Severity Filter
      if (activeFilter === "CRITICAL") {
        if (alert.decision !== "ACCEPT" && alert.severity !== "CRITICAL" && alert.severity !== "HIGH") return false;
      } else if (activeFilter === "SUSPICIOUS") {
        if (alert.decision !== "UNKNOWN_SUSPICIOUS" && alert.severity !== "MEDIUM") return false;
      } else if (activeFilter === "CLEAN") {
        if (alert.decision !== "INSUFFICIENT_EVIDENCE" && alert.severity !== "LOW" && alert.severity !== "INFO") return false;
      }

      // Search Query
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesId = alert.alert_id.toLowerCase().includes(query);
        const matchesType = (alert.threat_class || alert.detector_id || "").toLowerCase().includes(query);
        const matchesSrc = (alert.source?.ip || "").toLowerCase().includes(query);
        const matchesDst = (alert.destination?.ip || "").toLowerCase().includes(query);
        return matchesId || matchesType || matchesSrc || matchesDst;
      }
      return true;
    }).sort((left, right) => {
      const leftTime = Date.parse(left.timestamp);
      const rightTime = Date.parse(right.timestamp);
      return (Number.isFinite(rightTime) ? rightTime : 0) - (Number.isFinite(leftTime) ? leftTime : 0);
    });
  }, [displayedAlerts, activeFilter, searchQuery]);

  // Pagination
  const totalPages = Math.max(1, Math.ceil(filteredAlerts.length / rowsPerPage));
  const paginatedAlerts = useMemo(() => {
    const start = (page - 1) * rowsPerPage;
    return filteredAlerts.slice(start, start + rowsPerPage);
  }, [filteredAlerts, page, rowsPerPage]);

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedIds(new Set(paginatedAlerts.map((a) => a.alert_id)));
    } else {
      setSelectedIds(new Set());
    }
  };

  const handleToggleSelect = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedIds(next);
  };

  return (
    <div className="shad-table-container anim-fade-up anim-delay-3">
      {/* Table Toolbar */}
      <div className="shad-table-toolbar">
        {/* Filter Tabs */}
        <div className="shad-segmented-control" role="tablist" aria-label="Incident Severity Filters">
          <button
            onClick={() => { setActiveFilter("ALL"); setPage(1); }}
            className={`shad-segment-btn ${activeFilter === "ALL" ? "is-active" : ""}`}
          >
            All Incidents ({alerts.length})
          </button>
          <button
            onClick={() => { setActiveFilter("CRITICAL"); setPage(1); }}
            className={`shad-segment-btn ${activeFilter === "CRITICAL" ? "is-active" : ""}`}
          >
            Critical Attacks
          </button>
          <button
            onClick={() => { setActiveFilter("SUSPICIOUS"); setPage(1); }}
            className={`shad-segment-btn ${activeFilter === "SUSPICIOUS" ? "is-active" : ""}`}
          >
            Suspicious
          </button>
          <button
            onClick={() => { setActiveFilter("CLEAN"); setPage(1); }}
            className={`shad-segment-btn ${activeFilter === "CLEAN" ? "is-active" : ""}`}
          >
            Insufficient Evidence
          </button>
        </div>

        {/* Search Bar */}
        <div className="shad-table-search">
          <Search size={14} className="text-zinc-500" />
          <input
            type="text"
            placeholder="Search by IP, Alert ID, Attack signature..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setPage(1);
            }}
            aria-label="Search incidents"
          />
        </div>
      </div>

      {/* Floating Live Stream Notification */}
      {unseenAlertsCount > 0 && (
        <div style={{ display: "flex", justifyContent: "center", padding: "10px 0" }}>
          <button onClick={handleApplyLatestStream} className="shad-live-stream-pill">
            <ArrowUp size={13} />
            {unseenAlertsCount} new security incident{unseenAlertsCount > 1 ? "s" : ""} detected — Click to update feed
          </button>
        </div>
      )}

      {/* Table */}
      <div className="shad-table-wrapper">
        <table className="shad-table">
          <thead>
            <tr>
              <th style={{ width: "40px" }}>
                <input
                  type="checkbox"
                  checked={paginatedAlerts.length > 0 && selectedIds.size === paginatedAlerts.length}
                  onChange={handleSelectAll}
                  aria-label="Select all rows"
                />
              </th>
              <th>INCIDENT / ATTACK TYPE</th>
              <th>SEVERITY</th>
              <th>SOURCE ➔ TARGET</th>
              <th>DETECTOR RULE</th>
              <th>CONFIDENCE</th>
              <th>TIME</th>
              <th style={{ textAlign: "right" }}>ACTIONS</th>
            </tr>
          </thead>
          <tbody>
            {paginatedAlerts.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ textAlign: "center", padding: "48px 20px" }}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "10px" }}>
                    <ShieldCheck size={32} style={{ color: "#10b981" }} />
                    <span style={{ fontSize: "0.9rem", fontWeight: 600, color: "#f4f4f5" }}>
                      {searchQuery ? "No matching incidents found" : "No active security incidents detected"}
                    </span>
                    <span style={{ fontSize: "0.75rem", color: "#71717a" }}>
                      {searchQuery
                        ? "Try clearing your search query or adjusting severity filters."
                        : "Network traffic is currently clean and within baseline thresholds."}
                    </span>
                  </div>
                </td>
              </tr>
            ) : (
              paginatedAlerts.map((alert) => {
                const isCritical = alert.decision === "ACCEPT" || alert.severity === "CRITICAL" || alert.severity === "HIGH";
                const isSuspicious = alert.decision === "UNKNOWN_SUSPICIOUS" || alert.severity === "MEDIUM";
                const isSelected = selectedIds.has(alert.alert_id);

                return (
                  <tr
                    key={alert.alert_id}
                    onClick={() => setSelectedAlert(alert)}
                    style={{
                      background: selectedAlert?.alert_id === alert.alert_id ? "rgba(255, 255, 255, 0.05)" : undefined,
                    }}
                  >
                    <td onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => handleToggleSelect(alert.alert_id)}
                        aria-label={`Select alert ${alert.alert_id}`}
                      />
                    </td>
                    <td>
                      <div style={{ display: "flex", flexDirection: "column" }}>
                        <span style={{ fontWeight: 600, color: "#f4f4f5", textTransform: "capitalize" }}>
                          {alert.threat_class || alert.detector_id || "Network Anomaly"}
                        </span>
                        <span style={{ fontSize: "0.7rem", color: "#71717a", fontFamily: "monospace" }}>
                          {alert.alert_id.slice(0, 16)}...
                        </span>
                      </div>
                    </td>
                    <td>
                      {isCritical ? (
                        <span className="shad-badge shad-badge--critical">
                          <span className="shad-badge__dot" />
                          CRITICAL
                        </span>
                      ) : isSuspicious ? (
                        <span className="shad-badge shad-badge--warning">
                          <span className="shad-badge__dot" />
                          SUSPICIOUS
                        </span>
                      ) : (
                        <span className="shad-badge shad-badge--clean">
                          <span className="shad-badge__dot" />
                          LOW RISK
                        </span>
                      )}
                    </td>
                    <td style={{ fontFamily: "monospace", fontSize: "0.75rem", color: "#a1a1aa" }}>
                      {formatEndpoint(alert.source)} ➔ {formatEndpoint(alert.destination)}
                    </td>
                    <td>
                      <span className="shad-badge shad-badge--info">
                        {alert.detector_id || "HeuristicEngine"}
                      </span>
                    </td>
                    <td style={{ fontWeight: 600, color: isCritical ? "#ef4444" : "#f4f4f5" }}>
                      {alert.calibrated_confidence != null ? `${Math.round(alert.calibrated_confidence * 100)}%` : "95%"}
                    </td>
                    <td style={{ color: "#71717a", fontSize: "0.75rem" }}>
                      {formatTime(alert.timestamp)}
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedAlert(alert);
                        }}
                        className="shad-btn shad-btn--outline"
                        style={{ fontSize: "0.72rem", padding: "4px 8px" }}
                      >
                        Inspect <ExternalLink size={12} />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="shad-table-pagination">
        <div>
          {selectedIds.size} of {filteredAlerts.length} row(s) selected.
        </div>
        <div className="shad-pagination-btns">
          <span>
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="shad-btn shad-btn--ghost"
            style={{ padding: "4px 6px", opacity: page === 1 ? 0.3 : 1 }}
            aria-label="Previous Page"
          >
            <ChevronLeft size={14} />
          </button>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="shad-btn shad-btn--ghost"
            style={{ padding: "4px 6px", opacity: page === totalPages ? 0.3 : 1 }}
            aria-label="Next Page"
          >
            <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
