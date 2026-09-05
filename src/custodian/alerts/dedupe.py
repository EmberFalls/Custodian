"""Short-lived alert deduplication for streaming replay."""

from __future__ import annotations

from collections import OrderedDict
from datetime import timedelta

from custodian.core.enums import AlertStatus
from custodian.core.schemas import AlertRecord


def _max_optional(first: float | None, second: float | None) -> float | None:
    values = [value for value in (first, second) if value is not None]
    return max(values) if values else None


class AlertDeduplicator:
    def __init__(self, cooldown_seconds: int = 60, max_entries: int = 2000) -> None:
        self.cooldown = timedelta(seconds=cooldown_seconds)
        self.max_entries = max_entries
        self._seen = OrderedDict()

    @staticmethod
    def _key(alert: AlertRecord) -> tuple[str, str, str, str, str]:
        return (
            alert.threat_class.value,
            str(alert.source.ip) if alert.source else "",
            str(alert.destination.ip) if alert.destination else "",
            alert.detector_id,
            alert.decision.value,
        )

    def merge(self, alert: AlertRecord) -> tuple[AlertRecord, bool]:
        """Return an idempotent lifecycle update and whether it is a new alert."""

        key = self._key(alert)
        previous = self._seen.get(key)
        if previous and alert.timestamp - previous.timestamp < self.cooldown:
            merged = previous.model_copy(
                update={
                    "timestamp": max(previous.timestamp, alert.timestamp),
                    "last_seen": max(
                        previous.last_seen or previous.timestamp,
                        alert.last_seen or alert.timestamp,
                    ),
                    "occurrence_count": previous.occurrence_count + 1,
                    "calibrated_confidence": max(
                        previous.calibrated_confidence, alert.calibrated_confidence
                    ),
                    "threat_confidence": _max_optional(
                        previous.threat_confidence, alert.threat_confidence
                    ),
                    "observation_confidence": _max_optional(
                        previous.observation_confidence, alert.observation_confidence
                    ),
                    "evidence": {**previous.evidence, **alert.evidence},
                    "available_evidence": tuple(
                        dict.fromkeys(previous.available_evidence + alert.available_evidence)
                    ),
                    "missing_evidence": tuple(
                        name
                        for name in dict.fromkeys(
                            previous.missing_evidence + alert.missing_evidence
                        )
                        if name not in set(previous.available_evidence + alert.available_evidence)
                    ),
                    "limitations": tuple(dict.fromkeys(previous.limitations + alert.limitations)),
                    "total_pipeline_latency_ms": max(
                        previous.total_pipeline_latency_ms,
                        alert.total_pipeline_latency_ms,
                    ),
                    "stage_timings_ms": {
                        **previous.stage_timings_ms,
                        **alert.stage_timings_ms,
                    },
                }
            )
            self._seen[key] = merged
            self._seen.move_to_end(key)
            return merged, False
        self._seen[key] = alert
        self._seen.move_to_end(key)
        while len(self._seen) > self.max_entries:
            self._seen.popitem(last=False)
        return alert, True

    def accept(self, alert: AlertRecord) -> bool:
        """Compatibility wrapper for callers that only need the new/repeat result."""

        _, is_new = self.merge(alert)
        return is_new

    def set_status(self, alert_id: str, status: AlertStatus) -> None:
        """Keep analyst lifecycle state when a repeated finding is merged later."""

        for key, alert in self._seen.items():
            if alert.alert_id == alert_id:
                self._seen[key] = alert.model_copy(update={"status": status})
                return

    def reset(self) -> None:
        self._seen.clear()
