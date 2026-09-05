"""Validated alert creation, severity, and deduplication."""

from custodian.alerts.builder import build_alert
from custodian.alerts.dedupe import AlertDeduplicator

__all__ = ["AlertDeduplicator", "build_alert"]
